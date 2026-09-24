import logging
import os
import time
import urllib.request
import urllib.error
from django.utils import timezone
from .models import TemperatureTimeSeriesLog, TemperatureState

logger = logging.getLogger('netbox_rack_layout.tsdb')

import threading

# Optional external Time-Series Database URL (e.g. VictoriaMetrics or InfluxDB)
# Default is empty so requests are instant and do not block on DNS lookups.
TSDB_HTTP_URL = os.environ.get('TSDB_HTTP_URL', '').strip()


def get_temperature_status(temp):
    """
    Xác định trạng thái dựa trên ngưỡng nhiệt độ:
    - cool: < 20°C
    - normal: 20°C - 27°C
    - warning: 27°C - 32°C
    - critical: >= 32°C
    """
    if temp < 20.0:
        return 'cool'
    elif temp <= 27.0:
        return 'normal'
    elif temp <= 32.0:
        return 'warning'
    return 'critical'


def _async_send_to_tsdb(url, payload_bytes):
    try:
        req = urllib.request.Request(
            url,
            data=payload_bytes,
            headers={'Content-Type': 'text/plain'}
        )
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            pass
    except Exception:
        pass


def write_to_external_tsdb(location_id, object_type, object_id, object_name, temperature, status, timestamp_ns=None):
    """
    Gửi điểm dữ liệu theo Influx Line Protocol tới Time-Series Database (VictoriaMetrics / InfluxDB).
    Thực hiện bất đồng bộ (non-blocking thread) để không bao giờ làm trễ API của NetBox.
    """
    if not TSDB_HTTP_URL:
        return False

    if timestamp_ns is None:
        timestamp_ns = int(time.time() * 1e9)

    safe_name = str(object_name).replace(' ', '\\ ').replace(',', '\\,')
    line = f'temperature,location_id={location_id},object_type={object_type},object_id={object_id},name={safe_name},status={status} value={float(temperature)} {timestamp_ns}\n'

    # Gửi ngầm (fire-and-forget daemon thread)
    t = threading.Thread(target=_async_send_to_tsdb, args=(TSDB_HTTP_URL, line.encode('utf-8')), daemon=True)
    t.start()
    return True


def record_temperature_metric(location, object_type, object_id, object_name, temperature, min_temp=None, max_temp=None):
    """
    Ghi nhận một điểm nhiệt độ:
    1. Cập nhật trạng thái tức thời và dải [a, b] riêng trong TemperatureState
    2. Ghi một bản ghi vào Time-Series Database (bảng log tối ưu index chuỗi thời gian)
    3. Đẩy tới External TSDB (nếu có)
    """
    temp = round(float(temperature), 1)
    status = get_temperature_status(temp)
    now = timezone.now()

    # 1. Cập nhật trạng thái hiện tại
    state_defaults = {
        'current_temp': temp,
        'status': status,
        'last_updated': now
    }
    if min_temp is not None:
        state_defaults['min_temp'] = float(min_temp)
    if max_temp is not None:
        state_defaults['max_temp'] = float(max_temp)

    state, created = TemperatureState.objects.get_or_create(
        location=location,
        object_type=object_type,
        object_id=object_id,
        defaults={
            **state_defaults,
            'min_temp': float(min_temp) if min_temp is not None else 20.0,
            'max_temp': float(max_temp) if max_temp is not None else 30.0,
        }
    )
    if not created:
        for k, v in state_defaults.items():
            setattr(state, k, v)
        state.save()


    # 2. Ghi log Time-Series
    log_entry = TemperatureTimeSeriesLog.objects.create(
        location=location,
        object_type=object_type,
        object_id=object_id,
        object_name=object_name,
        temperature=temp,
        status=status,
        timestamp=now
    )

    # 3. Ghi vào External TSDB qua Line Protocol
    write_to_external_tsdb(
        location_id=location.id,
        object_type=object_type,
        object_id=object_id,
        object_name=object_name,
        temperature=temp,
        status=status
    )

    return log_entry
