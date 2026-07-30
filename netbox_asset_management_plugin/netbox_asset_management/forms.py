from django import forms
from django.core.exceptions import ValidationError
from netbox.forms import NetBoxModelForm, NetBoxModelFilterSetForm
from utilities.forms.fields import DynamicModelChoiceField, DynamicModelMultipleChoiceField, SlugField
from utilities.forms.widgets import DatePicker

from .models import Asset, AssetGroup, AssetStatusChoices, AssetGroupStatusChoices
from dcim.models import Region, Site, Location

class AssetForm(NetBoxModelForm):
    region = DynamicModelChoiceField(queryset=Region.objects.all(), required=False, label="Region")
    site = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        required=False,
        query_params={'region_id': '$region'},
        label="Site"
    )
    location = DynamicModelChoiceField(
        queryset=Location.objects.all(),
        required=False,
        query_params={'site_id': '$site'},
        label="Location"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.data and 'uploaded_files_json' not in self.data:
            self.data = self.data.copy()
            self.data['uploaded_files_json'] = '[]'

    class Meta:
        model = Asset
        fields = (
            'name', 'asset_code', 'asset_group', 'status', 'description', 
            'device_type', 'model', 'serial_number', 
            'manufacturer', 'installation_date', 'purchase_date', 
            'warranty_period', 'region', 'site', 'location'
        )
        widgets = {
            'installation_date': DatePicker(),
            'purchase_date': DatePicker(),
        }

    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)
        
        # Xử lý upload_file_plugin
        all_files_json = self.data.get('all_files')
        if all_files_json:
            import json, os, uuid, logging
            from django.conf import settings
            from django.core.files import File as DjangoFile
            from upload_file_plugin.models import UploadedFile
            logger = logging.getLogger(__name__)

            try:
                files = json.loads(all_files_json)
                model_name = 'asset'
                object_id = instance.pk
                upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', model_name)
                os.makedirs(upload_dir, exist_ok=True)
                
                input_file_names = [f.get('file_name') for f in files if f.get('file_name')]
                old_files_qs = UploadedFile.objects.filter(model_name=model_name, object_id=object_id)
                files_to_delete = old_files_qs.exclude(file_name__in=input_file_names)
                
                for f_del in files_to_delete:
                    try:
                        full_path = os.path.join(settings.MEDIA_ROOT, f_del.file.name)
                        if f_del.file and os.path.exists(full_path):
                            os.remove(full_path)
                        f_del.delete()
                    except Exception as e:
                        logger.error(f"Error deleting file: {e}")
                        
                existing_names = old_files_qs.values_list('file_name', flat=True)
                for f_dict in files:
                    f_name = f_dict.get('file_name')
                    temp_path = f_dict.get('path')
                    if f_name in existing_names or not temp_path or not os.path.exists(temp_path):
                        continue
                    try:
                        with open(temp_path, 'rb') as temp_f:
                            base, ext = os.path.splitext(f_name)
                            unique_name = f"{base}_{uuid.uuid4().hex}{ext}"
                            django_file = DjangoFile(temp_f, name=unique_name)
                            UploadedFile.objects.create(file=django_file, file_name=f_name, model_name=model_name, object_id=object_id)
                    except Exception as e:
                        logger.error(f"Error saving file: {e}")
            except Exception as e:
                logger.error(f"Error parsing all_files: {e}")
                
        return instance

# forms.py
class AssetGroupForm(NetBoxModelForm):
    slug = SlugField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.data and 'uploaded_files_json' not in self.data:
            self.data = self.data.copy()
            self.data['uploaded_files_json'] = '[]'

    class Meta:
        model = AssetGroup
        fields = ('name', 'slug', 'code', 'status', 'description', 'exclude_from_visualization')

    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)
        
        # Xử lý upload_file_plugin
        all_files_json = self.data.get('all_files')
        if all_files_json:
            import json, os, uuid, logging
            from django.conf import settings
            from django.core.files import File as DjangoFile
            from upload_file_plugin.models import UploadedFile
            logger = logging.getLogger(__name__)

            try:
                files = json.loads(all_files_json)
                model_name = 'assetgroup'
                object_id = instance.pk
                upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', model_name)
                os.makedirs(upload_dir, exist_ok=True)
                
                input_file_names = [f.get('file_name') for f in files if f.get('file_name')]
                old_files_qs = UploadedFile.objects.filter(model_name=model_name, object_id=object_id)
                files_to_delete = old_files_qs.exclude(file_name__in=input_file_names)
                
                for f_del in files_to_delete:
                    try:
                        full_path = os.path.join(settings.MEDIA_ROOT, f_del.file.name)
                        if f_del.file and os.path.exists(full_path):
                            os.remove(full_path)
                        f_del.delete()
                    except Exception as e:
                        logger.error(f"Error deleting file: {e}")
                        
                existing_names = old_files_qs.values_list('file_name', flat=True)
                for f_dict in files:
                    f_name = f_dict.get('file_name')
                    temp_path = f_dict.get('path')
                    if f_name in existing_names or not temp_path or not os.path.exists(temp_path):
                        continue
                    try:
                        with open(temp_path, 'rb') as temp_f:
                            base, ext = os.path.splitext(f_name)
                            unique_name = f"{base}_{uuid.uuid4().hex}{ext}"
                            django_file = DjangoFile(temp_f, name=unique_name)
                            UploadedFile.objects.create(file=django_file, file_name=f_name, model_name=model_name, object_id=object_id)
                    except Exception as e:
                        logger.error(f"Error saving file: {e}")
            except Exception as e:
                logger.error(f"Error parsing all_files: {e}")
                
        return instance

class AssetFilterForm(NetBoxModelFilterSetForm):
    model = Asset
    q = forms.CharField(required=False, label='Tìm kiếm')
    asset_group_id = DynamicModelMultipleChoiceField(queryset=AssetGroup.objects.all(), required=False, label='Nhóm tài sản')
    status = forms.MultipleChoiceField(choices=AssetStatusChoices, required=False, label='Trạng thái') 

class AssetGroupFilterForm(NetBoxModelFilterSetForm):
    model = AssetGroup
    q = forms.CharField(required=False, label='Tìm kiếm')
    status = forms.MultipleChoiceField(choices=AssetGroupStatusChoices, required=False, label='Trạng thái')
