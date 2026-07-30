import django_tables2 as tables
from .models import SmartLock
from netbox.tables import NetBoxTable, columns

class SmartLockTable(NetBoxTable):
    name = tables.Column(linkify=True, verbose_name="Tên")
    code = tables.Column(verbose_name="Mã")
    status = columns.ChoiceFieldColumn(verbose_name="Trạng thái")
    site = tables.Column(linkify=True, verbose_name="Địa điểm")
    location = tables.Column(linkify=True, verbose_name="Vị trí")
    rack = tables.Column(linkify=True, verbose_name="Rack")
    manufacturer = tables.Column(verbose_name="Nhà sản xuất")
    device_type = tables.Column(verbose_name="Loại thiết bị")
    
    # Người tạo, Thời gian tạo, Thời gian cập nhật
    # NetBox cung cấp sẵn các trường meta này trên NetBoxModel
    created = tables.DateTimeColumn(format='d/m/Y H:i', verbose_name="Thời gian tạo")
    last_updated = tables.DateTimeColumn(format='d/m/Y H:i', verbose_name="Thời gian cập nhật")
    
    actions = columns.ActionsColumn(actions=('edit', 'delete'))

    class Meta(NetBoxTable.Meta):
        model = SmartLock
        fields = (
            'pk', 'name', 'code', 'status', 'site', 'location', 'rack', 
            'manufacturer', 'device_type', 'created', 'last_updated', 'actions'
        )
        default_columns = (
            'name', 'code', 'status', 'site', 'location', 'rack', 
            'manufacturer', 'device_type', 'actions'
        )
