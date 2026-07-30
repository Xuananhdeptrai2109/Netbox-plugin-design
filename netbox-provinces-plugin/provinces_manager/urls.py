from django.urls import path
from . import views

app_name = 'provinces_manager'

urlpatterns = [
    # Tỉnh/Thành
    path('provinces/', views.ProvinceListView.as_view(), name='province_list'),
    path('provinces/add/', views.ProvinceEditView.as_view(), name='province_add'),
    path('provinces/import/', views.ProvinceImportView.as_view(), name='province_import'),
    path('provinces/<int:pk>/edit/', views.ProvinceEditView.as_view(), name='province_edit'),
    path('provinces/<int:pk>/delete/', views.ProvinceDeleteView.as_view(), name='province_delete'),

    # Quận/Huyện
    path('districts/', views.DistrictListView.as_view(), name='district_list'),
    path('districts/add/', views.DistrictEditView.as_view(), name='district_add'),
    path('districts/import/', views.DistrictImportView.as_view(), name='district_import'),
    path('districts/<int:pk>/edit/', views.DistrictEditView.as_view(), name='district_edit'),
    path('districts/<int:pk>/delete/', views.DistrictDeleteView.as_view(), name='district_delete'),

    # Xã/Phường
    path('wards/', views.WardListView.as_view(), name='ward_list'),
    path('wards/add/', views.WardEditView.as_view(), name='ward_add'),
    path('wards/import/', views.WardImportView.as_view(), name='ward_import'),
    path('wards/<int:pk>/edit/', views.WardEditView.as_view(), name='ward_edit'),
    path('wards/<int:pk>/delete/', views.WardDeleteView.as_view(), name='ward_delete'),
]