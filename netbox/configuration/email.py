import os

# Cấu hình SMTP Email cho NetBox
# Sử dụng biến môi trường để bảo mật thông tin nhạy cảm
EMAIL = {
    'SERVER': os.getenv('EMAIL_SERVER', 'localhost'),
    'PORT': int(os.getenv('EMAIL_PORT', 25)),
    'USERNAME': os.getenv('EMAIL_USERNAME', ''),
    'PASSWORD': os.getenv('EMAIL_PASSWORD', ''),
    'USE_SSL': os.getenv('EMAIL_USE_SSL', 'False').lower() == 'true',
    'USE_TLS': os.getenv('EMAIL_USE_TLS', 'False').lower() == 'true',
    'TIMEOUT': 10,
    'FROM_EMAIL': os.getenv('EMAIL_FROM', 'netbox@example.com'),
}
