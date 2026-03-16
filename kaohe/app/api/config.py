from flask import Blueprint, request
from app.extensions import db
from app.models import SystemConfig
from app.utils.response import success
from app.errors import BizError

config_bp = Blueprint('config', __name__, url_prefix='/api/config')

DEFAULT_CONFIGS = [
    {'key': 'scan_enabled', 'value': 'true', 'description': '是否启用定时扫描'},
    {'key': 'scan_hour', 'value': '2', 'description': '定时扫描小时 (0-23)'},
    {'key': 'scan_minute', 'value': '0', 'description': '定时扫描分钟 (0-59)'},
    {'key': 'scan_interval_days', 'value': '1', 'description': '扫描间隔天数'},
    {'key': 'repos_dir', 'value': '', 'description': '仓库克隆存放目录（绝对路径，为空则使用 .env 中的 REPOS_DIR）'},
]


@config_bp.route('', methods=['GET'])
def get_configs():
    """获取所有系统配置"""
    _ensure_defaults()
    configs = SystemConfig.query.all()
    return success([c.to_dict() for c in configs])


@config_bp.route('', methods=['PUT'])
def update_configs():
    """批量更新系统配置"""
    data = request.get_json()
    if not data or not isinstance(data, list):
        raise BizError('请提供配置列表')

    for item in data:
        key = item.get('key')
        value = item.get('value')
        if not key:
            continue
        config = SystemConfig.query.filter_by(key=key).first()
        if config:
            config.value = str(value)
        else:
            config = SystemConfig(key=key, value=str(value), description=item.get('description', ''))
            db.session.add(config)

    db.session.commit()

    _apply_scheduler_config()
    return success(message='配置已更新')


@config_bp.route('/<string:key>', methods=['GET'])
def get_config_by_key(key):
    """获取单个配置"""
    config = SystemConfig.query.filter_by(key=key).first()
    if not config:
        raise BizError('配置不存在', 404)
    return success(config.to_dict())


def _ensure_defaults():
    """Ensure default configs exist."""
    for item in DEFAULT_CONFIGS:
        existing = SystemConfig.query.filter_by(key=item['key']).first()
        if not existing:
            db.session.add(SystemConfig(**item))
    db.session.commit()


def _apply_scheduler_config():
    """Re-apply scheduler settings after config change."""
    from app.scheduler import reschedule_scan
    try:
        reschedule_scan()
    except Exception:
        pass
