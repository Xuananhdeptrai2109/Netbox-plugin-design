from rest_framework import serializers
from ..models import Layout, LayoutObject


class LayoutObjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = LayoutObject
        fields = ('id', 'object_type', 'object_id', 'x', 'y', 'rotation', 'z_index', 'width', 'height', 'parent_type', 'parent_id', 'wall_face')


class LayoutSerializer(serializers.ModelSerializer):
    layout_objects = LayoutObjectSerializer(many=True, read_only=True)

    class Meta:
        model = Layout
        fields = ('id', 'location', 'site', 'name', 'created', 'last_updated', 'layout_objects')
