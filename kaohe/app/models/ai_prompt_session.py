from datetime import datetime
from app.extensions import db


class AIPromptSession(db.Model):
    """Per-prompt-session AI usage detail.

    Each row corresponds to one git-ai prompt session. A single commit
    may contain multiple sessions (different tools / conversations).
    Data is populated from `git-ai search --commit <sha> --json`.
    """
    __tablename__ = 'ai_prompt_sessions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False, comment='项目ID')
    commit_sha = db.Column(db.String(40), comment='关联提交SHA')
    prompt_id = db.Column(db.String(64), nullable=False, comment='git-ai 会话ID')
    tool = db.Column(db.String(64), comment='AI工具: cursor/claude-code/copilot等')
    model = db.Column(db.String(128), comment='AI模型: claude-sonnet-4/gpt-4等')
    human_author = db.Column(db.String(128), comment='使用者(git作者)')
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'), comment='成员ID')

    total_additions = db.Column(db.Integer, default=0, comment='会话涉及的新增行数')
    total_deletions = db.Column(db.Integer, default=0, comment='会话涉及的删除行数')
    accepted_lines = db.Column(db.Integer, default=0, comment='AI代码被保留的行数')
    overridden_lines = db.Column(db.Integer, default=0, comment='AI代码被修改的行数')
    accepted_rate = db.Column(db.Float, comment='接受率: accepted/(accepted+overridden)')

    session_start = db.Column(db.DateTime, comment='会话开始时间')
    session_end = db.Column(db.DateTime, comment='会话结束时间')
    session_date = db.Column(db.Date, comment='会话日期(便于聚合)')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')

    member = db.relationship('Member', backref=db.backref('prompt_sessions', lazy='dynamic'))

    __table_args__ = (
        db.UniqueConstraint('project_id', 'prompt_id', name='uq_project_prompt'),
        db.Index('ix_prompt_project_commit', 'project_id', 'commit_sha'),
        db.Index('ix_prompt_tool', 'tool'),
        db.Index('ix_prompt_model', 'model'),
        db.Index('ix_prompt_member', 'member_id'),
        db.Index('ix_prompt_date', 'session_date'),
        db.Index('ix_prompt_member_date', 'member_id', 'session_date'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'commit_sha': self.commit_sha,
            'prompt_id': self.prompt_id,
            'tool': self.tool,
            'model': self.model,
            'human_author': self.human_author,
            'member_id': self.member_id,
            'total_additions': self.total_additions,
            'total_deletions': self.total_deletions,
            'accepted_lines': self.accepted_lines,
            'overridden_lines': self.overridden_lines,
            'accepted_rate': self.accepted_rate,
            'session_start': self.session_start.isoformat() if self.session_start else None,
            'session_end': self.session_end.isoformat() if self.session_end else None,
            'session_date': self.session_date.isoformat() if self.session_date else None,
        }
