from django.urls import path
from . import views

app_name = 'netbox_zabbix_plugin'

urlpatterns = [
    path('devices/<int:pk>/zabbix-host/', views.DeviceZabbixHostView.as_view(), name='device_zabbix_host'),
]
