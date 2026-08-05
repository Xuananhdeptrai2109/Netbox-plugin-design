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

        custom_fields = device_data.get("custom_fields", {}) or {}
        zabbix_monitored = custom_fields.get("zabbix_monitored")
        if zabbix_monitored is None:
            zabbix_monitored = True

        template_override = custom_fields.get("zabbix_template_override")

        # Kiểm tra sự kiện bị xóa hoặc bị hủy chọn (zabbix_monitored == False)
        if event_type == "deleted" or zabbix_monitored is False:
            logger.info(f"Device '{device_name}' (Event: {event_type}, Monitored: {zabbix_monitored}). Xử lý hủy giám sát theo Option A.")
            if settings.ZABBIX_DELETE_POLICY == "delete":
                return self.zbx_client.delete_host(device_name)
            else:
                return self.zbx_client.disable_host(device_name)

        # Lấy địa chỉ IP
        ip_address = self._extract_ip(device_data.get("primary_ip"))
        if not ip_address:
            logger.warning(f"Device '{device_name}' được đánh dấu zabbix_monitored=True nhưng chưa có Primary IP. Sẽ disable host.")
            return self.zbx_client.disable_host(device_name)

        # Xác định Host Group
        group_name = settings.DEFAULT_ZABBIX_GROUP
        site = device_data.get("site")
        if isinstance(site, dict) and site.get("name"):
            group_name = f"NetBox/{site['name']}"
        group_id = self.zbx_client.get_or_create_hostgroup(group_name)
        if not group_id:
            logger.error(f"Không thể lấy hoặc tạo Host Group '{group_name}' cho device '{device_name}'.")
            return False

        # Xác định Templates (Tùy chỉnh override hoặc mặc định)
        template_names = []
        if template_override and isinstance(template_override, str) and template_override.strip():
            template_names = [t.strip() for t in template_override.split(",") if t.strip()]
        else:
            template_names = [settings.DEFAULT_ZABBIX_TEMPLATE]

        template_ids = self.zbx_client.get_template_ids(template_names)
        if not template_ids:
            logger.warning(f"Không tìm thấy Template ID tương ứng cho device '{device_name}' ({template_names}).")

        # Cấu hình Host active/monitored
        return self.zbx_client.create_or_update_host(
            host_name=device_name,
            ip_address=ip_address,
            group_id=group_id,
            template_ids=template_ids,
            enabled=True
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
