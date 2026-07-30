from netbox.api.viewsets import NetBoxModelViewSet
from .. import filtersets, models
from . import serializers

class ProvinceViewSet(NetBoxModelViewSet):
    queryset = models.Province.objects.all()
    serializer_class = serializers.ProvinceSerializer
    filterset_class = filtersets.ProvinceFilterSet

class DistrictViewSet(NetBoxModelViewSet):
    queryset = models.District.objects.all()
    serializer_class = serializers.DistrictSerializer
    filterset_class = filtersets.DistrictFilterSet

class WardViewSet(NetBoxModelViewSet):
    queryset = models.Ward.objects.all()
    serializer_class = serializers.WardSerializer
    filterset_class = filtersets.WardFilterSet