"""Onboarding/invitation routes mounted at /v1/.

Separate from /v1/admin/ (IAM-admin only) because system admins — who are not
IAM admins — also use these, gated per-request by can_manage_system_invites.
"""

from django.urls import path

from console.views import invitations
from console.views import users

urlpatterns = [
    path("invitations", invitations.invitations_collection, name="invitations"),
    path("invitations/<uuid:invite_id>", invitations.invitation_detail, name="invitation_detail"),
    path("invitations/<uuid:invite_id>/resend", invitations.invitation_resend, name="invitation_resend"),
    path("me/admin-systems", invitations.my_admin_systems, name="my_admin_systems"),
    path("internal/admin-systems", invitations.internal_admin_systems, name="internal_admin_systems"),
    path("internal/invitations", invitations.internal_invitations, name="internal_invitations"),
    path("internal/invitations/<uuid:invite_id>/resend", invitations.internal_invitation_resend, name="internal_invitation_resend"),
    path("internal/admin-users", users.internal_users_list, name="internal_admin_users"),
    path("internal/admin-users/<uuid:user_id>", users.internal_user_delete, name="internal_admin_user_delete"),
    path("internal/admin-users/<uuid:user_id>/reactivate", users.internal_user_reactivate, name="internal_admin_user_reactivate"),
]
