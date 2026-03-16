import os
import shutil
import subprocess
import logging
import re
from urllib.parse import quote

logger = logging.getLogger(__name__)

CODE_EXTENSIONS = {
    '.py', '.js', '.ts', '.jsx', '.tsx', '.vue', '.java', '.kt', '.go',
    '.rs', '.c', '.cpp', '.h', '.hpp', '.cs', '.rb', '.php', '.swift',
    '.scala', '.ex', '.exs', '.sql', '.sh', '.bash',
    '.html', '.css', '.scss', '.less', '.yaml', '.yml', '.toml',
    '.xml', '.md', '.txt', '.cfg', '.ini', '.conf', '.json',
}


def build_auth_url(repo_url: str, auth_type: str = 'token',
                   token: str = None, username: str = None, password: str = None) -> str:
    """Build a git URL with embedded credentials."""
    if not repo_url.startswith('https://'):
        return repo_url
    if auth_type == 'token' and token:
        return repo_url.replace('https://', f'https://oauth2:{quote(token, safe="")}@')
    if auth_type == 'password' and username and password:
        return repo_url.replace('https://', f'https://{quote(username, safe="")}:{quote(password, safe="")}@')
    return repo_url


def run_git(args: list[str], cwd: str, timeout: int = 120) -> subprocess.CompletedProcess:
    """Run a git command and return the result."""
    result = subprocess.run(
        args, cwd=cwd, capture_output=True, text=True, timeout=timeout,
        encoding='utf-8', errors='replace',
    )
    return result


def clone_repo(repo_url: str, local_path: str, branch: str = 'main',
               auth_type: str = 'token', token: str = None,
               username: str = None, password: str = None) -> str:
    """Clone a repository to local_path. Returns the local path."""
    if os.path.exists(os.path.join(local_path, '.git')):
        logger.info(f'Repo already exists at {local_path}, pulling instead')
        pull_repo(local_path, auth_type, token, username, password)
        return local_path

    if os.path.exists(local_path):
        logger.warning(f'Directory {local_path} exists but has no .git, removing and re-cloning')
        shutil.rmtree(local_path, ignore_errors=True)

    parent_dir = os.path.dirname(local_path)
    os.makedirs(parent_dir, exist_ok=True)
    auth_url = build_auth_url(repo_url, auth_type, token, username, password)

    result = run_git(['git', 'clone', '-b', branch, '--single-branch', auth_url, local_path],
                     cwd=parent_dir, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f'Clone failed: {result.stderr}')

    fetch_notes(local_path)
    return local_path


def pull_repo(local_path: str, auth_type: str = 'token', token: str = None,
              username: str = None, password: str = None) -> bool:
    """Pull latest changes and fetch notes."""
    result = run_git(['git', 'pull', '--ff-only'], cwd=local_path, timeout=120)
    fetch_notes(local_path)
    return result.returncode == 0


def fetch_notes(local_path: str):
    """Fetch git-ai notes from remote."""
    run_git(['git', 'fetch', 'origin', 'refs/notes/*:refs/notes/*'],
            cwd=local_path, timeout=60)


def get_all_commits(local_path: str) -> list[dict]:
    """Get all commits with author info. Returns list of dicts."""
    result = run_git(
        ['git', 'log', '--all', '--format=%H|||%an|||%ae|||%aI'],
        cwd=local_path, timeout=60,
    )
    commits = []
    for line in result.stdout.strip().split('\n'):
        if not line:
            continue
        parts = line.split('|||')
        if len(parts) >= 4:
            commits.append({
                'sha': parts[0],
                'author_name': parts[1],
                'author_email': parts[2],
                'date': parts[3],
            })
    return commits


def check_ai_commit(local_path: str, commit_sha: str) -> int:
    """Check if a commit has AI involvement. Returns session count."""
    try:
        result = run_git(
            ['git-ai', 'search', '--commit', commit_sha, '--count'],
            cwd=local_path, timeout=30,
        )
        text = result.stdout.strip()
        return int(text) if text.isdigit() else 0
    except (subprocess.TimeoutExpired, Exception) as e:
        logger.warning(f'git-ai check failed for {commit_sha}: {e}')
        return 0


def get_ai_commit_detail(local_path: str, commit_sha: str) -> dict | None:
    """Get rich AI session data for a commit via git-ai search --json.

    Returns parsed JSON with per-prompt session details including
    tool, model, accepted_lines, overridden_lines, accepted_rate, etc.
    Returns None when git-ai has no data for this commit.
    """
    try:
        result = run_git(
            ['git-ai', 'search', '--commit', commit_sha, '--json'],
            cwd=local_path, timeout=30,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None
        import json
        data = json.loads(result.stdout)
        if not data.get('prompts'):
            return None
        return data
    except (subprocess.TimeoutExpired, ValueError, Exception) as e:
        logger.warning(f'git-ai detail failed for {commit_sha}: {e}')
        return None


def get_commit_line_stats(local_path: str, commit_sha: str) -> tuple[int, int]:
    """Get lines added and deleted for a commit. Returns (lines_added, lines_deleted)."""
    try:
        result = run_git(
            ['git', 'show', '--shortstat', '--format=', commit_sha],
            cwd=local_path, timeout=30,
        )
        added, deleted = 0, 0
        for part in result.stdout.strip().split(','):
            part = part.strip()
            if 'insertion' in part:
                added = int(re.search(r'\d+', part).group()) if re.search(r'\d+', part) else 0
            elif 'deletion' in part:
                deleted = int(re.search(r'\d+', part).group()) if re.search(r'\d+', part) else 0
        return (added, deleted)
    except (subprocess.TimeoutExpired, Exception) as e:
        logger.warning(f'git show failed for {commit_sha}: {e}')
        return (0, 0)


def get_commit_message(local_path: str, commit_sha: str) -> str:
    """Get the first line of a commit message."""
    try:
        result = run_git(
            ['git', 'log', '-1', '--format=%s', commit_sha],
            cwd=local_path, timeout=10,
        )
        return result.stdout.strip()[:512] if result.returncode == 0 else ''
    except (subprocess.TimeoutExpired, Exception):
        return ''


def get_tracked_files(local_path: str) -> list[str]:
    """Get all tracked files, filtered to code files."""
    result = run_git(['git', 'ls-files'], cwd=local_path, timeout=30)
    all_files = [f for f in result.stdout.strip().split('\n') if f]
    return [f for f in all_files if os.path.splitext(f)[1].lower() in CODE_EXTENSIONS]


def blame_file(local_path: str, file_path: str) -> list[dict]:
    """Run git blame --line-porcelain on a file. Returns per-line info."""
    result = run_git(
        ['git', 'blame', '--line-porcelain', file_path],
        cwd=local_path, timeout=120,
    )
    if result.returncode != 0:
        return []

    lines = []
    current_sha = None
    current_author = None
    current_email = None

    for raw_line in result.stdout.split('\n'):
        if not raw_line:
            continue

        sha_match = re.match(r'^([0-9a-f]{40})\s+\d+\s+\d+', raw_line)
        if sha_match:
            current_sha = sha_match.group(1)
            continue

        if raw_line.startswith('author '):
            current_author = raw_line[7:]
        elif raw_line.startswith('author-mail '):
            current_email = raw_line[12:].strip('<>')
        elif raw_line.startswith('\t'):
            if current_sha and current_sha != '0' * 40:
                lines.append({
                    'sha': current_sha,
                    'author': current_author or 'Unknown',
                    'author_email': current_email or '',
                })

    return lines
