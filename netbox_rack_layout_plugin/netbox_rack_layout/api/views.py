import json
import logging

from django.db import transaction
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

        # Lấy ContentType và ImageAttachment nếu có
        from django.contrib.contenttypes.models import ContentType
        try:
            from extras.models import ImageAttachment
        except ImportError:
            ImageAttachment = None

        try:
            from upload_file_plugin.models import UploadedFile
        except ImportError:
            UploadedFile = None

        def resolve_image_url(obj, model_name=None):
            if not obj:
                return None
            m_name = (model_name or getattr(getattr(obj, '_meta', None), 'model_name', None) or '').lower()

            # 1. Thử lấy từ UploadedFile (upload_file_plugin)
            if UploadedFile is not None and hasattr(obj, 'id'):
                try:
                    candidates = [m_name, m_name.replace('_', '')] if m_name else []
                    uf_qs = UploadedFile.objects.filter(object_id=obj.id)
                    if candidates:
                        uf_qs = uf_qs.filter(model_name__in=candidates)
                    uf_qs = uf_qs.order_by('-id')
                    for uf in uf_qs:
                        if uf.file:
                            ext = str(uf.file.name).lower().split('.')[-1]
                            if ext in ('jpg', 'jpeg', 'png', 'webp', 'gif', 'svg'):
                                return uf.file.url
                    first_uf = uf_qs.first()
                    if first_uf and first_uf.file:
                        return first_uf.file.url
                except Exception:
                    pass

            # 2. Thử lấy từ ImageField trực tiếp (image_attachments hoặc image)
            try:
                if hasattr(obj, 'image_attachments') and obj.image_attachments:
                    if getattr(obj.image_attachments, 'name', None):
                        return obj.image_attachments.url
            except Exception:
                pass

            try:
                if hasattr(obj, 'image') and obj.image:
                    if getattr(obj.image, 'name', None):
                        return obj.image.url
            except Exception:
                pass

            # 3. Thử lấy từ ImageAttachment
            if ImageAttachment is not None and hasattr(obj, 'id'):
                try:
                    ct = ContentType.objects.get_for_model(obj)
                    attachment = ImageAttachment.objects.filter(object_type=ct, object_id=obj.id).first()
                    if attachment and attachment.image and getattr(attachment.image, 'name', None):
                        return attachment.image.url
                except Exception:
                    pass

            # 4. Thử lấy từ custom_field_data
            try:
                cf_data = getattr(obj, 'custom_field_data', {}) or {}
                if isinstance(cf_data, dict):
                    for k in ('image', 'image_url', 'img', 'photo'):
                        if cf_data.get(k):
                            return str(cf_data[k])
            except Exception:
                pass

            # 5. Thử lấy từ asset_group nếu có
            try:
                if hasattr(obj, 'asset_group') and obj.asset_group:
                    ag_url = resolve_image_url(obj.asset_group, model_name='assetgroup')
                    if ag_url:
                        return ag_url
            except Exception:
                pass

            return None

        # Lấy thông tin Smart Lock liên kết với từng Rack
        smartlocks_by_rack = {}
        try:
            from netbox_smart_lock.models import SmartLock
            racks_ids = [r.id for r in racks_qs]
            smartlocks = SmartLock.objects.filter(rack_id__in=racks_ids)
            for s in smartlocks:
                if s.rack_id not in smartlocks_by_rack:
                    smartlocks_by_rack[s.rack_id] = {}
                s_img = resolve_image_url(s, model_name='smartlock')
                face_key = s.rack_face or 'front'
                smartlocks_by_rack[s.rack_id][face_key] = {
                    'id': s.id,
                    'name': s.name or f"Smart Lock #{s.id}",
                    'code': s.code,
                    'status': s.status,
                    'image_url': s_img,
                }
        except (ImportError, Exception):
            pass

        # Lấy danh sách Device trong từng Rack
        devices_by_rack = {}
        try:
            from dcim.models import Device
            racks_ids = [r.id for r in racks_qs]
            dev_qs = Device.objects.filter(rack_id__in=racks_ids).select_related('device_type')
            for dev in dev_qs:
                if dev.rack_id not in devices_by_rack:
                    devices_by_rack[dev.rack_id] = []
                
                # Tìm ảnh cho device: từ device -> device_type front_image -> ImageAttachment của device_type
                dev_img = resolve_image_url(dev)
                if not dev_img and dev.device_type:
                    if getattr(dev.device_type, 'front_image', None) and dev.device_type.front_image:
                        dev_img = dev.device_type.front_image.url
                    else:
                        dev_img = resolve_image_url(dev.device_type)

                pos = int(dev.position) if dev.position is not None else None
                u_h = dev.device_type.u_height if (dev.device_type and dev.device_type.u_height) else 1

                devices_by_rack[dev.rack_id].append({
                    'id': dev.id,
                    'name': dev.name or f"Device #{dev.id}",
                    'position': pos,
                    'u_height': u_h,
                    'face': dev.face or 'front',
                    'status': dev.status,
                    'image_url': dev_img,
                    'device_type': dev.device_type.model if dev.device_type else '',
                })
        except Exception:
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
            front_lock = rack_locks.get('front', None)
            rear_lock = rack_locks.get('rear', None)

            racks_list.append({
                'id': r.id,
                'name': r.name,
                'status': r.status,
                'u_height': r.u_height,
                'free_u': free_u,
                'free_percentage': free_percentage,
                'front_status': front_lock['status'] if front_lock else None,
                'rear_status': rear_lock['status'] if rear_lock else None,
                'front_lock': front_lock,
                'rear_lock': rear_lock,
                'devices': devices_by_rack.get(r.id, []),
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
                    'image_url': resolve_image_url(a, model_name='asset'),
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
                    'image_url': resolve_image_url(s, model_name='smartlock'),
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
            for obj in layout.layout_objects.all().order_by('id'):
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
                    'wall_face': obj.wall_face or ('back' if (obj.parent_type == 'wall' and obj.y >= 265) else 'front'),
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

        # The wall editor can include a mounted object in both its floor snapshot
        # and wall map. Keep the last occurrence so the current wall position wins.
        unique_objects = {}
        for obj_data in objects_data:
            object_type = obj_data.get('object_type', 'rack')
            object_id = obj_data.get('object_id', 0)
            unique_objects[(object_type, object_id)] = obj_data

        with transaction.atomic():
            layout, created = Layout.objects.get_or_create(
                location=location,
                defaults={'name': layout_name or f"Layout - {location.name}"}
            )
            if not created and layout_name:
                layout.name = layout_name
                layout.save()

            saved_object_ids = []
            for obj_data in unique_objects.values():
                layout_object, _ = LayoutObject.objects.update_or_create(
                    layout=layout,
                    object_type=obj_data.get('object_type', 'rack'),
                    object_id=obj_data.get('object_id', 0),
                    defaults={
                        'x': obj_data.get('x', 0),
                        'y': obj_data.get('y', 0),
                        'rotation': obj_data.get('rotation', 0),
                        'z_index': obj_data.get('z_index', 0),
                        'width': obj_data.get('width', 0),
                        'height': obj_data.get('height', 0),
                        'parent_type': obj_data.get('parent_type', None),
                        'parent_id': obj_data.get('parent_id', None),
                        'wall_face': obj_data.get('wall_face', 'front') if obj_data.get('parent_type') == 'wall' else 'front',
                    },
                )
                saved_object_ids.append(layout_object.id)

            # Remove objects intentionally removed from the canvas only after all
            # incoming objects have been written successfully.
            layout.layout_objects.exclude(id__in=saved_object_ids).delete()

        return JsonResponse({
            'status': 'ok',
            'message': f'Layout saved successfully ({len(saved_object_ids)} objects)',
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

                for obj in layout.layout_objects.all().order_by('id'):
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
                        'wall_face': obj.wall_face or ('back' if (obj.parent_type == 'wall' and obj.y >= 265) else 'front'),
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
            for obj in layout.layout_objects.all().order_by('id'):
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
                    'wall_face': obj.wall_face or ('back' if (obj.parent_type == 'wall' and obj.y >= 265) else 'front'),
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
                wall_face=obj_data.get('wall_face', 'front'),
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


class TemperatureDetailAPIView(LoginRequiredMixin, View):
    """
    GET /api/plugins/rack-layout/temperature/<location_id>/
    Trả về danh sách Racks và Assets kèm dải [a, b] riêng biệt và nhiệt độ hiện tại của từng thiết bị.
    """

    def get(self, request, location_id):
        import random
        from ..models import LocationTemperatureConfig, TemperatureState
        from ..tsdb import get_temperature_status

        try:
            location = Location.objects.get(pk=location_id)
        except Location.DoesNotExist:
            return JsonResponse({'error': 'Location not found'}, status=404)

        config, _ = LocationTemperatureConfig.objects.get_or_create(
            location=location,
            defaults={'min_temp': 20.0, 'max_temp': 30.0, 'interval_seconds': 10}
        )

        # Lấy trạng thái nhiệt độ và dải [a, b] riêng biệt đã lưu của từng thiết bị
        states_map = {}
        for s in TemperatureState.objects.filter(location=location):
            states_map[(s.object_type, s.object_id)] = {
                'temp': s.current_temp,
                'min_temp': s.min_temp,
                'max_temp': s.max_temp,
                'status': s.status,
                'last_updated': s.last_updated.strftime('%H:%M:%S %d/%m/%Y')
            }

        # Danh sách Racks
        racks_qs = Rack.objects.filter(location=location)
        racks_data = []
        all_temps = []

        for r in racks_qs:
            state = states_map.get(('rack', r.id))
            if state:
                cur_temp = state['temp']
                min_t = state['min_temp']
                max_t = state['max_temp']
                status = state['status']
                updated = state['last_updated']
            else:
                min_t = 20.0
                max_t = 30.0
                cur_temp = round(random.uniform(min_t, max_t), 1)
                status = get_temperature_status(cur_temp)
                updated = 'Chưa cập nhật'

            all_temps.append(cur_temp)
            racks_data.append({
                'id': r.id,
                'name': r.name,
                'status': r.status,
                'u_height': r.u_height,
                'min_temp': min_t,
                'max_temp': max_t,
                'current_temp': cur_temp,
                'temp_status': status,
                'last_updated': updated
            })

        # Danh sách Assets
        assets_data = []
        try:
            from netbox_asset_management.models import Asset
            for a in Asset.objects.filter(location=location):
                state = states_map.get(('asset', a.id))
                if state:
                    cur_temp = state['temp']
                    min_t = state['min_temp']
                    max_t = state['max_temp']
                    status = state['status']
                    updated = state['last_updated']
                else:
                    min_t = 20.0
                    max_t = 30.0
                    cur_temp = round(random.uniform(min_t, max_t), 1)
                    status = get_temperature_status(cur_temp)
                    updated = 'Chưa cập nhật'

                all_temps.append(cur_temp)
                assets_data.append({
                    'id': a.id,
                    'name': a.name or f"Asset #{a.id}",
                    'asset_code': a.asset_code or '',
                    'device_type': a.device_type or '',
                    'model': a.model or '',
                    'status': a.status or 'active',
                    'min_temp': min_t,
                    'max_temp': max_t,
                    'current_temp': cur_temp,
                    'temp_status': status,
                    'last_updated': updated
                })
        except ImportError:
            pass

        # Thống kê KPI tóm tắt
        avg_temp = round(sum(all_temps) / len(all_temps), 1) if all_temps else 0.0
        min_recorded = min(all_temps) if all_temps else 0.0
        max_recorded = max(all_temps) if all_temps else 0.0

        status_counts = {'cool': 0, 'normal': 0, 'warning': 0, 'critical': 0}
        for item in racks_data + assets_data:
            s = item.get('temp_status', 'normal')
            status_counts[s] = status_counts.get(s, 0) + 1

        return JsonResponse({
            'location': {
                'id': location.id,
                'name': location.name,
            },
            'interval_seconds': 10,
            'summary': {
                'avg_temp': avg_temp,
                'min_temp': min_recorded,
                'max_temp': max_recorded,
                'total_items': len(all_temps),
                'status_counts': status_counts,
            },
            'racks': racks_data,
            'assets': assets_data,
        })


class TemperatureConfigAPIView(LoginRequiredMixin, View):
    """
    POST /api/plugins/rack-layout/temperature/<location_id>/config/
    Cập nhật cài đặt chung của Location (nếu cần).
    """

    def post(self, request, location_id):
        from ..models import LocationTemperatureConfig

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        try:
            location = Location.objects.get(pk=location_id)
        except Location.DoesNotExist:
            return JsonResponse({'error': 'Location not found'}, status=404)

        config, _ = LocationTemperatureConfig.objects.get_or_create(location=location)
        if 'interval_seconds' in data:
            config.interval_seconds = int(data['interval_seconds'])
            config.save()

        return JsonResponse({'status': 'ok'})


class TemperatureUpdateAPIView(LoginRequiredMixin, View):
    """
    POST /api/plugins/rack-layout/temperature/<location_id>/update/
    Cập nhật dải [a, b] (min_temp, max_temp) riêng cho từng thiết bị và tự động random nhiệt độ trong [a, b].
    """

    def post(self, request, location_id):
        import random
        from ..tsdb import record_temperature_metric

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        try:
            location = Location.objects.get(pk=location_id)
        except Location.DoesNotExist:
            return JsonResponse({'error': 'Location not found'}, status=404)

        obj_type = data.get('object_type', 'rack')
        obj_id = int(data.get('object_id', 0))

        try:
            min_temp = float(data.get('min_temp', 20.0))
            max_temp = float(data.get('max_temp', 30.0))
        except (ValueError, TypeError):
            return JsonResponse({'error': 'min_temp (a) và max_temp (b) phải là số thực'}, status=400)

        if min_temp > max_temp:
            return JsonResponse({'error': 'Nhiệt độ tối thiểu a không được lớn hơn nhiệt độ tối đa b'}, status=400)

        # Lấy tên thiết bị
        obj_name = f"{obj_type} #{obj_id}"
        if obj_type == 'rack':
            r = Rack.objects.filter(location=location, id=obj_id).first()
            if r:
                obj_name = r.name
        else:
            try:
                from netbox_asset_management.models import Asset
                a = Asset.objects.filter(location=location, id=obj_id).first()
                if a:
                    obj_name = a.name or f"Asset #{a.id}"
            except ImportError:
                pass

        # Tự động sinh nhiệt độ mới ngẫu nhiên trong khoảng [a, b]
        new_temp = round(random.uniform(min_temp, max_temp), 1)

        log_entry = record_temperature_metric(
            location=location,
            object_type=obj_type,
            object_id=obj_id,
            object_name=obj_name,
            temperature=new_temp,
            min_temp=min_temp,
            max_temp=max_temp
        )

        return JsonResponse({
            'status': 'ok',
            'message': f'Đã cập nhật dải [{min_temp}°C - {max_temp}°C] cho {obj_name} thành công',
            'device': {
                'object_type': obj_type,
                'object_id': obj_id,
                'object_name': obj_name,
                'min_temp': min_temp,
                'max_temp': max_temp,
                'current_temp': log_entry.temperature,
                'status': log_entry.status,
                'timestamp': log_entry.timestamp.strftime('%H:%M:%S')
            }
        })


class TemperatureLogAPIView(LoginRequiredMixin, View):
    """
    GET /api/plugins/rack-layout/temperature/<location_id>/logs/?limit=50
    Lấy danh sách log chuỗi thời gian (time-series) nhiệt độ.
    POST: Chu kỳ tự động 10s: mỗi thiết bị tự động random nhiệt độ trong dải [a, b] riêng của nó và ghi TSDB.
    """

    def get(self, request, location_id):
        from ..models import TemperatureTimeSeriesLog

        try:
            location = Location.objects.get(pk=location_id)
        except Location.DoesNotExist:
            return JsonResponse({'error': 'Location not found'}, status=404)

        try:
            limit = int(request.GET.get('limit', 60))
        except (ValueError, TypeError):
            limit = 60

        object_type = request.GET.get('object_type')
        object_id = request.GET.get('object_id')

        qs = TemperatureTimeSeriesLog.objects.filter(location=location)
        if object_type:
            qs = qs.filter(object_type=object_type)
        if object_id:
            qs = qs.filter(object_id=object_id)

        logs = qs.order_by('-timestamp')[:min(limit, 300)]
        logs_list = [{
            'id': log.id,
            'timestamp': log.timestamp.strftime('%H:%M:%S'),
            'timestamp_full': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'object_type': log.object_type,
            'object_id': log.object_id,
            'object_name': log.object_name or f"{log.object_type} #{log.object_id}",
            'temperature': log.temperature,
            'status': log.status
        } for log in logs]

        return JsonResponse({
            'location_id': location.id,
            'count': len(logs_list),
            'logs': logs_list
        })

    def post(self, request, location_id):
        """
        Chu kỳ tự động 10s: Mỗi tủ rack và asset tự động sinh nhiệt độ ngẫu nhiên
        trong dải [a, b] riêng biệt của nó và ghi vào Time-Series Database.
        """
        import random
        from ..models import TemperatureState
        from ..tsdb import record_temperature_metric

        try:
            location = Location.objects.get(pk=location_id)
        except Location.DoesNotExist:
            return JsonResponse({'error': 'Location not found'}, status=404)

        # Lấy dải [a, b] và trạng thái hiện tại của từng thiết bị
        states = {
            (s.object_type, s.object_id): s
            for s in TemperatureState.objects.filter(location=location)
        }

        racks = Rack.objects.filter(location=location)
        new_logs = []

        for r in racks:
            st = states.get(('rack', r.id))
            min_t = st.min_temp if st else 20.0
            max_t = st.max_temp if st else 30.0

            # Sinh ngẫu nhiên trong dải [a, b] riêng biệt của rack này
            new_temp = round(random.uniform(min_t, max_t), 1)

            entry = record_temperature_metric(
                location=location,
                object_type='rack',
                object_id=r.id,
                object_name=r.name,
                temperature=new_temp,
                min_temp=min_t,
                max_temp=max_t
            )
            new_logs.append({
                'id': entry.id,
                'timestamp': entry.timestamp.strftime('%H:%M:%S'),
                'object_type': 'rack',
                'object_id': r.id,
                'object_name': r.name,
                'temperature': entry.temperature,
                'status': entry.status,
                'min_temp': min_t,
                'max_temp': max_t
            })

        try:
            from netbox_asset_management.models import Asset
            assets = Asset.objects.filter(location=location)
            for a in assets:
                st = states.get(('asset', a.id))
                min_t = st.min_temp if st else 20.0
                max_t = st.max_temp if st else 30.0

                new_temp = round(random.uniform(min_t, max_t), 1)
                name = a.name or f"Asset #{a.id}"

                entry = record_temperature_metric(
                    location=location,
                    object_type='asset',
                    object_id=a.id,
                    object_name=name,
                    temperature=new_temp,
                    min_temp=min_t,
                    max_temp=max_t
                )
                new_logs.append({
                    'id': entry.id,
                    'timestamp': entry.timestamp.strftime('%H:%M:%S'),
                    'object_type': 'asset',
                    'object_id': a.id,
                    'object_name': name,
                    'temperature': entry.temperature,
                    'status': entry.status,
                    'min_temp': min_t,
                    'max_temp': max_t
                })
        except ImportError:
            pass

        return JsonResponse({
            'status': 'ok',
            'interval': 10,
            'logged_count': len(new_logs),
            'new_logs': new_logs
        })


