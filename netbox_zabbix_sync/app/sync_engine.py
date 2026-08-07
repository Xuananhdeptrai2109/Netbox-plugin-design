import logging
from typing import Dict, Any, List
from app.config import settings
from app.netbox_client import NetBoxClient
from app.zabbix_client import ZabbixClient
from app.schemas import SyncResult

logger = logging.getLogger("netbox_zabbix_sync.engine")

class SyncEngine:
    def __init__(self):
        self.nb_client = NetBoxClient()
        self.zbx_client = ZabbixClient()

    def _extract_ip(self, primary_ip_obj: Any) -> str:
        """Trích xuất địa chỉ IP thuần (loại bỏ tiền tố CIDR /24)"""
        if not primary_ip_obj:
            return ""
        if isinstance(primary_ip_obj, dict):
            addr = primary_ip_obj.get("address", "")
        elif isinstance(primary_ip_obj, str):
            addr = primary_ip_obj
        else:
            addr = getattr(primary_ip_obj, "address", "")
        return addr.split("/")[0] if addr else ""

    def sync_device_data(self, device_data: Dict[str, Any], event_type: str = "updated") -> bool:
        """Đồng bộ thông tin 1 Device từ NetBox sang Zabbix"""
        device_name = device_data.get("name")
        if not device_name:
            logger.warning("Bỏ qua Device không có Tên (Name).")
            return False

        zabbix_config = device_data.get("zabbix_config") or {}
        custom_fields = device_data.get("custom_fields", {}) or {}

        # 1. Xác định trạng thái Enable / Delete
        enabled = zabbix_config.get("enabled", True) if zabbix_config else True
        zabbix_monitored = custom_fields.get("zabbix_monitored", True)
        if zabbix_monitored is None:
            zabbix_monitored = True

        if event_type == "deleted" or zabbix_monitored is False or enabled is False:
            logger.info(f"Device '{device_name}' (Event: {event_type}, Monitored: {zabbix_monitored}, Enabled: {enabled}). Xử lý hủy/tắt giám sát.")
            if settings.ZABBIX_DELETE_POLICY == "delete":
                return self.zbx_client.delete_host(device_name)
            else:
                return self.zbx_client.disable_host(device_name)

        host_name = zabbix_config.get("host_name") or device_name
        visible_name = zabbix_config.get("visible_name") or host_name
        description = zabbix_config.get("description", "")
        proxy_hostid = zabbix_config.get("proxy_hostid", "")

        # 2. Tự động xác định Host Group từ NetBox Device Role
        group_names = []
        role_obj = device_data.get("device_role") or device_data.get("role")
        if isinstance(role_obj, dict) and role_obj.get("name"):
            role_name = role_obj["name"]
            group_names.append(f"NetBox/{role_name}")

        # Thêm Custom Groups nếu có
        custom_groups = zabbix_config.get("custom_groups", []) if zabbix_config else []
        for cg in custom_groups:
            if cg and cg not in group_names:
                group_names.append(cg)

        if not group_names:
            group_names.append(settings.DEFAULT_ZABBIX_GROUP)

        # Lấy/tạo Group IDs trên Zabbix
        group_ids = []
        for gname in group_names:
            gid = self.zbx_client.get_or_create_hostgroup(gname)
            if gid:
                group_ids.append(gid)

        if not group_ids:
            logger.error(f"Không thể lấy hoặc tạo Host Group cho device '{device_name}'.")
            return False

        # 3. Xác định Templates
        template_names = zabbix_config.get("templates", []) if zabbix_config else []
        if not template_names:
            template_override = custom_fields.get("zabbix_template_override")
            if template_override and isinstance(template_override, str) and template_override.strip():
                template_names = [t.strip() for t in template_override.split(",") if t.strip()]
            else:
                template_names = [settings.DEFAULT_ZABBIX_TEMPLATE]

        template_ids = self.zbx_client.get_template_ids(template_names)

        # 4. Xây dựng danh sách 4 loại Interfaces (Agent, SNMP, IPMI, JMX)
        zbx_interfaces = []
        raw_interfaces = zabbix_config.get("interfaces", []) if zabbix_config else []

        if raw_interfaces:
            for iface in raw_interfaces:
                itype = int(iface.get("interface_type", 1))
                zbx_interfaces.append({
                    "type": itype,
                    "main": 1 if iface.get("is_default", True) else 0,
                    "useip": 1 if iface.get("use_ip", True) else 0,
                    "ip": iface.get("ip_address", ""),
                    "dns": iface.get("dns_name", ""),
                    "port": str(iface.get("port", "10050")),
                    "details": iface.get("details", {})
                })
        else:
            # Fallback lấy Primary IP từ NetBox
            primary_ip = self._extract_ip(device_data.get("primary_ip"))
            if primary_ip:
                zbx_interfaces.append({
                    "type": 1,  # Agent
                    "main": 1,
                    "useip": 1,
                    "ip": primary_ip,
                    "dns": "",
                    "port": "10050"
                })

        if not zbx_interfaces:
            logger.warning(f"Device '{device_name}' chưa có giao diện giám sát khả dụng. Sẽ disable host.")
            return self.zbx_client.disable_host(host_name)

        # 5. Kích hoạt tạo/cập nhật Host trên Zabbix Server
        return self.zbx_client.create_or_update_host(
            host_name=host_name,
            group_ids=group_ids,
            template_ids=template_ids,
            interfaces=zbx_interfaces,
            visible_name=visible_name,
            description=description,
            proxy_hostid=proxy_hostid,
            enabled=enabled
        )

    def run_full_sync(self) -> SyncResult:
        """Chạy tiến trình Full Reconciliation Sync định kỳ (Hybrid Model)"""
        logger.info("--- Bắt đầu tiến trình Hybrid Full Reconciliation Sync ---")
        devices = self.nb_client.get_all_monitored_devices()
        logger.info(f"Tìm thấy {len(devices)} thiết bị có zabbix_monitored=True trong NetBox.")

        processed = 0
        errors: List[str] = []

        for dev in devices:
            try:
                success = self.sync_device_data(dev, event_type="reconciliation")
                if success:
                    processed += 1
                else:
                    errors.append(f"Không thể sync device ID {dev.get('id')} ({dev.get('name')})")
            except Exception as e:
                err_msg = f"Lỗi ngoài dự kiến khi sync device ID {dev.get('id')}: {e}"
                logger.error(err_msg)
                errors.append(err_msg)

        logger.info(f"--- Hoàn thành Full Sync. Đã xử lý thành công: {processed}/{len(devices)} thiết bị ---")
        return SyncResult(
            success=len(errors) == 0,
            message=f"Đã xử lý {processed}/{len(devices)} thiết bị.",
            processed_count=processed,
            errors=errors
        )
