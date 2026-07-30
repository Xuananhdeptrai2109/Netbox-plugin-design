from netbox.api.serializers import NetBoxModelSerializer
from ..models import Asset, AssetGroup

class AssetGroupSerializer(NetBoxModelSerializer):
    class Meta:
        model = AssetGroup
        fields = (
            'id', 'display', 'name', 'slug', 'code', 'status', 
            'description', 'exclude_from_visualization', 'created', 'last_updated'
        )

class AssetSerializer(NetBoxModelSerializer):
    class Meta:
        model = Asset
        fields = (
            'id', 'display', 'name', 'asset_code', 'asset_group', 'status',
            'description', 'device_type', 'model', 'serial_number',
            'manufacturer', 'installation_date', 'purchase_date',
            'warranty_period', 'region', 'site', 'location', 'parent_asset',
            'custom_fields', 'created', 'last_updated'
        )
