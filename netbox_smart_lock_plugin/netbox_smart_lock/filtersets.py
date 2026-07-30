import django_filters
from django.db.models import Q
from netbox.filtersets import NetBoxModelFilterSet
from .models import SmartLock

try:
    from netbox_asset_management.models import AssetGroup
except ImportError:
    AssetGroup = None

class SmartLockFilterSet(NetBoxModelFilterSet):
    if AssetGroup:
        asset_group_id = django_filters.ModelMultipleChoiceFilter(
            queryset=AssetGroup.objects.all(),
            label='Nhóm tài sản (ID)',
        )

    class Meta:
        model = SmartLock
        fields = ('id', 'name', 'code', 'status', 'device_type', 'manufacturer', 'site', 'location', 'rack')

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value) | 
            Q(code__icontains=value) |
            Q(description__icontains=value)
        )
