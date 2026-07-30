from netbox.plugins import PluginMenuItem

menu_items = (
    PluginMenuItem(
        link='plugins:provinces_manager:province_list',
        link_text='Tỉnh / Thành phố',
    ),
    PluginMenuItem(
        link='plugins:provinces_manager:district_list',
        link_text='Quận / Huyện',
    ),
    PluginMenuItem(
        link='plugins:provinces_manager:ward_list',
        link_text='Xã / Phường',
    ),
)