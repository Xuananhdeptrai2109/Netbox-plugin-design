from django.contrib import admin
from netbox.admin import NetBoxModelAdmin
from .models import Asset, AssetGroup

@admin.register(Asset)
class AssetAdmin(NetBoxModelAdmin):
    # Hiển thị các cột thông tin quan trọng trong bảng Admin
    list_display = ('name', 'asset_code', 'asset_group', 'status', 'purchase_date', 'warranty_end')
    # Bộ lọc nhanh bên phải màn hình
    list_filter = ('status', 'asset_group', 'manufacturer')
    # Cho phép tìm kiếm theo các trường văn bản
    search_fields = ('name', 'asset_code', 'serial_number')

@admin.register(AssetGroup)
class AssetGroupAdmin(NetBoxModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name', 'slug')
    # Tự động tạo slug từ tên khi nhập trong Admin
    prepopulated_fields = {
        'slug': ('name',),
    }