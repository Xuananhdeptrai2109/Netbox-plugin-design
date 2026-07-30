from django.shortcuts import render, redirect
from ..models import UploadedFile
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from ..utils import get_serialized_uploaded_files_for_objects
from django.utils.translation import gettext as _
class GetFileFromDBAPIView(APIView):
    permission_classes = [IsAuthenticated]
    queryset = UploadedFile.objects.none()
    def post(self, request, *args, **kwargs):
        data = request.data
        objectIdList = data.get('objectIdList')
        modelName = data.get('modelName')

        files_data = get_serialized_uploaded_files_for_objects(objectIdList, modelName)
        
        return Response({
            'status': 'success',
            'files': files_data, 
            'count': len(files_data) 
        }, status=status.HTTP_200_OK)

class CheckImportFileView(APIView):
    permission_classes = [IsAuthenticated]
    queryset = UploadedFile.objects.none()
    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'Không có file nào được gửi'}, status=400)

        try:
            content = file.read().decode('utf-8-sig')  # hoặc utf-8
            return Response({'success': True})  # Pass
        except UnicodeDecodeError:
            return Response({'error': str(_("Cannot read the file. Make sure it is saved as UTF-8 encoded CSV."))}, status=400)