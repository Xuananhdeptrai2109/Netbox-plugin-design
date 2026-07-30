from django.urls import path, include
from .views import upload_file_view, delete_file_view, assign_object_id, delete_temp_file_view
from .views import SaveFilesView

urlpatterns = [
    path('upload/', upload_file_view, name='upload_file'),
    path('delete/', delete_file_view, name='delete_file'),
    path('assign_object_id/', assign_object_id, name='assign_object_id'),
    path('delete_temp_file/', delete_temp_file_view, name='delete_temp_file'),
    path('save_files/', SaveFilesView.as_view(), name='save_files'),
    path('api/', include('upload_file_plugin.api.urls')),
]