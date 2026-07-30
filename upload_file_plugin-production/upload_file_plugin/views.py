from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import UploadedFile
import logging
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
from django.conf import settings
import os
import uuid
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.core.files import File as DjangoFile
from django.http import FileResponse, Http404

logger = logging.getLogger(__name__)
VALID_MEDIA_TYPES = [
    'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'tiff',
    'pdf', 'docx', 'xlsx', 'pptx', 'odt', 'ods',
    'txt', 'csv', 'json', 'yaml', 'xml', 'md', 'log',
    'mp3', 'wav', 'mp4', 'mov', 'avi', 'mkv',
]

@require_http_methods(["POST"])
@csrf_exempt
def upload_file_view(request):
    files = request.FILES.getlist('files')
    
    valid_flg_str = request.POST.get('valid_flg', '0')
    validate_enabled = (valid_flg_str == '1') 
    type_file_json_str = request.POST.get('type_file', '[]')
    
    errors = []
    saved_files = []
        
    formatted_allowed_extensions_for_error = [] 

    upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads/tmp')
    os.makedirs(upload_dir, exist_ok=True)

    for f in files:
        is_file_valid = True
        validation_error_message = ""
        
        name, ext = os.path.splitext(f.name)
        file_type = f.name.split('.').pop().lower()
        logging.info(file_type)
        if file_type not in VALID_MEDIA_TYPES:
            is_file_valid = False
            validation_error_message = (
                f"File '{name}' có định dạng không được hỗ trợ ({file_type})."
            )
        
        if is_file_valid and validate_enabled :
            if file_type not in type_file_json_str:
                validation_error_message = (
                        f"File '{name}' không thuộc các định dạng cho phép: "
                        f"{', '.join(formatted_allowed_extensions_for_error)}."
                    )
        if not is_file_valid:
            errors.append(validation_error_message)
            logger.warning(f"File '{name}' bị từ chối: {validation_error_message}")
            continue
        
        new_file_name = f"{name}_{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(upload_dir, new_file_name)

        try:
            with open(file_path, 'wb+') as destination:
                for chunk in f.chunks():
                    destination.write(chunk)
            saved_files.append({
                'file_name': f.name,
                'size': f.size,
                'path': file_path
            })
            logger.info(f"Uploaded file: {f.name} -> {file_path}")
        except Exception as e:
            logger.error(f"Failed to upload file {f.name}: {e}")
            errors.append(f"Lỗi khi lưu file '{f.name}': {e}")

    return JsonResponse({
        'saved_files': saved_files,
        'errors': errors,
        'success': bool(saved_files) and not errors if files else False
    })

@require_http_methods(["POST"])
@csrf_exempt
def delete_file_view(request):
    try:
        # Ưu tiên lấy id từ JSON, nếu không có thì lấy từ form
        file_id = None
        if request.content_type and 'application/json' in request.content_type:
            data = json.loads(request.body)
            file_id = data.get('id')
        else:
            file_id = request.POST.get('id')
        if not file_id:
            return JsonResponse({'success': False, 'error': 'Missing file id'}, status=400)
        file = UploadedFile.objects.get(id=file_id)
        # Xóa file vật lý nếu có trường path
        if hasattr(file, 'path') and file.path:
            file_path = os.path.join(settings.BASE_DIR, file.path.lstrip('/'))
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    logger.error(f"Lỗi khi xóa file vật lý: {e}")
        file.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@csrf_exempt
def assign_object_id(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        session_key = data.get('session_key')
        object_id = data.get('object_id')
        model_name = data.get('model_name')
        files = UploadedFile.objects.filter(session_key=session_key, object_id__isnull=True, model_name=model_name)
        files.update(object_id=object_id)
        # Lấy lại danh sách file đã gán object_id
        uploaded_files = list(UploadedFile.objects.filter(object_id=object_id, model_name=model_name).values('id', 'file_name', 'file__size', 'created_at'))
        # Đổi 'file__size' thành 'size' nếu model bạn lưu size riêng
        return JsonResponse({'success': True, 'uploaded_files': uploaded_files})
    return JsonResponse({'success': False}, status=400)

@require_http_methods(["POST"])
@csrf_exempt
def delete_temp_file_view(request):
    try:
        file_name = request.POST.get('file_name')
        file_path = request.POST.get('path')
        if not file_name or not file_path:
            return JsonResponse({'success': False, 'error': 'Missing file_name or path'}, status=400)
        # Đảm bảo chỉ xóa file trong thư mục uploads/tmp
        allowed_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', 'tmp')
        abs_file_path = os.path.abspath(os.path.join(settings.BASE_DIR, file_path.lstrip('/')))
        if not abs_file_path.startswith(os.path.abspath(allowed_dir)):
            return JsonResponse({'success': False, 'error': 'Invalid file path'}, status=400)
        if os.path.exists(abs_file_path):
            try:
                os.remove(abs_file_path)
                logger.info(f"Deleted temp file: {abs_file_path}")
                return JsonResponse({'success': True})
            except Exception as e:
                logger.error(f"Error deleting temp file: {e}")
                return JsonResponse({'success': False, 'error': str(e)}, status=500)
        else:
            return JsonResponse({'success': False, 'error': 'File does not exist'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

class SaveFilesView(APIView):
    permission_classes = [IsAuthenticated]
    query_set = UploadedFile.objects.none()
    queryset = UploadedFile.objects.none()
    
    def post(self, request, *args, **kwargs):
        files_json = request.data.get('all_files')
        logger.info(f"Received files JSON: {files_json}")

        if not files_json or not files_json.strip():
            files_json = '[]'
        
        try:
            files = json.loads(files_json)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON format received: {files_json}")
            return JsonResponse({'success': False, 'error': 'Invalid JSON format.'}, status=400)
        
        errors = []
        saved_files = []
        model_name = request.data.get('model_name')
        object_id = request.data.get('object_id')

        upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', model_name)
        
        try:
            os.makedirs(upload_dir, exist_ok=True)
            logger.info(f"Ensured upload directory exists: {upload_dir}")
        except Exception as e:
            logger.error(f"Failed to create upload directory {upload_dir}: {e}")
            return JsonResponse({'success': False, 'error': f'Failed to prepare upload directory: {e}'}, status=500)

        # --- Delete old file ---
        input_file_names_from_client = [f.get('file_name') for f in files if f.get('file_name')]
        
        old_files_qs = UploadedFile.objects.filter(model_name=model_name, object_id=object_id)
        
        files_to_delete = old_files_qs.exclude(file_name__in=input_file_names_from_client)
        
        for file_obj_to_delete in files_to_delete:
            try:
                full_path_to_delete = os.path.join(settings.MEDIA_ROOT, file_obj_to_delete.file.name)
                
                # Check file exists
                if file_obj_to_delete.file and os.path.exists(full_path_to_delete):
                    os.remove(full_path_to_delete)
                    logger.info(f"Deleted file from disk: {full_path_to_delete}")
                
                # Delete record from Database
                file_obj_to_delete.delete()
                logger.info(f"Deleted record from DB: {file_obj_to_delete.file_name}")

            except Exception as e:
                logger.error(f"Error deleting old file '{file_obj_to_delete.file_name}': {e}")

        # --- Update new File ---
        existing_file_names = old_files_qs.values_list('file_name', flat=True)
        
        for file_dict in files:
            file_name = file_dict.get("file_name")
            temp_path = file_dict.get("path")

            if file_name in existing_file_names:
                logger.info(f"Skipping existing file: {file_name}")
                continue
            
            # Check exists file
            if not temp_path or not os.path.exists(temp_path):
                errors.append(f"Temp file not found or invalid: {file_name} at {temp_path}")
                logger.error(f"Temp file not found or invalid for {file_name}: {temp_path}")
                continue
            
            try:
                # Open File
                with open(temp_path, 'rb') as temp_file_object:
                    
                    #Create url unique
                    name_base, ext = os.path.splitext(file_name)
                    unique_final_filename = f"{name_base}_{uuid.uuid4().hex}{ext}"
                    
                    #Create File from file temp
                    django_file_to_save = DjangoFile(temp_file_object, name=unique_final_filename)

                    # Save Database
                    uploaded_file = UploadedFile.objects.create(
                        file=django_file_to_save, 
                        file_name=file_name, 
                        model_name=model_name,
                        object_id=object_id
                    )
                    
                # Add information file return
                saved_files.append({
                    'id': uploaded_file.id,
                    'file_name': uploaded_file.file_name, 
                    'path': uploaded_file.file.url,       
                    'size': uploaded_file.file.size,      
                })
                logger.info(f"Successfully saved file to DB and disk: {uploaded_file.file_name} -> {uploaded_file.file.url}")
            except Exception as e:
                logger.error(f"Failed to process and save file {file_name}: {e}")
                errors.append(f"Error saving file '{file_name}': {e}")

        # Return Json
        return JsonResponse({
            'success': len(errors) == 0,
            'saved_files': saved_files,
            'errors': errors
        })
