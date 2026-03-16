class BizError(Exception):
    def __init__(self, message='业务错误', code=400):
        self.message = message
        self.code = code
