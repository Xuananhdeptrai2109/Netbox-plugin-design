from django.urls import path
from . import views

app_name = 'netbox_rack_layout'

urlpatterns = [
    path('layout/', views.LayoutView.as_view(), name='layout'),
]
