from netbox.plugins import PluginConfig

class SmartLockConfig(PluginConfig):
    name = 'netbox_smart_lock'
    verbose_name = 'Quản lý Smart Lock'
    description = 'Chức năng cho phép người dùng quản lý danh sách smart lock có trong hệ thống'
    version = '0.1'
    base_url = 'netbox-smart-lock'

config = SmartLockConfig
