from rest_framework import serializers
from ..models import UploadedFile

class UploadedFileSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    file_name = serializers.SerializerMethodField()

    class Meta:
        model = UploadedFile
        fields = [
            'id', 
            'object_id', 
            'model_name', 
            'file', 
            'file_name'
        ]

    def get_file_url(self, obj):
        if obj.file:
            return obj.file.url
        return None