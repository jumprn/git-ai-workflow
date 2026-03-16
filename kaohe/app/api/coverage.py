from datetime import date
from flask import Blueprint, request
from app.services import coverage_service
from app.utils.response import success

coverage_bp = Blueprint('coverage', __name__, url_prefix='/api/coverage')


@coverage_bp.route('', methods=['GET'])
def get_coverage():
    """查询覆盖率数据（分页，支持按项目/成员/时间筛选）"""
    project_id = request.args.get('project_id', type=int)
    member_id = request.args.get('member_id', type=int)
    start_date = _parse_date(request.args.get('start_date'))
    end_date = _parse_date(request.args.get('end_date'))
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    result = coverage_service.query_coverage(
        project_id=project_id, member_id=member_id,
        start_date=start_date, end_date=end_date,
        page=page, per_page=per_page,
    )
    return success(result)


@coverage_bp.route('/trend', methods=['GET'])
def get_trend():
    """获取覆盖率趋势数据（折线图）"""
    project_id = request.args.get('project_id', type=int)
    member_id = request.args.get('member_id', type=int)
    start_date = _parse_date(request.args.get('start_date'))
    end_date = _parse_date(request.args.get('end_date'))

    data = coverage_service.get_trend_data(
        project_id=project_id, member_id=member_id,
        start_date=start_date, end_date=end_date,
    )
    return success(data)


@coverage_bp.route('/by-member', methods=['GET'])
def get_by_member():
    """按成员聚合覆盖率（可按项目、时间筛选，基于 commit 时间）"""
    project_id = request.args.get('project_id', type=int)
    start_date = _parse_date(request.args.get('start_date'))
    end_date = _parse_date(request.args.get('end_date'))
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    result = coverage_service.query_member_coverage_summary(
        project_id=project_id,
        start_date=start_date,
        end_date=end_date,
        page=page,
        per_page=per_page,
    )
    return success(result)


def _parse_date(date_str: str | None) -> date | None:
    if not date_str:
        return None
    try:
        return date.fromisoformat(date_str)
    except (ValueError, TypeError):
        return None
