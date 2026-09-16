import logging
from typing import Dict, Any, List, Tuple
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

    def sync_device_data(self, device_data: Dict[str, Any], event_type: str = "updated") -> Tuple[bool, str]:
        """Đồng bộ thông tin 1 Device từ NetBox sang Zabbix"""
        device_name = device_data.get("name")
        if not device_name:
            logger.warning("Bỏ qua Device không có Tên (Name).")
            return False, "Bỏ qua Device không có Tên (Name)."

        zabbix_config = device_data.get("zabbix_config") or {}
        custom_fields = device_data.get("custom_fields", {}) or {}

        # 1. Xác định trạng thái Enable / Delete
        enabled = zabbix_config.get("enabled", True) if zabbix_config else True
        monitored = zabbix_config.get("monitored", True) if (zabbix_config and "monitored" in zabbix_config) else custom_fields.get("zabbix_monitored", True)
        if monitored is None:
            monitored = True

        if not monitored:
            logger.info(f"Device '{device_name}' (Event: {event_type}, Monitored: False). Xử lý hủy/tắt giám sát.")
            res = self.zbx_client.disable_host(device_name)
            return (res, "" if res else f"Không thể vô hiệu hóa Host '{device_name}' trên Zabbix Server.")

        host_name = zabbix_config.get("host_name") or device_name
        visible_name = zabbix_config.get("visible_name") or host_name
        description = zabbix_config.get("description", "")
        proxy_hostid = zabbix_config.get("proxy_hostid", "")

        # 2. Đồng bộ Host Groups đồng đều với NetBox UI & Zabbix UI
        group_names = []
        custom_groups = zabbix_config.get("custom_groups", []) if zabbix_config else []
        if custom_groups and len(custom_groups) > 0:
            group_names = [cg.strip() for cg in custom_groups if cg and cg.strip()]
        else:
            role_obj = device_data.get("device_role") or device_data.get("role")
            if isinstance(role_obj, dict) and role_obj.get("name"):
                role_name = role_obj["name"]
                group_names.append(f"NetBox/{role_name}")

        if not group_names:
            group_names.append(settings.DEFAULT_ZABBIX_GROUP)

        # Lấy/tạo Group IDs trên Zabbix
        group_ids = []
        for gname in group_names:
            gid = self.zbx_client.get_or_create_hostgroup(gname)
            if gid:
                group_ids.append(gid)

        if not group_ids:
            err = f"Không thể tạo hoặc tìm thấy Host Group '{group_names[0]}' trên Zabbix Server."
            logger.error(err)
            return False, err

        # 3. Xác định Templates
        template_names = zabbix_config.get("templates") if (zabbix_config and zabbix_config.get("templates") is not None) else None
        if template_names is None:
            template_override = custom_fields.get("zabbix_template_override")
            if template_override and isinstance(template_override, str) and template_override.strip():
                template_names = [t.strip() for t in template_override.split(",") if t.strip()]
            else:
                template_names = [settings.DEFAULT_ZABBIX_TEMPLATE]

        template_ids = self.zbx_client.get_template_ids(template_names)

        # 4. Xác định Giao diện giám sát (Interfaces) từ NetBox ZabbixPlugin Model
        zbx_interfaces = []
        primary_ip = None
        prim_obj = device_data.get("primary_ip") or device_data.get("primary_ip4")
        if isinstance(prim_obj, dict) and prim_obj.get("address"):
            primary_ip = prim_obj["address"].split("/")[0]

        if zabbix_config and zabbix_config.get("interfaces"):
            for iface in zabbix_config["interfaces"]:
                ip_val = iface.get("ip_address") or primary_ip or ""
                itype = int(iface.get("interface_type", "1"))
                zbx_interfaces.append({
                    "type": itype,
                    "main": 1 if iface.get("is_default", True) else 0,
                    "useip": 1 if iface.get("use_ip", True) else 0,
                    "ip": ip_val,
                    "dns": iface.get("dns_name", ""),
                    "port": str(iface.get("port", "10050")),
                    "details": iface.get("details", {})
                })
        else:
            if primary_ip:
                zbx_interfaces.append({
                    "type": 1,  # Agent
                    "main": 1,
                    "useip": 1,
                    "ip": primary_ip,
                    "dns": "",
                    "port": "10050"
                })

        # Tự động bổ sung các loại Giao diện bị thiếu dựa trên từ khóa của các Template được chọn
        existing_types = {iface["type"] for iface in zbx_interfaces}
        tmpl_str_concat = " ".join(template_names).lower() if template_names else ""

        type_requirements = [
            (1, "10050", ["agent", "os", "linux", "windows", "icmp", "ping", "generic"]),
            (2, "161", ["snmp"]),
            (3, "623", ["ipmi"]),
            (4, "12345", ["jmx", "java", "tomcat", "catalina", "wildfly"]),
        ]

        for itype, default_port, keywords in type_requirements:
            if itype not in existing_types:
                if any(kw in tmpl_str_concat for kw in keywords):
                    logger.info(f"Tự động bổ sung Giao diện loại {itype} (Port {default_port}) cho Host '{device_name}' để tương thích với Template.")
                    zbx_interfaces.append({
                        "type": itype,
                        "main": 1,
                        "useip": 1,
                        "ip": primary_ip,
                        "dns": "",
                        "port": default_port
                    })
                    existing_types.add(itype)

        if not zbx_interfaces:
            # Nếu Host đã tồn tại trên Zabbix có giao diện, giữ nguyên giao diện để tránh vô hiệu hóa nhầm
            existing_zbx = self.zbx_client.get_host_by_name(host_name)
            if existing_zbx and existing_zbx.get("interfaces"):
                logger.info(f"Device '{device_name}' giữ nguyên giao diện hiện có trên Zabbix.")
                return True, ""
            logger.warning(f"Device '{device_name}' chưa có giao diện giám sát khả dụng. Sẽ disable host.")
            res = self.zbx_client.disable_host(host_name)
            return (res, "" if res else f"Thiết bị '{device_name}' chưa khai báo IP giao diện giám sát.")

        # 5. Kích hoạt tạo/cập nhật Host trên Zabbix Server
        return self.zbx_client.create_or_update_host(
            host_name=host_name,
            group_ids=group_ids,
            template_ids=template_ids,
            interfaces=zbx_interfaces,
            visible_name=visible_name,
            description=description,
            proxy_hostid=proxy_hostid,
            enabled=enabled,
            device_id=device_data.get("id"),
            template_names=template_names,
            macros=zabbix_config.get("host_macros"),
            custom_tags=zabbix_config.get("custom_tags"),
            inventory_mode=zabbix_config.get("inventory_mode", "disabled")
        )

    def _is_recently_updated(self, last_updated_str: str, threshold_seconds: int = 60) -> bool:
        """Kiểm tra xem NetBox ZabbixHostConfig có vừa được cập nhật trên NetBox UI gần đây hay không (mặc định 60 giây)"""
        if not last_updated_str:
            return False
        try:
            from datetime import datetime, timezone
            dt = datetime.fromisoformat(last_updated_str.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            return (now - dt).total_seconds() < threshold_seconds
        except Exception:
            return False

    def sync_zabbix_to_netbox(self, zabbix_host: Dict[str, Any], configs_map: Dict[int, Dict[str, Any]], devices_by_name: Dict[str, Dict[str, Any]], force: bool = False) -> bool:
        """Đồng bộ 1 Zabbix Host sang NetBox (Zabbix -> NetBox)"""
        host_name = zabbix_host.get("host", "")
        if not host_name:
            return False

        visible_name = zabbix_host.get("name", "")
        status = str(zabbix_host.get("status", "0"))
        enabled = (status == "0")
        description = zabbix_host.get("description", "")
        proxy_hostid = str(zabbix_host.get("proxy_hostid", "")) if zabbix_host.get("proxy_hostid") and zabbix_host.get("proxy_hostid") != "0" else ""

        # Lấy netbox_device_id và custom tags từ Zabbix Host Tags nếu có
        tags = zabbix_host.get("tags", [])
        nb_dev_id = None
        custom_tags = []
        for t in tags:
            if isinstance(t, dict):
                if t.get("tag") == "netbox_device_id" and t.get("value"):
                    try:
                        nb_dev_id = int(t.get("value"))
                    except ValueError:
                        pass
                elif t.get("tag"):
                    custom_tags.append({"tag": t.get("tag"), "value": t.get("value", "")})

        # Lấy Host Macros từ Zabbix Host
        raw_macros = zabbix_host.get("macros", [])
        host_macros = []
        for m in raw_macros:
            if isinstance(m, dict) and m.get("macro"):
                host_macros.append({
                    "macro": m.get("macro"),
                    "value": m.get("value", ""),
                    "description": m.get("description", "")
                })

        # Lấy Inventory Mode
        inv_mode_code = str(zabbix_host.get("inventory_mode", "-1"))
        inventory_mode = 'disabled'
        if inv_mode_code == '0': inventory_mode = 'manual'
        elif inv_mode_code == '1': inventory_mode = 'automatic'

        # Lấy danh sách Templates
        parent_templates = zabbix_host.get("parentTemplates", [])
        template_names = []
        for t in parent_templates:
            if isinstance(t, dict):
                tname = t.get("name") or t.get("host")
                if tname:
                    template_names.append(tname)

        # Lấy danh sách Groups
        groups = zabbix_host.get("groups", [])
        custom_groups = [g.get("name").strip() for g in groups if isinstance(g, dict) and g.get("name") and g.get("name").strip()]

        # Lấy danh sách Interfaces
        raw_ifaces = zabbix_host.get("interfaces", [])
        parsed_ifaces = []
        for iface in raw_ifaces:
            itype = str(iface.get("type", "1"))
            use_ip = (str(iface.get("useip", "1")) == "1")
            parsed_ifaces.append({
                "interface_type": itype,
                "ip_address": iface.get("ip", ""),
                "dns_name": iface.get("dns", ""),
                "use_ip": use_ip,
                "port": str(iface.get("port", "10050")),
                "is_default": (str(iface.get("main", "1")) == "1"),
                "details": iface.get("details", {}) or {}
            })

        # Tìm Config hiện tại
        existing_config = None

        # 1. Tìm theo nb_dev_id từ Tag
        if nb_dev_id and nb_dev_id in configs_map:
            existing_config = configs_map[nb_dev_id]

        # 2. Phân giải theo tên nếu chưa khớp Tag
        if not existing_config:
            for dev_id, cfg in configs_map.items():
                if cfg.get("host_name") == host_name or cfg.get("visible_name") == host_name or (visible_name and cfg.get("visible_name") == visible_name):
                    existing_config = cfg
                    break

        if existing_config:
            # Nếu không phải ép buộc đồng bộ (force=False) và NetBox vừa sửa trong 5s gần đây, bỏ qua đè từ Zabbix
            if not force and self._is_recently_updated(existing_config.get("last_updated"), threshold_seconds=5):
                logger.info(f"Bỏ qua Zabbix -> NetBox sync cho Host '{host_name}' vì vừa được sửa trên NetBox UI.")
                return True

            cfg_id = existing_config.get("id")
            dev_info = existing_config.get("device")
            dev_id = dev_info.get("id") if isinstance(dev_info, dict) else dev_info
            if dev_id:
                self.nb_client.update_device_name(dev_id, host_name)

            payload = {
                "host_name": host_name,
                "visible_name": visible_name or host_name,
                "description": description,
                "enabled": enabled,
                "proxy_hostid": proxy_hostid,
                "templates": template_names,
                "custom_groups": custom_groups,
                "interfaces": parsed_ifaces,
                "host_macros": host_macros,
                "custom_tags": custom_tags,
                "inventory_mode": inventory_mode
            }
            logger.info(f"Đồng bộ từ Zabbix sang NetBox cho Host '{host_name}' (Config ID: {cfg_id})")
            return self.nb_client.update_zabbix_config(cfg_id, payload)

        elif nb_dev_id or (host_name in devices_by_name):
            dev = devices_by_name.get(host_name)
            dev_id = nb_dev_id or (dev.get("id") if dev else None)
            if dev_id:
                payload = {
                    "device": dev_id,
                    "host_name": host_name,
                    "visible_name": visible_name or host_name,
                    "description": description,
                    "enabled": enabled,
                    "proxy_hostid": proxy_hostid,
                    "templates": template_names,
                    "custom_groups": custom_groups,
                    "use_device_role_as_group": True,
                    "interfaces": parsed_ifaces,
                    "host_macros": host_macros,
                    "custom_tags": custom_tags,
                    "inventory_mode": inventory_mode
                }
                logger.info(f"Tạo ZabbixHostConfig mới trên NetBox cho Device ID {dev_id} ('{host_name}') từ Zabbix Host")
                return self.nb_client.create_zabbix_config(payload)

        # Host chưa có trong NetBox -> Tạo Device mới từ Zabbix Host
        logger.info(f"Host '{host_name}' chưa tồn tại trong NetBox. Tạo Device mới từ Zabbix...")
        created = self.nb_client.create_device_and_zabbix_config(
            host_name=host_name,
            visible_name=visible_name,
            description=description,
            enabled=enabled,
            templates=template_names,
            custom_groups=custom_groups,
            interfaces=parsed_ifaces
        )
        return bool(created)

    def sync_single_zabbix_to_netbox(self, device_id: int) -> bool:
        """Đồng bộ tức thì từ Zabbix sang NetBox cho 1 Device cụ thể (dùng khi Reload/View tab NetBox UI)"""
        try:
            dev = self.nb_client.get_device_by_id(device_id)
            if not dev:
                logger.warning(f"Không tìm thấy Device ID {device_id} trong NetBox.")
                return False

            dev_name = dev.get("name")
            zbx_cfg = dev.get("zabbix_config") or {}
            host_name = zbx_cfg.get("host_name") or dev_name

            zbx_host = self.zbx_client.get_host_by_device_id_or_name(host_name, device_id)
            if not zbx_host:
                logger.info(f"Không tìm thấy Host trên Zabbix cho Device ID {device_id} ('{host_name}').")
                return False

            configs_map = self.nb_client.get_zabbix_configs_map()
            devices_by_name = {dev_name: dev} if dev_name else {}

            return self.sync_zabbix_to_netbox(zbx_host, configs_map, devices_by_name, force=False)
        except Exception as e:
            logger.error(f"Lỗi khi sync tức thì Zabbix -> NetBox cho Device ID {device_id}: {e}")
            return False

    def run_full_sync(self) -> SyncResult:
        """Chạy tiến trình Full Reconciliation Sync 2 chiều (Bidirectional Hybrid Model)"""
        logger.info("--- Bắt đầu tiến trình 2-Way Reconciliation Sync (Zabbix <-> NetBox) ---")
        errors: List[str] = []

        # Phase 1: Zabbix -> NetBox Sync (Ưu tiên đọc và cập nhật các sửa đổi từ Zabbix UI về NetBox trước)
        zbx_hosts = self.zbx_client.get_all_hosts()
        logger.info(f"[Phase 1: Zabbix -> NetBox] Tìm thấy {len(zbx_hosts)} hosts trên Zabbix Server.")
        configs_map = self.nb_client.get_zabbix_configs_map()

        nb_api = self.nb_client.get_api()
        devices_by_name = {}
        if nb_api:
            try:
                all_devs = nb_api.dcim.devices.all()
                for d in all_devs:
                    d_dict = dict(d)
                    if d_dict.get("name"):
                        devices_by_name[d_dict["name"]] = d_dict
            except Exception as e:
                logger.error(f"Lỗi khi lấy danh sách devices_by_name từ NetBox: {e}")

        zbx_processed = 0
        for zh in zbx_hosts:
            try:
                success = self.sync_zabbix_to_netbox(zh, configs_map, devices_by_name)
                if success:
                    zbx_processed += 1
                else:
                    errors.append(f"Không thể sync từ Zabbix sang NetBox cho Host '{zh.get('host')}'")
            except Exception as e:
                err_msg = f"Lỗi Zabbix->NetBox sync host '{zh.get('host')}': {e}"
                logger.error(err_msg)
                errors.append(err_msg)

        # Phase 2: NetBox -> Zabbix Sync (Đẩy các thiết bị NetBox cập nhật lên Zabbix)
        devices = self.nb_client.get_all_monitored_devices()
        logger.info(f"[Phase 2: NetBox -> Zabbix] Tìm thấy {len(devices)} thiết bị NetBox.")
        nb_processed = 0

        for dev in devices:
            try:
                success = self.sync_device_data(dev, event_type="reconciliation")
                if success:
                    nb_processed += 1
                else:
                    errors.append(f"Không thể sync từ NetBox sang Zabbix cho device ID {dev.get('id')} ({dev.get('name')})")
            except Exception as e:
                err_msg = f"Lỗi NetBox->Zabbix sync device ID {dev.get('id')}: {e}"
                logger.error(err_msg)
                errors.append(err_msg)

        logger.info(f"--- Hoàn thành 2-Way Sync. Zabbix->NetBox: {zbx_processed}, NetBox->Zabbix: {nb_processed} ---")
        return SyncResult(
            success=len(errors) == 0,
            message=f"Đã xử lý Zabbix->NetBox: {zbx_processed}, NetBox->Zabbix: {nb_processed}.",
            processed_count=zbx_processed + nb_processed,
            errors=errors
        )
