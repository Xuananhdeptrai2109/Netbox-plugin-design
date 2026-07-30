from dcim.models import Location, Site
from netbox.views import generic
from utilities.views import register_model_view, ViewTab


@register_model_view(Location, 'visualization', path='visualization')
class LocationVisualizationView(generic.ObjectView):
    """
    Tab "Visualization" trên trang chi tiết Location.
    Hiển thị giao diện Canvas 2D (Rack Layout Manager) cho Location hiện tại.
    """
    queryset = Location.objects.all()
    template_name = 'netbox_rack_layout/location_visualization.html'

    tab = ViewTab(
        label='Visualization',
        weight=500,
    )


@register_model_view(Site, 'visualization', path='visualization')
class SiteVisualizationView(generic.ObjectView):
    """
    Tab "Visualization" trên trang chi tiết Site.
    Hiển thị tổng quan trực quan tất cả Location thuộc Site,
    bao gồm hình ảnh rack/asset/wall đã sắp xếp cho từng Location.
    """
    queryset = Site.objects.all()
    template_name = 'netbox_rack_layout/site_visualization.html'

    tab = ViewTab(
        label='Visualization',
        weight=500,
    )
