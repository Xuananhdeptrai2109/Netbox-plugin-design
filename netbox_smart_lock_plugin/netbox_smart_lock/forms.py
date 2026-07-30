from django import forms
from django.core.exceptions import ValidationError
from netbox.forms import NetBoxModelForm, NetBoxModelFilterSetForm
from utilities.forms.fields import DynamicModelChoiceField, DynamicModelMultipleChoiceField
from utilities.forms.widgets import DatePicker

from .models import SmartLock, SmartLockStatusChoices, RackFaceChoices
from dcim.models import Region, Site, Location, Rack

# Import AssetGroup an toàn
try:
    from netbox_asset_management.models import AssetGroup
except ImportError:
    AssetGroup = None

class SmartLockForm(NetBoxModelForm):
    region = DynamicModelChoiceField(queryset=Region.objects.all(), required=False, label="Region")
    site = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        required=True,
        query_params={'region_id': '$region'},
        label="Site"
    )
    location = DynamicModelChoiceField(
        queryset=Location.objects.all(),
        required=False,
        query_params={'site_id': '$site'},
        label="Location"
    )
    rack = DynamicModelChoiceField(
        queryset=Rack.objects.all(),
        required=False,
        query_params={'location_id': '$location'},
        label="Rack"
    )
    
    warranty_end = forms.DateField(
        required=False,
        disabled=True,
        label="Thời gian bảo hành",
        widget=DatePicker(attrs={'placeholder': 'DD/MM/YYYY'})
    )
    
    asset_group = None
    if AssetGroup:
        asset_group = DynamicModelChoiceField(
            queryset=AssetGroup.objects.all(),
            required=False,
            label="Nhóm tài sản"
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.data and 'uploaded_files_json' not in self.data:
            self.data = self.data.copy()
            self.data['uploaded_files_json'] = '[]'
            
        if self.instance and self.instance.pk:
            self.fields['warranty_end'].initial = self.instance.warranty_end
            
        # Thêm dynamic field asset_group vào form nếu import được
        if AssetGroup and 'asset_group' not in self.fields:
            self.fields['asset_group'] = DynamicModelChoiceField(
                queryset=AssetGroup.objects.all(),
                required=False,
                label="Nhóm tài sản"
            )

    class Meta:
        model = SmartLock
        fields = (
            'name', 'code', 'status', 'description', 
            'device_type', 'model', 'serial', 
            'manufacturer', 'installation_date', 'purchase_date', 
            'warranty_period', 'region', 'site', 'location', 'rack', 'rack_face'
        )
        if AssetGroup:
            fields = fields + ('asset_group',)
            
        widgets = {
            'installation_date': DatePicker(attrs={'placeholder': 'DD/MM/YYYY'}),
            'purchase_date': DatePicker(attrs={'placeholder': 'DD/MM/YYYY'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name and len(name) > 100:
            raise ValidationError("Tên không được vượt quá 100 ký tự.")
        return name

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if code and len(code) > 50:
            raise ValidationError("Mã không được vượt quá 50 ký tự.")
        return code

    def clean_description(self):
        description = self.cleaned_data.get('description')
        if description and len(description) > 500:
            raise ValidationError("Mô tả không được vượt quá 500 ký tự.")
        return description

    def clean_device_type(self):
        device_type = self.cleaned_data.get('device_type')
        if device_type and len(device_type) > 100:
            raise ValidationError("Loại thiết bị không được vượt quá 100 ký tự.")
        return device_type

    def clean_warranty_period(self):
        warranty_period = self.cleaned_data.get('warranty_period')
        if warranty_period is not None and warranty_period < 0:
            raise ValidationError("Thời hạn bảo hành phải là số nguyên dương.")
        return warranty_period

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
                model_name = 'smartlock'
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

class SmartLockFilterForm(NetBoxModelFilterSetForm):
    model = SmartLock
    q = forms.CharField(required=False, label='Tìm kiếm')
    status = forms.MultipleChoiceField(choices=SmartLockStatusChoices, required=False, label='Trạng thái') 
    
    if AssetGroup:
        asset_group_id = DynamicModelMultipleChoiceField(
            queryset=AssetGroup.objects.all(),
            required=False,
            label='Nhóm tài sản'
        )
