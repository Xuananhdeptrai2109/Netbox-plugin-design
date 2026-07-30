from rest_framework import serializers
from ..models import Layout, LayoutObject


class LayoutObjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = LayoutObject
        fields = ('id', 'object_type', 'object_id', 'x', 'y', 'rotation', 'z_index')


class LayoutSerializer(serializers.ModelSerializer):
    layout_objects = LayoutObjectSerializer(many=True, read_only=True)

    class Meta:
        model = Layout
        fields = ('id', 'location', 'site', 'name', 'created', 'last_updated', 'layout_objects')
