import logging
import json
from typing import Optional, List
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, HTTPException, status
from apscheduler.schedulers.background import BackgroundScheduler
from app.config import settings
from app.schemas import NetBoxWebhookPayload, SyncResult, AcknowledgeRequestSchema
from app.sync_engine import SyncEngine

# Cấu hình Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("netbox_zabbix_sync.main")

sync_engine = SyncEngine()
scheduler = BackgroundScheduler()

def scheduled_full_sync():
    """Hàm wrapper cho Scheduled Reconciliation Job"""
    try:
        sync_engine.run_full_sync()
    except Exception as e:
        logger.error(f"Lỗi khi chạy scheduled full sync: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Quản lý vòng đời FastAPI & APScheduler Background Job"""
    logger.info("Khởi động NetBox-Zabbix Hybrid Sync Service...")
    # Thêm background job định kỳ cho Full Reconciliation Sync (chạy ngay lập tức khi khởi động + chạy lại mỗi SYNC_INTERVAL_MINUTES phút)
    scheduler.add_job(
        scheduled_full_sync,
        trigger="interval",
        minutes=settings.SYNC_INTERVAL_MINUTES,
        next_run_time=datetime.now(),
        id="full_reconciliation_sync",
        replace_existing=True
    )
    scheduler.start()
    logger.info(f"APScheduler đã được khởi động. Full Sync chạy ngay lập tức và lặp lại mỗi {settings.SYNC_INTERVAL_MINUTES} phút.")

    yield

    logger.info("Dừng NetBox-Zabbix Hybrid Sync Service...")
    scheduler.shutdown()

app = FastAPI(
    title="NetBox Zabbix Hybrid Sync Service",
    description="Dịch vụ đồng bộ Hybrid giữa NetBox và Zabbix kết hợp Real-time Webhook và Reconciliation định kỳ.",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """Endpoint kiểm tra sức khỏe dịch vụ"""
    return {"status": "ok", "service": "netbox_zabbix_sync"}

def process_webhook_event(payload: NetBoxWebhookPayload):
    """Background Task xử lý webhook payload để giải phóng HTTP response cho NetBox ngay lập tức"""
    logger.info(f"Nhận sự kiện Webhook: Model='{payload.model}', Event='{payload.event}'")
    if payload.model.lower() != "device":
        logger.info(f"Bỏ qua sự kiện cho model '{payload.model}'. Dịch vụ chỉ xử lý 'device'.")
        return

    try:
        sync_engine.sync_device_data(payload.data, event_type=payload.event)
    except Exception as e:
        logger.error(f"Lỗi khi xử lý Webhook event cho Device: {e}")

@app.post("/webhook", status_code=status.HTTP_200_OK)
def receive_webhook(payload: NetBoxWebhookPayload, background_tasks: BackgroundTasks):
    """
    Endpoint tiếp nhận Webhook POST từ NetBox khi có thay đổi Device
    Được thiết kế để phản hồi HTTP 200 OK ngay lập tức và đưa công việc vào BackgroundTask.
    """
    background_tasks.add_task(process_webhook_event, payload)
    return {"status": "accepted", "message": "Webhook payload queued for processing"}

@app.post("/webhook/zabbix", status_code=status.HTTP_200_OK)
def receive_zabbix_webhook(payload: dict, background_tasks: BackgroundTasks):
    """
    Endpoint tiếp nhận Webhook POST từ Zabbix (Media Type Webhook hoặc Action Script)
    Kích hoạt 2-Way Sync cho Host chỉ định hoặc chạy Full Sync.
    """
    def process_zbx_webhook(data: dict):
        logger.info(f"Nhận sự kiện Webhook từ Zabbix: {data}")
        host_name = data.get("host") or data.get("hostname")
        if host_name:
            zbx_host = sync_engine.zbx_client.get_host_by_name(host_name)
            if zbx_host:
                configs_map = sync_engine.nb_client.get_zabbix_configs_map()
                nb_api = sync_engine.nb_client.get_api()
                devices_by_name = {}
                if nb_api:
                    try:
                        all_devs = nb_api.dcim.devices.all()
                        devices_by_name = {dict(d).get("name"): dict(d) for d in all_devs if dict(d).get("name")}
                    except Exception as e:
                        logger.error(f"Lỗi lấy devices_by_name: {e}")
                sync_engine.sync_zabbix_to_netbox(zbx_host, configs_map, devices_by_name)
        else:
            sync_engine.run_full_sync()

    background_tasks.add_task(process_zbx_webhook, payload)
    return {"status": "accepted", "message": "Zabbix webhook payload queued for processing"}

@app.post("/sync/device/{device_id}", status_code=status.HTTP_200_OK)
def sync_single_device(device_id: int):
    """Endpoint kích hoạt đồng bộ TỨC THÌ NetBox -> Zabbix cho 1 Device khi chỉnh sửa ở NetBox UI"""
    logger.info(f"Yêu cầu đồng bộ tức thì NetBox -> Zabbix cho Device ID {device_id}")
    try:
        dev = sync_engine.nb_client.get_device_by_id(device_id)
        if dev:
            success, err_msg = sync_engine.sync_device_data(dev, event_type="updated")
            if success:
                return {"status": "ok", "device_id": device_id}
            else:
                return {"status": "error", "device_id": device_id, "message": err_msg}
        else:
            logger.warning(f"Không tìm thấy Device ID {device_id} trong NetBox")
            return {"status": "not_found", "device_id": device_id, "message": f"Không tìm thấy Device ID {device_id} trong NetBox"}
    except Exception as e:
        logger.error(f"Lỗi khi sync device {device_id}: {e}", exc_info=True)
        formatted_err = sync_engine.zbx_client.format_zabbix_error(e)
        return {"status": "error", "device_id": device_id, "message": formatted_err}

@app.post("/sync/zabbix-to-netbox/{device_id}", status_code=status.HTTP_200_OK)
def sync_zabbix_to_netbox_single(device_id: int):
    """Endpoint kích hoạt đồng bộ tức thì Zabbix -> NetBox cho 1 Device duy nhất khi Reload/View tab NetBox UI"""
    logger.info(f"Yêu cầu đồng bộ tức thì Zabbix -> NetBox cho Device ID {device_id}")
    success = sync_engine.sync_single_zabbix_to_netbox(device_id)
    return {"status": "ok" if success else "no_change", "device_id": device_id}

@app.get("/zabbix/templates", status_code=status.HTTP_200_OK)
def get_zabbix_templates():
    """Endpoint lấy tất cả danh sách Zabbix Templates từ Zabbix Server để hiển thị trên NetBox UI"""
    templates = sync_engine.zbx_client.get_all_templates()
    return {"templates": templates}

@app.get("/zabbix/hostgroups", status_code=status.HTTP_200_OK)
def get_zabbix_hostgroups():
    """Endpoint lấy tất cả danh sách Zabbix Host Groups từ Zabbix Server để hiển thị trên NetBox UI"""
    hostgroups = sync_engine.zbx_client.get_all_hostgroups()
    return {"hostgroups": hostgroups}

@app.get("/zabbix/problems", status_code=status.HTTP_200_OK)
def get_zabbix_problems(
    min_severity: int = 0,
    search: Optional[str] = None,
    recent: bool = True,
    host_name: Optional[str] = None,
    tags: Optional[str] = None,
    inventory: Optional[str] = None
):
    """Endpoint lấy danh sách Zabbix Active/Recent Problems cho NetBox Widget & View"""
    host_ids = None
    if host_name:
        zhost = sync_engine.zbx_client.get_host_by_name(host_name)
        if zhost:
            host_ids = [zhost["hostid"]]

    tag_filters = []
    if tags:
        try:
            for tag in json.loads(tags):
                if not isinstance(tag, dict) or not tag.get('name'):
                    continue
                tag_filters.append({
                    'tag': tag['name'],
                    'value': tag.get('value', ''),
                    'operator': 1 if tag.get('operator') == 'equals' else 0,
                })
        except (TypeError, ValueError, json.JSONDecodeError):
            logger.warning("Bỏ qua bộ lọc Tags không hợp lệ từ NetBox UI")

    problems = sync_engine.zbx_client.get_problems(
        min_severity=min_severity,
        search_problem=search,
        recent=recent,
        host_ids=host_ids,
        tags=tag_filters
    )
    return {"problems": problems, "count": len(problems)}

@app.post("/zabbix/problems/acknowledge", status_code=status.HTTP_200_OK)
def acknowledge_zabbix_problem(payload: AcknowledgeRequestSchema):
    """Endpoint Acknowledge (xác nhận) sự cố trên Zabbix API từ NetBox UI"""
    success, msg = sync_engine.zbx_client.acknowledge_problem(
        eventids=payload.eventids,
        message=payload.message or "Acknowledged from NetBox UI",
        action=payload.action
    )
    return {"status": "ok" if success else "error", "message": msg}

@app.post("/sync/full", response_model=SyncResult, status_code=status.HTTP_200_OK)
def trigger_full_sync():
    """Endpoint kích hoạt Full Reconciliation Sync 2 chiều thủ công qua API"""
    logger.info("Yêu cầu 2-Way Full Sync thủ công từ API endpoint.")
    result = sync_engine.run_full_sync()
    return result

