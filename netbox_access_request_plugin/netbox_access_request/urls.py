from django.urls import path
from . import models, views
from netbox.views.generic import ObjectChangeLogView

app_name = 'netbox_access_request'

urlpatterns = [
    # === Phiếu yêu cầu (AccessRequest) ===
    path(
        'requests/',
        views.AccessRequestListView.as_view(),
        name='accessrequest_list'
    ),
    path(
        'requests/add/',
        views.AccessRequestEditView.as_view(),
        name='accessrequest_add'
    ),
    path(
        'requests/<int:pk>/',
        views.AccessRequestView.as_view(),
        name='accessrequest'
    ),
    path(
        'requests/<int:pk>/edit/',
        views.AccessRequestEditView.as_view(),
        name='accessrequest_edit'
    ),
    path(
        'requests/<int:pk>/delete/',
        views.AccessRequestDeleteView.as_view(),
        name='accessrequest_delete'
    ),
    path(
        'requests/<int:pk>/changelog/',
        ObjectChangeLogView.as_view(),
        name='accessrequest_changelog',
        kwargs={'model': models.AccessRequest}
    ),

    # Workflow actions
    path(
        'requests/<int:pk>/submit/',
        views.AccessRequestSubmitView.as_view(),
        name='accessrequest_submit'
    ),
    path(
        'requests/<int:pk>/confirm/',
        views.AccessRequestConfirmView.as_view(),
        name='accessrequest_confirm'
    ),
    path(
        'requests/<int:pk>/approve/',
        views.AccessRequestApproveView.as_view(),
        name='accessrequest_approve'
    ),
    path(
        'requests/<int:pk>/reject/',
        views.AccessRequestRejectView.as_view(),
        name='accessrequest_reject'
    ),
    path(
        'requests/<int:pk>/complete/',
        views.AccessRequestCompleteView.as_view(),
        name='accessrequest_complete'
    ),

    # === Đối tượng (RequestSubject) ===
    path(
        'requests/subjects/import/',
        views.RequestSubjectImportView.as_view(),
        name='requestsubject_import'
    ),
    path(
        'requests/<int:request_pk>/subjects/add/',
        views.RequestSubjectEditView.as_view(),
        name='requestsubject_add'
    ),
    path(
        'requests/<int:request_pk>/subjects/<int:pk>/',
        views.RequestSubjectView.as_view(),
        name='requestsubject'
    ),
    path(
        'requests/<int:request_pk>/subjects/<int:pk>/edit/',
        views.RequestSubjectEditView.as_view(),
        name='requestsubject_edit'
    ),
    path(
        'requests/<int:request_pk>/subjects/<int:pk>/delete/',
        views.RequestSubjectDeleteView.as_view(),
        name='requestsubject_delete'
    ),
    path(
        'requests/<int:request_pk>/subjects/<int:pk>/verify/',
        views.RequestSubjectVerifyView.as_view(),
        name='requestsubject_verify'
    ),
    path(
        'requests/<int:request_pk>/subjects/<int:pk>/toggle-status/',
        views.RequestSubjectToggleStatusView.as_view(),
        name='requestsubject_toggle_status'
    ),
    path(
        'requests/<int:request_pk>/subjects/<int:pk>/changelog/',
        ObjectChangeLogView.as_view(),
        name='requestsubject_changelog',
        kwargs={'model': models.RequestSubject}
    ),
]
