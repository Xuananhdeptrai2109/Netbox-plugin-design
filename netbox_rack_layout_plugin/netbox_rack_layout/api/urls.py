from django.urls import path
from . import views

app_name = 'netbox_rack_layout'

urlpatterns = [
    path(
        'layout/<int:location_id>/',
        views.LayoutDetailAPIView.as_view(),
        name='layout_detail_api'
    ),
    path(
        'layout/save/',
        views.LayoutSaveAPIView.as_view(),
        name='layout_save_api'
    ),
    path(
        'site/<int:site_id>/locations/',
        views.SiteLocationsAPIView.as_view(),
        name='site_locations_api'
    ),
    path(
        'site-layout/<int:site_id>/',
        views.SiteLayoutDetailAPIView.as_view(),
        name='site_layout_detail_api'
    ),
    path(
        'site-layout/save/',
        views.SiteLayoutSaveAPIView.as_view(),
        name='site_layout_save_api'
    ),
    path(
        'temperature/<int:location_id>/',
        views.TemperatureDetailAPIView.as_view(),
        name='temperature_detail_api'
    ),
    path(
        'temperature/<int:location_id>/config/',
        views.TemperatureConfigAPIView.as_view(),
        name='temperature_config_api'
    ),
    path(
        'temperature/<int:location_id>/update/',
        views.TemperatureUpdateAPIView.as_view(),
        name='temperature_update_api'
    ),
    path(
        'temperature/<int:location_id>/logs/',
        views.TemperatureLogAPIView.as_view(),
        name='temperature_logs_api'
    ),
]


