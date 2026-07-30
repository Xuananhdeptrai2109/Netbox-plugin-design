import django_filters
from django.db.models import Q
from netbox.filtersets import NetBoxModelFilterSet
from .models import Asset, AssetGroup

class AssetFilterSet(NetBoxModelFilterSet):
    asset_group_id = django_filters.ModelMultipleChoiceFilter(
        queryset=AssetGroup.objects.all(),
        label='Nhóm tài sản (ID)',
    )

    class Meta:
        model = Asset
        fields = ('id', 'name', 'asset_code', 'status', 'device_type', 'manufacturer')

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value) | 
            Q(asset_code__icontains=value)
        )

class AssetGroupFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = AssetGroup
        fields = ('id', 'name', 'code', 'status')

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value) |
            Q(slug__icontains=value)
        )
