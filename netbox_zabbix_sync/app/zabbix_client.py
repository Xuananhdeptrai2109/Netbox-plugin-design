import logging
from typing import List, Dict, Any, Optional
from pyzabbix import ZabbixAPI, ZabbixAPIException
from app.config import settings

logger = logging.getLogger("netbox_zabbix_sync.zabbix")

class ZabbixClient:
    def __init__(self):
        self.url = settings.ZABBIX_URL
        self.user = settings.ZABBIX_USER
        self.password = settings.ZABBIX_PASSWORD
        self.token = settings.ZABBIX_TOKEN
        self.zapi = None

    def connect(self) -> bool:
        """Thực hiện kết nối tới Zabbix API Server"""
        try:
            url = settings.ZABBIX_URL
            user = settings.ZABBIX_USER
            password = settings.ZABBIX_PASSWORD
            token = settings.ZABBIX_TOKEN

            self.zapi = ZabbixAPI(url)
            if token:
                self.zapi.login(api_token=token)
            else:
                self.zapi.login(user, password)
            logger.info(f"Kết nối thành công tới Zabbix API tại {url} phiên bản {self.zapi.api_version()}")
            return True
        except Exception as e:
            logger.error(f"Không thể kết nối Zabbix API tại {self.url}: {e}")
            self.zapi = None
            return False

    def get_or_create_hostgroup(self, group_name: str) -> Optional[str]:
        """Lấy groupid của Host Group, tạo mới nếu chưa tồn tại"""
        if not self.zapi and not self.connect():
            return None

        try:
            groups = self.zapi.hostgroup.get(filter={"name": group_name})
            if groups:
                return groups[0]["groupid"]
            
            # Tạo mới Host Group
            created = self.zapi.hostgroup.create(name=group_name)
            logger.info(f"Đã tạo Zabbix Host Group mới: '{group_name}' (ID: {created['groupids'][0]})")
            return created["groupids"][0]
        except Exception as e:
            logger.error(f"Lỗi khi xử lý Zabbix Host Group '{group_name}': {e}")
            return None

    def get_template_ids(self, template_names: List[str]) -> List[str]:
        """Lấy danh sách templateid theo danh sách tên Template"""
        if not self.zapi and not self.connect():
            return []

        template_ids = []
        for name in template_names:
            name = name.strip()
            if not name:
                continue
            try:
                tmps = self.zapi.template.get(filter={"name": name})
                if tmps:
                    template_ids.append(tmps[0]["templateid"])
                else:
                    logger.warning(f"Không tìm thấy Zabbix Template có tên: '{name}'")
            except Exception as e:
                logger.error(f"Lỗi khi tìm Template '{name}': {e}")
        return template_ids

    def get_host_by_name(self, host_name: str) -> Optional[Dict[str, Any]]:
        """Tìm Zabbix Host theo Hostname"""
        if not self.zapi and not self.connect():
            return None

        try:
            hosts = self.zapi.host.get(filter={"host": host_name}, selectInterfaces="extend", selectParentTemplates="extend")
            if hosts:
                return hosts[0]
            return None
        except Exception as e:
            logger.error(f"Lỗi khi tìm Zabbix Host '{host_name}': {e}")
            return None

    def create_or_update_host(
        self,
        host_name: str,
        ip_address: str,
        group_id: str,
        template_ids: List[str],
        enabled: bool = True
    ) -> bool:
        """Tạo mới hoặc cập nhật Zabbix Host"""
        if not self.zapi and not self.connect():
            return False

        status = 0 if enabled else 1  # 0: Monitored, 1: Unmonitored/Disabled
        existing_host = self.get_host_by_name(host_name)

        interfaces = [{
            "type": 1,  # 1: Agent, 2: SNMP
            "main": 1,
            "useip": 1,
            "ip": ip_address,
            "dns": "",
            "port": "10050"
        }]

        groups = [{"groupid": group_id}]
        templates = [{"templateid": tid} for tid in template_ids]

        try:
            if existing_host:
                host_id = existing_host["hostid"]
                # Cập nhật thông tin Host
                update_params = {
                    "hostid": host_id,
                    "status": status,
                    "groups": groups,
                    "templates": templates
                }
                self.zapi.host.update(update_params)
                logger.info(f"Đã cập nhật Zabbix Host: '{host_name}' (ID: {host_id}, Status: {'Monitored' if enabled else 'Disabled'})")
                return True
            else:
                if not enabled:
                    logger.info(f"Bỏ qua tạo Zabbix Host '{host_name}' vì status = disabled.")
                    return True
                
                # Tạo mới Host
                created = self.zapi.host.create(
                    host=host_name,
                    status=status,
                    interfaces=interfaces,
                    groups=groups,
                    templates=templates
                )
                logger.info(f"Đã tạo Zabbix Host mới thành công: '{host_name}' (ID: {created['hostids'][0]})")
                return True
        except Exception as e:
            logger.error(f"Lỗi khi create_or_update Zabbix Host '{host_name}': {e}")
            return False

    def disable_host(self, host_name: str) -> bool:
        """Disable Zabbix Host (set status = 1)"""
        if not self.zapi and not self.connect():
            return False

        existing_host = self.get_host_by_name(host_name)
        if not existing_host:
            logger.info(f"Zabbix Host '{host_name}' không tồn tại, không cần disable.")
            return True

        try:
            self.zapi.host.update(hostid=existing_host["hostid"], status=1)
            logger.info(f"Đã chuyển Zabbix Host '{host_name}' sang trạng thái Disabled (Option A).")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi disable Zabbix Host '{host_name}': {e}")
            return False

    def delete_host(self, host_name: str) -> bool:
        """Delete Zabbix Host khỏi Zabbix Server"""
        if not self.zapi and not self.connect():
            return False

        existing_host = self.get_host_by_name(host_name)
        if not existing_host:
            return True

        try:
            self.zapi.host.delete(existing_host["hostid"])
            logger.info(f"Đã xóa Zabbix Host '{host_name}' khỏi Zabbix (Option B).")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi xóa Zabbix Host '{host_name}': {e}")
            return False
