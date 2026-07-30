from netbox.api.routers import NetBoxRouter
from . import views

router = NetBoxRouter()
router.register('provinces', views.ProvinceViewSet)
router.register('districts', views.DistrictViewSet)
router.register('wards', views.WardViewSet)

urlpatterns = router.urls