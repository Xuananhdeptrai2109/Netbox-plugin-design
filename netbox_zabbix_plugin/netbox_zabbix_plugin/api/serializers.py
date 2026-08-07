from netbox.api.serializers import NetBoxModelSerializer
from rest_framework import serializers
from ..models import ZabbixHostConfig, ZabbixInterfaceConfig

class ZabbixInterfaceConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = ZabbixInterfaceConfig
        fields = (
            'id', 'interface_type', 'ip_address', 'dns_name',
            'use_ip', 'port', 'is_default', 'details'
        )

class ZabbixHostConfigSerializer(NetBoxModelSerializer):
    interfaces = ZabbixInterfaceConfigSerializer(many=True, read_only=True)

    class Meta:
        model = ZabbixHostConfig
        fields = (
            'id', 'display', 'device', 'host_name', 'visible_name',
            'use_device_role_as_group', 'custom_groups', 'description',
            'proxy_hostid', 'enabled', 'templates', 'interfaces',
            'created', 'last_updated'
        )
