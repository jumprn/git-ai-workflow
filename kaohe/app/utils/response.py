from flask import jsonify


def success(data=None, message='success'):
    return jsonify({'code': 200, 'message': message, 'data': data})


def fail(code=400, message='error'):
    return jsonify({'code': code, 'message': message, 'data': None}), code
