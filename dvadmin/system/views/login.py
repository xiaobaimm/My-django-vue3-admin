import base64
from datetime import datetime, timedelta
from typing import Any

from captcha.models import CaptchaStore
from captcha.views import captcha_image
from django.db.models import Q
from drf_spectacular.utils import extend_schema

from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from My_django_vue3_admin import dispatch
from My_django_vue3_admin.dispatch import get_system_config_values
from dvadmin.system.models import Users
from dvadmin.utils.custom_exception.Validation import CustomValidationError
from dvadmin.utils.json_response import DetailResponse, ErrorResponse


class CaptchaView(APIView):
    """验证码请求视图"""

    authentication_classes = []
    permission_classes = []

    @extend_schema(
        summary="验证码请求",
        responses={"2000": {"type": "string", "example": "成功返回验证码"}},
    )
    def get(self, request: Request):
        data = {}
        if dispatch.get_system_config_values("base.captcha_state"):
            # 生成新的验证码
            hash_key: str = CaptchaStore.generate_key()
            captcha = CaptchaStore.objects.get(hashkey=hash_key)
            # 获取图片（通过 captcha_image 视图）
            image_response = captcha_image(request, captcha.hashkey)
            image_data = image_response.content

            # 转base64
            base64_data = base64.b64encode(image_data).decode("utf-8")
            img_base64 = f"data:image/png;base64,{base64_data}"
            data = {"hashkey": captcha.hashkey, "image_base": img_base64}
        return DetailResponse(data=data)


class LoginSerializer(TokenObtainPairSerializer):
    # 继承 TokenObtainPairSerializer 因为 TokenObtainPairView 的序列化指定api_settings.TOKEN_OBTAIN_SERIALIZER
    # 其实就是 serializers.TokenObtainPairSerializer => 继承TokenObtainSerializer 所以我们要重写 def validate()

    def validate(self, attrs: dict[str, Any]) -> dict[str, str]:

        self._validate_captcha()  # 判断验证码
        try:
            # Q() 对象表示可用于数据库相关操作的 SQL 条件 |(or)来连接三个查询条件
            user = Users.objects.get(
                Q(username=attrs["username"])
                | Q(email=attrs["username"])
                | Q(mobile=attrs["username"])
            )
        except Users.DoesNotExist:
            raise CustomValidationError("用户不存在")
        except Users.MultipleObjectsReturned:
            raise CustomValidationError(
                "您登录的账号存在多个,请联系管理员检查登录账号唯一性"
            )
        if not user.is_active:
            raise CustomValidationError("账号已被锁定,请联系管理员")
        try:
            # 必须重置用户名为username,否则使用邮箱手机号登录会提示密码错误
            attrs["username"] = user.username
            # simplejwt获取刷新和验证令牌access和refresh 并获得认证过的self.user:object
            # TokenObtainPairSerializer =>def validate ==> TokenObtainSerializer def validate 获得self.user
            data: dict[str, Any] = super().validate(attrs=attrs)
            data["username"] = self.user.username
            data["name"] = self.user.name
            data["userId"] = self.user.id
            data["avatar"] = self.user.avatar
            data["user_type"] = self.user.user_type
            data["pwd_change_count"] = self.user.pwd_change_count
            dept = getattr(self.user, "dept", None)
            if dept:
                data["dept_info"] = {"dept_id": dept.id, "dept_name": dept.name}
            role = getattr(self.user, "role", None)
            if role:
                # role 是多对多关系（ManyToManyField）
                # 一个用户可以拥有多个角色
                # 使用 role.values('id', 'name', 'key') 返回的是 QuerySet，包含多个角色的信息
                data["role_info"] = role.values("id", "name", "key")
            # DRF self.context:
            # 自动传递：在序列化器实例化时，DRF 会自动将一些上下文信息传递给 context 属性
            # request：当前的 HTTP 请求对象
            # view：当前处理请求的视图对象
            # format：响应格式
            request: Request = self.context.get("request")
            request.user = self.user
            # 记录登录日志,还没写挖坑中...
            # save_login_log(request=request)
            user.login_error_count = 0
            # update_time 在继承的模型有自动更新功能
            user.last_login = datetime.now()
            user.save()
            return {"code": 2000, "msg": "登入请求成功!", "data": data}
        except Exception as e:
            user.login_error_count += 1
            if user.login_error_count >= 5:
                user.is_active = False
                user.save()
                raise CustomValidationError("用户被禁用,请联系管理员")
            user.save()
            count = 5 - user.login_error_count
            raise CustomValidationError(f"账号/密码错误;重试{count}次后将被锁定~")

    def _validate_captcha(self) -> None:
        # 这里的 attrs有三个字段{'captcha','password','username'}其中captcha是上面定义的序列化字段,
        #'password','username两个字段来自源码 self.username_field指定了是username
        #        self.fields[self.username_field] = serializers.CharField(write_only=True)
        #        self.fields["password"] = PasswordField()
        # initial_data(dict) 是 django-rest-framework 中序列化器（serializer）的一个属性，
        # 它表示传入序列化器的原始数据（通常是来自请求的数据）所以是原始请求数据
        # 检测是否需要验证码
        if get_system_config_values("base.captcha_state"):
            captcha: str = self.initial_data.get("captcha", None)
            if captcha is None:
                raise CustomValidationError("验证码不能为空")
            image_code: CaptchaStore | None = CaptchaStore.objects.filter(
                hashkey=self.initial_data.get("hashkey", None)
            ).first()
            if image_code is None:
                raise CustomValidationError("验证码错误 image_code is None")

            five_minute_ago = datetime.now() - timedelta(minutes=5)
            if five_minute_ago > image_code.expiration:
                image_code.delete()
                raise CustomValidationError("验证码已过期")
            else:
                # 比较大小写
                if image_code.challenge == captcha or image_code.response == captcha:
                    image_code.delete()
                else:
                    image_code.delete()
                    raise CustomValidationError("图片验证码错误")


class LoginView(TokenObtainPairView):
    """
    登录视图
    """

    serializer_class = LoginSerializer
    # 父类 TokenObtainPairView 继承 TokenViewBase，TokenViewBase有 permission_classes = ()
    # 在这只是显示声明
    permission_classes = []
