from netbox.filtersets import NetBoxModelFilterSet
from .models import Province, District, Ward
import django_filters

class ProvinceFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = Province
        fields = ('id', 'name', 'code')

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            django_filters.db.models.Q(name__icontains=value) |
            django_filters.db.models.Q(code__icontains=value)
        )

class DistrictFilterSet(NetBoxModelFilterSet):
    # Cho phép lọc Quận dựa trên Tỉnh (Khóa ngoại)
    province_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Province.objects.all(),
        label='Tỉnh / Thành phố (ID)',
    )

    class Meta:
        model = District
        fields = ('id', 'name', 'code', 'province_id')

    def search(self, queryset, name, value):
        return queryset.filter(
            django_filters.db.models.Q(name__icontains=value) |
            django_filters.db.models.Q(code__icontains=value)
        )

class WardFilterSet(NetBoxModelFilterSet):
    # Cho phép lọc Xã dựa trên Quận (Khóa ngoại)
    district_id = django_filters.ModelMultipleChoiceFilter(
        queryset=District.objects.all(),
        label='Quận / Huyện (ID)',
    )

    class Meta:
        model = Ward
        fields = ('id', 'name', 'code', 'district_id')

    def search(self, queryset, name, value):
        return queryset.filter(
            django_filters.db.models.Q(name__icontains=value) |
            django_filters.db.models.Q(code__icontains=value)
        )