from netbox.plugins import PluginMenuButton, PluginMenuItem
from netbox.choices import ButtonColorChoices

# Định nghĩa các nút bấm nhanh (Dấu cộng để thêm mới) bên cạnh tên Menu
asset_buttons = [
    PluginMenuButton(
        link='plugins:netbox_asset_management:asset_add',
        title='Thêm mới tài sản',
        icon_class='mdi mdi-plus-thick',
        color=ButtonColorChoices.GREEN
    )
]

assetgroup_buttons = [
    PluginMenuButton(
        link='plugins:netbox_asset_management:assetgroup_add',
        title='Thêm mới nhóm tài sản',
        icon_class='mdi mdi-plus-thick',
        color=ButtonColorChoices.GREEN
    )
]

# Định nghĩa các mục Menu chính
menu_items = (
    PluginMenuItem(
        link='plugins:netbox_asset_management:asset_list',
        link_text='Quản lý tài sản',
        buttons=asset_buttons
    ),
    PluginMenuItem(
        link='plugins:netbox_asset_management:assetgroup_list',
        link_text='Nhóm tài sản',
        buttons=assetgroup_buttons
    ),
)