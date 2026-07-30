from django.contrib import admin
from .models import AccessRequest, RequestSubject, RequestHistory, UserRegionAssignment


@admin.register(UserRegionAssignment)
class UserRegionAssignmentAdmin(admin.ModelAdmin):
    """Quản lý phân quyền Region cho người dùng"""
    list_display = ('user', 'region')
    list_filter = ('region',)
    search_fields = ('user__username', 'region__name')
    autocomplete_fields = ('user', 'region')


@admin.register(AccessRequest)
class AccessRequestAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'expected_date', 'region', 'site', 'created_by', 'created', 'last_updated')
    list_filter = ('status', 'region', 'site')
    search_fields = ('name', 'reason')
    readonly_fields = ('created_by', 'created', 'last_updated')


@admin.register(RequestSubject)
class RequestSubjectAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'id_number', 'organization', 'status', 'verify_status', 'access_request')
    list_filter = ('status', 'verify_status')
    search_fields = ('full_name', 'id_number', 'organization')


@admin.register(RequestHistory)
class RequestHistoryAdmin(admin.ModelAdmin):
    list_display = ('access_request', 'user', 'action', 'status', 'timestamp')
    list_filter = ('action',)
    readonly_fields = ('timestamp',)
