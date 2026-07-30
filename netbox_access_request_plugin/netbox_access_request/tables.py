import django_tables2 as tables
from netbox.tables import NetBoxTable, columns
from .models import AccessRequest, RequestSubject
from .choices import RequestStatusChoices, SubjectStatusChoices, VerifyStatusChoices


class AccessRequestTable(NetBoxTable):
    """Bảng danh sách phiếu yêu cầu"""
    name = tables.Column(
        linkify=True,
        verbose_name="Tên phiếu"
    )
    status = columns.ChoiceFieldColumn(
        verbose_name="Trạng thái"
    )
    reason = tables.Column(
        verbose_name="Lý do"
    )
    expected_date = tables.DateColumn(
        format='d/m/Y',
        verbose_name="Ngày dự kiến"
    )
    region = tables.Column(
        verbose_name="Region"
    )
    site = tables.Column(
        verbose_name="Site"
    )
    created_by = tables.Column(
        verbose_name="Người tạo",
        accessor='created_by__username'
    )
    created = tables.DateTimeColumn(
        format='d/m/Y H:i',
        verbose_name="Thời gian tạo"
    )
    last_updated = tables.DateTimeColumn(
        format='d/m/Y H:i',
        verbose_name="Thời gian cập nhật"
    )
    actions = columns.ActionsColumn(
        actions=('edit', 'delete')
    )

    class Meta(NetBoxTable.Meta):
        model = AccessRequest
        fields = (
            'pk', 'name', 'status', 'reason', 'expected_date',
            'region', 'site', 'created_by', 'created', 'last_updated', 'actions'
        )
        default_columns = (
            'name', 'status', 'reason', 'expected_date',
            'region', 'site', 'created_by', 'last_updated', 'actions'
        )


class RequestSubjectTable(NetBoxTable):
    """Bảng danh sách đối tượng trong phiếu yêu cầu"""
    id_number = tables.Column(
        verbose_name="Mã định danh"
    )
    full_name = tables.Column(
        linkify=True,
        verbose_name="Họ tên"
    )
    organization = tables.Column(
        verbose_name="Đơn vị"
    )
    position = tables.Column(
        verbose_name="Chức vụ"
    )
    status = columns.ChoiceFieldColumn(
        verbose_name="Trạng thái"
    )
    created = tables.DateTimeColumn(
        format='d/m/Y H:i',
        verbose_name="Ngày tạo"
    )
    last_updated = tables.DateTimeColumn(
        format='d/m/Y H:i',
        verbose_name="Thời gian cập nhật"
    )
    verify_status = columns.ChoiceFieldColumn(
        verbose_name="Xác nhận"
    )
    uploaded_files = tables.Column(
        verbose_name="Tệp đính kèm",
        empty_values=(),
    )
    actions = columns.ActionsColumn(
        actions=('edit', 'delete')
    )

    def render_uploaded_files(self, record):
        files = record.get_uploaded_files
        if not files:
            return "-"
        return ", ".join([f.file_name for f in files])

    class Meta(NetBoxTable.Meta):
        model = RequestSubject
        fields = (
            'pk', 'id_number', 'full_name', 'organization', 'position',
            'status', 'created', 'last_updated', 'uploaded_files', 'verify_status', 'actions'
        )
        default_columns = (
            'id_number', 'full_name', 'organization', 'position',
            'status', 'last_updated', 'uploaded_files', 'verify_status', 'actions'
        )
