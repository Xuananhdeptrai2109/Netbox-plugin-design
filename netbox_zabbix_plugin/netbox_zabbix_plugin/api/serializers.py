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
    interfaces = ZabbixInterfaceConfigSerializer(many=True, required=False)

    class Meta:
        model = ZabbixHostConfig
        fields = (
            'id', 'display', 'device', 'host_name', 'visible_name',
            'use_device_role_as_group', 'custom_groups', 'description',
            'proxy_hostid', 'enabled', 'templates', 'interfaces',
            'host_macros', 'inventory_mode', 'custom_tags',
            'created', 'last_updated'
        )

    def create(self, validated_data):
        interfaces_data = validated_data.pop('interfaces', [])
        host_config = ZabbixHostConfig.objects.create(**validated_data)
        for iface_data in interfaces_data:
            ZabbixInterfaceConfig.objects.create(host_config=host_config, **iface_data)
        return host_config

    def update(self, instance, validated_data):
        interfaces_data = validated_data.pop('interfaces', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if interfaces_data is not None:
            instance.interfaces.all().delete()
            for iface_data in interfaces_data:
                ZabbixInterfaceConfig.objects.create(host_config=instance, **iface_data)
        return instance
