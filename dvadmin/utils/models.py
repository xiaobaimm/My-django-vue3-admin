from datetime import datetime
from typing import Any

from django.db import models
from rest_framework.request import Request

from My_django_vue3_admin import settings

table_prefix = settings.TABLE_PREFIX  # 数据库表名前缀

class CoreModelManager(models.Manager):
    """当调用Book.objects.all()其实就是调用get_queryset()
    只要是QuerySet类来的方法基本都调用get_queryset()
    这里重写get_queryset和create
    """

    def get_queryset(self):
        """
        重写后返回没有被软删除,flow_work_status=1的数据
        """
        is_deleted = getattr(self.model, "is_soft_deleted", False)
        # 为某些需要特定工作流状态的模型提供默认的查询条件
        # 通常用于标识记录在业务流程中的状态（如待审批、已审批等)
        flow_work_status = getattr(self.model, "flow_work_status", False)
        queryset = super().get_queryset()
        if flow_work_status:
            queryset = queryset.filter(flow_work_status=1)
        if is_deleted:
            queryset = queryset.filter(is_deleted=False)
        return queryset

    def create(self, request: Request = None, **kwargs):
        data = {**kwargs}
        if request:
            request_user = request.user
            data["creator"] = request_user
            # 这里存储user.id，modifier可能有空的
            data["modifier"] = request_user.id
            data["dept_belong_id"] = request_user.dept_id
        return super().create(**data)


class CoreModel(models.Model):
    """
    核心标准抽象模型模型,可直接继承使用
    增加审计字段, 覆盖字段时, 字段名称请勿修改, 必须统一审计字段名称
    """

    id = models.BigAutoField(primary_key=True, help_text="Id", verbose_name="Id")
    description = models.CharField(
        max_length=255, null=True, blank=True, help_text="描述", verbose_name="描述"
    )
    # to=settings.AUTH_USER_MODEL 指向自定义用户模型（这里是 Users 模型） 默认关联到目标模型的主键字段（通常是 id
    # on_delete=models.SET_NULL当关联的用户被删除时，该字段会被设为 NULL
    # related_query_name 反向查询时使用的名称 允许通过 Users 模型反向查询该用户创建的所有记录
    # 例如：user.creator_query.all() 可获取该用户创建的所有对象
    # help_text 在表单中显示的辅助说明文本
    # db_constraint=False 不在数据库层面创建外键约束(确保子表中的外键值必须在父表中存在，或者为NUL)，
    # 提高数据库性能，但牺牲了数据完整性保护
    creator = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_query_name="creator_query",
        help_text="help_text:创建人",
        verbose_name="创建人",
        db_constraint=False,
    )
    modifier = models.CharField(
        max_length=255, null=True, blank=True, help_text="修改人", verbose_name="修改人"
    )
    dept_belong_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="数据归属部门",
        verbose_name="数据归属部门",
    )
    # auto_now_add=True只会创建一次
    create_datetime = models.DateTimeField(
        auto_now_add=True,
        null=True,
        blank=True,
        help_text="创建时间",
        verbose_name="创建时间",
    )
    # auto_now每次都更新时间
    update_datetime = models.DateTimeField(
        auto_now=True,
        null=True,
        blank=True,
        help_text="更新时间",
        verbose_name="更性时间",
    )
    # 使用这个get_queryset会自动过滤软删除的内容，create函数会在创建时额外添加内容
    objects = CoreModelManager()
    # 当你需要访问所有记录，包括那些被软删除的记录时，你可以使用
    all_objects = models.Manager()

    class Meta:
        # 抽象基类在你要将公共信息放入很多模型时会很有用。编写你的基类，并在 Meta 类中填入 abstract=True。
        # 该模型将不会创建任何数据表。当其用作其它模型类的基类时，它的字段会自动添加至子类。
        abstract = True
        verbose_name = "True"
        verbose_name_plural = verbose_name

    # ======================请求工具函数================================
    def get_request_user(self, request: Request):
        """
        request.user 是 Django REST Framework 在请求对象中自动注入的当前认证用户对象
        这个用户对象通常是 Users 模型的实例（因为项目中 Users 继承了 AbstractUser）
        :param request:指明请求类型DRF的Request
        :return:返回user模型
        """
        # 指明返回user，如果没有就返回None
        if getattr(request, "user", None):
            return request.user
        return None

    def get_request_user_id(self, request: Request):
        """
        返回用户id
        :param request:
        :return:
        """
        if getattr(request, "user", None):
            return getattr(request, "id", None)
        return None

    def get_request_name(self, request: Request):
        """
        :return:用户的真实姓名
        """
        if getattr(request, "user", None):
            return getattr(request, "name", None)
        return None

    def get_request_username(self, request: Request):
        """
        返回用户账号
        """
        if getattr(request, "user", None):
            return getattr(request, "username", None)
        return None

    # ================== 数据操作封装=================================
    def common_insert_data(self, request: Request):
        """
        额外为数据添加：
            * 自动添加创建时间
            * 创建者user
            * 创建时间
            * 更改的用户名username
        """
        data = {
            "create_datetime": datetime.now(),
            "creator": self.get_request_user(request),
        }
        return {**data, **self.common_update_data(request)}

    def common_update_data(self, request: Request):
        """
        返回字典：
            * 更新时间
            * 修改人
        """
        return {
            "update_datetime": datetime.now(),
            "modifier": self.get_request_username(request),
        }

    # ==================== 获取字段=================================
    exclude_fields = [
        "_state",
        "pk",
        "id",
        "create_datetime",
        "update_datetime",
        "creator",
        "creator_id",
        "creator_pk",
        "creator_name",
        "modifier",
        "modifier_id",
        "modifier_pk",
        "modifier_name",
        "dept_belong_id",
    ]

    def get_exclude_fields(self):
        return self.exclude_fields

    def get_all_fields(self):
        """
        得到该模型的所有字段和它的父类
        :return list
        """
        return self._meta.fields

    def get_all_fields_names(self):
        """
        只获取所有i字段名
        :return: list
        """
        return [field.name for field in self.get_all_fields()]

    def get_need_fields_names(self):
        """获取字段名，不包括排除的内容"""
        return [
            field.name
            for field in self.get_all_fields()
            if field not in self.exclude_fields
        ]

    # ============模型转换为字典==========================
    def to_data(self):
        """
        将模型转化为字典（去除不包含字段）(注意与to_dict_data区分):
            * 智能处理关联对象：当字段是继承自 CoreModel 的关联对象时，只返回该对象的 id
            * 避免复杂嵌套：防止序列化时出现深层嵌套或循环引用
            * 返回简化数据：关联对象字段只返回主键值，而非完整对象
        """
        res = {}

        for field in self.get_need_fields_names():
            # 取得self对象的field属性
            field_value = getattr(self, field)
            # res[field]为了避免在序列化模型时出现循环引用或复杂嵌套对象：
            # 对于普通字段（如字符串、数字等）：直接返回字段值
            # 对于关联对象字段（如 ForeignKey）：只返回关联对象的 ID，而不是整个关联对象
            res[field] = (
                field_value.id
                if issubclass(field_value.__class__, CoreModel)
                else field_value
            )

    @property
    def DATA(self):
        return self.to_data()

    def to_dict_data(self):
        """需要导出的字段会返回完整的对象（去除不包含字段）
        （注意与to_data区分）
        直接映射字段：直接获取字段值，不进行特殊处理
        保持原始数据结构：如果字段是关联对象，会返回完整的对象
        简单转换：只是将模型字段转换为字典格式
        """
        return {field: getattr(self, field) for field in self.get_need_fields_names()}

    @property
    def DICT_DATA(self):
        return self.to_dict_data()

    def insert(self, request):

        assert (
            self.pk is None
        ), f"模型{self.__class__.__name__}还没有保存到数据中，不能手动指定ID"
        # 断言后，确定数据是安全的
        validated_date = {**self.common_insert_data(request), **self.DICT_DATA}
        # 调用自己写的创建函数
        return self.__class__._default_manager.create(**validated_date)

    def update(self, request, update_data: dict[str, Any] = None):
        # 我们要求更新的内容必须以字典的形式传过来
        assert isinstance(update_data, dict), "update_data必须为字典"
        validated_data = {**self.common_insert_data(request), **update_data}
        for key, value in validated_data.items():
            # 更新时不允许修改pk,id,uuid
            if key in ["pk", "id", "uuid"]:
                continue
            if hasattr(self, key):
                setattr(self, key, value)
        self.save()
        return self

class SoftDeleteQuerySet(models.QuerySet):
    pass

class SoftDeleteManager(models.Manager):
    def __init__(self):
        self.__add_is_del_filter = False
        super().__init__()

    def filter(self, *args, **kwargs):
        # 考虑是否主动传入is_deleted
        if not kwargs.get("is_deleted") is None:
            self.__add_is_del_filter = True
        super().filter(*args,**kwargs)

    def get_queryset(self):
        """
        当用户不指定 is_deleted 时（__add_is_del_filter = False）
        默认自动过滤掉已软删除的记录
            * MyModel.objects.all()
            * MyModel.objects.filter(name='test')
        当用户显式指定 is_deleted 时私有属性会变成True (__add_is_del_filter = True）
            * MyModel.objects.filter(is_deleted=True)   # 查询已软删除的记录
            * MyModel.objects.filter(is_deleted=False)  # 查询未软删除的记录
        """
        if self.__add_is_del_filter:
            # 要操作哪个模型的数据(self.model)
            # 要在哪个数据库上执行查询(using=self._db)
            # exclude(is_deleted=False) 查询时不包含is_deleted=False的字段
            return SoftDeleteQuerySet(self.model, using=self._db).exclude(
                is_deleted=False
            )
        return SoftDeleteQuerySet().exclude(is_deleted=True)

    def get_by_natural_key(self,name):
        """根据不同name获取对应模型实例"""
        return SoftDeleteQuerySet(self.model).get(username=name)


class SoftDeleteModel(models.Model):
    is_deleted = models.BooleanField(default=False, verbose_name="是否软删除")
    objects = SoftDeleteManager()

    class Meta:
        abstract = True
        verbose_name = "软删除模型"
        verbose_name_plural = verbose_name
        # 为 is_deleted 字段创建数据库索引
        # 加快基于软删除状态的查询速度
        indexes = [models.Index(fields=["is_deleted"])]

    def delete(self, using=None, soft_delete=True, *args, **kwargs):
        """
        重写删除方法，开启软删除时相关联的模型内容被软删除
        :param using:如果你的项目配置了多个数据库,可以通过 using 参数指定具体使用哪一个
        :return:
        """
        if soft_delete:
            self.is_deleted = True
            self.save(using=using)
            # 级联软删除关联对象
            # 通过 self._meta.related_objects 获取当前模型的所有关联关系，包括外键关联、一对一、一对多等关系
            for related_object in self._meta.related_objects:
                # 使用 get_accessor_name() 获取反向关联的属性名，getattr获取具体模型实例
                related_model = getattr(self, related_object.get_accessor_name())
                # 处理一对多和多对多的关联对象
                # 如果是一对多或多对多就获取所有关联对象集合
                if related_object.one_to_many or related_object.many_to_many:
                    related_objects = related_model.all()
                elif related_object.one_to_one:
                    related_objects = [related_model]
                else:
                    continue

                for obj in related_objects:
                    obj.delete(soft_delete=True)
        else:
            super().delete(using=using, *args, **kwargs)
