from netbox.api.viewsets import NetBoxModelViewSet
from .. import models, filtersets
from . import serializers

class AssetGroupViewSet(NetBoxModelViewSet):
    queryset = models.AssetGroup.objects.all()
    serializer_class = serializers.AssetGroupSerializer
    filterset_class = filtersets.AssetGroupFilterSet

class AssetViewSet(NetBoxModelViewSet):
    queryset = models.Asset.objects.all()
    serializer_class = serializers.AssetSerializer
    filterset_class = filtersets.AssetFilterSet
