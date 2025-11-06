"""
用户自定义异常
"""
from rest_framework.exceptions import APIException


class CustomValidationError(APIException):
    """自定义验证错误"""

    def __init__(self, detail=None):
        super().__init__(detail)

