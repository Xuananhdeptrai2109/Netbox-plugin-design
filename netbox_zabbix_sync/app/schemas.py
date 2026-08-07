from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

class ZabbixInterfaceSchema(BaseModel):
    interface_type: str  # '1': Agent, '2': SNMP, '3': IPMI, '4': JMX
    ip_address: Optional[str] = ""
    dns_name: Optional[str] = ""
    use_ip: bool = True
    port: str = "10050"
    is_default: bool = True
    details: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ZabbixHostConfigSchema(BaseModel):
    host_name: Optional[str] = None
    visible_name: Optional[str] = None
    use_device_role_as_group: bool = True
    custom_groups: List[str] = Field(default_factory=list)
    description: Optional[str] = ""
    proxy_hostid: Optional[str] = ""
    enabled: bool = True
    templates: List[str] = Field(default_factory=list)
    interfaces: List[ZabbixInterfaceSchema] = Field(default_factory=list)

class PrimaryIP(BaseModel):
    id: Optional[int] = None
    address: Optional[str] = None

class DeviceData(BaseModel):
    id: int
    name: Optional[str] = None
    status: Optional[Dict[str, Any]] = None
    primary_ip: Optional[PrimaryIP] = None
    custom_fields: Optional[Dict[str, Any]] = Field(default_factory=dict)
    device_type: Optional[Dict[str, Any]] = None
    device_role: Optional[Dict[str, Any]] = None
    role: Optional[Dict[str, Any]] = None
    site: Optional[Dict[str, Any]] = None
    tenant: Optional[Dict[str, Any]] = None
    platform: Optional[Dict[str, Any]] = None
    zabbix_config: Optional[ZabbixHostConfigSchema] = None

class NetBoxWebhookPayload(BaseModel):
    event: str  # e.g., 'created', 'updated', 'deleted'
    timestamp: str
    model: str  # e.g., 'device'
    username: Optional[str] = None
    request_id: Optional[str] = None
    data: Dict[str, Any]
    snapshots: Optional[Dict[str, Any]] = None

class SyncResult(BaseModel):
    success: bool
    message: str
    processed_count: int = 0
    errors: List[str] = Field(default_factory=list)
