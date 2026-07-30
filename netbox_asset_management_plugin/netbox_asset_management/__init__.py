from netbox.plugins import PluginConfig

class AssetManagementConfig(PluginConfig):
    name = 'netbox_asset_management'
    verbose_name = 'Quản lý tài sản'
    description = 'Chức năng cho phép người dùng quản lý danh sách tài sản có trong hệ thống'
    version = '0.1'
    base_url = 'netbox-asset-management' # Nên dùng gạch ngang cho URL

config = AssetManagementConfig 