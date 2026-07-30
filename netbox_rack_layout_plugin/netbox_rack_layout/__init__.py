from netbox.plugins import PluginConfig


class RackLayoutConfig(PluginConfig):
    name = 'netbox_rack_layout'
    verbose_name = 'Rack Layout Manager'
    description = 'Plugin quản lý bố cục tủ Rack 2D trên mặt bằng (Floor Plan) cho NetBox'
    version = '0.1'
    base_url = 'rack-layout'

    def ready(self):
        super().ready()
        # Import template_content để đăng ký tab Visualization trên Location detail view
        from . import template_content  # noqa: F401


config = RackLayoutConfig
