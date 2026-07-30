from netbox.api.serializers import NetBoxModelSerializer
from ..models import Province, District, Ward

class ProvinceSerializer(NetBoxModelSerializer):
    class Meta:
        model = Province
        fields = ('id', 'display', 'name', 'code', 'created', 'last_updated')

class DistrictSerializer(NetBoxModelSerializer):
    class Meta:
        model = District
        fields = ('id', 'display', 'name', 'code', 'province', 'created', 'last_updated')

class WardSerializer(NetBoxModelSerializer):
    class Meta:
        model = Ward
        fields = ('id', 'display', 'name', 'code', 'district', 'created', 'last_updated')