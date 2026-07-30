from netbox.plugins import PluginConfig

class UploadFilePluginConfig(PluginConfig):
    name = 'upload_file_plugin'
    verbose_name = 'Upload File Plugin'
    description = 'A plugin to handle file uploads.'
    version = '1.0.0'
    author = 'Your Name'
    base_url = 'upload-file'

config = UploadFilePluginConfig 