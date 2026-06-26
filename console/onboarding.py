"""Onboarding / invitation service.

IAM invites a user into a system and assigns role(s); credentials + MFA are set
by the invitee through the Custom Login UI. IAM only manages role identity — the
downstream system interprets the role into permissions.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import urllib.parse
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


def _ensure_invitation_bindings(invitation: Invitation) -> None:
    """Ensure accepted invitations have concrete approved bindings.

    Bindings are normally created when the invitation is issued. Re-checking at
    acceptance makes the flow resilient to older invitations or partial sync
    failures, and guarantees the ZITADEL grant receives real role keys.
    """
    if not invitation.user:
        return

    roles = list(
        Role.objects.filter(
            id__in=invitation.role_ids,
            system_code=invitation.system_code,
            is_deprecated=False,
        )
    )
    if not roles:
        logger.warning(
            "accept_invitation: no valid roles for invitation %s (%s)",
            invitation.id,
            invitation.system_code,
        )
        return

    for role in roles:
        RoleBinding.objects.get_or_create(
            role=role,
            user=invitation.user,
            state=RoleBinding.BindingState.APPROVED,
            defaults={
                "approver": invitation.invited_by,
                "justification": f"accepted invitation into {invitation.system_code}",
            },
        )

    sync_user_system_grant(invitation.user, invitation.system_code)


def invite_user(*, email, system_code, role_ids, invited_by, return_code=False,
                first_name="", last_name=""):
    """Provision (or reuse) the user, assign role(s), and issue an invite code.

    Returns (invitation, code, lookup_token) where code is non-None only in
    dev/return_code mode, and lookup_token is the opaque token for the invite URL.
    """
    client = _system_client(system_code)
    if not client:
        raise OnboardingError("unknown_system")

    roles = _resolve_roles(system_code, role_ids)
    z = zitadel()

    # Resolve/create the ZITADEL user.
    zu = z.find_user_by_email(email)
    zid = zu["userId"] if zu else z.create_human_user(email, first_name, last_name)

    # Resolve/create the Django mirror.
    user, created = User.objects.get_or_create(
        email=email, defaults={"status": UserStatus.PRE_ACTIVE}
    )
    if not created and user.status == UserStatus.DISABLED:
        raise OnboardingError("This user has been deactivated. Reactivate them before sending a new invitation.")
    if not user.zitadel_user_id:
        user.zitadel_user_id = zid
    user.first_name = first_name
    user.last_name = last_name
    user.save(update_fields=["zitadel_user_id", "first_name", "last_name"])

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
    lookup_token = secrets.token_urlsafe(16)
    inv = Invitation.objects.create(
        email=email,
        system_code=system_code,
        user=user,
        zitadel_user_id=zid,
        role_ids=[str(r.id) for r in roles],
        as_admin=any(r.is_admin for r in roles),
        token_hash=hashlib.sha256(raw.encode()).hexdigest(),
        lookup_token_hash=hashlib.sha256(lookup_token.encode()).hexdigest(),
        invited_by=invited_by,
        expires_at=timezone.now() + timedelta(hours=settings.INVITATION_TTL_HOURS),
    )

    code = _send_invite(z, zid, email, return_code, lookup_token)

    emit_event(
        actor_user_id=str(invited_by.id) if invited_by else "",
        action="user.invited",
        entity_type="invitation",
        entity_id=str(inv.id),
        channel="console",
        metadata={"system": system_code, "email": email, "as_admin": inv.as_admin},
    )
    return inv, code, lookup_token


def _send_invite(z, zitadel_user_id: str, email: str, return_code: bool, lookup_token: str = "") -> str | None:
    url_template = (
        settings.LOGIN_APP_BASE_URL
        + f"/invite?code={{.Code}}&t={urllib.parse.quote(lookup_token)}"
    )
    return z.request_password_set(
        zitadel_user_id,
        url_template=None if return_code else url_template,
        return_code=return_code,
    )


def resend_invitation(invitation: Invitation, return_code=False) -> tuple[str | None, str]:
    z = zitadel()
    lookup_token = secrets.token_urlsafe(16)
    code = _send_invite(z, invitation.zitadel_user_id, invitation.email, return_code, lookup_token)
    invitation.lookup_token_hash = hashlib.sha256(lookup_token.encode()).hexdigest()
    invitation.status = Invitation.Status.PENDING
    invitation.expires_at = timezone.now() + timedelta(hours=settings.INVITATION_TTL_HOURS)
    invitation.accepted_at = None
    if invitation.user and invitation.user.status != UserStatus.ACTIVE:
        invitation.user.status = UserStatus.PRE_ACTIVE
        invitation.user.save(update_fields=["status"])
    invitation.save(update_fields=["lookup_token_hash", "status", "expires_at", "accepted_at", "updated_at"])
    return code, lookup_token


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


def accept_invitation(*, lookup_token: str, code: str, password: str, first_name: str = "", last_name: str = "") -> dict:
    """Called when an invitee sets their password from the invite link.

    Sets the credential in ZITADEL, then activates the Django user and marks the
    invitation accepted. Returns the target system's frontend URL for redirect.
    """
    token_hash = hashlib.sha256(lookup_token.encode()).hexdigest()
    inv = (
        Invitation.objects.filter(
            lookup_token_hash=token_hash, status=Invitation.Status.PENDING
        )
        .select_related("user")
        .first()
    )
    if not inv:
        raise OnboardingError("invalid_or_expired")

    z = zitadel()
    z.set_password_with_code(inv.zitadel_user_id, code, password)
    system_url = settings.LOGIN_APP_BASE_URL
    if inv:
        inv.status = Invitation.Status.ACCEPTED
        inv.accepted_at = timezone.now()
        inv.save(update_fields=["status", "accepted_at", "updated_at"])
        if inv.user:
            _ensure_invitation_bindings(inv)
            inv.user.status = UserStatus.ACTIVE
            inv.user.first_name = first_name
            inv.user.last_name = last_name
            inv.user.save(update_fields=["status", "first_name", "last_name"])
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
