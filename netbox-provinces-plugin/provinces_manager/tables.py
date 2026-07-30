import django_tables2 as tables
from .models import Province, District, Ward
from netbox.tables import NetBoxTable, columns

class ProvinceTable(NetBoxTable):
    name = tables.Column(linkify=True)
    actions = columns.ActionsColumn(actions=('edit', 'delete'))

    class Meta(NetBoxTable.Meta):
        model = Province
        fields = ('pk', 'id', 'name', 'code', 'actions')
        default_columns = ('name', 'code', 'actions')

class DistrictTable(NetBoxTable):
    name = tables.Column(linkify=True)
    province = tables.Column(linkify=True)

    actions = columns.ActionsColumn(actions=('edit', 'delete'))
    class Meta(NetBoxTable.Meta):
        model = District
        fields = ('pk', 'id', 'name', 'code', 'province', 'actions')
        default_columns = ('name', 'code', 'province', 'actions')

class WardTable(NetBoxTable):
    name = tables.Column(linkify=True)
    district = tables.Column(linkify=True)

    actions = columns.ActionsColumn(actions=('edit', 'delete'))
    class Meta(NetBoxTable.Meta):
        model = Ward
        fields = ('pk', 'id', 'name', 'code', 'district', 'actions')
        default_columns = ('name', 'code', 'district', 'actions')

