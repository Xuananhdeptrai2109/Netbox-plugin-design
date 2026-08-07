import pynetbox
import requests
import logging
from typing import List, Dict, Any, Optional
from app.config import settings

logger = logging.getLogger("netbox_zabbix_sync.netbox")

class NetBoxClient:
    def get_api(self):
        if settings.NETBOX_URL and settings.NETBOX_TOKEN:
            return pynetbox.api(settings.NETBOX_URL, token=settings.NETBOX_TOKEN)
        return None

    def get_zabbix_configs_map(self) -> Dict[int, Dict[str, Any]]:
        """Lấy tất cả ZabbixHostConfig từ NetBox Plugin API và tạo map {device_id: zabbix_config_dict}"""
        if not settings.NETBOX_URL:
            return {}

        configs_map = {}
        try:
            url = f"{settings.NETBOX_URL.rstrip('/')}/api/plugins/netbox-zabbix/zabbix-hosts/?limit=0"
            headers = {"Accept": "application/json"}
            if settings.NETBOX_TOKEN:
                headers["Authorization"] = f"Token {settings.NETBOX_TOKEN}"
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                for cfg in results:
                    dev_info = cfg.get("device")
                    dev_id = None
                    if isinstance(dev_info, dict):
                        dev_id = dev_info.get("id")
                    elif isinstance(dev_info, int):
                        dev_id = dev_info
                    if dev_id:
                        configs_map[dev_id] = cfg
            else:
                logger.warning(f"Plugin API URL {url} trả về HTTP status {resp.status_code}")
        except Exception as e:
            logger.warning(f"Không thể lấy ZabbixHostConfig từ plugin API: {e}")
        return configs_map

    def get_all_monitored_devices(self) -> List[Dict[str, Any]]:
        """Lấy tất cả các Device trong NetBox kèm theo cấu hình zabbix_config từ Plugin"""
        nb = self.get_api()
        if not nb:
            logger.error("NetBox API client chưa được cấu hình token hoặc URL.")
            return []

        try:
            configs_map = self.get_zabbix_configs_map()
            devices = nb.dcim.devices.all()
            result = []
            for dev in devices:
                dev_dict = dict(dev)
                dev_id = dev_dict.get("id")
                custom_fields = dev_dict.get("custom_fields", {})
                if custom_fields.get("zabbix_monitored") in [True, None]:
                    if dev_id in configs_map:
                        dev_dict["zabbix_config"] = configs_map[dev_id]
                    result.append(dev_dict)
            return result
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách Device từ NetBox: {e}")
            return []

    def get_device_by_id(self, device_id: int) -> Optional[Dict[str, Any]]:
        """Lấy thông tin chi tiết 1 Device theo ID kèm zabbix_config"""
        nb = self.get_api()
        if not nb:
            return None

        try:
            dev = nb.dcim.devices.get(device_id)
            if dev:
                dev_dict = dict(dev)
                configs_map = self.get_zabbix_configs_map()
                if device_id in configs_map:
                    dev_dict["zabbix_config"] = configs_map[device_id]
                return dev_dict
            return None
        except Exception as e:
            logger.error(f"Lỗi khi lấy Device ID {device_id} từ NetBox: {e}")
            return None
