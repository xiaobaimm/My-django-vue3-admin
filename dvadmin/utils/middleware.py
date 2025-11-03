"""
日志 django中间件
"""
import json
import logging
from typing import Callable

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse, HttpResponseServerError
from rest_framework.request import Request

from dvadmin.system.models import OperationLog
from dvadmin.utils.request_util import (
    get_request_ip,
    get_request_data,
    get_request_path,
    get_verbose_name,
    get_request_user,
    get_os,
    get_browser,
)


class ApiLoggingMiddleware:
    """用于记录API访问日志中间件"""

    def __init__(self, get_response: Callable):
        """
        初始化中间件
        :param get_response: Django 请求处理函数
        """
        self.get_response = get_response
        self.enable = getattr(settings, "API_LOG_ENABLE", False)
        # 如果 API_LOG_METHODS 在 settings 中被显式设置为 None 或其他假值（falsy value）
        # 那么 getattr 会返回那个假值而不是默认的空集合
        # 此时or后面就成立，返回set()
        self.methods = getattr(settings, "API_LOG_METHODS", set()) or set()
    def __call__(self, request):
        """
        标准中间件入口（替代 process_request/process_response）
        :param request: HTTP 请求对象
        :return: HTTP 响应对象
        """

        # 1. 请求处理前（原 process_request）
        self._handle_request(request)
        # 2. 视图处理前（原 process_view）
        self._handle_view(request)
        # 3. 调用后续中间件和视图
        response = self.get_response(request)
        # 4. 响应处理后（原 process_response）
        self._handle_response(request, response)
        return response

    def _handle_request(self,request):
        """处理请求前的初始化"""
        request.request_ip = get_request_ip(request)
        request.request_data = get_request_data(request)
        request.request_path = get_request_path(request)

    def _handle_view(self, request:Request):
        """视图处理前的逻辑（原 process_view）"""
        # 如果API_LOG_ENABLE=False或者request请求不在self.methods列表里就不记录日志，返回
        if not self.enable:
            return

        # 确保 methods 是可迭代对象并且不是 'ALL'
        if self.methods != 'ALL':
            if not isinstance(self.methods, (list, tuple, set)):
                raise TypeError("self.methods 必须是一个可迭代对象（列表、元组或集合）")
            if request.method not in self.methods:
                return
        #在 Django 中，当一个请求到达时，URL 调度器会根据 URL 模式找到对应的视图函数，这个匹配结果就存储在 request.resolver_match 中
        #定义: queryset 是一个包含模型实例集合的属性，通常用于指定视图操作的数据源
        #检查这个视图函数是否属于基于类的视图 and 检查视图函数是否包含 queryset 属性
        resolver_match = getattr(request, 'resolver_match', None)
        if not resolver_match:
            return

        view_func = getattr(resolver_match, 'func', None)
        if not view_func:
            return

        view_cls = getattr(view_func, 'cls', None)
        if not view_cls:
            return

        queryset = getattr(view_cls, 'queryset', None)
        if not queryset:
            return

        try:
            modular_name = get_verbose_name(queryset)
            log = OperationLog(request_modular=modular_name)
            log.save()
            request.request_data['log_id'] = log.id
        except Exception as e:
            # 记录异常信息而不阻塞主流程（可根据需要替换为 logger）
            # print(f"[OperationLog] 日志保存失败: {e}")
            raise e

    def _handle_response(self, request, response):
        """响应处理后的日志记录（原 process_response）"""
        # 如果API_LOG_ENABLE=False或者request请求不在self.methods列表里就不记录日志，返回
        if not self.enable or (self.methods != 'ALL' and request.method not in self.methods):
            return

        if 'log_id' not in request.request_data:
            return

        # 提取
        log_id = request.request_data.pop('log_id')
        # 覆盖敏感信息
        body = getattr(request,'request_data',{})
        if isinstance(body,dict) and 'password' in body:
            body['password'] = '*' * 8

        # 解析响应数据
        response_data = {}
        if hasattr(response,'data') and isinstance(response.data, dict):
            response_data = response.data
        elif response.content:
            try:
                response_data = json.loads(response.content.decode())
            except (TypeError, json.JSONDecodeError):
                pass

        # 构建日志数据
        user = get_request_user(request)
        info = {
            "request_ip": getattr(request, "request_ip", "unknown"),
            "creator": user if not isinstance(user, AnonymousUser) else None,
            "dept_belong_id": getattr(request, "dept_belong_id", None),
            "request_method": request.method,
            "request_path": request.request_path,
            "request_body": request.body,
            "response_code": response_data.get("code"),
            "request_os": get_os(request),
            "request_browser": get_browser(request),
            "request_msg": request.session.get("request_msg"),
            "status": response_data.get("code") == 2000,
            "json_result": {
                "code": response_data.get("code"),
                "msg": response_data.get("msg"),
            },
        }
        # 保存操作日志
        operation_log, _ = OperationLog.objects.update_or_create(defaults=info, id=log_id)
        if not operation_log.request_modular and settings.API_MODEL_MAP.get(request.request_path):
            operation_log.request_modular = settings.API_MODEL_MAP.get(request.request_path)
        operation_log.save()

#copy过来的
class HealthCheckMiddleware:
    """
    存活检查中间件（已使用标准 __call__）
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger("healthz")

    def __call__(self, request):
        if request.method == "GET":
            if request.path == "/readiness":
                return self.readiness(request)
            elif request.path == "/healthz":
                return self.healthz(request)
        return self.get_response(request)

    def healthz(self, request):
        """健康检查端点"""
        return HttpResponse("OK")

    def readiness(self, request):
        """就绪检查端点"""
        try:
            from django.db import connections
            for name in connections:
                cursor = connections[name].cursor()
                cursor.execute("SELECT 1;")
                if cursor.fetchone() is None:
                    return HttpResponseServerError("db: invalid response")
        except Exception as e:
            self.logger.exception(e)
            return HttpResponseServerError("db: cannot connect to database.")

        try:
            from django.core.cache import caches
            from django.core.cache.backends.memcached import BaseMemcachedCache
            for cache in caches.all():
                if isinstance(cache, BaseMemcachedCache):
                    stats = cache._cache.get_stats()
                    if len(stats) != len(cache._servers):
                        return HttpResponseServerError("cache: cannot connect to cache.")
        except Exception as e:
            self.logger.exception(e)
            return HttpResponseServerError("cache: cannot connect to cache.")

        return HttpResponse("OK")
