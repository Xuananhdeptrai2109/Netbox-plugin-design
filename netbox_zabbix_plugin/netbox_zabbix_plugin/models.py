from django.db import models
from netbox.models import NetBoxModel
from dcim.models import Device

class ZabbixHostConfig(NetBoxModel):
    device = models.OneToOneField(
        to=Device,
        on_delete=models.CASCADE,
        related_name='zabbix_config'
    )
    host_name = models.CharField(
        max_length=255,
        help_text='Tên Host đại diện trên Zabbix'
    )
    visible_name = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='Tên hiển thị (Visible Name)'
    )
    use_device_role_as_group = models.BooleanField(
        default=True,
        help_text='Tự động lấy Device Role làm Zabbix Host Group'
    )
    custom_groups = models.JSONField(
        default=list,
        blank=True,
        help_text='Danh sách Host Groups tùy chỉnh'
    )
    description = models.TextField(
        blank=True,
        default='',
        help_text='Mô tả về Zabbix Host'
    )
    proxy_hostid = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='ID hoặc Tên của Zabbix Proxy (để rỗng nếu không dùng)'
    )
    enabled = models.BooleanField(
        default=True,
        help_text='Trạng thái giám sát (Monitored / Disabled)'
    )
    templates = models.JSONField(
        default=list,
        blank=True,
        help_text='Danh sách Zabbix Templates (ví dụ: ["Template OS Linux by Zabbix agent"])'
    )
    host_macros = models.JSONField(
        default=list,
        blank=True,
        help_text='Danh sách User Macros (ví dụ: [{"macro": "{$SNMP_COMMUNITY}", "value": "public", "type": "0", "description": ""}])'
    )
    inventory_mode = models.CharField(
        max_length=20,
        default='disabled',
        choices=(
            ('disabled', 'Disabled'),
            ('manual', 'Manual'),
            ('automatic', 'Automatic'),
        ),
        help_text='Chế độ quản lý Inventory'
    )
    custom_tags = models.JSONField(
        default=list,
        blank=True,
        help_text='Danh sách Custom Host Tags (ví dụ: [{"tag": "env", "value": "prod"}])'
    )

    class Meta:
        ordering = ('host_name',)
        verbose_name = 'Cấu hình Zabbix Host'
        verbose_name_plural = 'Cấu hình Zabbix Hosts'

    def __str__(self):
        return f"ZabbixHost: {self.host_name} ({self.device.name})"


class ZabbixInterfaceConfig(models.Model):
    INTERFACE_TYPE_CHOICES = (
        ('1', 'Agent'),
        ('2', 'SNMP'),
        ('3', 'IPMI'),
        ('4', 'JMX'),
    )

    host_config = models.ForeignKey(
        to=ZabbixHostConfig,
        on_delete=models.CASCADE,
        related_name='interfaces'
    )
    interface_type = models.CharField(
        max_length=10,
        choices=INTERFACE_TYPE_CHOICES,
        default='1'
    )
    ip_address = models.CharField(max_length=255, blank=True, default='')
    dns_name = models.CharField(max_length=255, blank=True, default='')
    use_ip = models.BooleanField(default=True)
    port = models.CharField(max_length=10, default='10050')
    is_default = models.BooleanField(default=False)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = 'Giao diện Zabbix Interface'
        verbose_name_plural = 'Giao diện Zabbix Interfaces'

    def __str__(self):
        return f"{self.get_interface_type_display()} Interface ({self.ip_address or self.dns_name}:{self.port})"
