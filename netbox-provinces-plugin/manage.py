import os
import sys
from types import ModuleType

# 1. Định nghĩa Module lười để giả lập các class NetBox chuẩn
class LazyNetBoxModelsModule(ModuleType):
    def __getattr__(self, name):
        import django.db.models as models
        if name == 'NetBoxModel':
            class MockNetBoxModel(models.Model):
                created = models.DateTimeField(auto_now_add=True, blank=True, null=True)
                last_updated = models.DateTimeField(auto_now=True, blank=True, null=True)
                custom_field_data = models.JSONField(blank=True, default=dict)
                class Meta:
                    abstract = True
                    app_label = 'provinces_manager'
            return MockNetBoxModel
        return models.Field 

def main():
    # 2. Cấu hình Django tối giản
    from django.conf import settings
    if not settings.configured:
        settings.configure(
            INSTALLED_APPS=['django.contrib.contenttypes', 'provinces_manager'],
            DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
        )

    # 3. GIẢ LẬP CÁC MODULE CỦA NETBOX
    sys.modules['netbox'] = ModuleType('netbox')
    
    nb_plugins = ModuleType('netbox.plugins')
    class DummyConfig:
        def __init__(self, *args, **kwargs): pass
    nb_plugins.PluginConfig = DummyConfig
    nb_plugins.PluginMenuItem = object
    sys.modules['netbox.plugins'] = nb_plugins

    sys.modules['netbox.models'] = LazyNetBoxModelsModule('netbox.models')

    import django.forms as forms
    nb_forms = ModuleType('netbox.forms')
    nb_forms.NetBoxModelForm = forms.ModelForm
    sys.modules['netbox.forms'] = nb_forms

    nb_tables = ModuleType('netbox.tables')
    nb_tables.NetBoxTable = object
    nb_tables.columns = object
    sys.modules['netbox.tables'] = nb_tables

    # 4. GIẢ LẬP PACKAGE UTILITIES
    utils = ModuleType('utilities')
    utils.__path__ = [] 
    sys.modules['utilities'] = utils
    
    utils_json = ModuleType('utilities.json')
    from django.core.serializers.json import DjangoJSONEncoder
    utils_json.CustomFieldJSONEncoder = DjangoJSONEncoder
    sys.modules['utilities.json'] = utils_json
    utils.json = utils_json 
    
    import django.db.models as models
    utils_fields = ModuleType('utilities.fields')
    utils_fields.JSONField = models.JSONField
    utils_fields.JSONArrayField = models.JSONField
    sys.modules['utilities.fields'] = utils_fields
    utils.fields = utils_fields

    utils_forms = ModuleType('utilities.forms')
    sys.modules['utilities.forms'] = utils_forms
    utils.forms = utils_forms

    # 5. GIẢ LẬP PACKAGE TAGGIT (ĐÃ BỔ SUNG TAGGABLE MANAGER CHUẨN)
    taggit = ModuleType('taggit')
    taggit.__path__ = []
    sys.modules['taggit'] = taggit
    
    taggit_managers = ModuleType('taggit.managers')
    
    # Class giả lập để "nuốt" các tham số through, to từ file migration
    class MockTaggableManager(models.Field):
        def __init__(self, *args, **kwargs):
            kwargs.pop('through', None)
            kwargs.pop('to', None)
            super().__init__(*args, **kwargs)
            
    taggit_managers.TaggableManager = MockTaggableManager
    sys.modules['taggit.managers'] = taggit_managers
    taggit.managers = taggit_managers

    # 6. Khởi động Django và chạy lệnh
    import django
    django.setup()

    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()