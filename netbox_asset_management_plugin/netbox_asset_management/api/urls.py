from netbox.api.routers import NetBoxRouter
from . import views

app_name = 'netbox_asset_management'

router = NetBoxRouter()
router.register('asset-groups', views.AssetGroupViewSet)
router.register('assets', views.AssetViewSet)

urlpatterns = router.urls
