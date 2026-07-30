from netbox.search import SearchIndex, register_search
from .models import AccessRequest, RequestSubject


@register_search
class AccessRequestIndex(SearchIndex):
    """Đăng ký phiếu yêu cầu vào hệ thống tìm kiếm toàn cục"""
    model = AccessRequest
    fields = (
        ('name', 100),
        ('reason', 200),
    )


@register_search
class RequestSubjectIndex(SearchIndex):
    """Đăng ký đối tượng vào hệ thống tìm kiếm toàn cục"""
    model = RequestSubject
    fields = (
        ('full_name', 100),
        ('id_number', 100),
        ('organization', 200),
        ('description', 500),
    )
