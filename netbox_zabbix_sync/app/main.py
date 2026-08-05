import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, HTTPException, status
from apscheduler.schedulers.background import BackgroundScheduler
from app.config import settings
from app.schemas import NetBoxWebhookPayload, SyncResult
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
    # Thêm background job định kỳ cho Full Reconciliation Sync
    scheduler.add_job(
        scheduled_full_sync,
        trigger="interval",
        minutes=settings.SYNC_INTERVAL_MINUTES,
        id="full_reconciliation_sync",
        replace_existing=True
    )
    scheduler.start()
    logger.info(f"APScheduler đã được khởi động. Full Sync được lên lịch mỗi {settings.SYNC_INTERVAL_MINUTES} phút.")

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

@app.post("/sync/full", response_model=SyncResult, status_code=status.HTTP_200_OK)
def trigger_full_sync():
    """Endpoint kích hoạt Full Reconciliation Sync thủ công qua API"""
    logger.info("Yêu cầu Full Sync thủ công từ API endpoint.")
    result = sync_engine.run_full_sync()
    return result
