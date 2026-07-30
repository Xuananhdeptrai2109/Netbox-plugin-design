from netbox.views import generic
from . import forms, models, tables, filtersets

class SmartLockListView(generic.ObjectListView):
    """Màn hình danh sách smart lock"""
    queryset = models.SmartLock.objects.all()
    table = tables.SmartLockTable
    filterset = filtersets.SmartLockFilterSet
    filterset_form = forms.SmartLockFilterForm
    action_buttons = ('add', 'import', 'export') 

class SmartLockView(generic.ObjectView):
    """Xem chi tiết thông tin smart lock"""
    queryset = models.SmartLock.objects.all()
    template_name = 'netbox_smart_lock/smartlock.html'

    def get_extra_context(self, request, instance):
        uploaded_files = []
        if instance.pk:
            try:
                from upload_file_plugin.models import UploadedFile
                uploaded_files = UploadedFile.objects.filter(
                    object_id=instance.pk, model_name='smartlock'
                )
            except ImportError:
                pass
                
        return {
            'uploaded_files': uploaded_files,
        }

class SmartLockEditView(generic.ObjectEditView):
    """Thêm mới và Chỉnh sửa smart lock"""
    queryset = models.SmartLock.objects.all()
    form = forms.SmartLockForm
    template_name = 'netbox_smart_lock/smartlock_edit.html'
    default_return_url = 'plugins:netbox_smart_lock:smartlock_list'
    
    def get_extra_context(self, request, instance):
        if not request.session.session_key:
            request.session.save()
        
        session_key = request.session.session_key
        object_id = instance.pk if instance.pk else ''
        model_name = 'smartlock'
        
        uploaded_files = []
        if object_id:
            try:
                from upload_file_plugin.models import UploadedFile
                uploaded_files = UploadedFile.objects.filter(
                    object_id=object_id, model_name=model_name
                )
            except ImportError:
                pass
            
        return {
            'object_id': object_id,
            'model_name': model_name,
            'session_key': session_key,
            'valid_flg': 0,
            'type_file': 'image', # Giới hạn là file ảnh theo mô tả
            'uploaded_files': uploaded_files,
        }
    
    def get_return_url(self, request, obj=None):
        from django.urls import reverse
        return_url = request.GET.get('return_url') or request.POST.get('return_url')
        if return_url and return_url.startswith('/'):
            return return_url
        return reverse(self.default_return_url)

class SmartLockDeleteView(generic.ObjectDeleteView):
    """Xóa smart lock"""
    queryset = models.SmartLock.objects.all()
    default_return_url = 'plugins:netbox_smart_lock:smartlock_list'
