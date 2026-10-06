import os

# Danh sách plugin nạp trực tiếp từ biến môi trường (bỏ qua nếu để trống trong .env)
PLUGINS = [
    plugin for plugin in [
        os.getenv('PLUGIN_1'),
        os.getenv('PLUGIN_2'),
        os.getenv('PLUGIN_3'),
        os.getenv('PLUGIN_4'),
        os.getenv('PLUGIN_5'),
        os.getenv('PLUGIN_6'),
        os.getenv('PLUGIN_7'),
    ] if plugin
]

# Tự động nạp thêm nếu có các biến PLUGIN_8, PLUGIN_9... được khai báo trong .env
for key, value in sorted(os.environ.items()):
    if key.startswith('PLUGIN_') and value and value not in PLUGINS:
        PLUGINS.append(value)

# Cấu hình bổ sung cho các plugin
PLUGINS_CONFIG = {plugin: {} for plugin in PLUGINS}