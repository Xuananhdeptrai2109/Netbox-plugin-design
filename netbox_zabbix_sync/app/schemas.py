from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

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
    site: Optional[Dict[str, Any]] = None
    tenant: Optional[Dict[str, Any]] = None
    platform: Optional[Dict[str, Any]] = None

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
