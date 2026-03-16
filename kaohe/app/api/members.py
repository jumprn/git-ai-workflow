from flask import Blueprint, request
from app.extensions import db
from app.models import Member
from app.utils.response import success, fail
from app.errors import BizError

members_bp = Blueprint('members', __name__, url_prefix='/api/members')


@members_bp.route('', methods=['GET'])
def get_members():
    """获取成员列表"""
    members = Member.query.filter_by(is_deleted=False).order_by(Member.name).all()
    return success([m.to_dict() for m in members])


@members_bp.route('/<int:member_id>', methods=['GET'])
def get_member(member_id):
    """获取单个成员"""
    member = db.session.get(Member, member_id)
    if not member or member.is_deleted:
        raise BizError('成员不存在', 404)
    return success(member.to_dict())


@members_bp.route('', methods=['POST'])
def create_member():
    """手动添加成员"""
    data = request.get_json()
    if not data or not data.get('name'):
        raise BizError('成员姓名不能为空')

    member = Member(
        name=data['name'],
        email=data.get('email'),
        is_manual=True,
    )
    db.session.add(member)
    db.session.commit()
    return success(member.to_dict(), '成员添加成功')


@members_bp.route('/<int:member_id>', methods=['PUT'])
def update_member(member_id):
    """更新成员"""
    member = db.session.get(Member, member_id)
    if not member or member.is_deleted:
        raise BizError('成员不存在', 404)

    data = request.get_json()
    if data.get('name'):
        member.name = data['name']
    if 'email' in data:
        member.email = data['email']

    db.session.commit()
    return success(member.to_dict(), '成员更新成功')


@members_bp.route('/<int:member_id>', methods=['DELETE'])
def delete_member(member_id):
    """删除成员（软删除）"""
    member = db.session.get(Member, member_id)
    if not member or member.is_deleted:
        raise BizError('成员不存在', 404)

    member.is_deleted = True
    db.session.commit()
    return success(message='成员已删除')
