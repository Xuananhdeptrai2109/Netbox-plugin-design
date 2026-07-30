import django_tables2 as tables
from .models import Asset, AssetGroup
from netbox.tables import NetBoxTable, columns

class AssetTable(NetBoxTable):
    name = tables.Column(linkify=True, verbose_name="Tên")
    status = columns.ChoiceFieldColumn(verbose_name="Trạng thái")
    actions = columns.ActionsColumn(actions=('edit', 'delete'))

    class Meta(NetBoxTable.Meta):
        model = Asset
        fields = ('pk', 'id', 'name', 'asset_code', 'status', 'asset_group', 'actions')
        default_columns = ('name', 'asset_code', 'status', 'asset_group', 'actions')

class AssetGroupTable(NetBoxTable):
    name = tables.Column(linkify=True, verbose_name="Tên")
    code = tables.Column(verbose_name="Mã") 
    status = columns.ChoiceFieldColumn(verbose_name="Trạng thái") 
    description = tables.Column(verbose_name="Mô tả") 
    created = tables.DateTimeColumn(format='d/m/Y H:i', verbose_name="Thời gian tạo") 
    last_updated = tables.DateTimeColumn(format='d/m/Y H:i', verbose_name="Thời gian cập nhật")
    actions = columns.ActionsColumn(actions=('edit', 'delete'))

    class Meta(NetBoxTable.Meta):
        model = AssetGroup
        fields = ('pk', 'name', 'code', 'status', 'description', 'created', 'last_updated', 'actions')
        default_columns = ('name', 'code', 'status', 'actions')