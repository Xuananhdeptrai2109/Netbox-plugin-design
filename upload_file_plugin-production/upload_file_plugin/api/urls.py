from django.urls import path
from .views import GetFileFromDBAPIView,CheckImportFileView

urlpatterns = [
    path('get_data_from_database/', GetFileFromDBAPIView.as_view(), name = 'get_data_from_database'),
    path('check-import/', CheckImportFileView.as_view(), name='check-import'),
]