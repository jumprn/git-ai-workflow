from datetime import datetime
from app.extensions import db


class Project(db.Model):
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(128), nullable=False, comment='项目名称')
    repo_url = db.Column(db.String(512), nullable=False, comment='仓库地址')
    auth_type = db.Column(db.String(32), default='token', comment='认证类型: token/password')
    auth_token = db.Column(db.String(512), comment='访问令牌')
    auth_username = db.Column(db.String(128), comment='用户名')
    auth_password = db.Column(db.String(512), comment='密码')
    local_path = db.Column(db.String(512), comment='本地仓库路径')
    branch = db.Column(db.String(128), default='main', comment='默认分支')
    status = db.Column(db.String(32), default='pending', comment='状态: pending/cloning/ready/error')
    error_message = db.Column(db.Text, comment='错误信息')
    last_scan_at = db.Column(db.DateTime, comment='最后扫描时间')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    is_deleted = db.Column(db.Boolean, default=False, comment='软删除标记')

    coverage_records = db.relationship('CoverageRecord', backref='project', lazy='dynamic')
    scan_tasks = db.relationship('ScanTask', backref='project', lazy='dynamic')
    commit_statuses = db.relationship('CommitAIStatus', backref='project', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'repo_url': self.repo_url,
            'auth_type': self.auth_type,
            'branch': self.branch,
            'status': self.status,
            'error_message': self.error_message,
            'last_scan_at': self.last_scan_at.isoformat() if self.last_scan_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
