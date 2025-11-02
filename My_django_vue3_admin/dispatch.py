from django.db import connection

from My_django_vue3_admin import settings


def is_tenants_mode():
    """
    判断是否为租户模式
    :return:
    ：connection 访问当前租户信息
    """

    # 多租户架构：一种软件架构，允许单个应用实例为多个客户（租户）提供服务
    # 数据隔离：每个租户的数据相互隔离，互不干扰
    # 资源共享：多个租户共享同一应用代码和基础设施
    # 实现方式
    # 独立数据库模式：每个租户拥有独立的数据库
    # 共享数据库独立模式：多个租户共享数据库，但使用不同的数据库模式（schema）
    # 共享数据库共享模式：所有租户共享同一数据库和模式，通过数据字段区分
    return hasattr(connection, "tenant") and connection.tenant.schema_name


def _get_all_system_config():
    data = {}
    from dvadmin.system.models import SystemConfig

    # 先查找所有的父级
    system_config_obj = (
        # Django ORM 允许直接通过 parent_id 进行查询
        SystemConfig.objects.filter(parent_id__isnull=False)
        # .values 只选择指定的字段，而不是返回完整的模型对象
        .values("parent__key", "key", "value", "form_item_type").order_by("sort")
    )
    for system_config in system_config_obj:
        # value定义models.JSONField(),json也许有url键
        value = system_config.get("value", "")
        # form_item_type：(7, "img"),(11, "array"),
        if value and system_config.get("form_item_type") == 7:
            value = value[0].get("url")
        # 如果是数组
        if value and system_config.get("form_item_type") == 11:
            new_value = []
            for ele in value:
                new_value.append(
                    {
                        "key": ele.get("key"),
                        "title": ele.get("title"),
                        "value": ele.get("value"),
                    }
                )
            new_value.sort(key=lambda s: s["key"])
            value = new_value
            # 父.子为key 如: login.login_background = alue
        data[f"{system_config.get('parent__key')}.{system_config.get('key')}"] = value
    return data


def refresh_system_config():
    """
    刷新系统配置
    :return:
    """
    # 判断是租户这里没看懂源码
    if is_tenants_mode():
        from django_tenants.utils import tenant_context, get_tenant_model

        for tenant in get_tenant_model().objects.filter():
            with tenant_context(tenant):
                settings.SYSTEM_CONFIG[connection.tenant.schema_name] = (
                    _get_all_system_config()
                )
    else:
        settings.SYSTEM_CONFIG = _get_all_system_config()


def get_system_config(schema_name=None):
    """
    获取系统配置中所有配置
    1.只传父级的key，返回全部子级，{ "父级key.子级key" : "值" }
    2."父级key.子级key"，返回子级值
    :param schema_name: 对应字典配置的租户schema_name值
    :return:
    """
    # 如果系统配置中没有数据，则进行初始化，一般第一次manage.py init就初始化了，提前有数据了
    if is_tenants_mode():
        dictionary_config = settings.SYSTEM_CONFIG[
            schema_name or connection.tenant.schema_name
        ]
    else:
        dictionary_config = settings.SYSTEM_CONFIG
    return dictionary_config or {}

