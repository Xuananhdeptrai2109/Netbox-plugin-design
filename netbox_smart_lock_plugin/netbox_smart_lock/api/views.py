from netbox.api.viewsets import NetBoxModelViewSet
from .. import models, filtersets
from . import serializers

class SmartLockViewSet(NetBoxModelViewSet):
    queryset = models.SmartLock.objects.all()
    serializer_class = serializers.SmartLockSerializer
    filterset_class = filtersets.SmartLockFilterSet
