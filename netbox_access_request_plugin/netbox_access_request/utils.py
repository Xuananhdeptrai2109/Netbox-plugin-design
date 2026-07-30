import logging

from django.conf import settings

from .models import RequestHistory

logger = logging.getLogger(__name__)


def is_admin_user(user):
    """Kiểm tra người dùng có phải Admin không (thuộc nhóm chứa 'admin', e.g., 'admin', 'Admin group' hoặc is_staff)"""
    if user.is_superuser or user.is_staff:
        return True
    return user.groups.filter(name__icontains='admin').exists()


def add_history(request_obj, user, action, status, description=''):
    """Thêm một bản ghi lịch sử cho phiếu yêu cầu"""
    RequestHistory.objects.create(
        access_request=request_obj,
        user=user,
        action=action,
        status=status,
        description=description
    )


def send_notification_email(request_obj, action, user):
    """
    Gửi email thông báo khi phiếu yêu cầu thay đổi trạng thái.
    
    action: 'submitted', 'approved', 'rejected', 'completed'
    """
    try:
        from django.core.mail import send_mail

        action_messages = {
            'submitted': {
                'subject': f'[NetBox] Phiếu yêu cầu mới: {request_obj.name}',
                'body': (
                    f'Phiếu yêu cầu "{request_obj.name}" đã được gửi bởi {user.username}.\n'
                    f'Ngày dự kiến: {request_obj.expected_date}\n'
                    f'Lý do: {request_obj.reason}\n'
                    f'Vui lòng đăng nhập NetBox để xem chi tiết và phê duyệt.'
                ),
            },
            'approved': {
                'subject': f'[NetBox] Phiếu yêu cầu đã được chấp nhận: {request_obj.name}',
                'body': (
                    f'Phiếu yêu cầu "{request_obj.name}" đã được chấp nhận bởi Admin {user.username}.\n'
                    f'Lý do: {request_obj.admin_reason or "Không có"}\n'
                    f'Vui lòng đăng nhập NetBox để xem chi tiết.'
                ),
            },
            'rejected': {
                'subject': f'[NetBox] Phiếu yêu cầu bị từ chối: {request_obj.name}',
                'body': (
                    f'Phiếu yêu cầu "{request_obj.name}" đã bị từ chối bởi Admin {user.username}.\n'
                    f'Lý do: {request_obj.admin_reason}\n'
                    f'Bạn có thể chỉnh sửa và gửi lại phiếu.'
                ),
            },
            'completed': {
                'subject': f'[NetBox] Phiếu yêu cầu hoàn thành: {request_obj.name}',
                'body': (
                    f'Phiếu yêu cầu "{request_obj.name}" đã được đánh dấu hoàn thành bởi Admin {user.username}.\n'
                    f'Vui lòng đăng nhập NetBox để xem chi tiết.'
                ),
            },
        }

        msg = action_messages.get(action)
        if not msg:
            return

        # Xác định người nhận
        recipients = []
        if action == 'submitted':
            # Gửi đến tất cả Admin (is_staff, is_superuser, hoặc thuộc nhóm 'admin')
            from django.contrib.auth.models import User, Group
            from django.db.models import Q
            admin_group = Group.objects.filter(name__iexact='admin').first()
            admin_filter = Q(is_staff=True) | Q(is_superuser=True)
            if admin_group:
                admin_filter = admin_filter | Q(groups=admin_group)
            admin_emails = User.objects.filter(
                admin_filter
            ).exclude(email='').distinct().values_list('email', flat=True)
            recipients = list(admin_emails)
        else:
            # Gửi đến người tạo phiếu
            if request_obj.created_by and request_obj.created_by.email:
                recipients = [request_obj.created_by.email]

        if not recipients:
            logger.info(f'No email recipients for action "{action}" on request "{request_obj.name}"')
            return

        # Lấy FROM email từ cấu hình NetBox
        from_email = getattr(settings, 'EMAIL', {}).get('FROM_EMAIL', 'netbox@localhost')

        send_mail(
            subject=msg['subject'],
            message=msg['body'],
            from_email=from_email,
            recipient_list=recipients,
            fail_silently=True,
        )
        logger.info(f'Sent notification email for "{action}" on request "{request_obj.name}" to {recipients}')

    except Exception as e:
        logger.error(f'Failed to send email notification: {e}')
