from django.db import models
from django.urls import reverse
from netbox.models import NetBoxModel
from utilities.querysets import RestrictedQuerySet



class Layout(NetBoxModel):
    """
    Lưu trữ bố cục mặt bằng 2D cho một Location hoặc Site.
    Mỗi Location/Site chỉ có duy nhất một Layout.
    """
    location = models.OneToOneField(
        to='dcim.Location',
        on_delete=models.CASCADE,
        related_name='rack_layout',
        verbose_name='Location',
        null=True,
        blank=True
    )
    site = models.OneToOneField(
        to='dcim.Site',
        on_delete=models.CASCADE,
        related_name='site_layout',
        verbose_name='Site',
        null=True,
        blank=True
    )
    name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Tên Layout'
    )

    class Meta:
        ordering = ['-last_updated']
        verbose_name = 'Layout'
        verbose_name_plural = 'Layouts'

    def clean(self):
        from django.core.exceptions import ValidationError
        super().clean()
        if not self.location and not self.site:
            raise ValidationError("Layout must be associated with either a Location or a Site.")
        if self.location and self.site:
            raise ValidationError("Layout cannot be associated with both a Location and a Site.")

    def __str__(self):
        if self.location:
            return self.name or f"Layout - {self.location}"
        elif self.site:
            return self.name or f"Site Layout - {self.site}"
        return self.name or f"Layout #{self.pk}"

    def get_absolute_url(self):
        return reverse('plugins:netbox_rack_layout:layout')


class LayoutObject(models.Model):
    """
    Lưu trữ vị trí hiển thị (tọa độ x, y) của một Rack, Device, Asset, Smart Lock, Wall hoặc Location
    trên Canvas 2D. KHÔNG sao chép dữ liệu, chỉ lưu tham chiếu (object_type + object_id).
    """
    OBJECT_TYPE_CHOICES = (
        ('rack', 'Rack'),
        ('device', 'Device'),
        ('asset', 'Asset'),
        ('smartlock', 'Smart Lock'),
        ('wall', 'Wall'),
        ('location', 'Location'),
        ('door_1', 'Cửa chính 1 cánh (Mặt bằng)'),
        ('door_2', 'Cửa sổ (Mặt bằng)'),
        ('window_floor', 'Cửa sổ (Mặt bằng)'),
        ('door_wall', 'Cửa chính (Trên tường)'),
        ('window_wall', 'Cửa sổ (Trên tường)'),
        ('window_2', 'Cửa sổ 2 cánh'),
        ('window_4', 'Cửa sổ 4 cánh'),
    )

    layout = models.ForeignKey(
        to=Layout,
        on_delete=models.CASCADE,
        related_name='layout_objects',
        verbose_name='Layout'
    )
    object_type = models.CharField(
        max_length=20,
        choices=OBJECT_TYPE_CHOICES,
        verbose_name='Loại đối tượng'
    )
    object_id = models.PositiveIntegerField(
        verbose_name='ID đối tượng'
    )
    x = models.FloatField(
        default=0,
        verbose_name='Tọa độ X'
    )
    y = models.FloatField(
        default=0,
        verbose_name='Tọa độ Y'
    )
    rotation = models.FloatField(
        default=0,
        verbose_name='Góc xoay (độ)'
    )
    z_index = models.IntegerField(
        default=0,
        verbose_name='Thứ tự lớp (Z-Index)'
    )
    width = models.FloatField(
        default=0,
        verbose_name='Chiều rộng (0 = mặc định)'
    )
    height = models.FloatField(
        default=0,
        verbose_name='Chiều cao (0 = mặc định)'
    )
    parent_type = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='Loại đối tượng cha'
    )
    parent_id = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name='ID đối tượng cha'
    )
    wall_face = models.CharField(
        max_length=10,
        choices=(
            ('front', 'Mặt trước'),
            ('back', 'Mặt sau'),
        ),
        default='front',
        blank=True,
        null=True,
        verbose_name='Mặt tường'
    )

    objects = RestrictedQuerySet.as_manager()

    class Meta:
        ordering = ['z_index']

        verbose_name = 'Layout Object'
        verbose_name_plural = 'Layout Objects'
        unique_together = ('layout', 'object_type', 'object_id')

    def __str__(self):
        return f"{self.object_type}:{self.object_id} @ ({self.x}, {self.y})"


class LocationTemperatureConfig(NetBoxModel):
    """
    Cấu hình dải nhiệt độ [a, b] và chu kỳ cập nhật cho một Location.
    """
    location = models.OneToOneField(
        to='dcim.Location',
        on_delete=models.CASCADE,
        related_name='temperature_config',
        verbose_name='Location'
    )
    min_temp = models.FloatField(
        default=20.0,
        verbose_name='Nhiệt độ tối thiểu a (°C)'
    )
    max_temp = models.FloatField(
        default=30.0,
        verbose_name='Nhiệt độ tối đa b (°C)'
    )
    interval_seconds = models.PositiveIntegerField(
        default=5,
        verbose_name='Chu kỳ ghi log (giây)'
    )
    is_auto_simulate = models.BooleanField(
        default=False,
        verbose_name='Tự động mô phỏng'
    )

    class Meta:
        verbose_name = 'Cấu hình nhiệt độ Location'
        verbose_name_plural = 'Cấu hình nhiệt độ Locations'

    def __str__(self):
        return f"Temp Config - {self.location} [{self.min_temp}°C - {self.max_temp}°C]"


class TemperatureState(models.Model):
    """
    Lưu trữ trạng thái nhiệt độ hiện tại của Rack hoặc Asset trong một Location.
    """
    location = models.ForeignKey(
        to='dcim.Location',
        on_delete=models.CASCADE,
        related_name='temperature_states',
        verbose_name='Location'
    )
    object_type = models.CharField(
        max_length=20,
        choices=(
            ('rack', 'Rack'),
            ('asset', 'Asset'),
        ),
        verbose_name='Loại đối tượng'
    )
    object_id = models.PositiveIntegerField(
        verbose_name='ID đối tượng'
    )
    current_temp = models.FloatField(
        default=25.0,
        verbose_name='Nhiệt độ hiện tại (°C)'
    )
    min_temp = models.FloatField(
        default=20.0,
        verbose_name='Nhiệt độ tối thiểu a (°C)'
    )
    max_temp = models.FloatField(
        default=30.0,
        verbose_name='Nhiệt độ tối đa b (°C)'
    )
    status = models.CharField(
        max_length=20,
        default='normal',
        choices=(
            ('cool', 'Cool'),
            ('normal', 'Normal'),
            ('warning', 'Warning'),
            ('critical', 'Critical'),
        ),
        verbose_name='Trạng thái nhiệt độ'
    )
    last_updated = models.DateTimeField(
        auto_now=True,
        verbose_name='Cập nhật lần cuối'
    )

    objects = RestrictedQuerySet.as_manager()

    class Meta:
        unique_together = ('location', 'object_type', 'object_id')
        verbose_name = 'Trạng thái nhiệt độ'
        verbose_name_plural = 'Trạng thái nhiệt độ'

    def __str__(self):
        return f"{self.object_type}:{self.object_id} - {self.current_temp}°C"


class TemperatureTimeSeriesLog(models.Model):
    """
    Lưu trữ log chuỗi thời gian (time-series) nhiệt độ cập nhật liên tục (mỗi 5s).
    Được đánh chỉ mục theo location và timestamp để truy vấn siêu nhanh.
    """
    location = models.ForeignKey(
        to='dcim.Location',
        on_delete=models.CASCADE,
        related_name='temperature_logs',
        verbose_name='Location',
        db_index=True
    )
    object_type = models.CharField(
        max_length=20,
        choices=(
            ('rack', 'Rack'),
            ('asset', 'Asset'),
        ),
        verbose_name='Loại đối tượng',
        db_index=True
    )
    object_id = models.PositiveIntegerField(
        verbose_name='ID đối tượng',
        db_index=True
    )
    object_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='Tên thiết bị'
    )
    temperature = models.FloatField(
        verbose_name='Nhiệt độ (°C)'
    )
    status = models.CharField(
        max_length=20,
        default='normal',
        verbose_name='Trạng thái'
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Thời gian ghi nhận'
    )

    objects = RestrictedQuerySet.as_manager()

    class Meta:

        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['location', '-timestamp']),
            models.Index(fields=['location', 'object_type', 'object_id', '-timestamp']),
        ]
        verbose_name = 'Log nhiệt độ Time-Series'
        verbose_name_plural = 'Logs nhiệt độ Time-Series'

    def __str__(self):
        return f"[{self.timestamp}] {self.object_name or self.object_type}: {self.temperature}°C"

