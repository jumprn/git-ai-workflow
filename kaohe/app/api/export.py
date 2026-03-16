from datetime import date
from flask import Blueprint, request, send_file
from app.services import export_service

export_bp = Blueprint('export', __name__, url_prefix='/api/export')


@export_bp.route('/by-project', methods=['GET'])
def export_by_project():
    """导出Excel（按项目分组：成员|项目|AI代码行数|总代码行数|覆盖率）"""
    project_id = request.args.get('project_id', type=int)
    member_id = request.args.get('member_id', type=int)
    start_date = _parse_date(request.args.get('start_date'))
    end_date = _parse_date(request.args.get('end_date'))

    output = export_service.export_by_project(
        project_id=project_id, member_id=member_id,
        start_date=start_date, end_date=end_date,
    )
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='AI代码覆盖率_按项目.xlsx',
    )


@export_bp.route('/by-member', methods=['GET'])
def export_by_member():
    """导出Excel（按成员汇总：成员|AI代码行数|总代码行数|覆盖率）"""
    project_id = request.args.get('project_id', type=int)
    member_id = request.args.get('member_id', type=int)
    start_date = _parse_date(request.args.get('start_date'))
    end_date = _parse_date(request.args.get('end_date'))

    output = export_service.export_by_member(
        project_id=project_id, member_id=member_id,
        start_date=start_date, end_date=end_date,
    )
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='AI代码覆盖率_按成员.xlsx',
    )


def _parse_date(date_str: str | None) -> date | None:
    if not date_str:
        return None
    try:
        return date.fromisoformat(date_str)
    except (ValueError, TypeError):
        return None
