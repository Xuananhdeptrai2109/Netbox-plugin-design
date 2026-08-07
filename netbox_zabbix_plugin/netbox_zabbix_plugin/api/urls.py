from netbox.api.routers import NetBoxRouter
from . import views

router = NetBoxRouter()
router.register('zabbix-hosts', views.ZabbixHostConfigViewSet)

urlpatterns = router.urls
