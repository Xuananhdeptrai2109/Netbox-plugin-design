from django.db import models
from django.urls import reverse
from netbox.models import NetBoxModel
from django.core.validators import MinValueValidator
from dateutil.relativedelta import relativedelta
from utilities.choices import ChoiceSet

class AssetGroupStatusChoices(ChoiceSet):
    STATUS_ACTIVE = 'active'
    STATUS_INACTIVE = 'inactive'
    CHOICES = (
        (STATUS_ACTIVE, 'Hoạt động', 'green'),
        (STATUS_INACTIVE, 'Không hoạt động', 'red'),
    )

class AssetGroup(NetBoxModel):
    name = models.CharField(max_length=100, unique=True, verbose_name="Tên")
    slug = models.SlugField(max_length=100, unique=True)
    code = models.CharField(max_length=50, unique=True, verbose_name="Mã") # 
    status = models.CharField(
        max_length=30, 
        choices=AssetGroupStatusChoices, 
        default=AssetGroupStatusChoices.STATUS_ACTIVE,
        verbose_name="Trạng thái"
    ) # 
    description = models.TextField(max_length=500, blank=True, verbose_name="Mô tả") # 
    image_attachments = models.ImageField(
        upload_to='plugins/netbox_asset_management/group_attachments/',
        blank=True, null=True, verbose_name="File đính kèm"
    ) # 
    exclude_from_visualization = models.BooleanField(default=False, verbose_name="Exclude from Visualization") # 

    class Meta:
        ordering = ['-last_updated'] # Sắp xếp theo thời gian cập nhật mới nhất [cite: 18]
        verbose_name = 'Nhóm tài sản'
        
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('plugins:netbox_asset_management:assetgroup', args=[self.pk])

class AssetStatusChoices(ChoiceSet):
    STATUS_ACTIVE = 'active'
    STATUS_SPARE = 'spare'
    STATUS_MAINTENANCE = 'maintenance'
    STATUS_BROKEN = 'broken'

    CHOICES = (
        (STATUS_ACTIVE, 'Đang hoạt động', 'green'),
        (STATUS_SPARE, 'Dự phòng', 'blue'),
        (STATUS_MAINTENANCE, 'Bảo trì', 'orange'),
        (STATUS_BROKEN, 'Hỏng', 'red'),
    )

class Asset(NetBoxModel):
    # Thông tin cơ bản
    name = models.CharField(
        max_length=100,
        verbose_name="Tên tài sản"
    )
    asset_code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Mã tài sản"
    )
    asset_group = models.ForeignKey(
        to='AssetGroup',
        on_delete=models.PROTECT,
        related_name='assets',
        verbose_name="Nhóm tài sản"
    )
    
    # Trạng thái tài sản
    status = models.CharField(
        max_length=30,
        choices=AssetStatusChoices,
        default=AssetStatusChoices.STATUS_ACTIVE,
        verbose_name="Trạng thái"
    )
    
    description = models.TextField(
        blank=True, 
        max_length=500, # Giới hạn 500 ký tự theo báo cáo
        verbose_name="Mô tả"
    )
    
    image_attachments = models.ImageField(
        upload_to='plugins/netbox_asset_management/attachments/',
        blank=True,
        null=True,
        verbose_name="File đính kèm"
    )
    
    device_type = models.CharField(max_length=100, verbose_name="Loại thiết bị")
    model = models.CharField(max_length=100, verbose_name="Model")
    serial_number = models.CharField(max_length=100, verbose_name="Số serial")
    manufacturer = models.CharField(max_length=100, verbose_name="Hãng sản xuất")
    installation_date = models.DateField(verbose_name="Ngày lắp đặt", null=True, blank=True)
    purchase_date = models.DateField(verbose_name="Ngày mua", null=True, blank=True)
    
    warranty_period = models.PositiveIntegerField(
        verbose_name="Thời hạn bảo hành (tháng)", 
        default=0,
        validators=[MinValueValidator(0)]
    )

    warranty_end = models.DateField(
        verbose_name="Thời gian bảo hành", 
        null=True, 
        blank=True, 
        editable=False # Disable theo báo cáo
    )

    # Liên kết tới DCIM
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
    
    parent_asset = models.ForeignKey(
        to='self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='child_assets',
        verbose_name="Tài sản cha"
    )

    class Meta:
        app_label = 'netbox_asset_management'
        ordering = ('-last_updated', 'name')
        verbose_name = 'Tài sản'
        verbose_name_plural = 'Tài sản'

    def __str__(self):
        return f"{self.name} ({self.asset_code})"

    def get_absolute_url(self):
        return reverse('plugins:netbox_asset_management:asset', args=[self.pk])

    def save(self, *args, **kwargs):
        if self.purchase_date and self.warranty_period:
            self.warranty_end = self.purchase_date + relativedelta(months=self.warranty_period)
        elif self.purchase_date:
            self.warranty_end = self.purchase_date
            
        super().save(*args, **kwargs)