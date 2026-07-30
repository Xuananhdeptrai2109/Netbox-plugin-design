from netbox.plugins import PluginConfig

class UploadFilePluginConfig(PluginConfig):
    name = "upload_file_plugin"
    verbose_name = "Upload File Plugin"
    description = "An example NetBox plugin"
    version = "0.1"
    author = ""
    base_url = "upload_file_plugin"
    required_settings = []
    default_settings = {}
    javascript = ['upload_file_plugin/js/toast.js']

config = UploadFilePluginConfig