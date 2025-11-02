import os

from django.contrib.auth.models import AbstractUser, UserManager
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models

from My_django_vue3_admin import dispatch
from dvadmin.utils.models import CoreModel, table_prefix


class CustomUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        # 下面是比较固定写法，接收返回的user后设置密码
        user = super().create_superuser(username, email, password, **extra_fields)
        user.set_password(password)
        try:
            user.role.add(Role.objects.get(name="管理员"))
            user.save(using=self._db)
            return user
        except ObjectDoesNotExist:
            user.delete()
            raise ValidationError(
                "角色`管理员`不存在, 创建失败, 请先执行python manage.py init"
            )


class Users(CoreModel, AbstractUser):
    """继承AbstractUser，扩展更多字段"""

    username = models.CharField(
        max_length=150,
        unique=True,
        db_index=True,
        verbose_name="用户账号",
        help_text="用户账号",
    )
    email = models.EmailField(
        max_length=255, verbose_name="邮箱", null=True, blank=True, help_text="邮箱"
    )
    mobile = models.CharField(
        max_length=255, verbose_name="电话", null=True, blank=True, help_text="电话"
    )
    avatar = models.CharField(
        max_length=255, verbose_name="头像", null=True, blank=True, help_text="头像"
    )
    name = models.CharField(max_length=40, verbose_name="姓名", help_text="姓名")
    GENDER_CHOICES = (
        (0, "未知"),
        (1, "男"),
        (2, "女"),
    )
    gender = models.IntegerField(
        choices=GENDER_CHOICES,
        default=0,
        verbose_name="性别",
        null=True,
        blank=True,
        help_text="性别",
    )
    USER_TYPE = (
        (0, "后台用户"),
        (1, "前台用户"),
    )
    user_type = models.IntegerField(
        choices=USER_TYPE,
        default=0,
        verbose_name="用户类型",
        null=True,
        blank=True,
        help_text="用户类型",
    )

    post = models.ManyToManyField(
        to="Post", db_constraint=False, verbose_name="关联岗位", help_text="关联岗位"
    )
    role = models.ManyToManyField(
        to="Role",
        blank=True,
        verbose_name="关联角色",
        db_constraint=False,
        help_text="关联角色",
    )
    # related_name反向查询
    current_role = models.ForeignKey(
        to="Role",
        null=True,
        blank=True,
        db_constraint=False,
        on_delete=models.SET_NULL,
        verbose_name="当前登录角色",
        help_text="当前登录角色",
        related_name="current_role_set",
    )
    manage_dept = models.ManyToManyField(
        to="Dept",
        verbose_name="管理部门",
        db_constraint=False,
        blank=True,
        help_text="管理部门",
        related_name="manage_dept_set",
    )
    login_error_count = models.IntegerField(
        default=0, verbose_name="登录错误次数", help_text="登录错误次数"
    )
    pwd_change_count = models.IntegerField(
        default=0, blank=True, verbose_name="密码修改次数", help_text="密码修改次数"
    )
    objects = CustomUserManager()

    class Meta:
        db_table = table_prefix + "system_users"
        verbose_name = "用户表"
        verbose_name_plural = verbose_name
        # “-”表示降序，从大到小
        ordering = ("-create_datetime",)

    def set_password(self, raw_password):
        """raw_password: 用户输入的原始密码（明文）"""
        if raw_password:
            super().set_password(raw_password)
            # super().set_password(
            #     hashlib.md5(raw_password.encode(encoding="UTF-8")).hexdigest()
            # )

    def save(self, *args, **kwargs):
        if self.name == "":
            self.name = self.username
        super().save(*args, **kwargs)


class Post(CoreModel):
    name = models.CharField(
        null=False, max_length=64, verbose_name="岗位名称", help_text="岗位名称"
    )
    code = models.CharField(
        max_length=32, verbose_name="岗位编码", help_text="岗位编码"
    )
    sort = models.IntegerField(default=1, verbose_name="岗位顺序", help_text="岗位顺序")
    STATUS_CHOICES = (
        (0, "离职"),
        (1, "在职"),
    )
    status = models.IntegerField(
        choices=STATUS_CHOICES, default=1, verbose_name="岗位状态", help_text="岗位状态"
    )

    class Meta:
        db_table = table_prefix + "system_post"
        verbose_name = "岗位表"
        verbose_name_plural = verbose_name
        ordering = ("sort",)


class Role(CoreModel):
    name = models.CharField(
        max_length=64, verbose_name="角色名称", help_text="角色名称"
    )
    key = models.CharField(
        max_length=64, unique=True, verbose_name="权限字符", help_text="权限字符"
    )
    sort = models.IntegerField(default=1, verbose_name="角色顺序", help_text="角色顺序")
    status = models.BooleanField(
        default=True, verbose_name="角色状态", help_text="角色状态"
    )

    class Meta:
        db_table = table_prefix + "system_role"
        verbose_name = "角色表"
        verbose_name_plural = verbose_name
        ordering = ("sort",)


class Dept(CoreModel):
    name = models.CharField(
        max_length=64, verbose_name="部门名称", help_text="部门名称"
    )
    key = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        verbose_name="关联字符",
        help_text="关联字符",
    )
    sort = models.IntegerField(default=1, verbose_name="显示排序", help_text="显示排序")
    owner = models.CharField(
        max_length=32, verbose_name="负责人", null=True, blank=True, help_text="负责人"
    )
    phone = models.CharField(
        max_length=32,
        verbose_name="联系电话",
        null=True,
        blank=True,
        help_text="联系电话",
    )
    email = models.EmailField(
        max_length=32, verbose_name="邮箱", null=True, blank=True, help_text="邮箱"
    )
    status = models.BooleanField(
        default=True,
        verbose_name="部门状态",
        null=True,
        blank=True,
        help_text="部门状态",
    )
    parent = models.ForeignKey(
        to="self",
        on_delete=models.CASCADE,
        default=None,
        verbose_name="上级部门",
        db_constraint=False,
        null=True,
        blank=True,
        help_text="上级部门",
    )

    @classmethod
    def _recursion(cls, instance, parent: str, result: str):
        """递归查询部门及其所有子部门"""
        new_instance = getattr(instance, parent, None)
        data = getattr(instance, result, None)
        res = []
        if data:
            res.append(data)
        if new_instance:
            # 如果存在父级，继续递归调用 _recursion 方法
            array = cls._recursion(new_instance, parent, result)
            res += array
        return res

    @classmethod
    def get_region_name(cls, obj):
        """
        获取某个用户的自己部门到自己所有上级名称(不是获取所有部门)
        """
        dept_name_all = cls._recursion(obj, "parent", "name")
        # 收集到的数据顺序是从子到父（子部门 → 父部门 → 祖父部门）
        # 部门层级展示通常需要从上到下的顺序（祖父部门 → 父部门 → 子部门）
        dept_name_all.reverse()
        return "/".join(dept_name_all)

    @classmethod
    def recursion_all_dept(cls, dept_id: int, dept_all_list=None, dept_list=None):
        """
        递归获取部门的所有下级部门
        :param dept_id: 需要获取的id
        :param dept_all_list: 存{'id': 2, 'parent': 1}
        :param dept_list: 最后结果
        :return:
        """
        if not dept_all_list:
            # 接收dict格式{'id': 2, 'parent': 1}
            dept_all_list = Dept.objects.values("id", "parent")
        if dept_list is None:
            dept_list = [dept_id]
        for ele in dept_all_list:
            if ele.get("parent") == dept_id:
                dept_list.append(ele.get("id"))
                cls.recursion_all_dept(ele.get("id"), dept_all_list, dept_list)
        return list(set(dept_list))

    class Meta:
        db_table = table_prefix + "system_dept"
        verbose_name = "部门表"
        verbose_name_plural = verbose_name
        ordering = ("sort",)


class SystemConfig(CoreModel):
    parent = models.ForeignKey(
        to="self",
        on_delete=models.CASCADE,
        db_constraint=False,
        verbose_name="父级",
        help_text="父级,on_delete=models.CASCADE",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=50, verbose_name="标题", help_text="标题")
    key = models.CharField(
        max_length=100, verbose_name="键", help_text="键", db_index=True
    )
    value = models.JSONField(
        max_length=100, verbose_name="值", help_text="值", null=True, blank=True
    )
    sort = models.IntegerField(
        default=0, verbose_name="排序", help_text="排序", blank=True
    )
    status = models.BooleanField(
        default=True, verbose_name="启用状态", help_text="启用状态"
    )
    data_options = models.JSONField(
        verbose_name="数据options", help_text="数据options", null=True, blank=True
    )
    FORM_ITEM_TYPE_LIST = (
        (0, "text"),
        (1, "datetime"),
        (2, "date"),
        (3, "textarea"),
        (4, "select"),
        (5, "checkbox"),
        (6, "radio"),
        (7, "img"),
        (8, "file"),
        (9, "switch"),
        (10, "number"),
        (11, "array"),
        (12, "imgs"),
        (13, "foreignkey"),
        (14, "manytomany"),
        (15, "time"),
    )
    form_item_type = models.IntegerField(
        choices=FORM_ITEM_TYPE_LIST,
        verbose_name="表单类型",
        help_text="表单类型",
        default=0,
        null=True,
    )
    rule = models.JSONField(
        null=True, blank=True, verbose_name="校验规则", help_text="校验规则"
    )
    placeholder = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="提示信息",
        help_text="提示信息",
    )
    setting = models.JSONField(
        null=True, blank=True, verbose_name="配置", help_text="配置"
    )

    def __str__(self):
        return f"{self.title}"

    class Meta:
        db_table = table_prefix + "system_config"
        verbose_name = "系统配置表"
        verbose_name_plural = verbose_name
        # 指定默认查询时的排序规则，用于获取对象列表时，按照 sort 字段升序排列，越小越靠前
        ordering = ("sort",)
        # 确保在 SystemConfig 表中，key 和 parent_id 字段的组合值必须是唯一的
        # 约束规则：在同一父级(parent_id)下，不能存在相同的key值
        unique_together = (("key", "parent_id"),)

    def save(
        self,
        *args,
        force_insert=False,
        force_update=False,
        using=None,
        update_fields=None,
    ):
        super().save(
            *args,
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )
        dispatch.refresh_system_config()  # 有更新则刷新系统配置

    def delete(self, using=None, keep_parents=False):
        res = super().delete(using, keep_parents)
        dispatch.refresh_system_config()
        return res


class OperationLog(CoreModel):
    request_modular = models.CharField(
        max_length=64,
        verbose_name="请求模块",
        null=True,
        blank=True,
        help_text="null=True,blank=True,请求模块",
    )
    request_path = models.CharField(
        max_length=255,
        verbose_name="请求地址",
        null=True,
        blank=True,
        help_text="null=True,blank=True,请求地址",
    )
    request_body = models.TextField(
        null=True,
        blank=True,
        help_text="null=True,blank=True,请求参数",
        verbose_name="请求参数",
    )
    request_method = models.CharField(
        max_length=8,
        null=True,
        blank=True,
        verbose_name="请求方式",
        help_text="null=True,blank=True,请求方式",
    )
    request_msg = models.TextField(
        verbose_name="操作说明", null=True, blank=True, help_text="操作说明"
    )
    request_ip = models.CharField(
        max_length=32,
        verbose_name="请求ip地址",
        null=True,
        blank=True,
        help_text="请求ip地址",
    )
    request_browser = models.CharField(
        max_length=64,
        verbose_name="请求浏览器",
        null=True,
        blank=True,
        help_text="请求浏览器",
    )
    response_code = models.CharField(
        max_length=32,
        verbose_name="响应状态码",
        null=True,
        blank=True,
        help_text="响应状态码",
    )
    request_os = models.CharField(
        max_length=64,
        verbose_name="操作系统",
        null=True,
        blank=True,
        help_text="操作系统",
    )
    json_result = models.TextField(
        verbose_name="返回信息", null=True, blank=True, help_text="返回信息"
    )
    status = models.BooleanField(
        default=False, verbose_name="响应状态", help_text="响应状态"
    )

    class Meta:
        db_table = table_prefix + "system_operation_log"
        verbose_name = "操作日志"
        verbose_name_plural = verbose_name
        ordering = ("-create_datetime",)

    def media_file_name(instance, filename):
        """
        避免文件名冲突：使用 MD5 值代替原始文件名
        文件去重：相同内容的文件具有相同 MD5，避免重复存储
        分散存储：通过 MD5 的前两位字符建立目录结构，避免单一目录下文件过多
        保留扩展名：维持文件原有的扩展名，方便识别文件类型
        """
        h = instance.md5sum
        # 使用 os.path.splitext 分离文件名和扩展名
        basename, ext = os.path.splitext(filename)
        return os.path.join("files", h[:1], h[1:2], h + ext.lower())
