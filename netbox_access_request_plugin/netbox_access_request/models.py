from django.db import models
from django.urls import reverse
from django.conf import settings
from django.core.validators import RegexValidator
from netbox.models import NetBoxModel
from utilities.querysets import RestrictedQuerySet

from .choices import RequestStatusChoices, SubjectStatusChoices, VerifyStatusChoices


class UserRegionAssignment(models.Model):
    """Bảng mapping User-Region: quản lý phân quyền Region cho người dùng"""
    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='region_assignments',
        verbose_name="Người dùng"
    )
    region = models.ForeignKey(
        to='dcim.Region',
        on_delete=models.CASCADE,
        related_name='user_assignments',
        verbose_name="Region"
    )

    objects = RestrictedQuerySet.as_manager()

    class Meta:
        unique_together = ('user', 'region')
        verbose_name = 'Phân quyền Region'
        verbose_name_plural = 'Phân quyền Region'

    def __str__(self):
        return f"{self.user.username} - {self.region.name}"


class AccessRequest(NetBoxModel):
    """Phiếu yêu cầu ra vào trung tâm dữ liệu"""
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Tên phiếu"
    )
    expected_date = models.DateField(
        verbose_name="Ngày dự kiến"
    )
    reason = models.TextField(
        max_length=500,
        verbose_name="Lý do"
    )
    status = models.CharField(
        max_length=30,
        choices=RequestStatusChoices,
        default=RequestStatusChoices.STATUS_DRAFT,
        verbose_name="Trạng thái"
    )
    region = models.ForeignKey(
        to='dcim.Region',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Region"
    )
    site = models.ForeignKey(
        to='dcim.Site',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Site"
    )
    created_by = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='access_requests',
        verbose_name="Người tạo"
    )
    admin_reason = models.TextField(
        max_length=500,
        blank=True,
        verbose_name="Lý do Admin"
    )

    class Meta:
        ordering = ['-last_updated']
        verbose_name = 'Phiếu yêu cầu ra vào'
        verbose_name_plural = 'Phiếu yêu cầu ra vào'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('plugins:netbox_access_request:accessrequest', args=[self.pk])

    def get_status_color(self):
        return RequestStatusChoices.colors.get(self.status)


class RequestSubject(NetBoxModel):
    """Đối tượng đăng ký ra vào trung tâm dữ liệu"""
    access_request = models.ForeignKey(
        to=AccessRequest,
        on_delete=models.CASCADE,
        related_name='subjects',
        verbose_name="Phiếu yêu cầu"
    )
    id_number = models.CharField(
        max_length=12,
        verbose_name="Mã định danh",
        validators=[
            RegexValidator(
                regex=r'^\d{12}$',
                message='Mã định danh phải có đúng 12 ký tự số'
            )
        ]
    )
    full_name = models.CharField(
        max_length=50,
        verbose_name="Họ và tên"
    )
    organization = models.CharField(
        max_length=100,
        verbose_name="Đơn vị"
    )
    position = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Chức danh"
    )
    phone = models.CharField(
        max_length=10,
        blank=True,
        verbose_name="Số điện thoại",
        validators=[
            RegexValidator(
                regex=r'^0\d{9}$',
                message='Số điện thoại phải có 10 chữ số và bắt đầu bằng 0'
            )
        ]
    )
    location = models.ForeignKey(
        to='dcim.Location',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Location"
    )
    description = models.TextField(
        max_length=500,
        blank=True,
        verbose_name="Mô tả"
    )
    status = models.CharField(
        max_length=30,
        choices=SubjectStatusChoices,
        default=SubjectStatusChoices.STATUS_PENDING,
        verbose_name="Trạng thái"
    )
    verify_status = models.CharField(
        max_length=30,
        choices=VerifyStatusChoices,
        default=VerifyStatusChoices.STATUS_PENDING,
        verbose_name="Xác nhận"
    )

    class Meta:
        ordering = ['-last_updated']
        verbose_name = 'Đối tượng'
        verbose_name_plural = 'Đối tượng'

    def __str__(self):
        return f"{self.full_name} ({self.id_number})"

    def get_absolute_url(self):
        return reverse('plugins:netbox_access_request:requestsubject', args=[
            self.access_request.pk, self.pk
        ])

    def get_status_color(self):
        return SubjectStatusChoices.colors.get(self.status)

    def get_verify_status_color(self):
        return VerifyStatusChoices.colors.get(self.verify_status)

    @property
    def get_uploaded_files(self):
        try:
            from upload_file_plugin.models import UploadedFile
            return UploadedFile.objects.filter(model_name='requestsubject', object_id=self.pk)
        except ImportError:
            return []


class RequestHistory(models.Model):
    """Lịch sử thao tác trên phiếu yêu cầu"""
    access_request = models.ForeignKey(
        to=AccessRequest,
        on_delete=models.CASCADE,
        related_name='history',
        verbose_name="Phiếu yêu cầu"
    )
    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Người thực hiện"
    )
    action = models.CharField(
        max_length=100,
        verbose_name="Hoạt động"
    )
    status = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Trạng thái"
    )
    description = models.TextField(
        max_length=500,
        blank=True,
        verbose_name="Mô tả"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Thời gian"
    )

    objects = RestrictedQuerySet.as_manager()

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Lịch sử yêu cầu'
        verbose_name_plural = 'Lịch sử yêu cầu'

    def __str__(self):
        return f"{self.action} - {self.timestamp}"
