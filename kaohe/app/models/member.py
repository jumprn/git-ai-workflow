from datetime import datetime
from app.extensions import db


class Member(db.Model):
    __tablename__ = 'members'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(128), nullable=False, comment='成员姓名')
    email = db.Column(db.String(128), comment='邮箱')
    is_manual = db.Column(db.Boolean, default=False, comment='是否手动添加')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    is_deleted = db.Column(db.Boolean, default=False, comment='软删除标记')

    coverage_records = db.relationship('CoverageRecord', backref='member', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'is_manual': self.is_manual,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
