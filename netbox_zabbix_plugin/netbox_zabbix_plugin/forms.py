from django import forms
from .models import ZabbixHostConfig

class ZabbixHostConfigForm(forms.ModelForm):
    # Host basic settings
    host_name = forms.CharField(
        label='Host name',
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    visible_name = forms.CharField(
        label='Visible name',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    use_device_role_as_group = forms.BooleanField(
        label='Use Device Role as Zabbix Host Group',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    custom_groups = forms.CharField(
        label='Custom Groups (phân cách bằng dấu phẩy)',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'NetBox/Router, Linux Servers'})
    )
    templates = forms.CharField(
        label='Templates (phân cách bằng dấu phẩy)',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Linux by Zabbix agent, ICMP Ping'})
    )
    description = forms.CharField(
        label='Description',
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )
    proxy_hostid = forms.CharField(
        label='Monitored by proxy',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(no proxy)'})
    )
    enabled = forms.BooleanField(
        label='Enabled',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = ZabbixHostConfig
        fields = [
            'host_name', 'visible_name', 'use_device_role_as_group', 'custom_groups',
            'templates', 'description', 'proxy_hostid', 'enabled'
        ]
