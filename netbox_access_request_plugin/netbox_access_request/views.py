import logging

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from netbox.views import generic

from . import forms, models, tables, filtersets
from .choices import RequestStatusChoices, SubjectStatusChoices, VerifyStatusChoices
from .utils import add_history, send_notification_email, is_admin_user

logger = logging.getLogger(__name__)


# ========================================================================
# PHIẾU YÊU CẦU (AccessRequest) VIEWS
# ========================================================================

class AccessRequestListView(generic.ObjectListView):
    """Danh sách phiếu yêu cầu - sắp xếp theo thời gian cập nhật mới nhất"""
    queryset = models.AccessRequest.objects.all()
    table = tables.AccessRequestTable
    filterset = filtersets.AccessRequestFilterSet
    filterset_form = forms.AccessRequestFilterForm
    action_buttons = ('add', 'export')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not is_admin_user(request.user):
            # Guest chỉ thấy phiếu của mình
            qs = qs.filter(created_by=request.user)
        else:
            # Admin thấy tất cả, ngoại trừ các phiếu nháp của người khác
            from django.db.models import Q
            qs = qs.exclude(
                Q(status=RequestStatusChoices.STATUS_DRAFT) & ~Q(created_by=request.user)
            )
        return qs

    def get_permitted_actions(self, user, model=None):
        permitted_actions = super().get_permitted_actions(user, model)
        # Nếu là Admin, ẩn nút "+ Add" (tạo mới phiếu) trên danh sách
        if is_admin_user(user):
            permitted_actions = [action for action in permitted_actions if action != 'add']
        return permitted_actions


class AccessRequestView(generic.ObjectView):
    """Xem chi tiết phiếu yêu cầu - bao gồm 4 tabs"""
    queryset = models.AccessRequest.objects.all()

    def dispatch(self, request, *args, **kwargs):
        """Kiểm tra quyền truy cập: Admin xem tất cả (trừ nháp của người khác), User chỉ xem phiếu của mình"""
        if 'pk' in kwargs:
            obj = get_object_or_404(models.AccessRequest, pk=kwargs['pk'])
            if not is_admin_user(request.user):
                if obj.created_by != request.user:
                    messages.error(request, 'Bạn không có quyền xem phiếu yêu cầu này.')
                    return redirect(reverse('plugins:netbox_access_request:accessrequest_list'))
            else:
                # Nếu là Admin, chặn xem phiếu nháp của người khác
                if obj.status == RequestStatusChoices.STATUS_DRAFT and obj.created_by != request.user:
                    messages.error(request, 'Phiếu yêu cầu này đang ở trạng thái Nháp và chưa được gửi.')
                    return redirect(reverse('plugins:netbox_access_request:accessrequest_list'))
        return super().dispatch(request, *args, **kwargs)

    def get_extra_context(self, request, instance):
        # Tab Đối tượng
        subjects = models.RequestSubject.objects.filter(access_request=instance)
        subject_table = tables.RequestSubjectTable(subjects)

        # Tab Lịch sử yêu cầu
        history = models.RequestHistory.objects.filter(access_request=instance)

        # File đính kèm cho phiếu
        uploaded_files = []
        if instance.pk:
            try:
                from upload_file_plugin.models import UploadedFile
                uploaded_files = UploadedFile.objects.filter(
                    object_id=instance.pk, model_name='accessrequest'
                )
            except ImportError:
                pass

        # Tab Nhật ký thay đổi (Changelog)
        changelog = []
        if instance.pk:
            try:
                from django.contrib.contenttypes.models import ContentType
                from extras.models import ObjectChange
                from django.db.models import Q
                request_ct = ContentType.objects.get_for_model(instance)
                subject_ct = ContentType.objects.get_for_model(models.RequestSubject)
                subject_pks = list(subjects.values_list('pk', flat=True))
                changelog = ObjectChange.objects.filter(
                    Q(changed_object_type=request_ct, changed_object_id=instance.pk) |
                    Q(related_object_type=request_ct, related_object_id=instance.pk) |
                    Q(changed_object_type=subject_ct, changed_object_id__in=subject_pks)
                ).prefetch_related('user', 'changed_object_type').order_by('-time')[:100]
            except Exception as e:
                logger.error(f"Error querying changelog: {e}")

        # Xác định quyền hiện tại
        user_is_admin = is_admin_user(request.user)
        user_is_creator = (instance.created_by == request.user)
        subject_count = subjects.count()
        has_invalid_subject = subjects.filter(
            verify_status=VerifyStatusChoices.STATUS_INVALID
        ).exists()

        return {
            'subject_table': subject_table,
            'history': history,
            'changelog': changelog,
            'uploaded_files': uploaded_files,
            'user_is_admin': user_is_admin,
            'user_is_creator': user_is_creator,
            'subject_count': subject_count,
            'has_invalid_subject': has_invalid_subject,
            'active_tab': request.GET.get('tab', 'request_info'),
        }


class AccessRequestEditView(generic.ObjectEditView):
    """Thêm mới / Chỉnh sửa phiếu yêu cầu"""
    queryset = models.AccessRequest.objects.all()
    form = forms.AccessRequestForm
    template_name = 'netbox_access_request/accessrequest_edit.html'
    default_return_url = 'plugins:netbox_access_request:accessrequest_list'

    def dispatch(self, request, *args, **kwargs):
        # Admin không được phép tạo mới hoặc chỉnh sửa phiếu yêu cầu
        if is_admin_user(request.user):
            messages.error(request, 'Tài khoản quản trị không được phép tạo mới hoặc chỉnh sửa phiếu yêu cầu.')
            return redirect(reverse(self.default_return_url))

        if 'pk' in kwargs:
            obj = get_object_or_404(models.AccessRequest, pk=kwargs['pk'])
            # Chỉ người tạo phiếu mới được sửa
            if obj.created_by != request.user:
                messages.error(request, 'Bạn không có quyền chỉnh sửa phiếu yêu cầu này.')
                return redirect(obj.get_absolute_url())
            if obj.status in (RequestStatusChoices.STATUS_APPROVED, RequestStatusChoices.STATUS_COMPLETED):
                messages.error(request, 'Không thể chỉnh sửa phiếu yêu cầu đã được Chấp nhận hoặc Hoàn thành.')
                return redirect(obj.get_absolute_url())
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, *args, **kwargs):
        form = super().get_form(*args, **kwargs)
        if hasattr(self.request, 'user'):
            from dcim.models import Region
            assigned_region_ids = models.UserRegionAssignment.objects.filter(
                user=self.request.user
            ).values_list('region_id', flat=True)
            if assigned_region_ids:
                form.fields['region'].queryset = Region.objects.filter(
                    pk__in=assigned_region_ids
                )
        return form

    def get_extra_context(self, request, instance):
        if not request.session.session_key:
            request.session.save()

        session_key = request.session.session_key
        object_id = instance.pk if instance.pk else ''
        model_name = 'accessrequest'

        uploaded_files = []
        if object_id:
            try:
                from upload_file_plugin.models import UploadedFile
                uploaded_files = UploadedFile.objects.filter(
                    object_id=object_id, model_name=model_name
                )
            except ImportError:
                pass

        return {
            'object_id': object_id,
            'model_name': model_name,
            'session_key': session_key,
            'valid_flg': 0,
            'type_file': '',
            'uploaded_files': uploaded_files,
        }

    def alter_object(self, obj, request, url_args, url_kwargs):
        """Tự động gán người tạo khi thêm mới"""
        if not obj.pk:
            obj.created_by = request.user
        return obj

    def post(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        response = super().post(request, *args, **kwargs)
        # Nếu lưu thành công (redirect), ghi lịch sử
        if hasattr(response, 'url'):
            if pk:
                try:
                    obj = models.AccessRequest.objects.get(pk=pk)
                    add_history(obj, request.user, 'Chỉnh sửa phiếu', obj.status, 'Cập nhật thông tin phiếu yêu cầu')
                except models.AccessRequest.DoesNotExist:
                    pass
            else:
                # Lấy object mới tạo từ response URL
                try:
                    parts = response.url.strip('/').split('/')
                    new_pk = int(parts[-1])
                    new_obj = models.AccessRequest.objects.get(pk=new_pk)
                    add_history(new_obj, request.user, 'Tạo phiếu', new_obj.status, 'Tạo mới phiếu yêu cầu')
                except Exception:
                    pass
        return response

    def get_return_url(self, request, obj=None):
        return_url = request.GET.get('return_url') or request.POST.get('return_url')
        if return_url and return_url.startswith('/'):
            return return_url
        if obj and obj.pk:
            return obj.get_absolute_url()
        return reverse(self.default_return_url)


class AccessRequestDeleteView(generic.ObjectDeleteView):
    """Xóa phiếu yêu cầu - chỉ khi chưa hoàn thành"""
    queryset = models.AccessRequest.objects.all()
    default_return_url = 'plugins:netbox_access_request:accessrequest_list'

    def dispatch(self, request, *args, **kwargs):
        if 'pk' in kwargs:
            obj = get_object_or_404(models.AccessRequest, pk=kwargs['pk'])
            # Chỉ người tạo phiếu mới được xoá
            if obj.created_by != request.user:
                messages.error(request, 'Bạn không có quyền xoá phiếu yêu cầu này.')
                return redirect(obj.get_absolute_url())
            if obj.status in (RequestStatusChoices.STATUS_APPROVED, RequestStatusChoices.STATUS_COMPLETED):
                messages.error(request, 'Không thể xoá phiếu yêu cầu đã được Chấp nhận hoặc Hoàn thành.')
                return redirect(obj.get_absolute_url())
        return super().dispatch(request, *args, **kwargs)


class AccessRequestSubmitView(View):
    """Gửi phiếu yêu cầu đến Admin"""

    def post(self, request, pk):
        obj = get_object_or_404(models.AccessRequest, pk=pk)

        # Chỉ người tạo phiếu mới được gửi
        if obj.created_by != request.user:
            messages.error(request, 'Bạn không có quyền gửi phiếu yêu cầu này.')
            return redirect(obj.get_absolute_url())

        # Kiểm tra: phải có ít nhất 1 đối tượng
        if obj.subjects.count() == 0:
            messages.error(request, 'Phiếu yêu cầu phải có ít nhất một đối tượng để gửi.')
            return redirect(obj.get_absolute_url())

        # Kiểm tra trạng thái hợp lệ
        if obj.status not in (RequestStatusChoices.STATUS_DRAFT, RequestStatusChoices.STATUS_REJECTED):
            messages.error(request, 'Không thể gửi phiếu ở trạng thái hiện tại.')
            return redirect(obj.get_absolute_url())

        obj.status = RequestStatusChoices.STATUS_SUBMITTED
        obj.save()

        add_history(obj, request.user, 'Gửi phiếu', obj.status, 'Gửi phiếu yêu cầu đến Admin')

        # Gửi email thông báo đến Admin
        send_notification_email(
            request_obj=obj,
            action='submitted',
            user=request.user
        )

        messages.success(request, f'Phiếu "{obj.name}" đã được gửi thành công.')
        return redirect(obj.get_absolute_url())


class AccessRequestConfirmView(View):
    """Admin xác nhận (tiếp nhận) phiếu yêu cầu"""

    def post(self, request, pk):
        # Chỉ Admin mới được xác nhận phiếu
        if not is_admin_user(request.user):
            messages.error(request, 'Bạn không có quyền thực hiện thao tác này.')
            return redirect(reverse('plugins:netbox_access_request:accessrequest_list'))

        obj = get_object_or_404(models.AccessRequest, pk=pk)

        if obj.status != RequestStatusChoices.STATUS_SUBMITTED:
            messages.error(request, 'Chỉ có thể xác nhận phiếu ở trạng thái "Đã gửi".')
            return redirect(obj.get_absolute_url())

        obj.status = RequestStatusChoices.STATUS_CONFIRMED
        obj.save()

        add_history(obj, request.user, 'Xác nhận phiếu', obj.status, 'Admin xác nhận phiếu yêu cầu')

        messages.success(request, f'Phiếu "{obj.name}" đã được xác nhận.')
        return redirect(obj.get_absolute_url())


class AccessRequestApproveView(View):
    """Admin chấp nhận phiếu yêu cầu"""

    def post(self, request, pk):
        # Chỉ Admin mới được chấp nhận phiếu
        if not is_admin_user(request.user):
            messages.error(request, 'Bạn không có quyền thực hiện thao tác này.')
            return redirect(reverse('plugins:netbox_access_request:accessrequest_list'))

        obj = get_object_or_404(models.AccessRequest, pk=pk)

        if obj.status != RequestStatusChoices.STATUS_CONFIRMED:
            messages.error(request, 'Chỉ có thể chấp nhận phiếu ở trạng thái "Đã xác nhận".')
            return redirect(obj.get_absolute_url())

        # Kiểm tra: không có đối tượng "Không hợp lệ"
        has_invalid = obj.subjects.filter(
            verify_status=VerifyStatusChoices.STATUS_INVALID
        ).exists()
        if has_invalid:
            messages.error(
                request,
                'Không thể chấp nhận phiếu. Tồn tại đối tượng có trạng thái xác nhận "Không hợp lệ".'
            )
            return redirect(obj.get_absolute_url())

        reason = request.POST.get('reason', '')
        obj.status = RequestStatusChoices.STATUS_APPROVED
        obj.admin_reason = reason
        obj.save()

        add_history(obj, request.user, 'Chấp nhận phiếu', obj.status, reason or 'Admin chấp nhận phiếu yêu cầu')

        # Gửi email thông báo đến người tạo phiếu
        send_notification_email(
            request_obj=obj,
            action='approved',
            user=request.user
        )

        messages.success(request, f'Phiếu "{obj.name}" đã được chấp nhận.')
        return redirect(obj.get_absolute_url())


class AccessRequestRejectView(View):
    """Admin từ chối phiếu yêu cầu"""

    def post(self, request, pk):
        # Chỉ Admin mới được từ chối phiếu
        if not is_admin_user(request.user):
            messages.error(request, 'Bạn không có quyền thực hiện thao tác này.')
            return redirect(reverse('plugins:netbox_access_request:accessrequest_list'))

        obj = get_object_or_404(models.AccessRequest, pk=pk)

        if obj.status != RequestStatusChoices.STATUS_CONFIRMED:
            messages.error(request, 'Chỉ có thể từ chối phiếu ở trạng thái "Đã xác nhận".')
            return redirect(obj.get_absolute_url())

        reason = request.POST.get('reason', '')
        if not reason.strip():
            messages.error(request, 'Vui lòng nhập lý do từ chối.')
            return redirect(obj.get_absolute_url())

        obj.status = RequestStatusChoices.STATUS_REJECTED
        obj.admin_reason = reason
        obj.save()

        add_history(obj, request.user, 'Từ chối phiếu', obj.status, reason)

        # Gửi email thông báo đến người tạo phiếu
        send_notification_email(
            request_obj=obj,
            action='rejected',
            user=request.user
        )

        messages.success(request, f'Phiếu "{obj.name}" đã bị từ chối.')
        return redirect(obj.get_absolute_url())


class AccessRequestCompleteView(View):
    """Admin hoàn thành phiếu yêu cầu"""

    def post(self, request, pk):
        # Chỉ Admin mới được hoàn thành phiếu
        if not is_admin_user(request.user):
            messages.error(request, 'Bạn không có quyền thực hiện thao tác này.')
            return redirect(reverse('plugins:netbox_access_request:accessrequest_list'))

        obj = get_object_or_404(models.AccessRequest, pk=pk)

        if obj.status != RequestStatusChoices.STATUS_APPROVED:
            messages.error(request, 'Chỉ có thể hoàn thành phiếu ở trạng thái "Chấp nhận".')
            return redirect(obj.get_absolute_url())

        obj.status = RequestStatusChoices.STATUS_COMPLETED
        obj.save()

        add_history(obj, request.user, 'Hoàn thành phiếu', obj.status, 'Admin hoàn thành phiếu yêu cầu')

        # Gửi email thông báo đến người tạo phiếu
        send_notification_email(
            request_obj=obj,
            action='completed',
            user=request.user
        )

        messages.success(request, f'Phiếu "{obj.name}" đã hoàn thành.')
        return redirect(obj.get_absolute_url())


# ========================================================================
# ĐỐI TƯỢNG (RequestSubject) VIEWS
# ========================================================================

class RequestSubjectView(generic.ObjectView):
    """Xem chi tiết đối tượng"""
    queryset = models.RequestSubject.objects.all()

    def dispatch(self, request, *args, **kwargs):
        """Kiểm tra quyền truy cập: Admin xem tất cả, User chỉ xem đối tượng trong phiếu của mình"""
        if 'pk' in kwargs and 'request_pk' in kwargs:
            subject = get_object_or_404(
                models.RequestSubject, pk=kwargs['pk'], access_request__pk=kwargs['request_pk']
            )
            if not is_admin_user(request.user) and subject.access_request.created_by != request.user:
                messages.error(request, 'Bạn không có quyền xem thông tin đối tượng này.')
                return redirect(reverse('plugins:netbox_access_request:accessrequest_list'))
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, **kwargs):
        return get_object_or_404(
            models.RequestSubject,
            pk=self.kwargs['pk'],
            access_request__pk=self.kwargs['request_pk']
        )

    def get_extra_context(self, request, instance):
        uploaded_files = []
        if instance.pk:
            try:
                from upload_file_plugin.models import UploadedFile
                uploaded_files = UploadedFile.objects.filter(
                    object_id=instance.pk, model_name='requestsubject'
                )
            except ImportError:
                pass

        user_is_admin = is_admin_user(request.user)
        user_is_creator = (instance.access_request.created_by == request.user)

        return {
            'uploaded_files': uploaded_files,
            'access_request': instance.access_request,
            'user_is_admin': user_is_admin,
            'user_is_creator': user_is_creator,
        }


class RequestSubjectEditView(generic.ObjectEditView):
    """Thêm mới / Chỉnh sửa đối tượng"""
    queryset = models.RequestSubject.objects.all()
    form = forms.RequestSubjectForm
    template_name = 'netbox_access_request/requestsubject_edit.html'

    def dispatch(self, request, *args, **kwargs):
        # Chỉ người tạo phiếu mới được thêm/sửa đối tượng
        request_pk = kwargs.get('request_pk')
        if request_pk:
            access_request = get_object_or_404(models.AccessRequest, pk=request_pk)
            if access_request.created_by != request.user:
                messages.error(request, 'Bạn không có quyền chỉnh sửa đối tượng trong phiếu yêu cầu này.')
                return redirect(access_request.get_absolute_url() + '?tab=subjects')
        if 'pk' in kwargs:
            obj = get_object_or_404(models.RequestSubject, pk=kwargs['pk'], access_request__pk=kwargs['request_pk'])
            if obj.verify_status == VerifyStatusChoices.STATUS_VALID:
                messages.error(request, 'Không thể chỉnh sửa đối tượng đã được xác nhận Hợp lệ.')
                return redirect(obj.access_request.get_absolute_url() + '?tab=subjects')
            if obj.access_request.status in (RequestStatusChoices.STATUS_APPROVED, RequestStatusChoices.STATUS_COMPLETED):
                messages.error(request, 'Không thể chỉnh sửa đối tượng khi phiếu yêu cầu đã được Chấp nhận hoặc Hoàn thành.')
                return redirect(obj.access_request.get_absolute_url() + '?tab=subjects')
        return super().dispatch(request, *args, **kwargs)

    def alter_object(self, obj, request, url_args, url_kwargs):
        if 'request_pk' in url_kwargs:
            obj.access_request = get_object_or_404(models.AccessRequest, pk=url_kwargs['request_pk'])
        return obj

    def get_object(self, **kwargs):
        if 'pk' in kwargs:
            return get_object_or_404(
                models.RequestSubject,
                pk=kwargs['pk'],
                access_request__pk=kwargs['request_pk']
            )
        return models.RequestSubject()

    def get_form(self, *args, **kwargs):
        request_pk = self.kwargs.get('request_pk')
        access_request = get_object_or_404(models.AccessRequest, pk=request_pk)
        form_class = self.form
        if self.request.method == 'POST':
            return form_class(
                self.request.POST,
                instance=self.get_object(**self.kwargs),
                access_request=access_request
            )
        else:
            return form_class(
                instance=self.get_object(**self.kwargs),
                access_request=access_request
            )

    def get_extra_context(self, request, instance):
        request_pk = self.kwargs.get('request_pk')
        access_request = get_object_or_404(models.AccessRequest, pk=request_pk)

        if not request.session.session_key:
            request.session.save()

        session_key = request.session.session_key
        object_id = instance.pk if instance.pk else ''
        model_name = 'requestsubject'

        uploaded_files = []
        if object_id:
            try:
                from upload_file_plugin.models import UploadedFile
                uploaded_files = UploadedFile.objects.filter(
                    object_id=object_id, model_name=model_name
                )
            except ImportError:
                pass

        # Kiểm tra nếu là "Tạo và thêm cái khác"
        add_another = request.GET.get('add_another', '') == '1'

        return {
            'access_request': access_request,
            'object_id': object_id,
            'model_name': model_name,
            'session_key': session_key,
            'valid_flg': 1,
            'type_file': "['jpg', 'jpeg', 'png']",
            'uploaded_files': uploaded_files,
            'add_another': add_another,
        }

    def get_return_url(self, request, obj=None):
        request_pk = self.kwargs.get('request_pk')
        add_another = request.POST.get('_addanother', '')
        if add_another:
            return reverse(
                'plugins:netbox_access_request:requestsubject_add',
                args=[request_pk]
            ) + '?add_another=1'
        return reverse(
            'plugins:netbox_access_request:accessrequest',
            args=[request_pk]
        ) + '?tab=subjects'

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        return response


class RequestSubjectDeleteView(generic.ObjectDeleteView):
    """Xóa đối tượng"""
    queryset = models.RequestSubject.objects.all()

    def dispatch(self, request, *args, **kwargs):
        if 'pk' in kwargs:
            obj = get_object_or_404(models.RequestSubject, pk=kwargs['pk'], access_request__pk=kwargs['request_pk'])
            access_request = obj.access_request
            # Chỉ người tạo phiếu mới được xoá đối tượng
            if access_request.created_by != request.user:
                messages.error(request, 'Bạn không có quyền xoá đối tượng trong phiếu yêu cầu này.')
                return redirect(access_request.get_absolute_url() + '?tab=subjects')
            if access_request.status == RequestStatusChoices.STATUS_COMPLETED:
                messages.error(request, 'Không thể xoá đối tượng khi phiếu yêu cầu đã Hoàn thành.')
                return redirect(access_request.get_absolute_url() + '?tab=subjects')
            if obj.verify_status == VerifyStatusChoices.STATUS_VALID:
                messages.error(request, 'Không thể xoá đối tượng đã được xác nhận Hợp lệ.')
                return redirect(access_request.get_absolute_url() + '?tab=subjects')
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, **kwargs):
        return get_object_or_404(
            models.RequestSubject,
            pk=kwargs['pk'],
            access_request__pk=kwargs['request_pk']
        )

    def get_return_url(self, request, obj=None):
        if obj:
            return reverse(
                'plugins:netbox_access_request:accessrequest',
                args=[obj.access_request.pk]
            ) + '?tab=subjects'
        return reverse('plugins:netbox_access_request:accessrequest_list')


class RequestSubjectVerifyView(View):
    """Admin verify đối tượng: Hợp lệ / Không hợp lệ"""

    def post(self, request, request_pk, pk):
        # Chỉ Admin mới được verify đối tượng
        if not is_admin_user(request.user):
            messages.error(request, 'Bạn không có quyền thực hiện thao tác này.')
            return redirect(
                reverse('plugins:netbox_access_request:accessrequest', args=[request_pk]) + '?tab=subjects'
            )

        subject = get_object_or_404(
            models.RequestSubject,
            pk=pk,
            access_request__pk=request_pk
        )
        verify_action = request.POST.get('verify_action', '')

        if verify_action == 'valid':
            subject.verify_status = VerifyStatusChoices.STATUS_VALID
            subject.save()
            messages.success(request, f'Đối tượng "{subject.full_name}" đã được xác nhận hợp lệ.')
        elif verify_action == 'invalid':
            subject.verify_status = VerifyStatusChoices.STATUS_INVALID
            subject.save()
            messages.warning(request, f'Đối tượng "{subject.full_name}" đã được đánh dấu không hợp lệ.')
        else:
            messages.error(request, 'Hành động không hợp lệ.')

        return redirect(
            reverse('plugins:netbox_access_request:accessrequest',
                    args=[request_pk]) + '?tab=subjects'
        )


class RequestSubjectToggleStatusView(View):
    """Admin toggle trạng thái In/Out cho đối tượng"""

    def post(self, request, request_pk, pk):
        # Chỉ Admin mới được toggle trạng thái In/Out
        if not is_admin_user(request.user):
            messages.error(request, 'Bạn không có quyền thực hiện thao tác này.')
            return redirect(
                reverse('plugins:netbox_access_request:accessrequest', args=[request_pk]) + '?tab=subjects'
            )

        subject = get_object_or_404(
            models.RequestSubject,
            pk=pk,
            access_request__pk=request_pk
        )
        access_request = subject.access_request

        # Chỉ toggle khi phiếu đã được chấp nhận
        if access_request.status != RequestStatusChoices.STATUS_APPROVED:
            messages.error(request, 'Chỉ có thể thay đổi trạng thái khi phiếu đã được chấp nhận.')
            return redirect(
                reverse('plugins:netbox_access_request:accessrequest',
                        args=[request_pk]) + '?tab=subjects'
            )

        toggle_action = request.POST.get('toggle_action', '')

        if toggle_action == 'in':
            subject.status = SubjectStatusChoices.STATUS_IN
            subject.save()
            add_history(
                access_request, request.user,
                f'Check-in đối tượng {subject.full_name}',
                access_request.status,
                f'Đối tượng {subject.full_name} đã check-in'
            )
            messages.success(request, f'Đối tượng "{subject.full_name}" đã check-in.')
        elif toggle_action == 'out':
            subject.status = SubjectStatusChoices.STATUS_OUT
            subject.save()
            add_history(
                access_request, request.user,
                f'Check-out đối tượng {subject.full_name}',
                access_request.status,
                f'Đối tượng {subject.full_name} đã check-out'
            )
            messages.success(request, f'Đối tượng "{subject.full_name}" đã check-out.')
        else:
            messages.error(request, 'Hành động không hợp lệ.')

        return redirect(
            reverse('plugins:netbox_access_request:accessrequest',
                    args=[request_pk]) + '?tab=subjects'
        )


class RequestSubjectImportView(generic.BulkImportView):
    """Import đối tượng từ file CSV"""
    queryset = models.RequestSubject.objects.all()
    model_form = forms.RequestSubjectImportForm
    default_return_url = 'plugins:netbox_access_request:accessrequest_list'

    def get_return_url(self, request, obj=None):
        access_request_id = request.GET.get('access_request') or request.POST.get('access_request')
        if access_request_id:
            try:
                if str(access_request_id).isdigit():
                    req = models.AccessRequest.objects.get(pk=access_request_id)
                else:
                    req = models.AccessRequest.objects.get(name=access_request_id)
                return req.get_absolute_url() + '?tab=subjects'
            except Exception:
                pass
        return super().get_return_url(request, obj)

