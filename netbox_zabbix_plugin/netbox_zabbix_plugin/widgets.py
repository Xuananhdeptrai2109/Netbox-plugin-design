try:
    from extras.dashboard.widgets import DashboardWidget
    from extras.dashboard.utils import register_widget
except ImportError:
    try:
        from netbox.dashboard.widgets import DashboardWidget
        from netbox.dashboard.utils import register_widget
    except ImportError:
        DashboardWidget = object
        def register_widget(cls): return cls

from django.template.loader import render_to_string

@register_widget
class ZabbixProblemsWidget(DashboardWidget):
    description = 'Hiển thị danh sách các sự cố giám sát Zabbix theo thời gian thực (Zabbix Monitoring Problems)'
    default_title = 'Zabbix Active Problems'
    width = 12
    height = 5

    def render(self, request):
        return render_to_string('netbox_zabbix_plugin/widgets/zabbix_problems_widget.html', request=request)
