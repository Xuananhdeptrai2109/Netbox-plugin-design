import logging
from typing import List, Dict, Any, Optional, Tuple
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
        """Lấy danh sách templateid theo danh sách tên Template (hỗ trợ cả visible name, technical name và ID)"""
        if not self.zapi and not self.connect():
            return []

        if not template_names:
            return []

        try:
            all_tmps = self.zapi.template.get(output=["templateid", "name", "host"])
            name_to_id = {}
            for t in all_tmps:
                tid = str(t.get("templateid"))
                if t.get("name"):
                    name_to_id[t["name"].strip().lower()] = tid
                if t.get("host"):
                    name_to_id[t["host"].strip().lower()] = tid
                name_to_id[tid] = tid  # Hỗ trợ truyền thẳng ID chuỗi số

            template_ids = []
            for name in template_names:
                n = str(name).strip().lower()
                if not n:
                    continue
                if n in name_to_id:
                    template_ids.append(name_to_id[n])
                else:
                    logger.warning(f"Không tìm thấy Zabbix Template có tên hoặc ID: '{name}'")
            return list(set(template_ids))
        except Exception as e:
            logger.error(f"Lỗi khi lấy template_ids từ Zabbix: {e}")
            return []

    def get_all_templates(self) -> List[str]:
        """Lấy tất cả danh sách tên Template hiện có trên Zabbix Server để ánh xạ lên NetBox UI"""
        if not self.zapi and not self.connect():
            return []
        try:
            tmps = self.zapi.template.get(output=["templateid", "name", "host"], sortfield="name")
            res = []
            for t in tmps:
                name = t.get("name")
                host = t.get("host")
                if name and name.strip():
                    res.append(name.strip())
                if host and host.strip() and host.strip() != name.strip():
                    res.append(host.strip())
            return sorted(list(set(res)))
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách Templates từ Zabbix: {e}")
            return []

    def get_all_hostgroups(self) -> List[str]:
        """Lấy tất cả danh sách tên Host Groups hiện có trên Zabbix Server để hiển thị trên NetBox UI"""
        if not self.zapi and not self.connect():
            return []
        try:
            groups = self.zapi.hostgroup.get(output=["groupid", "name"], sortfield="name")
            res = [g["name"].strip() for g in groups if isinstance(g, dict) and g.get("name") and g.get("name").strip()]
            return sorted(list(set(res)))
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách Host Groups từ Zabbix: {e}")
            return []

    def get_all_hosts(self) -> List[Dict[str, Any]]:
        """Lấy tất cả các Host trên Zabbix Server kèm Interfaces, Templates, Groups, Tags, Macros"""
        if not self.zapi and not self.connect():
            return []

        try:
            hosts = self.zapi.host.get(
                output=["hostid", "host", "name", "status", "description", "proxy_hostid", "inventory_mode"],
                selectInterfaces="extend",
                selectParentTemplates="extend",
                selectGroups="extend",
                selectTags="extend",
                selectMacros="extend"
            )
            return hosts
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách Host từ Zabbix: {e}")
            return []

    def get_host_by_device_id_or_name(self, host_name: str, device_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Tìm Zabbix Host theo netbox_device_id tag trước, sau đó mới theo host_name"""
        if not self.zapi and not self.connect():
            return None

        try:
            if device_id:
                hosts = self.zapi.host.get(
                    evaltype=0,
                    tags=[{"tag": "netbox_device_id", "value": str(device_id)}],
                    selectInterfaces="extend",
                    selectParentTemplates="extend",
                    selectGroups="extend",
                    selectTags="extend",
                    selectMacros="extend"
                )
                if hosts:
                    return hosts[0]

            hosts = self.zapi.host.get(
                filter={"host": host_name},
                selectInterfaces="extend",
                selectParentTemplates="extend",
                selectGroups="extend",
                selectTags="extend",
                selectMacros="extend"
            )
            if hosts:
                return hosts[0]
            return None
        except Exception as e:
            logger.error(f"Lỗi khi tìm Zabbix Host '{host_name}' (Device ID: {device_id}): {e}")
            return None

    def get_host_by_name(self, host_name: str) -> Optional[Dict[str, Any]]:
        """Tìm Zabbix Host theo Hostname"""
        return self.get_host_by_device_id_or_name(host_name, None)

    def format_zabbix_error(self, e: Exception) -> str:
        """Phân tích ngoại lệ ZabbixAPIException, loại bỏ các mã số kỹ thuật RPC (-32602) và hiển thị câu thông báo tiếng Việt sạch sẽ, dễ hiểu nhất"""
        import re

        if hasattr(e, 'args') and e.args and isinstance(e.args, (list, tuple)):
            err_raw = str(e.args[0])
        else:
            err_raw = str(e)

        # Loại bỏ các tiền tố kỹ thuật như "Error -32602: Invalid params., "
        err_clean = re.sub(r'^Error\s+-?\d+:\s*Invalid params\.?,?\s*', '', err_raw, flags=re.IGNORECASE).strip()
        err_clean = re.sub(r"^['\"]|\(['\"]|['\"],?\s*-?\d+\)?$", '', err_clean).strip()
        err_lower = err_clean.lower()

        # 1. Trùng Đồ thị (Graph)
        if "graph" in err_lower and "already exists" in err_lower:
            m = re.search(r'Graph "(.*?)" already exists', err_clean, re.IGNORECASE)
            graph_name = m.group(1) if m else "chỉ số đồ thị"
            return f"Xung đột Template: Đồ thị '{graph_name}' đã tồn tại trên Host (do thừa kế từ Template khác). Vui lòng vào tab 'Templates' gỡ bỏ Template bị trùng."

        # 2. Trùng Chỉ số (Item)
        if "item" in err_lower and "already exists" in err_lower:
            m = re.search(r'Item "(.*?)" already exists', err_clean, re.IGNORECASE)
            item_name = m.group(1) if m else "chỉ số item"
            return f"Xung đột Template: Chỉ số giám sát (Item) '{item_name}' đã tồn tại trên Host. Vui lòng vào tab 'Templates' gỡ bỏ Template bị trùng."

        # 3. Trùng Cảnh báo (Trigger)
        if "trigger" in err_lower and "already exists" in err_lower:
            return "Xung đột Template: Quy tắc cảnh báo (Trigger) bị trùng lặp giữa các Template được gán. Vui lòng gỡ bớt Template trùng lặp."

        # 4. Thiếu Giao diện Giám sát (Interface)
        if "cannot find host interface" in err_lower:
            return "Thiếu Giao diện Giám sát: Template yêu cầu loại giao diện (SNMP/JMX/IPMI/Agent) nhưng chưa có IP/DNS. Vui lòng kiểm tra lại phần Interfaces."

        # 5. Lỗi Host Group
        if "host group" in err_lower and ("does not exist" in err_lower or "cannot find" in err_lower):
            return "Nhóm Host Group được chọn không tồn tại trên Zabbix Server. Vui lòng kiểm tra lại danh sách Groups."

        return f"Xung đột cấu hình Zabbix: {err_clean}"

    def create_or_update_host(
        self,
        host_name: str,
        group_ids: List[str],
        template_ids: List[str],
        interfaces: Optional[List[Dict[str, Any]]] = None,
        ip_address: Optional[str] = None,
        visible_name: Optional[str] = None,
        description: Optional[str] = None,
        proxy_hostid: Optional[str] = None,
        enabled: bool = True,
        device_id: Optional[int] = None,
        template_names: Optional[List[str]] = None,
        macros: Optional[List[Dict[str, Any]]] = None,
        custom_tags: Optional[List[Dict[str, Any]]] = None,
        inventory_mode: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Tạo mới hoặc cập nhật Zabbix Host với đầy đủ cấu hình interfaces, macros, tags, inventory. Trả về (success, error_message)"""
        if not self.zapi and not self.connect():
            return False, "Không thể kết nối tới Zabbix Server API."

        status = 0 if enabled else 1  # 0: Monitored, 1: Unmonitored/Disabled
        existing_host = self.get_host_by_device_id_or_name(host_name, device_id)

        # Xây dựng danh sách interfaces nếu chưa truyền vào
        if not interfaces:
            interfaces = [{
                "type": 1,  # 1: Agent
                "main": 1,
                "useip": 1,
                "ip": ip_address or "",
                "dns": "",
                "port": "10050"
            }]

        groups = [{"groupid": gid} for gid in group_ids if gid]
        templates = [{"templateid": tid} for tid in template_ids if tid]

        tags = []
        if device_id:
            tags.append({"tag": "netbox_device_id", "value": str(device_id)})

        if custom_tags and isinstance(custom_tags, list):
            for ct in custom_tags:
                if isinstance(ct, dict) and ct.get("tag"):
                    tags.append({"tag": str(ct["tag"]).strip(), "value": str(ct.get("value", "")).strip()})

        zbx_macros = []
        if macros and isinstance(macros, list):
            for m in macros:
                if isinstance(m, dict) and m.get("macro"):
                    zbx_macros.append({
                        "macro": str(m["macro"]).strip(),
                        "value": str(m.get("value", "")).strip(),
                        "description": str(m.get("description", "")).strip()
                    })

        params = {
            "host": host_name,
            "name": visible_name or host_name,
            "status": status,
            "groups": groups,
            "templates": templates,
            "interfaces": interfaces,
        }
        if tags:
            params["tags"] = tags
        if zbx_macros:
            params["macros"] = zbx_macros
        if description:
            params["description"] = description
        if proxy_hostid:
            params["proxy_hostid"] = proxy_hostid

        inv_code = -1
        if inventory_mode == 'manual': inv_code = 0
        elif inventory_mode == 'automatic': inv_code = 1
        params["inventory_mode"] = inv_code

        try:
            if existing_host:
                host_id = existing_host["hostid"]
                existing_ifaces = list(existing_host.get("interfaces", []))

                # Gán interfaceid của Zabbix vào danh sách interfaces mới để Zabbix API cập nhật tại chỗ
                if interfaces:
                    for iface in interfaces:
                        itype = str(iface.get("type", 1))
                        matched = [ex for ex in existing_ifaces if str(ex.get("type")) == itype]
                        if matched:
                            iface["interfaceid"] = matched[0]["interfaceid"]
                            existing_ifaces.remove(matched[0])

                # Xác định danh sách Templates cần unlink & clear vs Templates gán mới
                existing_tmpls = existing_host.get("parentTemplates", [])
                existing_tmpl_ids = [str(t.get("templateid")) for t in existing_tmpls if isinstance(t, dict) and t.get("templateid")]
                requested_tmpl_ids = [str(tid) for tid in template_ids if tid]

                if template_names is not None and len(template_names) > 0 and len(requested_tmpl_ids) < len(template_names):
                    logger.warning(
                        f"Có {len(template_names) - len(requested_tmpl_ids)} template không giải mã được ID trên Zabbix. "
                        f"Bỏ qua 'templates_clear' để bảo vệ dữ liệu Zabbix Host '{host_name}'."
                    )
                    templates_clear_ids = []
                else:
                    templates_clear_ids = [tid for tid in existing_tmpl_ids if tid not in requested_tmpl_ids]

                update_params = {
                    "hostid": host_id,
                    "host": host_name,
                    "name": visible_name or host_name,
                    "status": status,
                    "groups": groups,
                    "templates": [{"templateid": tid} for tid in requested_tmpl_ids],
                    "interfaces": interfaces,
                }
                if templates_clear_ids:
                    update_params["templates_clear"] = [{"templateid": tid} for tid in templates_clear_ids]

                if tags:
                    update_params["tags"] = tags
                if description is not None:
                    update_params["description"] = description

                try:
                    self.zapi.host.update(update_params)
                except Exception as update_err:
                    err_str = str(update_err).lower()
                    if "cannot find host interface" in err_str:
                        logger.warning(f"Zabbix API báo thiếu Giao diện khi gán Template. Tự động bổ sung đủ các loại Giao diện và thử lại...")
                        current_iface_types = {str(i.get("type")) for i in interfaces}
                        default_ip = (interfaces[0].get("ip") if interfaces else "") or "127.0.0.1"

                        all_types = [("1", "10050"), ("2", "161"), ("3", "623"), ("4", "12345")]
                        for type_code, port in all_types:
                            if type_code not in current_iface_types:
                                interfaces.append({
                                    "type": int(type_code),
                                    "main": 1,
                                    "useip": 1,
                                    "ip": default_ip,
                                    "dns": "",
                                    "port": port
                                })
                        update_params["interfaces"] = interfaces
                        self.zapi.host.update(update_params)
                    else:
                        raise update_err

                logger.info(f"Đã cập nhật Zabbix Host: '{host_name}' (ID: {host_id}, Status: {'Monitored' if enabled else 'Disabled'})")
                return True, ""
            else:
                if not enabled:
                    logger.info(f"Bỏ qua tạo Zabbix Host '{host_name}' vì status = disabled.")
                    return True, ""
                
                try:
                    created = self.zapi.host.create(**params)
                except Exception as create_err:
                    err_str = str(create_err).lower()
                    if "cannot find host interface" in err_str:
                        logger.warning(f"Zabbix API báo thiếu Giao diện khi tạo Host. Tự động bổ sung các loại Giao diện và thử lại...")
                        current_iface_types = {str(i.get("type")) for i in interfaces}
                        default_ip = (interfaces[0].get("ip") if interfaces else "") or "127.0.0.1"
                        all_types = [("1", "10050"), ("2", "161"), ("3", "623"), ("4", "12345")]
                        for type_code, port in all_types:
                            if type_code not in current_iface_types:
                                interfaces.append({
                                    "type": int(type_code),
                                    "main": 1,
                                    "useip": 1,
                                    "ip": default_ip,
                                    "dns": "",
                                    "port": port
                                })
                        params["interfaces"] = interfaces
                        created = self.zapi.host.create(**params)
                    else:
                        raise create_err

                logger.info(f"Đã tạo Zabbix Host mới thành công: '{host_name}' (ID: {created['hostids'][0]})")
                return True, ""
        except Exception as e:
            logger.error(f"Lỗi khi create_or_update Zabbix Host '{host_name}': {e}", exc_info=True)
            formatted_err = self.format_zabbix_error(e)
            return False, formatted_err

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

    def get_problems(
        self,
        min_severity: int = 0,
        host_ids: Optional[List[str]] = None,
        group_ids: Optional[List[str]] = None,
        search_problem: Optional[str] = None,
        recent: bool = True,
        time_from: Optional[int] = None,
        tags: Optional[List[Dict[str, str]]] = None,
        acknowledged: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """Lấy danh sách các sự cố (Problems) từ Zabbix Server API kèm thông tin Host, Trigger, Acks, Tags"""
        if not self.zapi and not self.connect():
            return []

        try:
            params: Dict[str, Any] = {
                "output": ["eventid", "objectid", "name", "severity", "clock", "r_clock", "acknowledged", "opdata", "suppressed"],
                "selectTags": "extend",
                "selectAcknowledges": "extend",
                "sortfield": ["eventid"],
                "sortorder": "DESC",
            }
            if recent:
                params["recent"] = True
            if min_severity > 0:
                params["severities"] = [s for s in range(min_severity, 6)]
            if host_ids:
                params["hostids"] = host_ids
            if group_ids:
                params["groupids"] = group_ids
            if search_problem:
                params["search"] = {"name": search_problem}
            if time_from:
                params["time_from"] = time_from
            if tags:
                params["tags"] = tags
            if acknowledged is not None:
                params["acknowledged"] = acknowledged

            raw_problems = self.zapi.problem.get(**params)
            if not raw_problems:
                return []

            # Thu thập objectids (triggerids) để lấy thông tin Host tương ứng
            trigger_ids = list(set([p["objectid"] for p in raw_problems if p.get("objectid")]))
            hosts_map = {}
            if trigger_ids:
                triggers = self.zapi.trigger.get(
                    triggerids=trigger_ids,
                    output=["triggerid", "description", "expression"],
                    selectHosts=["hostid", "host", "name", "inventory"]
                )
                for t in triggers:
                    if t.get("hosts"):
                        hosts_map[t["triggerid"]] = t["hosts"][0]

            # Gộp thông tin host và định dạng dữ liệu trả về cho UI
            result = []
            for p in raw_problems:
                obj_id = p.get("objectid")
                host_info = hosts_map.get(obj_id, {})
                
                # Trích xuất netbox_device_id từ host tags nếu có
                netbox_device_id = None
                p_tags = p.get("tags", [])
                for tag in p_tags:
                    if tag.get("tag") == "netbox_device_id" and tag.get("value"):
                        try:
                            netbox_device_id = int(tag["value"])
                        except ValueError:
                            pass

                acks = p.get("acknowledges", [])
                result.append({
                    "eventid": p.get("eventid"),
                    "objectid": p.get("objectid"),
                    "name": p.get("name"),
                    "severity": int(p.get("severity", 0)),
                    "clock": int(p.get("clock", 0)),
                    "r_clock": int(p.get("r_clock", 0)),
                    "acknowledged": bool(int(p.get("acknowledged", 0))),
                    "opdata": p.get("opdata", ""),
                    "suppressed": p.get("suppressed", "0"),
                    "host": host_info.get("host", ""),
                    "host_name": host_info.get("name", host_info.get("host", "")),
                    "hostid": host_info.get("hostid", ""),
                    "inventory": host_info.get("inventory", {}) or {},
                    "netbox_device_id": netbox_device_id,
                    "tags": p_tags,
                    "acknowledges": acks
                })
            return result
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách problems từ Zabbix: {e}")
            return []

    def acknowledge_problem(self, eventids: List[str], message: str = "", action: int = 6) -> Tuple[bool, str]:
        """Acknowledge (xác nhận) sự cố trên Zabbix API. action=6 tương ứng với Close + Ack"""
        if not self.zapi and not self.connect():
            return False, "Không thể kết nối tới Zabbix API."

        try:
            self.zapi.event.acknowledge(
                eventids=eventids,
                message=message,
                action=action
            )
            return True, "Đã xác nhận sự cố thành công."
        except Exception as e:
            logger.error(f"Lỗi khi acknowledge problem {eventids}: {e}")
            return False, str(e)

