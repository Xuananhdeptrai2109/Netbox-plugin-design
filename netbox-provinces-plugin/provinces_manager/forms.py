from django import forms
from django.core.exceptions import ValidationError
from utilities.forms.fields import CSVModelChoiceField
from netbox.forms import NetBoxModelForm, NetBoxModelImportForm, NetBoxModelFilterSetForm
from utilities.forms.fields import DynamicModelMultipleChoiceField
from .models import Province, District, Ward

class ProvinceForm(NetBoxModelForm):
    class Meta:
        model = Province
        fields = ('name', 'code')

class DistrictForm(NetBoxModelForm):
    class Meta:
        model = District
        fields = ('province', 'name', 'code')

class WardForm(NetBoxModelForm):
    class Meta:
        model = Ward
        fields = ('district', 'name', 'code')
        
# ----------------------------------------------------------------------------------------------------------------------        

class ProvinceImportForm(NetBoxModelImportForm):
    class Meta:
        model = Province
        fields = ('name', 'code')
        
    def clean_code(self):
        code = self.cleaned_data.get('code')
        if Province.objects.filter(code=code).exclude(pk=self.instance.pk).exists():
            raise ValidationError(f"Mã code '{code}' đã tồn tại cho một Tỉnh/Thành phố khác. Vui lòng nhập mã khác.")
        return code

class DistrictImportForm(NetBoxModelImportForm):
    province = CSVModelChoiceField(
        queryset=Province.objects.all(),
        to_field_name='name',
        help_text='Tên Tỉnh / Thành phố'
    )

    class Meta:
        model = District
        fields = ('province', 'name', 'code')
        
    def clean_code(self):
        code = self.cleaned_data.get('code')
        if District.objects.filter(code=code).exclude(pk=self.instance.pk).exists():
            raise ValidationError(f"Mã code '{code}' đã tồn tại cho một Quận/Huyện khác. Vui lòng nhập mã khác.")
        return code    
    
class WardImportForm(NetBoxModelImportForm):
    district = CSVModelChoiceField(
        queryset=District.objects.all(),
        to_field_name='name',
        help_text='Tên Quận / Huyện'
    )

    class Meta:
        model = Ward
        fields = ('district', 'name', 'code')
        
    def clean_code(self):
        code = self.cleaned_data.get('code')
        if Ward.objects.filter(code=code).exclude(pk=self.instance.pk).exists():
            raise ValidationError(f"Mã code '{code}' đã tồn tại cho một Xã/Phường khác. Vui lòng nhập mã khác.")
        return code
        
# ----------------------------------------------------------------------------------------------

class ProvinceFilterForm(NetBoxModelFilterSetForm):
    model = Province
    name = forms.CharField(required=False, label='Tên Tỉnh')
    code = forms.CharField(required=False, label='Mã Code')

class DistrictFilterForm(NetBoxModelFilterSetForm):
    model = District
    province_id = DynamicModelMultipleChoiceField(
        queryset=Province.objects.all(),
        required=False,
        label='Tỉnh / Thành phố'
    )
    name = forms.CharField(required=False, label='Tên Quận')

class WardFilterForm(NetBoxModelFilterSetForm):
    model = Ward
    district_id = DynamicModelMultipleChoiceField(
        queryset=District.objects.all(),
        required=False,
        label='Quận / Huyện'
    )
    name = forms.CharField(required=False, label='Tên Xã/Phường') 
