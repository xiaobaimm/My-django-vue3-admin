from rest_framework.views import APIView

from My_django_vue3_admin import dispatch
from dvadmin.system.models import SystemConfig
from dvadmin.utils.json_response import DetailResponse


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
        源码的这里有问题,使用self.request.query_params要先传入request，所以不用
        :param data:
        :return:
        """
        pass
        # if not self.request.query_params.get("key", ""):
        #     return data
        # new_data = {}
        # #若请求有key参数，按要求返回
        # for key in self.request.query_params.get("key", "").split("|"):
        #     if key:
        #         new_data.update(
        #             **dict(filter(lambda x: x[0].startswith(key), data.items()))
        #         )
        # return new_data

    def _filter_system_data(self,data):
        """
        过滤系统配置数据，移除后端专用配置
        :param data: 原始配置数据字典
        :param backend_config: 后端专用配置键列表
        :return: 过滤后的配置数据字典
        """
        backend_config = [
            # parent_id__isnull=False说明过滤得到所有父组件，父组的patent_id=None
            f"{ele.get("parent__key")}.{ele.get("key")}"
            for ele in SystemConfig.objects.filter(
                status=False, parent_id__isnull=False
            ).values("parent__key", "key")
        ]
        filter_data = {}
        for key,value in data.items():
            if key not in backend_config:
                filter_data[key] = value
        return filter_data

    def get(self, request):
        # 获取系统资源
        data: dict = dispatch.get_system_config()
        if not data:
            dispatch.refresh_system_config()
            data = dispatch.get_system_config()
        # 不返回后端专用配置
        # 过滤内容：状态为禁用（status=False）且有父级配置（parent_id__isnull=False）的系统配置项
        # 生成格式：将这些配置项的键名组合成 parent_key.key 格式的字符串列表
        # 用途：在返回系统配置给前端时，排除这些被禁用的配置项，确保前端不会获取到无效的系统配置
        #注释的代码用self._filter_system_data(data=data)代替，容易理解
        # data = dict(filter(lambda x: x[0] not in backend_config, data.items()))
        data = self._filter_system_data(data=data)
        return DetailResponse(data)
