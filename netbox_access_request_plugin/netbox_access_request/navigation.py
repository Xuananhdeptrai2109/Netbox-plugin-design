from netbox.plugins import PluginMenuButton, PluginMenuItem
from netbox.choices import ButtonColorChoices

# Nút thêm mới phiếu yêu cầu
accessrequest_buttons = [
    PluginMenuButton(
        link='plugins:netbox_access_request:accessrequest_add',
        title='Thêm mới phiếu yêu cầu',
        icon_class='mdi mdi-plus-thick',
        color=ButtonColorChoices.GREEN
    )
]

# Menu items hiển thị trong sidebar
menu_items = (
    PluginMenuItem(
        link='plugins:netbox_access_request:accessrequest_list',
        link_text='Phiếu yêu cầu ra vào',
        buttons=accessrequest_buttons
    ),
)
