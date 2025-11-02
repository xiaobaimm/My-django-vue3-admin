from rest_framework.views import APIView


class InitSettingsViewSet(APIView):
    """
    获取初始化配置
    """

    authentication_classes = []
    permission_classes = []

    def fillter_system_config_values(self, data: dict):
        """
        过滤系统初始化配置
        前端可按模块或功能请求特定范围的系统配置，减少不必要的数据传输
        :param data:
        :return:
        """


    def get(self, request):
        pass
