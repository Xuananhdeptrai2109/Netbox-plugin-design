from netbox.views import generic
from django.db.models import Count
from . import forms, models, tables, filtersets

# --- VIEWS CHO ASSET (Tài sản) ---

class AssetListView(generic.ObjectListView):
    """Màn hình danh sách tài sản"""
    queryset = models.Asset.objects.all()
    table = tables.AssetTable
    filterset = filtersets.AssetFilterSet
    filterset_form = forms.AssetFilterForm
    # Cho phép export excel theo yêu cầu báo cáo
    action_buttons = ('add', 'import', 'export') 

class AssetView(generic.ObjectView):
    """Xem chi tiết thông tin tài sản"""
    queryset = models.Asset.objects.all()

    def get_extra_context(self, request, instance):
        # Logic báo cáo: "Đối tượng liên quan: Các tài sản: số lượng"
        # Giả sử ta đếm các tài sản cùng nhóm hoặc cùng site
        related_assets_count = models.Asset.objects.filter(
            asset_group=instance.asset_group
        ).exclude(pk=instance.pk).count()

        uploaded_files = []
        if instance.pk:
            try:
                from upload_file_plugin.models import UploadedFile
                uploaded_files = UploadedFile.objects.filter(
                    object_id=instance.pk, model_name='asset'
                )
            except ImportError:
                pass
                
        return {
            'related_assets_count': related_assets_count,
            'uploaded_files': uploaded_files,
        }

class AssetEditView(generic.ObjectEditView):
    """Thêm mới và Chỉnh sửa tài sản"""
    queryset = models.Asset.objects.all()
    form = forms.AssetForm
    template_name = 'netbox_asset_management/edit.html'
    default_return_url = 'plugins:netbox_asset_management:asset_list'
    
    def get_extra_context(self, request, instance):
        if not request.session.session_key:
            request.session.save()
        
        session_key = request.session.session_key
        object_id = instance.pk if instance.pk else ''
        model_name = 'asset'
        
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
            'type_file': '',
            'uploaded_files': uploaded_files,
        }

    
    def get_return_url(self, request, obj=None):
        from django.urls import reverse
        return_url = request.GET.get('return_url') or request.POST.get('return_url')
        if return_url and return_url.startswith('/'):
            return return_url
        return reverse(self.default_return_url)

class AssetDeleteView(generic.ObjectDeleteView):
    """Xóa tài sản với popup xác nhận"""
    queryset = models.Asset.objects.all()
    default_return_url = 'plugins:netbox_asset_management:asset_list'


# --- VIEWS CHO ASSET GROUP (Nhóm tài sản) ---
class AssetGroupView(generic.ObjectView):
    queryset = models.AssetGroup.objects.all()
    
    def get_extra_context(self, request, instance):
        # Lấy danh sách tài sản thuộc nhóm này để hiển thị [cite: 42]
        assets = models.Asset.objects.filter(asset_group=instance)
        
        uploaded_files = []
        if instance.pk:
            try:
                from upload_file_plugin.models import UploadedFile
                uploaded_files = UploadedFile.objects.filter(
                    object_id=instance.pk, model_name='assetgroup'
                )
            except ImportError:
                pass
                
        return {
            'asset_count': assets.count(),
            'uploaded_files': uploaded_files,
        }
        
class AssetGroupListView(generic.ObjectListView):
    queryset = models.AssetGroup.objects.annotate(
            asset_count=Count('assets')
        )
    filterset = filtersets.AssetGroupFilterSet
    filterset_form = forms.AssetGroupFilterForm
    table = tables.AssetGroupTable

class AssetGroupEditView(generic.ObjectEditView):
    queryset = models.AssetGroup.objects.all()
    form = forms.AssetGroupForm
    template_name = 'netbox_asset_management/edit.html'
    default_return_url = 'plugins:netbox_asset_management:assetgroup_list'
    
    def get_extra_context(self, request, instance):
        if not request.session.session_key:
            request.session.save()
        
        session_key = request.session.session_key
        object_id = instance.pk if instance.pk else ''
        model_name = 'assetgroup'
        
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
            'type_file': '',
            'uploaded_files': uploaded_files,
        }
    
    def get_return_url(self, request, obj=None):
        from django.urls import reverse
        return_url = request.GET.get('return_url') or request.POST.get('return_url')
        if return_url and return_url.startswith('/'):
            return return_url
        return reverse(self.default_return_url)
    
class AssetGroupDeleteView(generic.ObjectDeleteView):
    """Xóa nhóm tài sản"""
    queryset = models.AssetGroup.objects.all()
    default_return_url = 'plugins:netbox_asset_management:assetgroup_list'