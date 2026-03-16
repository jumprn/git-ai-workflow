import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REPOS_DIR = os.getenv('REPOS_DIR', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'repos'))
    SCAN_HOUR = int(os.getenv('SCAN_HOUR', '2'))
    SCAN_MINUTE = int(os.getenv('SCAN_MINUTE', '0'))


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
