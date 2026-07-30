from utilities.choices import ChoiceSet


class RequestStatusChoices(ChoiceSet):
    """Trạng thái phiếu yêu cầu"""
    STATUS_DRAFT = 'draft'
    STATUS_SUBMITTED = 'submitted'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_COMPLETED = 'completed'

    CHOICES = (
        (STATUS_DRAFT, 'Nháp', 'gray'),
        (STATUS_SUBMITTED, 'Đã gửi', 'blue'),
        (STATUS_CONFIRMED, 'Đã xác nhận', 'cyan'),
        (STATUS_APPROVED, 'Chấp nhận', 'green'),
        (STATUS_REJECTED, 'Từ chối', 'red'),
        (STATUS_COMPLETED, 'Hoàn thành', 'dark-gray'),
    )


class SubjectStatusChoices(ChoiceSet):
    """Trạng thái ra/vào của đối tượng"""
    STATUS_PENDING = 'pending'
    STATUS_IN = 'in'
    STATUS_OUT = 'out'

    CHOICES = (
        (STATUS_PENDING, 'Chờ', 'gray'),
        (STATUS_IN, 'In', 'green'),
        (STATUS_OUT, 'Out', 'orange'),
    )


class VerifyStatusChoices(ChoiceSet):
    """Trạng thái xác nhận đối tượng bởi Admin"""
    STATUS_PENDING = 'pending'
    STATUS_VALID = 'valid'
    STATUS_INVALID = 'invalid'

    CHOICES = (
        (STATUS_PENDING, 'Chờ xác nhận', 'gray'),
        (STATUS_VALID, 'Hợp lệ', 'green'),
        (STATUS_INVALID, 'Không hợp lệ', 'red'),
    )
