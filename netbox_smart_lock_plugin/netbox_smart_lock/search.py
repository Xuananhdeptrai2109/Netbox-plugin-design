from netbox.search import SearchIndex, register_search
from .models import SmartLock

@register_search
class SmartLockIndex(SearchIndex):
    model = SmartLock
    fields = (
        ('name', 100),
        ('code', 100),
        ('serial', 150),
        ('model', 150),
        ('manufacturer', 200),
        ('description', 500),
    )
