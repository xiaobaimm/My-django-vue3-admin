from rest_framework.views import exception_handler, set_rollback
from rest_framework.exceptions import APIException as DRFAPIException

from dvadmin.utils.json_response import ErrorResponse


def custom_exception_handler(exc, context:dict):
    """
    统一异常拦截处理
    目的:(1)取消所有的500异常响应,统一响应为标准错误返回
        (2)准确显示错误信息
    :param ex:
    :param context:
    :return:
    """
    msg = ''
    code = 4000

    response = exception_handler(exc, context)
    if isinstance(exc, DRFAPIException):
        set_rollback()
        msg = exc.detail
        if isinstance(msg,dict):
            # msg = {
            #     "non_field_errors": ["验证码错误"],
            #     "password": ["密码长度不能少于8位"]
            # }
            # 输出
            # non_field_errors:验证码错误
            # password:密码长度不能少于8位
            error_messages = []
            for k,v in msg:
                for i in v:
                    error_messages.append("%s:%s" % (k, i))
            msg = "; ".join(error_messages)

    return ErrorResponse(msg=msg,code=code)
