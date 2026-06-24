"""Onboarding/invitation routes mounted at /v1/.

Separate from /v1/admin/ (IAM-admin only) because system admins — who are not
IAM admins — also use these, gated per-request by can_manage_system_invites.
"""

from django.urls import path

from console.views import invitations

urlpatterns = [
    path("invitations", invitations.invitations_collection, name="invitations"),
    path("invitations/<uuid:invite_id>", invitations.invitation_detail, name="invitation_detail"),
    path("invitations/<uuid:invite_id>/resend", invitations.invitation_resend, name="invitation_resend"),
    path("me/admin-systems", invitations.my_admin_systems, name="my_admin_systems"),
]
