from netbox.api.routers import NetBoxRouter
from . import views

app_name = 'netbox_access_request'

router = NetBoxRouter()
router.register('access-requests', views.AccessRequestViewSet)
router.register('request-subjects', views.RequestSubjectViewSet)

urlpatterns = router.urls
