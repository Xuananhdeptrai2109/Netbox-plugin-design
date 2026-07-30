from django.urls import path
from . import models, views
from netbox.views.generic import ObjectChangeLogView

app_name = 'netbox_asset_management'

urlpatterns = [
    path('assets/', views.AssetListView.as_view(), name='asset_list'),
    path('assets/add/', views.AssetEditView.as_view(), name='asset_add'),
    path('assets/<int:pk>/', views.AssetView.as_view(), name='asset'),
    path('assets/<int:pk>/edit/', views.AssetEditView.as_view(), name='asset_edit'),
    path('assets/<int:pk>/delete/', views.AssetDeleteView.as_view(), name='asset_delete'),
    path('assets/<int:pk>/changelog/', ObjectChangeLogView.as_view(), name='asset_changelog', kwargs={'model': models.Asset}),
    
    path('asset-groups/', views.AssetGroupListView.as_view(), name='assetgroup_list'),
    path('asset-groups/add/', views.AssetGroupEditView.as_view(), name='assetgroup_add'),
    path('asset-groups/<int:pk>/', views.AssetGroupView.as_view(), name='assetgroup'),
    path('asset-groups/<int:pk>/edit/', views.AssetGroupEditView.as_view(), name='assetgroup_edit'),
    path('asset-groups/<int:pk>/delete/', views.AssetGroupDeleteView.as_view(), name='assetgroup_delete'),
    path('asset-groups/<int:pk>/changelog/', ObjectChangeLogView.as_view(), name='assetgroup_changelog', kwargs={'model': models.AssetGroup}),
]