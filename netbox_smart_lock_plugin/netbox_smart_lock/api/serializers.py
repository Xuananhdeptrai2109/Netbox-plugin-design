from netbox.api.serializers import NetBoxModelSerializer
from ..models import SmartLock

class SmartLockSerializer(NetBoxModelSerializer):
    class Meta:
        model = SmartLock
        fields = (
            'id', 'display', 'name', 'code', 'status', 'description',
            'device_type', 'model', 'serial', 'manufacturer',
            'installation_date', 'purchase_date', 'warranty_period', 'warranty_end',
            'region', 'site', 'location', 'rack', 'rack_face', 'asset_group',
            'custom_fields', 'created', 'last_updated'
        )
