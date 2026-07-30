# LOGGING = {}
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
            'level': 'DEBUG', 
        },
        'netbox.plugins': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}