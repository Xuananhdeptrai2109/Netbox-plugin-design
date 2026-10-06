import os

# Cấu hình ghi log cho NetBox
# Sử dụng biến môi trường tương tự cấu hình EMAIL
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', os.getenv('LOG_LEVEL', 'INFO')),
        },
        'netbox.plugins': {
            'handlers': ['console'],
            'level': os.getenv('PLUGINS_LOG_LEVEL', os.getenv('LOG_LEVEL', 'INFO')),
        },
    },
}