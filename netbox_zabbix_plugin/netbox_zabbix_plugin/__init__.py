from netbox.plugins import PluginConfig

class NetBoxZabbixConfig(PluginConfig):
    name = 'netbox_zabbix_plugin'
    verbose_name = 'NetBox Zabbix Integration'
    description = 'Tích hợp quản lý Zabbix Host trực tiếp trên giao diện Device của NetBox'
    version = '1.0.0'
    base_url = 'netbox-zabbix'

config = NetBoxZabbixConfig
