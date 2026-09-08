from django.urls import path
from . import views

app_name = 'netbox_zabbix_plugin'

urlpatterns = [
    path('devices/<int:pk>/zabbix-host/', views.DeviceZabbixHostView.as_view(), name='device_zabbix_host'),
    path('problems/', views.ZabbixProblemsView.as_view(), name='zabbix_problems'),
    path('api/problems/', views.ZabbixProblemsApiProxyView.as_view(), name='api_zabbix_problems'),
    path('api/acknowledge/', views.ZabbixAcknowledgeApiProxyView.as_view(), name='api_zabbix_acknowledge'),
    path('api/hostgroups/', views.ZabbixHostGroupsApiProxyView.as_view(), name='api_zabbix_hostgroups'),
    path('api/hosts/', views.ZabbixHostsApiProxyView.as_view(), name='api_zabbix_hosts'),
]



