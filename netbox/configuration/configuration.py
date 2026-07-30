import os

ALLOWED_HOSTS = ['*']

DATABASE = {
    'NAME': os.getenv('DB_NAME'),
    'USER': os.getenv('DB_USER'),
    'PASSWORD': os.getenv('DB_PASSWORD'),
    'HOST': os.getenv('DB_HOST'),
    'PORT': os.getenv('DB_PORT'),
}

REDIS = {
    'tasks': {
        'HOST': os.getenv('REDIS_HOST'),
        'PORT': int(os.getenv('REDIS_PORT')),
        'PASSWORD': os.getenv('REDIS_PASSWORD'),
        'DATABASE': 0,
        'SSL': False,
    },
    'caching': {
        'HOST': os.getenv('REDIS_CACHE_HOST'),
        'PORT': int(os.getenv('REDIS_CACHE_PORT')),
        'PASSWORD': os.getenv('REDIS_CACHE_PASSWORD'),
        'DATABASE': 1,
        'SSL': False,
    }
}

SECRET_KEY = os.getenv("SECRET_KEY")
DEVELOPMENT = True
DEVELOPER = True