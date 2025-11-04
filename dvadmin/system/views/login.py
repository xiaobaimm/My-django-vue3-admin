import base64

from captcha.models import CaptchaStore
from captcha.views import captcha_image
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.views import APIView

from My_django_vue3_admin import dispatch
from dvadmin.utils.json_response import DetailResponse


class CaptchaView(APIView):
    """验证码请求视图"""

    authentication_classes = []
    permission_classes = []

    @extend_schema(
        summary="验证码请求",
        responses={"2000": {"type": "string", "example": "成功返回验证码信息"}},
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
