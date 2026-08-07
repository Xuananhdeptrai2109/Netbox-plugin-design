import re
import requests
import logging
from django.shortcuts import render, redirect
from django.contrib import messages
from netbox.views import generic
from utilities.views import ViewTab, register_model_view
from dcim.models import Device
from .models import ZabbixHostConfig, ZabbixInterfaceConfig
from .forms import ZabbixHostConfigForm

logger = logging.getLogger('netbox_zabbix_plugin')

DNS_REGEX = re.compile(
    r'^([a-zA-Z0-9_]|[a-zA-Z0-9_][a-zA-Z0-9_\-]{0,61}[a-zA-Z0-9_])'
    r'(\.([a-zA-Z0-9_]|[a-zA-Z0-9_][a-zA-Z0-9_\-]{0,61}[a-zA-Z0-9_]))*$'
)

def is_valid_dns_name(dns_name: str) -> bool:
    if not dns_name:
        return False
    dns_name = dns_name.strip()
    if len(dns_name) > 253:
        return False
    if dns_name.startswith(('http://', 'https://')) or '/' in dns_name or ':' in dns_name or ' ' in dns_name:
        return False
    return bool(DNS_REGEX.match(dns_name))

def parse_interfaces_from_post(request, default_ip=""):
    interfaces_map = [
        ('1', 'agent', '10050'),
        ('2', 'snmp', '161'),
        ('3', 'ipmi', '623'),
        ('4', 'jmx', '12345'),
    ]

    parsed = {'1': [], '2': [], '3': [], '4': []}

    for type_code, prefix, default_port in interfaces_map:
        ips = request.POST.getlist(f'{prefix}_ip[]')
        dnss = request.POST.getlist(f'{prefix}_dns[]')
        connect_tos = request.POST.getlist(f'{prefix}_connect_to[]')
        ports = request.POST.getlist(f'{prefix}_port[]')
        default_idx = request.POST.get(f'{prefix}_default_idx', '0')

        communities = request.POST.getlist('snmp_community[]') if prefix == 'snmp' else []
        usernames = request.POST.getlist('ipmi_username[]') if prefix == 'ipmi' else []
        passwords = request.POST.getlist('ipmi_password[]') if prefix == 'ipmi' else []

        max_len = max(len(ips), len(dnss), len(connect_tos))
        for i in range(max_len):
            ip = ips[i].strip() if i < len(ips) else ''
            dns = dnss[i].strip() if i < len(dnss) else ''
            port = ports[i].strip() if i < len(ports) else default_port
            conn_to = connect_tos[i] if i < len(connect_tos) else 'ip'
            is_def = (str(i) == str(default_idx))

            # Tự động lấy Primary IP nếu là Agent interface và dùng IP nhưng ô IP trống
            if prefix == 'agent' and conn_to == 'ip' and not ip and default_ip:
                ip = default_ip

            details = {}
            if prefix == 'snmp' and i < len(communities):
                details['community'] = communities[i].strip()
            elif prefix == 'ipmi':
                if i < len(usernames): details['username'] = usernames[i].strip()
                if i < len(passwords): details['password'] = passwords[i].strip()

            if ip or dns:
                parsed[type_code].append({
                    'interface_type': type_code,
                    'ip_address': ip,
                    'dns_name': dns,
                    'use_ip': (conn_to == 'ip'),
                    'port': port or default_port,
                    'is_default': is_def,
                    'details': details
                })

    return parsed

@register_model_view(Device, name='zabbix_host', path='zabbix-host')
class DeviceZabbixHostView(generic.ObjectView):
    queryset = Device.objects.all()
    template_name = 'netbox_zabbix_plugin/device_zabbix_host.html'
    tab = ViewTab(
        label='Zabbix Host',
        permission='dcim.view_device'
    )

    def get(self, request, pk):
        device = self.get_object(pk=pk)
        config, _ = ZabbixHostConfig.objects.get_or_create(
            device=device,
            defaults={
                'host_name': device.name or f"Device-{device.id}",
                'visible_name': device.name or '',
                'use_device_role_as_group': True,
                'templates': ["Linux by Zabbix agent"],
                'enabled': True,
            }
        )

        initial_data = {
            'host_name': config.host_name,
            'visible_name': config.visible_name,
            'use_device_role_as_group': config.use_device_role_as_group,
            'custom_groups': ', '.join(config.custom_groups) if isinstance(config.custom_groups, list) else config.custom_groups,
            'templates': ', '.join(config.templates) if isinstance(config.templates, list) else config.templates,
            'description': config.description,
            'proxy_hostid': config.proxy_hostid,
            'enabled': config.enabled,
        }

        form = ZabbixHostConfigForm(initial=initial_data)

        # Lấy danh sách giao diện nhóm theo loại
        all_ifaces = list(config.interfaces.all())
        agent_interfaces = [i for i in all_ifaces if i.interface_type == '1']
        snmp_interfaces = [i for i in all_ifaces if i.interface_type == '2']
        ipmi_interfaces = [i for i in all_ifaces if i.interface_type == '3']
        jmx_interfaces = [i for i in all_ifaces if i.interface_type == '4']

        # Giá trị mặc định nếu chưa có Agent interface nào
        default_ip = str(device.primary_ip.address.ip) if device.primary_ip else ''
        if not agent_interfaces and default_ip:
            agent_interfaces = [{
                'ip_address': default_ip,
                'dns_name': '',
                'use_ip': True,
                'port': '10050',
                'is_default': True,
                'details': {}
            }]

        device_role_name = device.role.name if getattr(device, 'role', None) else (device.device_role.name if getattr(device, 'device_role', None) else 'Unassigned')

        return render(request, self.template_name, {
            'object': device,
            'tab': self.tab,
            'form': form,
            'config': config,
            'device_role_name': device_role_name,
            'default_ip': default_ip,
            'agent_interfaces': agent_interfaces,
            'snmp_interfaces': snmp_interfaces,
            'ipmi_interfaces': ipmi_interfaces,
            'jmx_interfaces': jmx_interfaces,
        })

    def post(self, request, pk):
        device = self.get_object(pk=pk)
        config, _ = ZabbixHostConfig.objects.get_or_create(device=device)
        form = ZabbixHostConfigForm(request.POST)

        default_ip = str(device.primary_ip.address.ip) if device.primary_ip else ''
        parsed_ifaces = parse_interfaces_from_post(request, default_ip)

        if form.is_valid():
            # Kiểm tra tính hợp lệ của DNS khi kết nối bằng DNS trước khi lưu
            type_labels = {'1': 'Agent', '2': 'SNMP', '3': 'IPMI', '4': 'JMX'}
            dns_errors = []
            for type_code, iface_list in parsed_ifaces.items():
                label = type_labels.get(type_code, 'Interface')
                for iface in iface_list:
                    if not iface['use_ip']:  # Connect to DNS
                        dns = iface['dns_name']
                        if not dns:
                            dns_errors.append(f"Yêu cầu bắt buộc phải nhập Tên DNS cho giao diện {label} khi chọn kết nối bằng DNS.")
                        elif not is_valid_dns_name(dns):
                            dns_errors.append(f"Tên DNS '{dns}' của giao diện {label} không hợp lệ! Vui lòng nhập tên DNS đúng định dạng (ví dụ: server01.company.local).")

            if dns_errors:
                for err in dns_errors:
                    messages.error(request, err)
                device_role_name = device.role.name if getattr(device, 'role', None) else (device.device_role.name if getattr(device, 'device_role', None) else 'Unassigned')
                return render(request, self.template_name, {
                    'object': device,
                    'tab': self.tab,
                    'form': form,
                    'config': config,
                    'device_role_name': device_role_name,
                    'default_ip': default_ip,
                    'agent_interfaces': parsed_ifaces['1'],
                    'snmp_interfaces': parsed_ifaces['2'],
                    'ipmi_interfaces': parsed_ifaces['3'],
                    'jmx_interfaces': parsed_ifaces['4'],
                })

            data = form.cleaned_data
            config.host_name = data['host_name']
            config.visible_name = data['visible_name']
            config.use_device_role_as_group = data['use_device_role_as_group']
            
            groups_str = data.get('custom_groups', '')
            config.custom_groups = [g.strip() for g in groups_str.split(',') if g.strip()]
            
            templates_str = data.get('templates', '')
            config.templates = [t.strip() for t in templates_str.split(',') if t.strip()]

            config.description = data['description']
            config.proxy_hostid = data['proxy_hostid']
            config.enabled = data['enabled']
            config.save()

            # Xóa các giao diện cũ để ghi nhận danh sách mới
            config.interfaces.all().delete()
            
            for type_code, iface_list in parsed_ifaces.items():
                for iface in iface_list:
                    ZabbixInterfaceConfig.objects.create(
                        host_config=config,
                        interface_type=iface['interface_type'],
                        ip_address=iface['ip_address'],
                        dns_name=iface['dns_name'],
                        use_ip=iface['use_ip'],
                        port=iface['port'],
                        is_default=iface['is_default'],
                        details=iface['details']
                    )

            # Đồng bộ tự động sang FastAPI Sync Service
            try:
                requests.post("http://netbox-zabbix-sync:8000/sync/full", timeout=3)
            except Exception as e:
                logger.warning(f"Could not notify netbox-zabbix-sync service: {e}")

            messages.success(request, f"Đã cập nhật cấu hình Zabbix Host cho thiết bị {device.name}.")
            return redirect('plugins:netbox_zabbix_plugin:device_zabbix_host', pk=device.pk)

        device_role_name = device.role.name if getattr(device, 'role', None) else (device.device_role.name if getattr(device, 'device_role', None) else 'Unassigned')
        return render(request, self.template_name, {
            'object': device,
            'tab': self.tab,
            'form': form,
            'config': config,
            'device_role_name': device_role_name,
            'default_ip': default_ip,
            'agent_interfaces': parsed_ifaces['1'],
            'snmp_interfaces': parsed_ifaces['2'],
            'ipmi_interfaces': parsed_ifaces['3'],
            'jmx_interfaces': parsed_ifaces['4'],
        })
