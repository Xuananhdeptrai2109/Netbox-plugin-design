import pynetbox
import logging
from typing import List, Dict, Any, Optional
from app.config import settings

logger = logging.getLogger("netbox_zabbix_sync.netbox")

class NetBoxClient:
    def get_api(self):
        if settings.NETBOX_URL and settings.NETBOX_TOKEN:
            return pynetbox.api(settings.NETBOX_URL, token=settings.NETBOX_TOKEN)
        return None

    def get_all_monitored_devices(self) -> List[Dict[str, Any]]:
        """Lấy tất cả các Device trong NetBox có custom field zabbix_monitored = True"""
        nb = self.get_api()
        if not nb:
            logger.error("NetBox API client chưa được cấu hình token hoặc URL.")
            return []

        try:
            # Filter devices directly or fetch all devices and filter in Python
            devices = nb.dcim.devices.all()
            result = []
            for dev in devices:
                dev_dict = dict(dev)
                custom_fields = dev_dict.get("custom_fields", {})
                if custom_fields.get("zabbix_monitored") in [True, None]:
                    result.append(dev_dict)
            return result
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách Device từ NetBox: {e}")
            return []

    def get_device_by_id(self, device_id: int) -> Optional[Dict[str, Any]]:
        """Lấy thông tin chi tiết 1 Device theo ID"""
        nb = self.get_api()
        if not nb:
            return None

        try:
            dev = nb.dcim.devices.get(device_id)
            if dev:
                return dict(dev)
            return None
        except Exception as e:
            logger.error(f"Lỗi khi lấy Device ID {device_id} từ NetBox: {e}")
            return None
