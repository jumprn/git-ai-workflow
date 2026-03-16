from datetime import date

from sqlalchemy import func, case

from app.extensions import db
from app.models import CommitAIStatus, AIPromptSession, Project, Member


def _base_filters():
    """Common filters: non-deleted projects/members, non-null member_id."""
    return (
        Project.is_deleted.is_(False),
        Member.is_deleted.is_(False),
        CommitAIStatus.member_id.isnot(None),
        CommitAIStatus.commit_date.isnot(None),
    )


def query_coverage(project_id: int = None, member_id: int = None,
                   start_date: date = None, end_date: date = None,
                   page: int = 1, per_page: int = 20) -> dict:
    """Query coverage records with filters. Returns paginated results."""
    query = (
        db.session.query(
            CommitAIStatus.project_id,
            Project.name.label('project_name'),
            CommitAIStatus.member_id,
            Member.name.label('member_name'),
            CommitAIStatus.commit_date.label('date'),
            func.sum(CommitAIStatus.ai_lines_added).label('ai_lines'),
            func.sum(CommitAIStatus.total_lines).label('total_lines'),
            func.sum(CommitAIStatus.accepted_lines).label('accepted_lines'),
            func.sum(CommitAIStatus.overridden_lines).label('overridden_lines'),
        )
        .join(Project, CommitAIStatus.project_id == Project.id)
        .join(Member, CommitAIStatus.member_id == Member.id)
        .filter(*_base_filters())
    )

    if project_id:
        query = query.filter(CommitAIStatus.project_id == project_id)
    if member_id:
        query = query.filter(CommitAIStatus.member_id == member_id)
    if start_date:
        query = query.filter(CommitAIStatus.commit_date >= start_date)
    if end_date:
        query = query.filter(CommitAIStatus.commit_date <= end_date)

    query = query.group_by(
        CommitAIStatus.project_id, Project.name,
        CommitAIStatus.member_id, Member.name,
        CommitAIStatus.commit_date,
    ).order_by(CommitAIStatus.commit_date.desc())

    count_subq = query.subquery()
    total = db.session.query(func.count()).select_from(count_subq).scalar() or 0
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    pages = (total + per_page - 1) // per_page if per_page > 0 else 0

    return {
        'items': [_row_to_dict(row) for row in items],
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': pages,
    }


def get_trend_data(project_id: int = None, member_id: int = None,
                   start_date: date = None, end_date: date = None) -> list[dict]:
    """Get daily coverage trend data for charts."""
    query = (
        db.session.query(
            CommitAIStatus.commit_date.label('date'),
            func.sum(CommitAIStatus.ai_lines_added).label('ai_lines'),
            func.sum(CommitAIStatus.total_lines).label('total_lines'),
            func.sum(CommitAIStatus.accepted_lines).label('accepted_lines'),
            func.sum(CommitAIStatus.overridden_lines).label('overridden_lines'),
            func.count(case((CommitAIStatus.is_ai.is_(True), 1))).label('ai_commits'),
            func.count().label('total_commits'),
        )
        .join(Project, CommitAIStatus.project_id == Project.id)
        .join(Member, CommitAIStatus.member_id == Member.id)
        .filter(*_base_filters())
    )

    if project_id:
        query = query.filter(CommitAIStatus.project_id == project_id)
    if member_id:
        query = query.filter(CommitAIStatus.member_id == member_id)
    if start_date:
        query = query.filter(CommitAIStatus.commit_date >= start_date)
    if end_date:
        query = query.filter(CommitAIStatus.commit_date <= end_date)

    query = query.group_by(CommitAIStatus.commit_date).order_by(CommitAIStatus.commit_date)
    results = query.all()

    return [
        {
            'date': row.date.isoformat() if row.date else None,
            'ai_lines': row.ai_lines or 0,
            'total_lines': row.total_lines or 0,
            'coverage_rate': round((row.ai_lines or 0) / row.total_lines * 100, 2) if row.total_lines else 0,
            'accepted_lines': row.accepted_lines or 0,
            'overridden_lines': row.overridden_lines or 0,
            'accepted_rate': _calc_accepted_rate(row.accepted_lines, row.overridden_lines),
            'ai_commits': row.ai_commits or 0,
            'total_commits': row.total_commits or 0,
        }
        for row in results
    ]


def query_member_coverage_summary(project_id: int = None,
                                  start_date: date = None,
                                  end_date: date = None,
                                  page: int = 1,
                                  per_page: int = 20) -> dict:
    """Query coverage aggregated by member (and project) over a period."""
    query = (
        db.session.query(
            CommitAIStatus.member_id,
            Member.name.label('member_name'),
            CommitAIStatus.project_id,
            Project.name.label('project_name'),
            func.sum(CommitAIStatus.ai_lines_added).label('ai_lines'),
            func.sum(CommitAIStatus.total_lines).label('total_lines'),
            func.sum(CommitAIStatus.accepted_lines).label('accepted_lines'),
            func.sum(CommitAIStatus.overridden_lines).label('overridden_lines'),
        )
        .join(Project, CommitAIStatus.project_id == Project.id)
        .join(Member, CommitAIStatus.member_id == Member.id)
        .filter(*_base_filters())
    )

    if project_id:
        query = query.filter(CommitAIStatus.project_id == project_id)
    if start_date:
        query = query.filter(CommitAIStatus.commit_date >= start_date)
    if end_date:
        query = query.filter(CommitAIStatus.commit_date <= end_date)

    query = query.group_by(
        CommitAIStatus.member_id,
        Member.name,
        CommitAIStatus.project_id,
        Project.name,
    )

    count_subq = query.subquery()
    total = db.session.query(func.count()).select_from(count_subq).scalar() or 0
    items = query.order_by(
        func.sum(CommitAIStatus.ai_lines_added).desc(),
    ).offset((page - 1) * per_page).limit(per_page).all()
    pages = (total + per_page - 1) // per_page if per_page > 0 else 0

    def _row_to_member_dict(row) -> dict:
        ai = row.ai_lines or 0
        total_lines = row.total_lines or 0
        return {
            'member_id': row.member_id,
            'member_name': row.member_name,
            'project_id': row.project_id,
            'project_name': row.project_name,
            'ai_lines': ai,
            'total_lines': total_lines,
            'coverage_rate': round(ai / total_lines * 100, 2) if total_lines > 0 else 0,
            'accepted_lines': row.accepted_lines or 0,
            'overridden_lines': row.overridden_lines or 0,
            'accepted_rate': _calc_accepted_rate(row.accepted_lines, row.overridden_lines),
        }

    return {
        'items': [_row_to_member_dict(row) for row in items],
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': pages,
    }


def get_summary(project_id: int = None, start_date: date = None,
                end_date: date = None) -> dict:
    """Get summary statistics for dashboard."""
    base = (
        db.session.query(CommitAIStatus)
        .join(Project, CommitAIStatus.project_id == Project.id)
        .join(Member, CommitAIStatus.member_id == Member.id)
        .filter(*_base_filters())
    )

    if project_id:
        base = base.filter(CommitAIStatus.project_id == project_id)
    if start_date:
        base = base.filter(CommitAIStatus.commit_date >= start_date)
    if end_date:
        base = base.filter(CommitAIStatus.commit_date <= end_date)

    latest_date = base.with_entities(func.max(CommitAIStatus.commit_date)).scalar()

    if not latest_date:
        return {
            'total_projects': Project.query.filter_by(is_deleted=False).count(),
            'total_members': Member.query.filter_by(is_deleted=False).count(),
            'avg_coverage': 0,
            'total_ai_lines': 0,
            'total_lines': 0,
            'accepted_lines': 0,
            'overridden_lines': 0,
            'accepted_rate': 0,
            'ai_commits': 0,
            'total_commits': 0,
            'latest_date': None,
        }

    stats = base.filter(
        CommitAIStatus.commit_date == latest_date,
    ).with_entities(
        func.sum(CommitAIStatus.ai_lines_added).label('ai'),
        func.sum(CommitAIStatus.total_lines).label('total'),
        func.sum(CommitAIStatus.accepted_lines).label('accepted'),
        func.sum(CommitAIStatus.overridden_lines).label('overridden'),
        func.count(case((CommitAIStatus.is_ai.is_(True), 1))).label('ai_commits'),
        func.count().label('total_commits'),
    ).first()

    ai = stats.ai or 0
    total = stats.total or 0

    return {
        'total_projects': Project.query.filter_by(is_deleted=False).count(),
        'total_members': Member.query.filter_by(is_deleted=False).count(),
        'avg_coverage': round(ai / total * 100, 2) if total > 0 else 0,
        'total_ai_lines': ai,
        'total_lines': total,
        'accepted_lines': stats.accepted or 0,
        'overridden_lines': stats.overridden or 0,
        'accepted_rate': _calc_accepted_rate(stats.accepted, stats.overridden),
        'ai_commits': stats.ai_commits or 0,
        'total_commits': stats.total_commits or 0,
        'latest_date': latest_date.isoformat() if latest_date else None,
    }


def get_project_coverage(start_date: date = None, end_date: date = None) -> list[dict]:
    """Get coverage grouped by project (latest date)."""
    query = (
        db.session.query(
            CommitAIStatus.project_id,
            Project.name,
            func.sum(CommitAIStatus.ai_lines_added).label('ai_lines'),
            func.sum(CommitAIStatus.total_lines).label('total_lines'),
            func.sum(CommitAIStatus.accepted_lines).label('accepted_lines'),
            func.sum(CommitAIStatus.overridden_lines).label('overridden_lines'),
        )
        .join(Project, CommitAIStatus.project_id == Project.id)
        .filter(
            Project.is_deleted.is_(False),
            CommitAIStatus.commit_date.isnot(None),
        )
    )

    if start_date:
        query = query.filter(CommitAIStatus.commit_date >= start_date)
    if end_date:
        query = query.filter(CommitAIStatus.commit_date <= end_date)

    latest_date = db.session.query(
        func.max(CommitAIStatus.commit_date),
    ).filter(CommitAIStatus.commit_date.isnot(None)).scalar()

    if latest_date:
        query = query.filter(CommitAIStatus.commit_date == latest_date)

    results = query.group_by(CommitAIStatus.project_id, Project.name).all()

    return [
        {
            'project_id': row.project_id,
            'project_name': row.name,
            'ai_lines': row.ai_lines or 0,
            'total_lines': row.total_lines or 0,
            'coverage_rate': round((row.ai_lines or 0) / row.total_lines * 100, 2) if row.total_lines else 0,
            'accepted_rate': _calc_accepted_rate(row.accepted_lines, row.overridden_lines),
        }
        for row in results
    ]


def get_member_ranking(project_id: int = None, start_date: date = None,
                       end_date: date = None, limit: int = 10) -> list[dict]:
    """Get member ranking by AI coverage rate."""
    query = (
        db.session.query(
            CommitAIStatus.member_id,
            Member.name,
            func.sum(CommitAIStatus.ai_lines_added).label('ai_lines'),
            func.sum(CommitAIStatus.total_lines).label('total_lines'),
            func.sum(CommitAIStatus.accepted_lines).label('accepted_lines'),
            func.sum(CommitAIStatus.overridden_lines).label('overridden_lines'),
        )
        .join(Project, CommitAIStatus.project_id == Project.id)
        .join(Member, CommitAIStatus.member_id == Member.id)
        .filter(*_base_filters())
    )

    if project_id:
        query = query.filter(CommitAIStatus.project_id == project_id)
    if start_date:
        query = query.filter(CommitAIStatus.commit_date >= start_date)
    if end_date:
        query = query.filter(CommitAIStatus.commit_date <= end_date)

    latest_date = db.session.query(
        func.max(CommitAIStatus.commit_date),
    ).filter(CommitAIStatus.commit_date.isnot(None)).scalar()

    if latest_date:
        query = query.filter(CommitAIStatus.commit_date == latest_date)

    results = query.group_by(
        CommitAIStatus.member_id, Member.name,
    ).order_by(func.sum(CommitAIStatus.ai_lines_added).desc()).limit(limit).all()

    return [
        {
            'member_id': row.member_id,
            'member_name': row.name,
            'ai_lines': row.ai_lines or 0,
            'total_lines': row.total_lines or 0,
            'coverage_rate': round((row.ai_lines or 0) / row.total_lines * 100, 2) if row.total_lines else 0,
            'accepted_rate': _calc_accepted_rate(row.accepted_lines, row.overridden_lines),
        }
        for row in results
    ]


def get_tool_stats(project_id: int = None, start_date: date = None,
                   end_date: date = None) -> list[dict]:
    """Get AI tool usage statistics from prompt sessions."""
    query = (
        db.session.query(
            AIPromptSession.tool,
            func.count().label('session_count'),
            func.sum(AIPromptSession.accepted_lines).label('accepted_lines'),
            func.sum(AIPromptSession.overridden_lines).label('overridden_lines'),
            func.sum(AIPromptSession.total_additions).label('total_additions'),
            func.count(func.distinct(AIPromptSession.member_id)).label('user_count'),
        )
        .filter(AIPromptSession.tool.isnot(None))
    )

    if project_id:
        query = query.filter(AIPromptSession.project_id == project_id)
    if start_date:
        query = query.filter(AIPromptSession.session_date >= start_date)
    if end_date:
        query = query.filter(AIPromptSession.session_date <= end_date)

    results = query.group_by(AIPromptSession.tool).order_by(func.count().desc()).all()

    return [
        {
            'tool': row.tool,
            'session_count': row.session_count,
            'accepted_lines': row.accepted_lines or 0,
            'overridden_lines': row.overridden_lines or 0,
            'total_additions': row.total_additions or 0,
            'accepted_rate': _calc_accepted_rate(row.accepted_lines, row.overridden_lines),
            'user_count': row.user_count or 0,
        }
        for row in results
    ]


def get_model_stats(project_id: int = None, start_date: date = None,
                    end_date: date = None) -> list[dict]:
    """Get AI model effectiveness statistics from prompt sessions."""
    query = (
        db.session.query(
            AIPromptSession.model,
            func.count().label('session_count'),
            func.sum(AIPromptSession.accepted_lines).label('accepted_lines'),
            func.sum(AIPromptSession.overridden_lines).label('overridden_lines'),
            func.sum(AIPromptSession.total_additions).label('total_additions'),
        )
        .filter(AIPromptSession.model.isnot(None))
    )

    if project_id:
        query = query.filter(AIPromptSession.project_id == project_id)
    if start_date:
        query = query.filter(AIPromptSession.session_date >= start_date)
    if end_date:
        query = query.filter(AIPromptSession.session_date <= end_date)

    results = query.group_by(AIPromptSession.model).order_by(func.count().desc()).all()

    return [
        {
            'model': row.model,
            'session_count': row.session_count,
            'accepted_lines': row.accepted_lines or 0,
            'overridden_lines': row.overridden_lines or 0,
            'total_additions': row.total_additions or 0,
            'accepted_rate': _calc_accepted_rate(row.accepted_lines, row.overridden_lines),
        }
        for row in results
    ]


def _calc_accepted_rate(accepted, overridden) -> float:
    a = accepted or 0
    o = overridden or 0
    return round(a / (a + o) * 100, 2) if (a + o) > 0 else 0


def _row_to_dict(row) -> dict:
    ai = row.ai_lines or 0
    total = row.total_lines or 0
    return {
        'project_id': row.project_id,
        'project_name': row.project_name,
        'member_id': row.member_id,
        'member_name': row.member_name,
        'date': row.date.isoformat() if row.date else None,
        'ai_lines': ai,
        'total_lines': total,
        'coverage_rate': round(ai / total * 100, 2) if total > 0 else 0,
        'accepted_lines': row.accepted_lines or 0,
        'overridden_lines': row.overridden_lines or 0,
        'accepted_rate': _calc_accepted_rate(row.accepted_lines, row.overridden_lines),
    }
