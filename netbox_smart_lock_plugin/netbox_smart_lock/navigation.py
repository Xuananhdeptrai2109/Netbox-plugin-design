from netbox.plugins import PluginMenuButton, PluginMenuItem
from netbox.choices import ButtonColorChoices

smartlock_buttons = [
    PluginMenuButton(
        link='plugins:netbox_smart_lock:smartlock_add',
        title='Thêm mới Smart Lock',
        icon_class='mdi mdi-plus-thick',
        color=ButtonColorChoices.GREEN
    )
]

menu_items = (
    PluginMenuItem(
        link='plugins:netbox_smart_lock:smartlock_list',
        link_text='Quản lý smart lock',
        buttons=smartlock_buttons
    ),
)
