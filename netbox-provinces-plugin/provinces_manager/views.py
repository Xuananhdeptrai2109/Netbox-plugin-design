from netbox.views import generic
import csv
import io
from django.contrib import messages
from django.shortcuts import render
from . import forms
from . import filtersets
from .models import Province, District, Ward
from .tables import ProvinceTable, DistrictTable, WardTable

# View cho Tỉnh/Thành
class ProvinceListView(generic.ObjectListView):
    queryset = Province.objects.all()
    table = ProvinceTable
    template_name = 'generic/object_list.html'
    filterset = filtersets.ProvinceFilterSet  
    filterset_form = forms.ProvinceFilterForm
    extra_context = {
        'import_url': 'plugins:provinces_manager:province_import',
    }

class ProvinceEditView(generic.ObjectEditView):
    queryset = Province.objects.all()
    form = forms.ProvinceForm
    default_return_url = 'plugins:provinces_manager:province_list'

class ProvinceDeleteView(generic.ObjectDeleteView):
    queryset = Province.objects.all()
    
class ProvinceImportView(generic.BulkImportView):
    queryset = Province.objects.all()
    model_form = forms.ProvinceImportForm
    default_return_url = 'plugins:provinces_manager:province_list'
    
    def post(self, request, *args, **kwargs):
        if not _check_csv_duplicates(request, "Tỉnh/Thành phố"):
            return self.get(request, *args, **kwargs)
        return super().post(request, *args, **kwargs)

# View cho Quận/Huyện
class DistrictListView(generic.ObjectListView):
    queryset = District.objects.all()
    table = DistrictTable    
    template_name = 'generic/object_list.html'
    filterset = filtersets.DistrictFilterSet   
    filterset_form = forms.DistrictFilterForm
    extra_context = {
        'import_url': 'plugins:provinces_manager:district_import',
    }

class DistrictEditView(generic.ObjectEditView):
    queryset = District.objects.all()
    form = forms.DistrictForm
    default_return_url = 'plugins:provinces_manager:district_list'

class DistrictDeleteView(generic.ObjectDeleteView):
    queryset = District.objects.all()
    
class DistrictImportView(generic.BulkImportView):
    queryset = District.objects.all()
    model_form = forms.DistrictImportForm
    default_return_url = 'plugins:provinces_manager:district_list'

    def post(self, request, *args, **kwargs):
        if not _check_csv_duplicates(request, "Quận/Huyện"):
            return self.get(request, *args, **kwargs)
        return super().post(request, *args, **kwargs)

# View cho Xã/Phường
class WardListView(generic.ObjectListView):
    queryset = Ward.objects.all()
    table = WardTable
    template_name = 'generic/object_list.html'
    filterset = filtersets.WardFilterSet     
    filterset_form = forms.WardFilterForm
    extra_context = {
        'import_url': 'plugins:provinces_manager:ward_import',
    }

class WardEditView(generic.ObjectEditView):
    queryset = Ward.objects.all()
    form = forms.WardForm
    default_return_url = 'plugins:provinces_manager:ward_list'
    
class WardDeleteView(generic.ObjectDeleteView):
    queryset = Ward.objects.all()
    
class WardImportView(generic.BulkImportView):
    queryset = Ward.objects.all()
    model_form = forms.WardImportForm
    default_return_url = 'plugins:provinces_manager:ward_list'

    def post(self, request, *args, **kwargs):
        if not _check_csv_duplicates(request, "Xã/Phường"):
            return self.get(request, *args, **kwargs)
        return super().post(request, *args, **kwargs)

def _check_csv_duplicates(request, level_name):
    import_file = request.FILES.get('import_file')
    if not import_file:
        return True

    # Đọc dữ liệu từ file CSV
    file_data = import_file.read().decode('utf-8')
    reader = csv.DictReader(io.StringIO(file_data))
    
    # 1. Xác định Model tương ứng để truy vấn Database
    from .models import Province, District, Ward
    model_map = {
        "Tỉnh/Thành phố": Province,
        "Quận/Huyện": District,
        "Xã/Phường": Ward
    }
    model_class = model_map.get(level_name)
    
    # Lấy tập hợp các mã code đã tồn tại trong Database
    existing_codes = set(model_class.objects.values_list('code', flat=True))
    
    codes_in_file = set()
    duplicate_in_db = []    # Danh sách mã trùng với Database
    duplicate_in_file = []  # Danh sách mã trùng nội bộ file CSV

    # 2. Quét toàn bộ file để gom nhóm các lỗi
    for row in reader:
        code = row.get('code')
        if not code:
            continue
            
        # Kiểm tra trùng với Database (Trường hợp import lần 2)
        if code in existing_codes:
            if code not in duplicate_in_db:
                duplicate_in_db.append(code)
            
        # Kiểm tra trùng nội bộ file CSV
        if code in codes_in_file:
            if code not in duplicate_in_file:
                duplicate_in_file.append(code)
            
        codes_in_file.add(code)

    # 3. Hiển thị thông báo tổng hợp bằng dấu phẩy
    has_error = False
    
    if duplicate_in_db:
        list_db = ", ".join(duplicate_in_db)
        messages.error(
            request, 
            f"Lỗi: Các mã code sau đã tồn tại trong hệ thống: {list_db}. Vui lòng kiểm tra lại."
        )
        has_error = True

    if duplicate_in_file:
        list_file = ", ".join(duplicate_in_file)
        messages.error(
            request, 
            f"Lỗi: Các mã code sau bị lặp lại nhiều lần trong file CSV: {list_file}."
        )
        has_error = True

    if has_error:
        return False

    # Nếu không có lỗi, reset con trỏ file để NetBox xử lý lưu
    import_file.seek(0)
    return True