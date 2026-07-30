from netbox.api.routers import NetBoxRouter
from . import views

app_name = 'netbox_smart_lock'

router = NetBoxRouter()
router.register('smart-locks', views.SmartLockViewSet)

urlpatterns = router.urls
