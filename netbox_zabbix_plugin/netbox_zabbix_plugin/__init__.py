from netbox.plugins import PluginConfig

class NetBoxZabbixConfig(PluginConfig):
    name = 'netbox_zabbix_plugin'
    verbose_name = 'NetBox Zabbix Integration'
    description = 'Tích hợp quản lý Zabbix Host trực tiếp trên giao diện Device của NetBox'
    version = '1.0.0'
    base_url = 'netbox-zabbix'

    def ready(self):
        super().ready()
        try:
            import netbox_zabbix_plugin.widgets
        except Exception as e:
            import logging
            logging.getLogger('netbox_zabbix_plugin').error(f"Could not register ZabbixProblemsWidget: {e}")

config = NetBoxZabbixConfig
