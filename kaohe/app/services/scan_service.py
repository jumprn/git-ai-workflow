import logging
import os
import threading
from collections import Counter
from datetime import datetime, date

from app.extensions import db
from app.models import Project, Member, ScanTask, CommitAIStatus, AIPromptSession
from app.services import git_service

logger = logging.getLogger(__name__)


def start_scan(project_id: int, scan_type: str = 'manual', full_scan: bool = False, app=None) -> ScanTask:
    """Create a scan task and start scanning in background.
    full_scan: if True, clear existing commit cache and rescan all commits (防篡改).
    """
    task = ScanTask(
        project_id=project_id,
        scan_type=scan_type,
        status='pending',
        created_at=datetime.now(),
    )
    db.session.add(task)
    db.session.commit()

    if app is None:
        from flask import current_app
        app = current_app._get_current_object()

    thread = threading.Thread(
        target=_run_scan,
        args=(app, task.id, project_id, full_scan),
        daemon=True,
    )
    thread.start()
    return task


def _run_scan(app, task_id: int, project_id: int, full_scan: bool = False):
    """Background scan worker."""
    with app.app_context():
        task = db.session.get(ScanTask, task_id)
        project = db.session.get(Project, project_id)
        if not task or not project:
            return

        try:
            task.status = 'running'
            task.started_at = datetime.now()
            task.current_phase = '正在准备仓库...'
            db.session.commit()

            _ensure_repo(project, task)
            _check_commits(project, task, full_scan=full_scan)

            task.status = 'completed'
            task.progress = 100
            task.current_phase = '扫描完成'
            task.completed_at = datetime.now()
            project.last_scan_at = datetime.now()
            db.session.commit()

        except Exception as e:
            logger.error(f'Scan failed for project {project_id}: {e}', exc_info=True)
            task.status = 'failed'
            task.message = str(e)
            task.completed_at = datetime.now()
            db.session.commit()


def _ensure_repo(project: Project, task: ScanTask):
    """Clone or pull the repository."""
    repos_dir = os.path.abspath(_get_repos_dir())
    local_path = project.local_path

    if not local_path or not os.path.isabs(local_path):
        local_path = os.path.join(repos_dir, str(project.id))
        project.local_path = local_path

    task.current_phase = '正在克隆/更新仓库...'
    db.session.commit()

    git_service.clone_repo(
        repo_url=project.repo_url,
        local_path=local_path,
        branch=project.branch or 'main',
        auth_type=project.auth_type or 'token',
        token=project.auth_token,
        username=project.auth_username,
        password=project.auth_password,
    )
    project.status = 'ready'
    db.session.commit()


def _check_commits(project: Project, task: ScanTask, full_scan: bool = False):
    """Check AI involvement and line stats for commits.
    full_scan=True clears the project's commit cache before rescanning.
    member_id and commit_date are resolved inline for each commit.
    """
    local_path = project.local_path
    all_commits = git_service.get_all_commits(local_path)
    task.total_commits = len(all_commits)
    task.total_files = 0
    task.scanned_files = 0
    db.session.commit()

    if full_scan:
        AIPromptSession.query.filter_by(project_id=project.id).delete()
        deleted = CommitAIStatus.query.filter_by(project_id=project.id).delete()
        db.session.commit()
        logger.info(f'Full scan: cleared {deleted} commit cache for project {project.id}')
        cached_shas = set()
    else:
        cached_shas = {
            row.commit_sha
            for row in CommitAIStatus.query.filter_by(project_id=project.id).all()
        }

    new_commits = [c for c in all_commits if c['sha'] not in cached_shas]
    checked = len(all_commits) - len(new_commits)

    member_cache = {}

    for i, commit in enumerate(new_commits):
        sha = commit['sha']
        lines_added, lines_deleted = git_service.get_commit_line_stats(local_path, sha)
        total_lines = (lines_added or 0) + (lines_deleted or 0)
        committed_at = _parse_iso_date(commit['date'])
        commit_msg = git_service.get_commit_message(local_path, sha)

        cache_key = (commit['author_name'], commit['author_email'])
        if cache_key not in member_cache:
            member_cache[cache_key] = _get_or_create_member(
                commit['author_name'], commit['author_email'],
            )
        member = member_cache[cache_key]

        ai_detail = git_service.get_ai_commit_detail(local_path, sha)

        # git-ai --json 的 prompts 字段可能是「列表」也可能是「以 prompt_id 为 key 的字典」
        prompts: list[dict] = []
        if ai_detail:
            raw_prompts = ai_detail.get('prompts')
            if isinstance(raw_prompts, dict):
                for pid, pdata in raw_prompts.items():
                    if isinstance(pdata, dict):
                        item = dict(pdata)
                    else:
                        item = {}
                    item.setdefault('id', pid)
                    prompts.append(item)
            elif isinstance(raw_prompts, list):
                prompts = [p for p in raw_prompts if isinstance(p, dict)]

        if prompts:
            agg = _aggregate_prompt_sessions(
                project.id, sha, prompts, member, committed_at,
            )
            # git-ai search --json does NOT carry accepted/overridden line counts
            # (those live in prompts.db via `git-ai prompts`).
            # When the session data has no line stats, fall back to git's own
            # diff stats so coverage is never incorrectly reported as 0.
            ai_lines_val = agg['accepted'] + agg['overridden']
            if ai_lines_val == 0:
                ai_lines_val = lines_added or 0
                logger.debug(
                    f'commit {sha[:8]}: no per-session line stats from git-ai, '
                    f'falling back to git diff lines_added={lines_added}'
                )
            status = CommitAIStatus(
                project_id=project.id,
                member_id=member.id,
                commit_sha=sha,
                commit_message=commit_msg,
                is_ai=True,
                ai_session_count=len(prompts),
                primary_tool=agg['primary_tool'],
                author_name=commit['author_name'],
                author_email=commit['author_email'],
                committed_at=committed_at,
                commit_date=committed_at.date() if committed_at else None,
                lines_added=lines_added,
                lines_deleted=lines_deleted,
                total_lines=total_lines,
                ai_lines_added=ai_lines_val,
                ai_lines_deleted=0,
                accepted_lines=agg['accepted'],
                overridden_lines=agg['overridden'],
                accepted_rate=agg['rate'],
            )
        else:
            ai_count = git_service.check_ai_commit(local_path, sha)
            is_ai_commit = ai_count > 0
            status = CommitAIStatus(
                project_id=project.id,
                member_id=member.id,
                commit_sha=sha,
                commit_message=commit_msg,
                is_ai=is_ai_commit,
                ai_session_count=ai_count,
                author_name=commit['author_name'],
                author_email=commit['author_email'],
                committed_at=committed_at,
                commit_date=committed_at.date() if committed_at else None,
                lines_added=lines_added,
                lines_deleted=lines_deleted,
                total_lines=total_lines,
                ai_lines_added=lines_added if is_ai_commit else 0,
                ai_lines_deleted=lines_deleted if is_ai_commit else 0,
            )
        db.session.add(status)

        checked += 1
        task.checked_commits = checked
        commit_progress = int((checked / len(all_commits)) * 90)
        task.progress = min(commit_progress, 90)
        task.current_phase = f'正在检查提交 ({checked}/{len(all_commits)})...'

        if i % 20 == 0:
            db.session.commit()

    db.session.commit()
    _sync_members_from_commits(project.id)


def _aggregate_prompt_sessions(project_id: int, commit_sha: str,
                               prompts: list[dict], member: Member,
                               committed_at: datetime | None) -> dict:
    """Persist individual AIPromptSession rows and return aggregated metrics.

    Returns dict with keys: accepted, overridden, rate, primary_tool.
    """
    total_accepted = 0
    total_overridden = 0
    tool_counter: Counter = Counter()

    for p in prompts:
        prompt_id = p.get('id', '')
        if not prompt_id:
            continue

        # Avoid violating unique constraint uq_project_prompt (project_id, prompt_id)
        # by skipping sessions that已经存在于当前项目。
        existing = AIPromptSession.query.filter_by(
            project_id=project_id,
            prompt_id=prompt_id,
        ).first()
        if existing:
            continue

        tool = p.get('tool', '')
        model = p.get('model', '')
        accepted = p.get('accepted_lines') or 0
        overridden = p.get('overridden_lines') or 0
        rate = p.get('accepted_rate')
        additions = p.get('total_additions') or 0
        deletions = p.get('total_deletions') or 0
        author = p.get('author') or p.get('human_author') or ''

        start_ts = p.get('start_time')
        end_ts = p.get('last_time') or p.get('end_time')
        session_start = datetime.fromtimestamp(start_ts) if start_ts else None
        session_end = datetime.fromtimestamp(end_ts) if end_ts else None
        session_date = session_start.date() if session_start else (
            committed_at.date() if committed_at else None
        )

        session = AIPromptSession(
            project_id=project_id,
            commit_sha=commit_sha,
            prompt_id=prompt_id,
            tool=tool or None,
            model=model or None,
            human_author=author or None,
            member_id=member.id,
            total_additions=additions,
            total_deletions=deletions,
            accepted_lines=accepted,
            overridden_lines=overridden,
            accepted_rate=rate,
            session_start=session_start,
            session_end=session_end,
            session_date=session_date,
        )
        db.session.add(session)

        total_accepted += accepted
        total_overridden += overridden
        if tool:
            tool_counter[tool] += 1

    denominator = total_accepted + total_overridden
    agg_rate = (total_accepted / denominator) if denominator > 0 else None
    primary_tool = tool_counter.most_common(1)[0][0] if tool_counter else None

    return {
        'accepted': total_accepted,
        'overridden': total_overridden,
        'rate': agg_rate,
        'primary_tool': primary_tool,
    }


def _sync_members_from_commits(project_id: int):
    """Auto-extract members from commit authors and backfill member_id/commit_date for legacy records."""
    authors = db.session.query(
        CommitAIStatus.author_name, CommitAIStatus.author_email,
    ).filter_by(project_id=project_id).distinct().all()

    for name, email in authors:
        if not name:
            continue
        member = _get_or_create_member(name, email)
        CommitAIStatus.query.filter(
            CommitAIStatus.project_id == project_id,
            CommitAIStatus.author_name == name,
            CommitAIStatus.member_id.is_(None),
        ).update({'member_id': member.id}, synchronize_session=False)

    db.session.execute(
        db.text(
            "UPDATE commit_ai_status SET commit_date = DATE(committed_at) "
            "WHERE commit_date IS NULL AND committed_at IS NOT NULL AND project_id = :pid"
        ),
        {'pid': project_id},
    )
    db.session.commit()


def _get_or_create_member(name: str, email: str = None) -> Member:
    """Find or create a member by name/email."""
    member = None
    if email:
        member = Member.query.filter_by(email=email, is_deleted=False).first()
    if not member:
        member = Member.query.filter_by(name=name, is_deleted=False).first()
    if not member:
        member = Member(name=name, email=email, is_manual=False)
        db.session.add(member)
        db.session.commit()
    return member


def _get_repos_dir() -> str:
    """Get repos directory: DB config > .env > default."""
    from flask import current_app
    from app.models import SystemConfig
    config = SystemConfig.query.filter_by(key='repos_dir').first()
    if config and config.value and config.value.strip():
        return config.value.strip()
    return current_app.config.get('REPOS_DIR', 'repos')


def _parse_iso_date(date_str: str):
    """Parse ISO date string to datetime, tolerant of various formats."""
    try:
        return datetime.fromisoformat(date_str)
    except (ValueError, TypeError):
        return None


def scan_all_projects(app):
    """Scheduled task: scan all active projects."""
    with app.app_context():
        projects = Project.query.filter_by(is_deleted=False, status='ready').all()
        for project in projects:
            try:
                start_scan(project.id, scan_type='scheduled', app=app)
            except Exception as e:
                logger.error(f'Scheduled scan failed for project {project.id}: {e}')
