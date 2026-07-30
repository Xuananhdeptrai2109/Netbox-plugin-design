from django import forms
from django.core.exceptions import ValidationError
from netbox.forms import NetBoxModelForm, NetBoxModelImportForm, NetBoxModelFilterSetForm
from utilities.forms.fields import DynamicModelChoiceField, DynamicModelMultipleChoiceField, CSVModelChoiceField
from utilities.forms.widgets import DatePicker

from dcim.models import Region, Site, Location

from .models import AccessRequest, RequestSubject, UserRegionAssignment
from .choices import RequestStatusChoices


class AccessRequestForm(NetBoxModelForm):
    """Form thêm mới / chỉnh sửa phiếu yêu cầu"""
    region = DynamicModelChoiceField(
        queryset=Region.objects.all(),
        required=False,
        label="Region"
    )
    site = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        required=False,
        query_params={'region_id': '$region'},
        label="Site"
    )
    class Meta:
        model = AccessRequest
        fields = ('name', 'expected_date', 'reason', 'region', 'site')
        widgets = {
            'expected_date': DatePicker(attrs={'placeholder': 'dd/mm/yyyy'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Lọc Region theo phân quyền UserRegionAssignment
        if self.user:
            assigned_region_ids = UserRegionAssignment.objects.filter(
                user=self.user
            ).values_list('region_id', flat=True)
            self.fields['region'].queryset = Region.objects.filter(
                pk__in=assigned_region_ids
            )

        # Xử lý uploaded_files_json cho upload_file_plugin
        if self.data and 'uploaded_files_json' not in self.data:
            self.data = self.data.copy()
            self.data['uploaded_files_json'] = '[]'

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            qs = AccessRequest.objects.filter(name=name)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError('Tên phiếu đã tồn tại. Vui lòng chọn tên khác.')
        return name


class RequestSubjectForm(NetBoxModelForm):
    """Form thêm mới / chỉnh sửa đối tượng"""
    location = DynamicModelChoiceField(
        queryset=Location.objects.all(),
        required=False,
        label="Location"
    )

    class Meta:
        model = RequestSubject
        fields = (
            'id_number', 'full_name', 'organization', 'position',
            'phone', 'location', 'description'
        )
    def __init__(self, *args, **kwargs):
        self.access_request = kwargs.pop('access_request', None)
        super().__init__(*args, **kwargs)

        if not self.access_request and getattr(self.instance, 'access_request', None):
            self.access_request = self.instance.access_request

        # Lọc Location theo Site của phiếu yêu cầu
        if self.access_request and self.access_request.site:
            self.fields['location'].queryset = Location.objects.filter(
                site=self.access_request.site
            )
            self.fields['location'].query_params = {
                'site_id': self.access_request.site.pk
            }

        # Xử lý uploaded_files_json cho upload_file_plugin
        if self.data and 'uploaded_files_json' not in self.data:
            self.data = self.data.copy()
            self.data['uploaded_files_json'] = '[]'

    def clean_id_number(self):
        id_number = self.cleaned_data.get('id_number')
        if id_number and self.access_request:
            qs = RequestSubject.objects.filter(
                access_request=self.access_request,
                id_number=id_number
            )
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(
                    'Mã định danh đã tồn tại trong phiếu này. Vui lòng nhập mã khác.'
                )
        return id_number

    def clean(self):
        cleaned_data = super().clean()

        # Kiểm tra file đính kèm bắt buộc
        all_files_json = self.data.get('all_files')
        has_files = False
        if all_files_json:
            import json
            try:
                files = json.loads(all_files_json)
                if files:
                    has_files = True
                    # Validate định dạng (jpg, jpeg, png) và dung lượng file (<= 25MB)
                    for f in files:
                        f_name = f.get('file_name') or f.get('name') or ''
                        size = f.get('size')

                        # Validate định dạng đuôi file
                        ext = f_name.split('.')[-1].lower() if '.' in f_name else ''
                        if ext not in ['jpg', 'jpeg', 'png']:
                            raise ValidationError(f"File '{f_name}' không đúng định dạng. Chỉ cho phép định dạng: jpg, jpeg, png.")

                        # Validate dung lượng (25MB = 25 * 1024 * 1024)
                        if size and int(size) > 25 * 1024 * 1024:
                            raise ValidationError(f"File '{f_name}' vượt quá dung lượng tối đa cho phép (25MB).")
            except json.JSONDecodeError:
                pass

        if not has_files:
            raise ValidationError("Tệp đính kèm là bắt buộc. Vui lòng tải lên ít nhất một file ảnh (jpg, jpeg, png).")

        return cleaned_data

    def save(self, *args, **kwargs):
        if self.access_request and not self.instance.pk:
            self.instance.access_request = self.access_request
        instance = super().save(*args, **kwargs)

        # Xử lý upload_file_plugin
        all_files_json = self.data.get('all_files')
        if all_files_json:
            import json
            import os
            import uuid
            import logging
            from django.conf import settings
            from django.core.files import File as DjangoFile
            from upload_file_plugin.models import UploadedFile
            logger = logging.getLogger(__name__)

            try:
                files = json.loads(all_files_json)
                model_name = 'requestsubject'
                object_id = instance.pk
                upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', model_name)
                os.makedirs(upload_dir, exist_ok=True)

                input_file_names = [f.get('file_name') for f in files if f.get('file_name')]
                old_files_qs = UploadedFile.objects.filter(
                    model_name=model_name, object_id=object_id
                )
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
                            UploadedFile.objects.create(
                                file=django_file,
                                file_name=f_name,
                                model_name=model_name,
                                object_id=object_id
                            )
                    except Exception as e:
                        logger.error(f"Error saving file: {e}")
            except Exception as e:
                logger.error(f"Error parsing all_files: {e}")

        return instance


class AccessRequestFilterForm(NetBoxModelFilterSetForm):
    """Form tìm kiếm / lọc phiếu yêu cầu"""
    model = AccessRequest
    q = forms.CharField(required=False, label='Tìm kiếm')
    status = forms.MultipleChoiceField(
        choices=RequestStatusChoices,
        required=False,
        label='Trạng thái'
    )


class AdminReasonForm(forms.Form):
    """Form nhập lý do chấp nhận / từ chối"""
    reason = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'maxlength': 500}),
        max_length=500,
        required=False,
        label='Lý do'
    )


class RequestSubjectImportForm(NetBoxModelImportForm):
    """Form import đối tượng bằng file CSV"""
    access_request = CSVModelChoiceField(
        queryset=AccessRequest.objects.all(),
        to_field_name='name',
        help_text='Tên phiếu yêu cầu'
    )
    location = CSVModelChoiceField(
        queryset=Location.objects.all(),
        to_field_name='name',
        required=False,
        help_text='Tên Location'
    )

    class Meta:
        model = RequestSubject
        fields = (
            'access_request', 'id_number', 'full_name', 'organization',
            'position', 'phone', 'location', 'description'
        )

    def clean_id_number(self):
        id_number = self.cleaned_data.get('id_number')
        access_request = self.cleaned_data.get('access_request')
        if id_number:
            if len(id_number) != 12 or not id_number.isdigit():
                raise ValidationError("Mã định danh phải có đúng 12 ký tự số.")
            if access_request and RequestSubject.objects.filter(access_request=access_request, id_number=id_number).exists():
                raise ValidationError(f"Mã định danh '{id_number}' đã tồn tại trong phiếu '{access_request.name}'.")
        return id_number

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            if len(phone) != 10 or not phone.isdigit() or not phone.startswith('0'):
                raise ValidationError("Số điện thoại phải có 10 chữ số và bắt đầu bằng 0.")
        return phone

