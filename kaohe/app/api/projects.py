from flask import Blueprint, request
from app.extensions import db
from app.models import Project
from app.utils.response import success, fail
from app.errors import BizError

projects_bp = Blueprint('projects', __name__, url_prefix='/api/projects')


@projects_bp.route('', methods=['GET'])
def get_projects():
    """获取项目列表"""
    projects = Project.query.filter_by(is_deleted=False).order_by(Project.created_at.desc()).all()
    return success([p.to_dict() for p in projects])


@projects_bp.route('/<int:project_id>', methods=['GET'])
def get_project(project_id):
    """获取单个项目"""
    project = db.session.get(Project, project_id)
    if not project or project.is_deleted:
        raise BizError('项目不存在', 404)
    return success(project.to_dict())


@projects_bp.route('', methods=['POST'])
def create_project():
    """创建项目"""
    data = request.get_json()
    if not data or not data.get('name') or not data.get('repo_url'):
        raise BizError('项目名称和仓库地址不能为空')

    project = Project(
        name=data['name'],
        repo_url=data['repo_url'],
        auth_type=data.get('auth_type', 'token'),
        auth_token=data.get('auth_token'),
        auth_username=data.get('auth_username'),
        auth_password=data.get('auth_password'),
        branch=data.get('branch', 'main'),
    )
    db.session.add(project)
    db.session.commit()
    return success(project.to_dict(), '项目创建成功')


@projects_bp.route('/<int:project_id>', methods=['PUT'])
def update_project(project_id):
    """更新项目"""
    project = db.session.get(Project, project_id)
    if not project or project.is_deleted:
        raise BizError('项目不存在', 404)

    data = request.get_json()
    if data.get('name'):
        project.name = data['name']
    if data.get('repo_url'):
        project.repo_url = data['repo_url']
    if 'auth_type' in data:
        project.auth_type = data['auth_type']
    if 'auth_token' in data:
        project.auth_token = data['auth_token']
    if 'auth_username' in data:
        project.auth_username = data['auth_username']
    if 'auth_password' in data:
        project.auth_password = data['auth_password']
    if data.get('branch'):
        project.branch = data['branch']

    db.session.commit()
    return success(project.to_dict(), '项目更新成功')


@projects_bp.route('/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    """删除项目（软删除）"""
    project = db.session.get(Project, project_id)
    if not project or project.is_deleted:
        raise BizError('项目不存在', 404)

    project.is_deleted = True
    db.session.commit()
    return success(message='项目已删除')
