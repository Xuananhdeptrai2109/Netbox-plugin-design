from netbox.plugins import PluginMenuItem

menu_items = (
    PluginMenuItem(
        link='plugins:netbox_zabbix_plugin:zabbix_problems',
        link_text='Zabbix Problems',
        permissions=['dcim.view_device'],
    ),
)

