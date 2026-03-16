from flask import jsonify
from app.errors import BizError


def register_error_handlers(app):
    @app.errorhandler(BizError)
    def handle_biz_error(e):
        return jsonify(code=e.code, message=e.message, data=None), e.code

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify(code=400, message=str(e), data=None), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify(code=404, message='资源不存在', data=None), 404

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.error(f'Internal error: {e}', exc_info=True)
        return jsonify(code=500, message='服务器内部错误', data=None), 500
