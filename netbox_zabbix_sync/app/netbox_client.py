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

    def _ensure_default_prerequisites(self):
        """Đảm bảo NetBox có Site, Device Role, Manufacturer, và Device Type mặc định khi auto-create Device từ Zabbix"""
        nb = self.get_api()
        if not nb:
            return None, None, None

        try:
            # Site
            sites = list(nb.dcim.sites.all())
            site = sites[0] if sites else nb.dcim.sites.create(name="Default Site", slug="default-site")

            # Role
            roles = list(nb.dcim.device_roles.all())
            role = roles[0] if roles else nb.dcim.device_roles.create(name="Server", slug="server", color="009688")

            # Manufacturer & Device Type
            manufacturers = list(nb.dcim.manufacturers.all())
            mfr = manufacturers[0] if manufacturers else nb.dcim.manufacturers.create(name="Generic", slug="generic")

            device_types = list(nb.dcim.device_types.all())
            dtype = device_types[0] if device_types else nb.dcim.device_types.create(model="Generic Device", slug="generic-device", manufacturer=mfr.id)

            return site, role, dtype
        except Exception as e:
            logger.error(f"Lỗi khi đảm bảo Site/Role/DeviceType mặc định: {e}")
            return None, None, None

    def create_zabbix_config(self, payload: Dict[str, Any]) -> bool:
        """Tạo mới ZabbixHostConfig trên NetBox Plugin API"""
        if not settings.NETBOX_URL:
            return False
        try:
            url = f"{settings.NETBOX_URL.rstrip('/')}/api/plugins/netbox-zabbix/zabbix-hosts/"
            headers = {"Content-Type": "application/json", "Accept": "application/json"}
            if settings.NETBOX_TOKEN:
                headers["Authorization"] = f"Token {settings.NETBOX_TOKEN}"
            resp = requests.post(url, json=payload, headers=headers, timeout=5)
            if resp.status_code in [200, 201]:
                logger.info(f"Đã tạo thành công ZabbixHostConfig cho Device ID {payload.get('device')}")
                return True
            else:
                logger.error(f"Lỗi tạo ZabbixHostConfig HTTP {resp.status_code}: {resp.text}")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi gọi API create_zabbix_config: {e}")
            return False

    def update_zabbix_config(self, config_id: int, payload: Dict[str, Any]) -> bool:
        """Cập nhật ZabbixHostConfig & Interfaces trên NetBox Plugin API"""
        if not settings.NETBOX_URL:
            return False
        try:
            url = f"{settings.NETBOX_URL.rstrip('/')}/api/plugins/netbox-zabbix/zabbix-hosts/{config_id}/"
            headers = {"Content-Type": "application/json", "Accept": "application/json"}
            if settings.NETBOX_TOKEN:
                headers["Authorization"] = f"Token {settings.NETBOX_TOKEN}"
            resp = requests.patch(url, json=payload, headers=headers, timeout=5)
            if resp.status_code in [200, 201]:
                logger.info(f"Đã cập nhật thành công ZabbixHostConfig ID {config_id} trên NetBox")
                return True
            else:
                logger.error(f"Lỗi cập nhật ZabbixHostConfig HTTP {resp.status_code}: {resp.text}")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi gọi API update_zabbix_config: {e}")
            return False

    def update_device_name(self, device_id: int, new_name: str) -> bool:
        """Cập nhật Tên Device trong NetBox nếu tên đổi trên Zabbix"""
        nb = self.get_api()
        if not nb:
            return False
        try:
            dev = nb.dcim.devices.get(device_id)
            if dev and dev.name != new_name:
                dev.update({"name": new_name})
                logger.info(f"Đã cập nhật tên NetBox Device ID {device_id} thành '{new_name}'")
                return True
            return False
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật tên Device ID {device_id}: {e}")
            return False

    def create_device_and_zabbix_config(self, host_name: str, visible_name: str, description: str, enabled: bool, templates: List[str], custom_groups: List[str], interfaces: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Tạo mới một Device trong NetBox kèm theo ZabbixHostConfig & Interfaces từ Zabbix Host"""
        nb = self.get_api()
        if not nb:
            return None

        try:
            site, role, dtype = self._ensure_default_prerequisites()
            if not site or not role or not dtype:
                logger.error("Không thể lấy hoặc tạo Site/Role/DeviceType mặc định trên NetBox.")
                return None

            dev = nb.dcim.devices.create(
                name=host_name,
                device_type=dtype.id,
                role=role.id,
                site=site.id,
                status="active"
            )
            logger.info(f"Đã tạo NetBox Device mới thành công: '{host_name}' (ID: {dev.id})")

            config_payload = {
                "device": dev.id,
                "host_name": host_name,
                "visible_name": visible_name or host_name,
                "description": description or "",
                "enabled": enabled,
                "templates": templates,
                "custom_groups": custom_groups,
                "use_device_role_as_group": True,
                "interfaces": interfaces
            }
            self.create_zabbix_config(config_payload)
            return dict(dev)
        except Exception as e:
            logger.error(f"Lỗi khi tạo NetBox Device từ Zabbix Host '{host_name}': {e}")
            return None
