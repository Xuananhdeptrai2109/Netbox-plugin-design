from netbox.api.viewsets import NetBoxModelViewSet
from ..models import ZabbixHostConfig
from .serializers import ZabbixHostConfigSerializer

class ZabbixHostConfigViewSet(NetBoxModelViewSet):
    queryset = ZabbixHostConfig.objects.all()
    serializer_class = ZabbixHostConfigSerializer
