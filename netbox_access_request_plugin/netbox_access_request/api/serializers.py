from netbox.api.serializers import NetBoxModelSerializer
from ..models import AccessRequest, RequestSubject


class AccessRequestSerializer(NetBoxModelSerializer):
    class Meta:
        model = AccessRequest
        fields = (
            'id', 'display', 'name', 'expected_date', 'reason', 'status',
            'region', 'site', 'created_by', 'admin_reason',
            'custom_fields', 'created', 'last_updated'
        )


class RequestSubjectSerializer(NetBoxModelSerializer):
    class Meta:
        model = RequestSubject
        fields = (
            'id', 'display', 'access_request', 'id_number', 'full_name',
            'organization', 'position', 'phone', 'location',
            'description', 'status', 'verify_status',
            'custom_fields', 'created', 'last_updated'
        )
