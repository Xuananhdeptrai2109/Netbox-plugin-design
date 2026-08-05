from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    NETBOX_URL: str = "http://netbox:8080"
    NETBOX_TOKEN: str = ""

    ZABBIX_URL: str = "http://zabbix:80/zabbix"
    ZABBIX_USER: str = "Admin"
    ZABBIX_PASSWORD: str = "zabbix"
    ZABBIX_TOKEN: Optional[str] = None

    ZABBIX_DELETE_POLICY: str = "disable"  # 'disable' or 'delete'
    SYNC_INTERVAL_MINUTES: int = 15

    DEFAULT_ZABBIX_GROUP: str = "NetBox Discovered Devices"
    DEFAULT_ZABBIX_TEMPLATE: str = "Linux by Zabbix agent"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
