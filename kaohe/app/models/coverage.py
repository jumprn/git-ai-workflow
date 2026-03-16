from datetime import datetime
from app.extensions import db


class CoverageRecord(db.Model):
    __tablename__ = 'coverage_records'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False, comment='项目ID')
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False, comment='成员ID')
    date = db.Column(db.Date, nullable=False, comment='统计日期')
    ai_lines = db.Column(db.Integer, default=0, comment='AI生成代码行数')
    total_lines = db.Column(db.Integer, default=0, comment='总代码行数')
    coverage_rate = db.Column(db.Float, default=0.0, comment='AI代码覆盖率')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')

    __table_args__ = (
        db.UniqueConstraint('project_id', 'member_id', 'date', name='uq_coverage_project_member_date'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'project_name': self.project.name if self.project else None,
            'member_id': self.member_id,
            'member_name': self.member.name if self.member else None,
            'date': self.date.isoformat() if self.date else None,
            'ai_lines': self.ai_lines,
            'total_lines': self.total_lines,
            'coverage_rate': self.coverage_rate,
        }
