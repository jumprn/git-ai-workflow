from datetime import date
from flask import Blueprint, request
from app.services import coverage_service
from app.utils.response import success

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')


@dashboard_bp.route('/summary', methods=['GET'])
def get_summary():
    """获取仪表盘概览数据"""
    project_id = request.args.get('project_id', type=int)
    start_date = _parse_date(request.args.get('start_date'))
    end_date = _parse_date(request.args.get('end_date'))

    data = coverage_service.get_summary(
        project_id=project_id,
        start_date=start_date, end_date=end_date,
    )
    return success(data)


@dashboard_bp.route('/trend', methods=['GET'])
def get_trend():
    """获取覆盖率趋势"""
    project_id = request.args.get('project_id', type=int)
    member_id = request.args.get('member_id', type=int)
    start_date = _parse_date(request.args.get('start_date'))
    end_date = _parse_date(request.args.get('end_date'))

    data = coverage_service.get_trend_data(
        project_id=project_id, member_id=member_id,
        start_date=start_date, end_date=end_date,
    )
    return success(data)


@dashboard_bp.route('/by-project', methods=['GET'])
def get_by_project():
    """获取各项目覆盖率"""
    start_date = _parse_date(request.args.get('start_date'))
    end_date = _parse_date(request.args.get('end_date'))
    data = coverage_service.get_project_coverage(start_date=start_date, end_date=end_date)
    return success(data)


@dashboard_bp.route('/ranking', methods=['GET'])
def get_ranking():
    """获取成员覆盖率排行"""
    project_id = request.args.get('project_id', type=int)
    start_date = _parse_date(request.args.get('start_date'))
    end_date = _parse_date(request.args.get('end_date'))
    limit = request.args.get('limit', 10, type=int)

    data = coverage_service.get_member_ranking(
        project_id=project_id,
        start_date=start_date, end_date=end_date,
        limit=limit,
    )
    return success(data)


@dashboard_bp.route('/tool-stats', methods=['GET'])
def get_tool_stats():
    """获取AI工具使用统计"""
    project_id = request.args.get('project_id', type=int)
    start_date = _parse_date(request.args.get('start_date'))
    end_date = _parse_date(request.args.get('end_date'))

    data = coverage_service.get_tool_stats(
        project_id=project_id,
        start_date=start_date, end_date=end_date,
    )
    return success(data)


@dashboard_bp.route('/model-stats', methods=['GET'])
def get_model_stats():
    """获取AI模型效果统计"""
    project_id = request.args.get('project_id', type=int)
    start_date = _parse_date(request.args.get('start_date'))
    end_date = _parse_date(request.args.get('end_date'))

    data = coverage_service.get_model_stats(
        project_id=project_id,
        start_date=start_date, end_date=end_date,
    )
    return success(data)


def _parse_date(date_str: str | None) -> date | None:
    if not date_str:
        return None
    try:
        return date.fromisoformat(date_str)
    except (ValueError, TypeError):
        return None
