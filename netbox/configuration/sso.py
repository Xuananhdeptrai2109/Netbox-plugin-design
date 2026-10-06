import os
import requests
import jwt
from social_core.backends.keycloak import KeycloakOAuth2

KEYCLOAK_URL = os.getenv('KEYCLOAK_URL')

if KEYCLOAK_URL:
    KEYCLOAK_REALM = os.getenv('KEYCLOAK_REALM', 'master')
    KEYCLOAK_BACKEND_URL = os.getenv('KEYCLOAK_BACKEND_URL', 'http://keycloak:8080')

    # Bỏ qua lỗi Audience doesn't match bằng cách tắt verify_aud trong PyJWT
    def patch_user_data(self, access_token, *args, **kwargs):
        return jwt.decode(
            access_token,
            key=self.public_key(),
            algorithms=self.algorithm(),
            options={"verify_aud": False},
        )

    KeycloakOAuth2.user_data = patch_user_data

    REMOTE_AUTH_BACKEND = 'social_core.backends.keycloak.KeycloakOAuth2'
    REMOTE_AUTH_AUTO_CREATE_USER = True
    REMOTE_AUTH_DEFAULT_GROUPS = []

    SOCIAL_AUTH_KEYCLOAK_KEY = os.getenv('KEYCLOAK_CLIENT_ID', 'netbox')
    SOCIAL_AUTH_KEYCLOAK_SECRET = os.getenv('KEYCLOAK_CLIENT_SECRET', '')

    # Lấy public key từ biến môi trường hoặc tự động lấy từ API realm Keycloak
    public_key = os.getenv('KEYCLOAK_PUBLIC_KEY')
    if not public_key:
        try:
            resp = requests.get(f"{KEYCLOAK_BACKEND_URL}/realms/{KEYCLOAK_REALM}", timeout=3)
            if resp.status_code == 200:
                public_key = resp.json().get('public_key')
        except Exception:
            pass
    SOCIAL_AUTH_KEYCLOAK_PUBLIC_KEY = public_key

    # URL trình duyệt người dùng chuyển hướng tới đăng nhập
    SOCIAL_AUTH_KEYCLOAK_AUTHORIZATION_URL = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/auth"

    # URL nội bộ NetBox container gọi tới Keycloak container để lấy Token
    SOCIAL_AUTH_KEYCLOAK_ACCESS_TOKEN_URL = f"{KEYCLOAK_BACKEND_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
