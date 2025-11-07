from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from dvadmin.system.models import Users
from dvadmin.utils.custom_exception.Validation import CustomValidationError


class CaptchaViewTest(TestCase):
    """
    验证码：
    *   测试get_system_config_values为True或False结果
    """

    def test_captcha_generation_when_enabled(self):
        with patch(
            "dvadmin.system.views.login.dispatch.get_system_config_values",
            return_value=True,
        ):
            response = self.client.get(reverse("login_captcha"))
            self.assertEqual(response.status_code, 200)
            response_data = response.json()
            self.assertIn("hashkey", response_data["data"])
            self.assertIn("image_base", response_data["data"])

    def test_captcha_when_disabled(self):
        """测试验证码功能关闭时的行为"""
        with patch(
            "dvadmin.system.views.login.dispatch.get_system_config_values",
            return_value=False,
        ):
            response = self.client.get(reverse("login_captcha"))
            self.assertEqual(response.status_code, 200)
            response_data = response.json()
            self.assertEqual(response_data["data"], {})

    def test_captcha_image_validity(self):
        """测试生成的验证码图片数据有效性"""
        with patch(
            "dvadmin.system.views.login.dispatch.get_system_config_values",
            return_value=True,
        ):
            response = self.client.get(reverse("login_captcha"))
            self.assertEqual(response.status_code, 200)
            response_data = response.json()
            # 检查图片数据是否为有效的base64格式
            self.assertIn("data:image/png;base64,", response_data["data"]["image_base"])

    def test_captcha_hashkey_uniqueness(self):
        """测试生成的hashkey唯一性"""
        with patch(
            "dvadmin.system.views.login.dispatch.get_system_config_values",
            return_value=True,
        ):
            response1 = self.client.get(reverse("login_captcha"))
            response2 = self.client.get(reverse("login_captcha"))
            data1 = response1.json()["data"]
            data2 = response2.json()["data"]
            # 确保两次请求生成不同的hashkey
            self.assertNotEqual(data1["hashkey"], data2["hashkey"])

    def test_captcha_concurrent_requests(self):
        """测试高并发请求下的验证码生成功能"""
        with patch(
            "dvadmin.system.views.login.dispatch.get_system_config_values",
            return_value=True,
        ):
            # 创建多个并发请求
            urls = [reverse("login_captcha") for _ in range(10)]

            # 使用线程池模拟并发请求
            with ThreadPoolExecutor(max_workers=5) as executor:
                # 提交所有请求
                future_to_url = {
                    executor.submit(self.client.get, url): url for url in urls
                }

                # 收集所有响应
                responses = []
                for future in as_completed(future_to_url):
                    response = future.result()
                    responses.append(response)

                # 验证所有响应都是成功的
                for response in responses:
                    self.assertEqual(response.status_code, 200)
                    response_data = response.json()
                    self.assertIn("hashkey", response_data["data"])
                    self.assertIn("image_base", response_data["data"])

                # 验证所有hashkey都是唯一的
                hashkeys = [
                    response.json()["data"]["hashkey"] for response in responses
                ]
                self.assertEqual(
                    len(hashkeys), len(set(hashkeys)), "所有hashkey应该是唯一的"
                )


class LoginViewTest(TestCase):
    """
    登录视图测试
    """

    def setUp(self):
        """初始化测试用户"""
        self.user = Users.objects.create_user(
            username="testuser",
            password="testpassword123",
            email="test@example.com",
            name="Test User",
        )
        self.user.is_active = True
        self.user.save()

        # 登录URL
        self.login_url = "/api/login/"

    def test_successful_login_with_username(self):
        """测试使用用户名成功登录"""
        # 先获取验证码
        with patch(
            "dvadmin.system.views.login.dispatch.get_system_config_values",
            return_value=False,  # 禁用验证码以简化测试
        ):
            data = {"username": "testuser", "password": "testpassword123"}
            response = self.client.post(self.login_url, data, format="json")
            self.assertEqual(response.status_code, 200)
            response_data = response.json()
            self.assertEqual(response_data["code"], 2000)
            self.assertIn("data", response_data)
            self.assertIn("access", response_data["data"])
            self.assertIn("refresh", response_data["data"])

    def test_login_with_email(self):
        """测试使用邮箱登录"""
        with patch(
            "dvadmin.system.views.login.dispatch.get_system_config_values",
            return_value=False,  # 禁用验证码以简化测试
        ):
            data = {"username": "test@example.com", "password": "testpassword123"}
            response = self.client.post(self.login_url, data, format="json")
            self.assertEqual(response.status_code, 200)
            response_data = response.json()
            self.assertEqual(response_data["code"], 2000)

    def test_login_with_mobile(self):
        """测试使用手机号登录（模拟）"""
        # 更新用户手机号
        self.user.mobile = "13800138000"
        self.user.save()

        with patch(
            "dvadmin.system.views.login.dispatch.get_system_config_values",
            return_value=False,  # 禁用验证码以简化测试
        ):
            data = {"username": "13800138000", "password": "testpassword123"}
            response = self.client.post(self.login_url, data, format="json")
            self.assertEqual(response.status_code, 200)
            response_data = response.json()
            self.assertEqual(response_data["code"], 2000)

    def test_login_with_invalid_credentials(self):
        """测试使用无效凭据登录"""
        with patch(
            "dvadmin.system.views.login.dispatch.get_system_config_values",
            return_value=False,  # 禁用验证码以简化测试
        ):
            data = {"username": "testuser", "password": "wrongpassword"}
            response = self.client.post(self.login_url, data, format="json")
            # 请求返回200代表请求成功，业务状态码4000代表无效凭据
            self.assertEqual(response.status_code, 200)
            response_data = response.json()
            self.assertEqual(response_data["code"], 4000)

    def test_login_nonexistent_user(self):
        """测试登录不存在的用户"""
        with patch(
            "dvadmin.system.views.login.dispatch.get_system_config_values",
            return_value=False,  # 禁用验证码以简化测试
        ):
            data = {"username": "nonexistent", "password": "password"}
            response = self.client.post(self.login_url, data, format="json")
            # 请求返回200代表请求成功，业务状态码4000代表无效凭据
            self.assertEqual(response.status_code, 200)
            response_data = response.json()
            self.assertEqual(response_data["code"], 4000)

    def test_login_inactive_user(self):
        """测试登录被禁用的用户"""
        # 禁用用户
        self.user.is_active = False
        self.user.save()

        with patch(
            "dvadmin.system.views.login.dispatch.get_system_config_values",
            return_value=False,  # 禁用验证码以简化测试
        ):
            data = {"username": "testuser", "password": "testpassword123"}
            response = self.client.post(self.login_url, data, format="json")
            # 请求返回200代表请求成功，业务状态码4000代表无效凭据
            self.assertEqual(response.status_code, 200)
            response_data = response.json()
            self.assertEqual(response_data["code"], 4000)

    def test_login_with_valid_captcha(self):
        """测试启用验证码时的登录流程"""
        with patch(
            "dvadmin.system.views.login.dispatch.get_system_config_values",
            return_value=True,  # 启用验证码
        ):
            # 需要mock验证码验证方法，使其通过验证
            with patch(
                "dvadmin.system.views.login.LoginSerializer._validate_captcha",
                return_value=None,  # 模拟验证码验证通过
            ):
                data = {
                    "username": "testuser",
                    "password": "testpassword123",
                    "captcha": "test_captcha",
                    "hashkey": "test_hashkey",
                }
                response = self.client.post(self.login_url, data, format="json")
                self.assertEqual(response.status_code, 200)
                response_data = response.json()
                self.assertEqual(response_data["code"], 2000)
                self.assertIn("data", response_data)
                self.assertIn("access", response_data["data"])
                self.assertIn("refresh", response_data["data"])
                # 验证返回了基本的用户信息
                self.assertEqual(response_data["data"]["username"], "testuser")

    def test_login_with_invalid_captcha(self):
        """测试验证码错误时的登录"""
        with patch(
            "dvadmin.system.views.login.dispatch.get_system_config_values",
            return_value=True,  # 启用验证码
        ):
            # 显式mock验证码验证失败
            # side_effect 指定mock方法的副作用（如抛出异常、执行特定函数等）
            # 不执行原始逻辑，而是抛出指定的 CustomValidationError 异常
            with patch(
                "dvadmin.system.views.login.LoginSerializer._validate_captcha",
                side_effect=CustomValidationError(
                    "图片验证码错误"
                ),  # 模拟验证码验证失败
            ):
                data = {
                    "username": "testuser",
                    "password": "testpassword123",
                    "captcha": "wrong_captcha",  # 这里随便写一个
                    "hashkey": "test_hashkey",
                }
                response = self.client.post(self.login_url, data, format="json")
                self.assertEqual(response.status_code, 200)
                response_data = response.json()
                self.assertEqual(response_data["code"], 4000)
