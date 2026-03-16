from datetime import datetime
from app.extensions import db


class SystemConfig(db.Model):
    __tablename__ = 'system_configs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    key = db.Column(db.String(128), unique=True, nullable=False, comment='配置键')
    value = db.Column(db.Text, comment='配置值')
    description = db.Column(db.String(256), comment='配置说明')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    def to_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value,
            'description': self.description,
        }
