from datetime import datetime
from app.extensions import db


class ScanTask(db.Model):
    __tablename__ = 'scan_tasks'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False, comment='项目ID')
    scan_type = db.Column(db.String(32), default='manual', comment='扫描类型: manual/scheduled')
    status = db.Column(db.String(32), default='pending', comment='状态: pending/running/completed/failed')
    progress = db.Column(db.Integer, default=0, comment='进度百分比 0-100')
    current_phase = db.Column(db.String(64), comment='当前阶段描述')
    total_files = db.Column(db.Integer, default=0, comment='总文件数')
    scanned_files = db.Column(db.Integer, default=0, comment='已扫描文件数')
    total_commits = db.Column(db.Integer, default=0, comment='总提交数')
    checked_commits = db.Column(db.Integer, default=0, comment='已检查提交数')
    message = db.Column(db.Text, comment='消息/错误信息')
    started_at = db.Column(db.DateTime, comment='开始时间')
    completed_at = db.Column(db.DateTime, comment='完成时间')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'project_name': self.project.name if self.project else None,
            'scan_type': self.scan_type,
            'status': self.status,
            'progress': self.progress,
            'current_phase': self.current_phase,
            'total_files': self.total_files,
            'scanned_files': self.scanned_files,
            'total_commits': self.total_commits,
            'checked_commits': self.checked_commits,
            'message': self.message,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }
