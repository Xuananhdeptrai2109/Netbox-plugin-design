from netbox.search import SearchIndex, register_search
from .models import Asset, AssetGroup

@register_search
class AssetIndex(SearchIndex):
    """Đăng ký Model Asset vào hệ thống tìm kiếm toàn cục"""
    model = Asset
    # Định nghĩa các trường dữ liệu sẽ được lập chỉ mục (index)
    # Cú pháp: (tên_trường, trọng_số) - Trọng số càng thấp càng được ưu tiên kết quả
    fields = (
        ('name', 100),
        ('asset_code', 100),
        ('serial_number', 150),
        ('model', 150),
        ('manufacturer', 200),
        ('description', 500),
    )

@register_search
class AssetGroupIndex(SearchIndex):
    """Đăng ký Nhóm tài sản vào hệ thống tìm kiếm"""
    model = AssetGroup
    fields = (
        ('name', 100),
        ('slug', 110),
    )