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
        label='Visualization 2D',
        weight=500,
    )


@register_model_view(Location, 'visualization_3d', path='visualization-3d')
class LocationVisualization3DView(generic.ObjectView):
    """
    Tab "Visualization 3D" trên trang chi tiết Location.
    Hiển thị giao diện 3D Isometric Room cho Location hiện tại dựa trên dữ liệu 2D layout.
    """
    queryset = Location.objects.all()
    template_name = 'netbox_rack_layout/location_visualization_3d.html'

    tab = ViewTab(
        label='Visualization 3D',
        weight=510,
    )


@register_model_view(Location, 'temperature', path='temperature')
class LocationTemperatureView(generic.ObjectView):
    """
    Tab "Temperature" trên trang chi tiết Location.
    Hiển thị giao diện giám sát nhiệt độ, điều chỉnh dải [a, b], cập nhật nhiệt độ
    và ghi log chuỗi thời gian (time-series) chu kỳ 5 giây cho Racks và Assets.
    """
    queryset = Location.objects.all()
    template_name = 'netbox_rack_layout/location_temperature.html'

    tab = ViewTab(
        label='Temperature',
        weight=520,
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
