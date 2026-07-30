from django.urls import path
from . import models, views
from netbox.views.generic import ObjectChangeLogView

app_name = 'netbox_smart_lock'

urlpatterns = [
    path('smart-locks/', views.SmartLockListView.as_view(), name='smartlock_list'),
    path('smart-locks/add/', views.SmartLockEditView.as_view(), name='smartlock_add'),
    path('smart-locks/<int:pk>/', views.SmartLockView.as_view(), name='smartlock'),
    path('smart-locks/<int:pk>/edit/', views.SmartLockEditView.as_view(), name='smartlock_edit'),
    path('smart-locks/<int:pk>/delete/', views.SmartLockDeleteView.as_view(), name='smartlock_delete'),
    path('smart-locks/<int:pk>/changelog/', ObjectChangeLogView.as_view(), name='smartlock_changelog', kwargs={'model': models.SmartLock}),
]
