import os
import logging
from urllib.parse import urlparse, urlunparse

from flask import Flask
from app.config import config_map
from app.extensions import db, migrate, cors
from app.errors.handlers import register_error_handlers
from app.api import register_blueprints

logger = logging.getLogger(__name__)


def _ensure_mysql_database(uri: str):
    """If using MySQL, create the database if it doesn't exist."""
    if not uri.startswith('mysql'):
        return
    try:
        import pymysql
        parsed = urlparse(uri)
        db_name = parsed.path.lstrip('/')
        if '?' in db_name:
            db_name = db_name.split('?')[0]
        server_uri = urlunparse(parsed._replace(path='/'))
        from sqlalchemy import create_engine, text
        engine = create_engine(server_uri)
        with engine.connect() as conn:
            conn.execute(text(f'CREATE DATABASE IF NOT EXISTS `{db_name}` '
                              f'DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci'))
            conn.commit()
        engine.dispose()
        logger.info(f'Ensured database "{db_name}" exists')
    except Exception as e:
        logger.warning(f'Could not auto-create database: {e}')


def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config_map.get(config_name, config_map['default']))

    os.makedirs(app.config['REPOS_DIR'], exist_ok=True)

    _ensure_mysql_database(app.config['SQLALCHEMY_DATABASE_URI'])

    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app, resources={r'/api/*': {'origins': '*'}})

    register_error_handlers(app)
    register_blueprints(app)

    with app.app_context():
        from app import models  # noqa: F401
        db.create_all()

    from app.scheduler import init_scheduler
    init_scheduler(app)

    return app
