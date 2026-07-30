from netbox.plugins import PluginConfig

class ProvincesManagerConfig(PluginConfig):
    name = 'provinces_manager'
    verbose_name = 'Quản lý Địa danh'
    description = 'Quản lý Tỉnh, Huyện, Xã'
    version = '0.1'
    base_url = 'provinces-manager'

config = ProvincesManagerConfig