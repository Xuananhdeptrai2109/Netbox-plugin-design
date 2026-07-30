import json
import logging

from django.http import JsonResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin

from dcim.models import Location, Rack

from ..models import Layout, LayoutObject

logger = logging.getLogger(__name__)


class LayoutDetailAPIView(LoginRequiredMixin, View):
    """
    GET /api/plugins/rack-layout/layout/<location_id>/
    Trả về layout (nếu có) kèm danh sách Rack và Device thuộc Location.
    """

    def get(self, request, location_id):
        try:
            location = Location.objects.get(pk=location_id)
        except Location.DoesNotExist:
            return JsonResponse({'error': 'Location not found'}, status=404)

        # Lấy tất cả Rack thuộc Location và tính toán dung lượng trống
        racks_qs = Rack.objects.filter(location=location)

        # Lấy thông tin Smart Lock liên kết với từng Rack
        smartlocks_by_rack = {}
        try:
            from netbox_smart_lock.models import SmartLock
            racks_ids = [r.id for r in racks_qs]
            smartlocks = SmartLock.objects.filter(rack_id__in=racks_ids)
            for s in smartlocks:
                if s.rack_id not in smartlocks_by_rack:
                    smartlocks_by_rack[s.rack_id] = {}
                smartlocks_by_rack[s.rack_id][s.rack_face] = s.status
        except (ImportError, Exception):
            pass

        racks_list = []
        for r in racks_qs:
            utilization = r.get_utilization()
            free_percentage = 100.0 - utilization
            free_u = (free_percentage / 100.0) * r.u_height
            
            if free_u % 1 == 0:
                free_u = int(free_u)
            else:
                free_u = round(free_u, 1)
                
            free_percentage = round(free_percentage, 1)
            
            rack_locks = smartlocks_by_rack.get(r.id, {})
            
            racks_list.append({
                'id': r.id,
                'name': r.name,
                'status': r.status,
                'u_height': r.u_height,
                'free_u': free_u,
                'free_percentage': free_percentage,
                'front_status': rack_locks.get('front', None),
                'rear_status': rack_locks.get('rear', None),
            })



        # Lấy tất cả Asset thuộc Location (nếu có cài đặt netbox_asset_management)
        asset_list = []
        try:
            from netbox_asset_management.models import Asset
            assets = Asset.objects.filter(location=location).select_related('asset_group')
            for a in assets:
                asset_list.append({
                    'id': a.id,
                    'name': a.name or f"Asset #{a.id}",
                    'asset_code': a.asset_code,
                    'status': a.status,
                    'device_type': a.device_type,
                    'model': a.model,
                    'serial_number': a.serial_number,
                    'manufacturer': a.manufacturer,
                    'asset_group': a.asset_group.name if a.asset_group else '',
                })
        except ImportError:
            pass

        # Lấy tất cả SmartLock thuộc Location (nếu có cài đặt netbox_smart_lock)
        smartlock_list = []
        try:
            from netbox_smart_lock.models import SmartLock
            smartlocks = SmartLock.objects.filter(location=location).select_related('asset_group')
            for s in smartlocks:
                smartlock_list.append({
                    'id': s.id,
                    'name': s.name or f"Smart Lock #{s.id}",
                    'code': s.code,
                    'status': s.status,
                    'device_type': s.device_type,
                    'model': s.model,
                    'serial': s.serial,
                    'manufacturer': s.manufacturer,
                    'asset_group': s.asset_group.name if s.asset_group else '',
                    'rack_id': s.rack_id,
                    'rack_face': s.rack_face,
                })
        except ImportError:
            pass

        # Lấy layout đã lưu (nếu có)
        layout_data = None
        layout_objects = []
        try:
            layout = Layout.objects.get(location=location)
            layout_data = {
                'id': layout.id,
                'name': layout.name,
                'created': str(layout.created),
                'last_updated': str(layout.last_updated),
            }
            for obj in layout.layout_objects.all():
                layout_objects.append({
                    'id': obj.id,
                    'object_type': obj.object_type,
                    'object_id': obj.object_id,
                    'x': obj.x,
                    'y': obj.y,
                    'rotation': obj.rotation,
                    'z_index': obj.z_index,
                    'width': obj.width,
                    'height': obj.height,
                    'parent_type': obj.parent_type,
                    'parent_id': obj.parent_id,
                })
        except Layout.DoesNotExist:
            pass

        return JsonResponse({
            'location': {
                'id': location.id,
                'name': location.name,
            },
            'racks': racks_list,
            'assets': asset_list,
            'smartlocks': smartlock_list,
            'layout': layout_data,
            'objects': layout_objects,
        })


class LayoutSaveAPIView(LoginRequiredMixin, View):
    """
    POST /api/plugins/rack-layout/layout/save/
    Lưu toàn bộ vị trí các đối tượng trên Canvas cho một Location.

    Body JSON:
    {
        "location_id": 1,
        "layout_name": "Tên Layout (tùy chọn)",
        "objects": [
            {"object_type": "rack", "object_id": 1, "x": 100, "y": 200, "rotation": 0, "z_index": 1},
            {"object_type": "device", "object_id": 5, "x": 300, "y": 400, "rotation": 90, "z_index": 2}
        ]
    }
    """

    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        location_id = data.get('location_id')
        layout_name = data.get('layout_name', '')
        objects_data = data.get('objects', [])

        if not location_id:
            return JsonResponse({'error': 'location_id is required'}, status=400)

        try:
            location = Location.objects.get(pk=location_id)
        except Location.DoesNotExist:
            return JsonResponse({'error': 'Location not found'}, status=404)

        # Tạo hoặc cập nhật Layout
        layout, created = Layout.objects.get_or_create(
            location=location,
            defaults={'name': layout_name or f"Layout - {location.name}"}
        )
        if not created and layout_name:
            layout.name = layout_name
            layout.save()

        # Xóa toàn bộ LayoutObject cũ và tạo lại
        layout.layout_objects.all().delete()

        new_objects = []
        for obj_data in objects_data:
            new_objects.append(LayoutObject(
                layout=layout,
                object_type=obj_data.get('object_type', 'rack'),
                object_id=obj_data.get('object_id', 0),
                x=obj_data.get('x', 0),
                y=obj_data.get('y', 0),
                rotation=obj_data.get('rotation', 0),
                z_index=obj_data.get('z_index', 0),
                width=obj_data.get('width', 0),
                height=obj_data.get('height', 0),
                parent_type=obj_data.get('parent_type', None),
                parent_id=obj_data.get('parent_id', None),
            ))

        LayoutObject.objects.bulk_create(new_objects)

        return JsonResponse({
            'status': 'ok',
            'message': f'Layout saved successfully ({len(new_objects)} objects)',
            'layout_id': layout.id,
        })


class SiteLayoutDetailAPIView(LoginRequiredMixin, View):
    """
    GET /api/plugins/rack-layout/site-layout/<site_id>/
    Trả về layout site (nếu có) kèm danh sách Location thuộc Site và các layout objects của chúng.
    """

    def get(self, request, site_id):
        from dcim.models import Site as SiteModel
        from dcim.models import Location, Rack

        try:
            site = SiteModel.objects.get(pk=site_id)
        except SiteModel.DoesNotExist:
            return JsonResponse({'error': 'Site not found'}, status=404)

        # Lấy tất cả Location thuộc Site
        locations = Location.objects.filter(site=site).order_by('name')
        locations_list = []

        for loc in locations:
            rack_count = Rack.objects.filter(location=loc).count()

            # Lấy layout của location để vẽ preview
            has_layout = False
            object_count = 0
            layout_objects = []
            racks_data = {}
            assets_data = {}

            try:
                layout = Layout.objects.get(location=loc)
                has_layout = True
                object_count = layout.layout_objects.count()

                for obj in layout.layout_objects.all():
                    layout_objects.append({
                        'object_type': obj.object_type,
                        'object_id': obj.object_id,
                        'x': obj.x,
                        'y': obj.y,
                        'rotation': obj.rotation,
                        'width': obj.width,
                        'height': obj.height,
                        'parent_type': obj.parent_type,
                        'parent_id': obj.parent_id,
                    })

                for r in Rack.objects.filter(location=loc):
                    utilization = r.get_utilization()
                    free_percentage = 100.0 - utilization
                    racks_data[str(r.id)] = {
                        'name': r.name,
                        'free_percentage': free_percentage,
                        'u_height': r.u_height,
                        'status': r.status,
                    }

                try:
                    from netbox_asset_management.models import Asset
                    for a in Asset.objects.filter(location=loc):
                        assets_data[str(a.id)] = {
                            'name': a.name or f"Asset #{a.id}",
                            'status': a.status,
                            'asset_code': a.asset_code,
                            'asset_group': a.asset_group.name if a.asset_group else '',
                        }
                except ImportError:
                    pass

            except Layout.DoesNotExist:
                pass

            locations_list.append({
                'id': loc.id,
                'name': loc.name,
                'slug': loc.slug,
                'rack_count': rack_count,
                'has_layout': has_layout,
                'object_count': object_count,
                'layout_objects': layout_objects,
                'racks_data': racks_data,
                'assets_data': assets_data,
            })

        # Lấy site-level layout (nếu có)
        layout_data = None
        layout_objects = []
        try:
            layout = Layout.objects.get(site=site)
            layout_data = {
                'id': layout.id,
                'name': layout.name,
                'created': str(layout.created),
                'last_updated': str(layout.last_updated),
            }
            for obj in layout.layout_objects.all():
                layout_objects.append({
                    'id': obj.id,
                    'object_type': obj.object_type,
                    'object_id': obj.object_id,
                    'x': obj.x,
                    'y': obj.y,
                    'rotation': obj.rotation,
                    'z_index': obj.z_index,
                    'width': obj.width,
                    'height': obj.height,
                    'parent_type': obj.parent_type,
                    'parent_id': obj.parent_id,
                })
        except Layout.DoesNotExist:
            pass

        return JsonResponse({
            'site': {
                'id': site.id,
                'name': site.name,
            },
            'locations': locations_list,
            'layout': layout_data,
            'objects': layout_objects,
        })


class SiteLayoutSaveAPIView(LoginRequiredMixin, View):
    """
    POST /api/plugins/rack-layout/site-layout/save/
    Lưu vị trí các Location (và tường) trên canvas 2D ở Site-level layout.
    """

    def post(self, request):
        from dcim.models import Site as SiteModel

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        site_id = data.get('site_id')
        layout_name = data.get('layout_name', '')
        objects_data = data.get('objects', [])

        if not site_id:
            return JsonResponse({'error': 'site_id is required'}, status=400)

        try:
            site = SiteModel.objects.get(pk=site_id)
        except SiteModel.DoesNotExist:
            return JsonResponse({'error': 'Site not found'}, status=404)

        # Tạo hoặc cập nhật Layout cho Site
        layout, created = Layout.objects.get_or_create(
            site=site,
            defaults={'name': layout_name or f"Site Layout - {site.name}"}
        )
        if not created and layout_name:
            layout.name = layout_name
            layout.save()

        # Xóa toàn bộ LayoutObject cũ và tạo lại
        layout.layout_objects.all().delete()

        new_objects = []
        for obj_data in objects_data:
            new_objects.append(LayoutObject(
                layout=layout,
                object_type=obj_data.get('object_type', 'location'),
                object_id=obj_data.get('object_id', 0),
                x=obj_data.get('x', 0),
                y=obj_data.get('y', 0),
                rotation=obj_data.get('rotation', 0),
                z_index=obj_data.get('z_index', 0),
                width=obj_data.get('width', 0),
                height=obj_data.get('height', 0),
                parent_type=obj_data.get('parent_type', None),
                parent_id=obj_data.get('parent_id', None),
            ))

        LayoutObject.objects.bulk_create(new_objects)

        return JsonResponse({
            'status': 'ok',
            'message': f'Site layout saved successfully ({len(new_objects)} objects)',
            'layout_id': layout.id,
        })


class SiteLocationsAPIView(LoginRequiredMixin, View):
    """
    GET /api/plugins/rack-layout/site/<site_id>/locations/
    Trả về danh sách tất cả Location thuộc Site, kèm thông tin:
    - Số lượng rack
    - Số lượng device
    - Trạng thái layout (đã lưu hay chưa)
    - Số object đã sắp xếp trên canvas
    """

    def get(self, request, site_id):
        from dcim.models import Site as SiteModel

        try:
            site = SiteModel.objects.get(pk=site_id)
        except SiteModel.DoesNotExist:
            return JsonResponse({'error': 'Site not found'}, status=404)

        locations = Location.objects.filter(site=site).order_by('name')
        locations_list = []

        for loc in locations:
            rack_count = Rack.objects.filter(location=loc).count()

            # Kiểm tra layout đã lưu chưa
            has_layout = False
            object_count = 0
            layout_objects = []
            racks_data = {}
            assets_data = {}
            
            try:
                layout = Layout.objects.get(location=loc)
                has_layout = True
                object_count = layout.layout_objects.count()
                
                # Lấy layout objects để vẽ preview thu nhỏ
                for obj in layout.layout_objects.all():
                    layout_objects.append({
                        'object_type': obj.object_type,
                        'object_id': obj.object_id,
                        'x': obj.x,
                        'y': obj.y,
                        'rotation': obj.rotation,
                        'width': obj.width,
                        'height': obj.height,
                        'parent_type': obj.parent_type,
                        'parent_id': obj.parent_id,
                    })
                
                # Lấy thông tin utilization của rack
                for r in Rack.objects.filter(location=loc):
                    utilization = r.get_utilization()
                    free_percentage = 100.0 - utilization
                    racks_data[str(r.id)] = {
                        'free_percentage': free_percentage
                    }
                
                # Lấy trạng thái của asset
                try:
                    from netbox_asset_management.models import Asset
                    for a in Asset.objects.filter(location=loc):
                        assets_data[str(a.id)] = {
                            'status': a.status
                        }
                except ImportError:
                    pass
            except Layout.DoesNotExist:
                pass

            locations_list.append({
                'id': loc.id,
                'name': loc.name,
                'slug': loc.slug,
                'status': loc.status if hasattr(loc, 'status') else 'active',
                'rack_count': rack_count,
                'has_layout': has_layout,
                'object_count': object_count,
                'layout_objects': layout_objects,
                'racks_data': racks_data,
                'assets_data': assets_data,
            })

        return JsonResponse({
            'site': {
                'id': site.id,
                'name': site.name,
            },
            'locations': locations_list,
        })
