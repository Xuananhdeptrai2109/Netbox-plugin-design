import django_filters
from django.db.models import Q
from netbox.filtersets import NetBoxModelFilterSet
from .models import AccessRequest, RequestSubject


class AccessRequestFilterSet(NetBoxModelFilterSet):
    """Bộ lọc phiếu yêu cầu"""
    class Meta:
        model = AccessRequest
        fields = ('id', 'name', 'status', 'region', 'site')

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value) |
            Q(reason__icontains=value)
        )


class RequestSubjectFilterSet(NetBoxModelFilterSet):
    """Bộ lọc đối tượng"""
    access_request_id = django_filters.ModelMultipleChoiceFilter(
        queryset=AccessRequest.objects.all(),
        label='Phiếu yêu cầu (ID)',
    )

    class Meta:
        model = RequestSubject
        fields = ('id', 'full_name', 'id_number', 'status', 'verify_status')

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(full_name__icontains=value) |
            Q(id_number__icontains=value) |
            Q(organization__icontains=value)
        )
