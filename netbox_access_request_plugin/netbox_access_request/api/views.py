from rest_framework.exceptions import PermissionDenied
from netbox.api.viewsets import NetBoxModelViewSet
from .. import models, filtersets
from ..utils import is_admin_user
from . import serializers


class AccessRequestViewSet(NetBoxModelViewSet):
    queryset = models.AccessRequest.objects.all()
    serializer_class = serializers.AccessRequestSerializer
    filterset_class = filtersets.AccessRequestFilterSet

    def get_queryset(self):
        qs = super().get_queryset()
        if not is_admin_user(self.request.user):
            # User chỉ thấy phiếu của mình
            qs = qs.filter(created_by=self.request.user)
        else:
            # Admin thấy tất cả, ngoại trừ các phiếu nháp của người khác
            from django.db.models import Q
            from ..choices import RequestStatusChoices
            qs = qs.exclude(
                Q(status=RequestStatusChoices.STATUS_DRAFT) & ~Q(created_by=self.request.user)
            )
        return qs

    def perform_create(self, serializer):
        """Tự động gán người tạo khi thêm mới qua API"""
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        """Chỉ người tạo phiếu mới được sửa"""
        if not is_admin_user(self.request.user) and serializer.instance.created_by != self.request.user:
            raise PermissionDenied('Bạn không có quyền chỉnh sửa phiếu yêu cầu này.')
        serializer.save()

    def perform_destroy(self, instance):
        """Chỉ người tạo phiếu mới được xoá"""
        if instance.created_by != self.request.user:
            raise PermissionDenied('Bạn không có quyền xoá phiếu yêu cầu này.')
        super().perform_destroy(instance)


class RequestSubjectViewSet(NetBoxModelViewSet):
    queryset = models.RequestSubject.objects.all()
    serializer_class = serializers.RequestSubjectSerializer
    filterset_class = filtersets.RequestSubjectFilterSet

    def get_queryset(self):
        qs = super().get_queryset()
        if not is_admin_user(self.request.user):
            # User chỉ thấy đối tượng trong phiếu của mình
            qs = qs.filter(access_request__created_by=self.request.user)
        else:
            # Admin thấy tất cả đối tượng, ngoại trừ đối tượng nằm trong phiếu nháp của người khác
            from django.db.models import Q
            from ..choices import RequestStatusChoices
            qs = qs.exclude(
                Q(access_request__status=RequestStatusChoices.STATUS_DRAFT) &
                ~Q(access_request__created_by=self.request.user)
            )
        return qs

    def perform_create(self, serializer):
        """Chỉ người tạo phiếu mới được thêm đối tượng"""
        access_request = serializer.validated_data.get('access_request')
        if access_request and access_request.created_by != self.request.user:
            raise PermissionDenied('Bạn không có quyền thêm đối tượng vào phiếu yêu cầu này.')
        serializer.save()

    def perform_update(self, serializer):
        """Chỉ người tạo phiếu mới được sửa đối tượng"""
        if not is_admin_user(self.request.user):
            if serializer.instance.access_request.created_by != self.request.user:
                raise PermissionDenied('Bạn không có quyền chỉnh sửa đối tượng này.')
        serializer.save()

    def perform_destroy(self, instance):
        """Chỉ người tạo phiếu mới được xoá đối tượng"""
        if instance.access_request.created_by != self.request.user:
            raise PermissionDenied('Bạn không có quyền xoá đối tượng này.')
        super().perform_destroy(instance)
