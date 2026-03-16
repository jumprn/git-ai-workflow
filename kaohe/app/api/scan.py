from datetime import datetime
from flask import Blueprint, request
from app.extensions import db
from app.models import ScanTask, Project
from app.services import scan_service
from app.utils.response import success
from app.errors import BizError

scan_bp = Blueprint('scan', __name__, url_prefix='/api/scan')


@scan_bp.route('/start', methods=['POST'])
def start_scan():
    """启动实时扫描。full_scan=True 时强制全量扫描（清空该项目的 commit 缓存后重扫，防篡改）。"""
    data = request.get_json()
    project_id = data.get('project_id') if data else None
    if not project_id:
        raise BizError('请指定项目')

    project = db.session.get(Project, project_id)
    if not project or project.is_deleted:
        raise BizError('项目不存在', 404)

    full_scan = bool(data.get('full_scan')) if data else False
    running_task = ScanTask.query.filter_by(
        project_id=project_id, status='running',
    ).first()
    if running_task:
        if full_scan:
            running_task.status = 'failed'
            running_task.message = '被全量扫描取代'
            running_task.completed_at = running_task.completed_at or datetime.now()
            db.session.commit()
        else:
            raise BizError('该项目正在扫描中，请等待完成')

    task = scan_service.start_scan(project_id, scan_type='manual', full_scan=full_scan)
    return success(task.to_dict(), '扫描已启动')


@scan_bp.route('/progress/<int:task_id>', methods=['GET'])
def get_progress(task_id):
    """查询扫描进度"""
    task = db.session.get(ScanTask, task_id)
    if not task:
        raise BizError('扫描任务不存在', 404)
    return success(task.to_dict())


@scan_bp.route('/tasks', methods=['GET'])
def get_tasks():
    """获取扫描任务列表"""
    project_id = request.args.get('project_id', type=int)
    query = ScanTask.query.order_by(ScanTask.created_at.desc())
    if project_id:
        query = query.filter_by(project_id=project_id)
    tasks = query.limit(50).all()
    return success([t.to_dict() for t in tasks])


@scan_bp.route('/repair', methods=['POST'])
def repair_ai_lines():
    """一次性修复：对 is_ai=1 但 ai_lines_added=0 的记录，用 lines_added 回填。"""
    result = db.session.execute(db.text(
        "UPDATE commit_ai_status "
        "SET ai_lines_added = lines_added "
        "WHERE is_ai = 1 AND ai_lines_added = 0 AND lines_added > 0"
    ))
    db.session.commit()
    return success({'fixed_rows': result.rowcount}, f'已修复 {result.rowcount} 条记录')


@scan_bp.route('/scan-all', methods=['POST'])
def scan_all():
    """扫描所有已就绪的项目"""
    from flask import current_app
    app = current_app._get_current_object()
    projects = Project.query.filter_by(is_deleted=False).all()
    started = []
    for project in projects:
        running = ScanTask.query.filter_by(project_id=project.id, status='running').first()
        if not running:
            task = scan_service.start_scan(project.id, scan_type='manual', app=app)
            started.append(task.to_dict())
    return success(started, f'已启动 {len(started)} 个项目的扫描')
