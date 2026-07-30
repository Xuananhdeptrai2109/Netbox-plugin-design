from netbox.plugins import PluginConfig


class AccessRequestConfig(PluginConfig):
    name = 'netbox_access_request'
    verbose_name = 'Quản lý phiếu yêu cầu ra vào'
    description = 'Chức năng cho phép người dùng quản lý danh sách phiếu yêu cầu ra vào trung tâm dữ liệu'
    version = '0.1'
    base_url = 'netbox-access-request'


config = AccessRequestConfig
