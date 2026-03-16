from datetime import datetime
from app.extensions import db


class CommitAIStatus(db.Model):
    """Per-commit AI involvement cache.

    Each row maps to one git commit. Fields like accepted_lines /
    overridden_lines / accepted_rate are aggregated from the related
    ai_prompt_sessions rows for that commit.
    """
    __tablename__ = 'commit_ai_status'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False, comment='项目ID')
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'), comment='成员ID')
    commit_sha = db.Column(db.String(40), nullable=False, comment='提交SHA')
    commit_message = db.Column(db.String(512), comment='提交消息(首行)')
    is_ai = db.Column(db.Boolean, default=False, comment='是否包含AI辅助')
    ai_session_count = db.Column(db.Integer, default=0, comment='AI会话数')
    primary_tool = db.Column(db.String(64), comment='主要AI工具(cursor/claude-code等)')
    author_name = db.Column(db.String(128), comment='提交作者')
    author_email = db.Column(db.String(128), comment='作者邮箱')
    committed_at = db.Column(db.DateTime, comment='提交时间')
    commit_date = db.Column(db.Date, comment='提交日期(冗余字段便于聚合)')

    lines_added = db.Column(db.Integer, default=0, comment='该提交新增行数(git统计)')
    lines_deleted = db.Column(db.Integer, default=0, comment='该提交删除行数(git统计)')
    total_lines = db.Column(db.Integer, default=0, comment='该提交总变更行数(新增+删除)')

    ai_lines_added = db.Column(db.Integer, default=0, comment='AI贡献新增行数(accepted+overridden)')
    ai_lines_deleted = db.Column(db.Integer, default=0, comment='AI贡献删除行数')
    accepted_lines = db.Column(db.Integer, default=0, comment='AI代码被人类原样保留的行数')
    overridden_lines = db.Column(db.Integer, default=0, comment='AI代码被人类修改的行数')
    accepted_rate = db.Column(db.Float, comment='AI代码接受率: accepted/(accepted+overridden)')

    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')

    member = db.relationship('Member', backref=db.backref('commit_statuses', lazy='dynamic'))
    prompt_sessions = db.relationship(
        'AIPromptSession',
        primaryjoin='and_(CommitAIStatus.project_id==foreign(AIPromptSession.project_id), '
                    'CommitAIStatus.commit_sha==foreign(AIPromptSession.commit_sha))',
        viewonly=True, lazy='dynamic',
    )

    __table_args__ = (
        db.UniqueConstraint('project_id', 'commit_sha', name='uq_project_commit'),
        db.Index('ix_commit_ai_member', 'member_id'),
        db.Index('ix_commit_ai_project_member_date', 'project_id', 'member_id', 'commit_date'),
        db.Index('ix_commit_ai_tool', 'primary_tool'),
    )
