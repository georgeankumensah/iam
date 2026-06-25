"""Onboarding / invitation service.

IAM invites a user into a system and assigns role(s); credentials + MFA are set
by the invitee through the Custom Login UI. IAM only manages role identity — the
downstream system interprets the role into permissions.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import timedelta
from urllib.parse import urlparse

from django.conf import settings
from django.utils import timezone

from accounts.models import Invitation, User, UserStatus
from audit.emit import emit_event
from clients.models import OIDCClient
from console.permissions import is_iam_admin
from core.zitadel import zitadel
from rbac.models import Role, RoleBinding
from rbac.services import check_sod, sync_user_system_grant

logger = logging.getLogger("iam.console.onboarding")


class OnboardingError(Exception):
    pass


def _system_client(system_code: str) -> OIDCClient | None:
    return OIDCClient.objects.filter(system_code=system_code).exclude(zitadel_project_id="").first()


def system_frontend_url(client: OIDCClient) -> str:
    for uri in client.redirect_uris or []:
        p = urlparse(uri)
        if p.scheme and p.netloc:
            return f"{p.scheme}://{p.netloc}"
    return settings.LOGIN_APP_BASE_URL


def _resolve_roles(system_code: str, role_ids: list[str]) -> list[Role]:
    if not role_ids:
        raise OnboardingError("role_required")
    roles = list(Role.objects.filter(id__in=role_ids, system_code=system_code, is_deprecated=False))
    if not roles:
        raise OnboardingError("no valid roles for this system")
    if len(roles) != len(set(role_ids)):
        raise OnboardingError("some roles do not belong to this system")
    return roles


def invite_user(*, email, system_code, role_ids, invited_by, return_code=False):
    """Provision (or reuse) the user, assign role(s), and issue an invite code.

    Returns (invitation, code) where code is non-None only in dev/return_code mode.
    """
    client = _system_client(system_code)
    if not client:
        raise OnboardingError("unknown_system")

    roles = _resolve_roles(system_code, role_ids)
    z = zitadel()

    # Resolve/create the ZITADEL user.
    zu = z.find_user_by_email(email)
    zid = zu["userId"] if zu else z.create_human_user(email, "", "")

    # Resolve/create the Django mirror.
    user, _ = User.objects.get_or_create(
        email=email, defaults={"status": UserStatus.PRE_ACTIVE}
    )
    if not user.zitadel_user_id:
        user.zitadel_user_id = zid
        user.save(update_fields=["zitadel_user_id"])

    inviter_is_global = is_iam_admin(invited_by) if invited_by else True

    # Create bindings. Admin-tier roles assigned by a non-IAM-admin (i.e. a system
    # admin inviting another admin) are held for DG approval; everything else is
    # effective immediately.
    for role in roles:
        check_sod(user, role)
        needs_approval = role.is_admin and not inviter_is_global
        state = (
            RoleBinding.BindingState.REQUESTED
            if needs_approval
            else RoleBinding.BindingState.APPROVED
        )
        RoleBinding.objects.get_or_create(
            role=role,
            user=user,
            state=state,
            defaults={
                "approver": None if needs_approval else invited_by,
                "justification": f"onboarding invite into {system_code}",
            },
        )

    # Push the approved subset to ZITADEL so it lands in tokens.
    sync_user_system_grant(user, system_code)

    raw = secrets.token_urlsafe(32)
    inv = Invitation.objects.create(
        email=email,
        system_code=system_code,
        user=user,
        zitadel_user_id=zid,
        role_ids=[str(r.id) for r in roles],
        as_admin=any(r.is_admin for r in roles),
        token_hash=hashlib.sha256(raw.encode()).hexdigest(),
        invited_by=invited_by,
        expires_at=timezone.now() + timedelta(hours=settings.INVITATION_TTL_HOURS),
    )

    code = _send_invite(z, zid, return_code)

    emit_event(
        actor_user_id=str(invited_by.id) if invited_by else "",
        action="user.invited",
        entity_type="invitation",
        entity_id=str(inv.id),
        channel="console",
        metadata={"system": system_code, "email": email, "as_admin": inv.as_admin},
    )
    return inv, code


def _send_invite(z, zitadel_user_id: str, return_code: bool) -> str | None:
    url_template = (
        settings.LOGIN_APP_BASE_URL
        + "/invite?userID={{.UserID}}&code={{.Code}}&org={{.OrgID}}"
    )
    return z.request_password_set(
        zitadel_user_id,
        url_template=None if return_code else url_template,
        return_code=return_code,
    )


def resend_invitation(invitation: Invitation, return_code=False) -> str | None:
    z = zitadel()
    code = _send_invite(z, invitation.zitadel_user_id, return_code)
    invitation.expires_at = timezone.now() + timedelta(hours=settings.INVITATION_TTL_HOURS)
    invitation.save(update_fields=["expires_at", "updated_at"])
    return code


def revoke_invitation(invitation: Invitation, actor=None) -> None:
    invitation.status = Invitation.Status.REVOKED
    invitation.save(update_fields=["status", "updated_at"])
    emit_event(
        actor_user_id=str(actor.id) if actor else "",
        action="invitation.revoked",
        entity_type="invitation",
        entity_id=str(invitation.id),
        channel="console",
    )


def accept_invitation(*, zitadel_user_id: str, code: str, password: str) -> dict:
    """Called when an invitee sets their password from the invite link.

    Sets the credential in ZITADEL, then activates the Django user and marks the
    invitation accepted. Returns the target system's frontend URL for redirect.
    """
    z = zitadel()
    z.set_password_with_code(zitadel_user_id, code, password)

    inv = (
        Invitation.objects.filter(
            zitadel_user_id=zitadel_user_id, status=Invitation.Status.PENDING
        )
        .order_by("-created_at")
        .first()
    )
    system_url = settings.LOGIN_APP_BASE_URL
    if inv:
        inv.status = Invitation.Status.ACCEPTED
        inv.accepted_at = timezone.now()
        inv.save(update_fields=["status", "accepted_at", "updated_at"])
        if inv.user:
            inv.user.status = UserStatus.ACTIVE
            inv.user.save(update_fields=["status"])
        client = _system_client(inv.system_code)
        if client:
            system_url = system_frontend_url(client)
        emit_event(
            actor_user_id=str(inv.user.id) if inv.user else "",
            action="invitation.accepted",
            entity_type="invitation",
            entity_id=str(inv.id),
            channel="auth",
        )
    return {"system_url": system_url}
