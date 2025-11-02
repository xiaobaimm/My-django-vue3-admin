import json

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import AnonymousUser
from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication
from user_agents import parse


def get_request_ip(request):
    """
    获取请求IP
    :param request:
    :return:
    """
    x_forwarded_for = request.META.get("x_forwarded_for", "")
    if x_forwarded_for:
        # 选最后一个，我觉得第一个可能有伪造的，我们信任代理服务器
        ip = x_forwarded_for.split(",")[-1].strip()
        return ip
    # REMOTE_ADDR 是 Web 服务器标准环境变量，总是可用
    ip = request.META.get("REMOTE_ADDR", "") or getattr(request, "request_ip", None)
    return ip or "unknown"


def get_request_data(request):
    """
    获取请求参数
    :param request:
    :return:
    """
    request_data = getattr(request, "request_data", None)
    if request_data:
        return request_data
    # /api/users?page=1&size=10&search=john 会生成字典：{'page': '1', 'size': '10', 'search': 'john'}
    # username=admin&password=123456 会生成字典：{'username': 'admin', 'password': '123456'}
    data: dict = {**request.GET.dict(), **request_data.POST.dict()}
    if not data:
        try:
            body = request.body
            if body:
                body = json.loads(body)
        except Exception as e:
            pass
        if not isinstance(data, dict):
            data = {"data": data}
    return data


def get_request_path(request, *args):
    """
    获取请求路径
    :param request:
    :return:
    """
    request_path = getattr(request, "request_path", None)
    if request_path:
        return request_path
    values = []
    for arg in args:
        if len(arg) == 0:
            continue
        if isinstance(arg, str):
            values.append(arg)
        elif isinstance(arg, (list, tuple, set)):
            values.extend(arg)
        elif isinstance(arg, dict):
            values.extend(arg.values())
    if len(values) == 0:
        # Django原生属性，直接从HTTP请求URL中解析得到路径
        return request.path
    path: str = request.path
    for value in values:
        # /api/users/123/posts/456/
        # 转换为 /api/users/{id}/posts/{id}/，这样可以将具体的资源ID替换为通用的标识符，便于日志记录和路径标准化
        path = path.replace("/" + value, "/" + "{id}")
    return path


def get_verbose_name(queryset=None):
    """
    获取模型类或queryset的verbose_name
    :param queryset:
    :return:
    """
    if queryset is None:
        return ""
    try:
        model_verbose_name = queryset.model._meta.verbose_name
        return model_verbose_name
    except AttributeError as e:
        return ""


def get_request_user(request: Request) -> AbstractBaseUser | None:
    user: AbstractBaseUser = getattr(request, "user", None)
    if user and user.is_authenticated:
        return user

    auth_result = JWTAuthentication().authenticate(request)
    if auth_result is not None:
        user, token = auth_result
    else:
        user = None
    return user or AnonymousUser()


def get_os(request: Request):
    """获取操作系统"""
    us_string: str = request.META["HTTP_USER_AGENT"]
    user_agent = parse(us_string)
    return user_agent.get_os()


def get_browser(request: Request):
    us_string: str = request.META["HTTP_USER_AGENT"]
    user_agent = parse(us_string)
    return user_agent.get_browser()

