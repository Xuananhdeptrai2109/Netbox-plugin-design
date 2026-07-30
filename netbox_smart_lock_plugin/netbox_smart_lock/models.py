from django.db import models
from django.urls import reverse
from netbox.models import NetBoxModel
from django.core.validators import MinValueValidator
from dateutil.relativedelta import relativedelta
from utilities.choices import ChoiceSet

class SmartLockStatusChoices(ChoiceSet):
    STATUS_ACTIVE = 'active'
    STATUS_INACTIVE = 'inactive'
    
    CHOICES = (
        (STATUS_ACTIVE, 'Hoạt động', 'green'),
        (STATUS_INACTIVE, 'Không hoạt động', 'red'),
    )

class RackFaceChoices(ChoiceSet):
    FACE_FRONT = 'front'
    FACE_REAR = 'rear'
    
    CHOICES = (
        (FACE_FRONT, 'Mặt trước', 'blue'),
        (FACE_REAR, 'Mặt sau', 'orange'),
    )

class SmartLock(NetBoxModel):
    # Thông tin cơ bản
    name = models.CharField(
        max_length=100,
        verbose_name="Tên"
    )
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Mã"
    )
    status = models.CharField(
        max_length=30,
        choices=SmartLockStatusChoices,
        default=SmartLockStatusChoices.STATUS_ACTIVE,
        verbose_name="Trạng thái"
    )
    description = models.TextField(
        blank=True,
        max_length=500,
        verbose_name="Mô tả"
    )
    
    # Thông số thiết bị
    device_type = models.CharField(
        max_length=100,
        verbose_name="Loại thiết bị"
    )
    model = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Model"
    )
    serial = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Số serial"
    )
    manufacturer = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Hãng sản xuất"
    )
    
    # Bảo hành & Ngày mua
    installation_date = models.DateField(
        verbose_name="Ngày lắp đặt",
        null=True,
        blank=True
    )
    purchase_date = models.DateField(
        verbose_name="Ngày mua",
        null=True,
        blank=True
    )
    warranty_period = models.PositiveIntegerField(
        verbose_name="Thời hạn bảo hành (tháng)",
        default=0,
        validators=[MinValueValidator(0)]
    )
    warranty_end = models.DateField(
        verbose_name="Thời gian bảo hành",
        null=True,
        blank=True,
        editable=False
    )
    
    # Liên kết vị trí NetBox
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
    location = models.ForeignKey(
        to='dcim.Location',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Location"
    )
    rack = models.ForeignKey(
        to='dcim.Rack',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Rack"
    )
    rack_face = models.CharField(
        max_length=30,
        choices=RackFaceChoices,
        blank=True,
        verbose_name="Mặt rack"
    )
    
    # Liên kết nhóm tài sản nếu có cài đặt netbox_asset_management
    asset_group = models.ForeignKey(
        to='netbox_asset_management.AssetGroup',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='smart_locks',
        verbose_name="Nhóm tài sản"
    )

    class Meta:
        ordering = ('-last_updated', 'name')
        verbose_name = 'Smart Lock'
        verbose_name_plural = 'Smart Locks'

    def __str__(self):
        return f"{self.name} ({self.code})"

    def get_absolute_url(self):
        return reverse('plugins:netbox_smart_lock:smartlock', args=[self.pk])

    def save(self, *args, **kwargs):
        if self.purchase_date and self.warranty_period:
            self.warranty_end = self.purchase_date + relativedelta(months=self.warranty_period)
        elif self.purchase_date:
            self.warranty_end = self.purchase_date
            
        super().save(*args, **kwargs)
