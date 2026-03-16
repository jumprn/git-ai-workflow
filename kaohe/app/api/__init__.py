from app.api.projects import projects_bp
from app.api.members import members_bp
from app.api.coverage import coverage_bp
from app.api.scan import scan_bp
from app.api.export import export_bp
from app.api.dashboard import dashboard_bp
from app.api.config import config_bp


def register_blueprints(app):
    app.register_blueprint(projects_bp)
    app.register_blueprint(members_bp)
    app.register_blueprint(coverage_bp)
    app.register_blueprint(scan_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(config_bp)
