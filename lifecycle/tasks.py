import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger("iam.lifecycle.tasks")


# Handler result statuses that indicate the event could not be applied cleanly
# and needs human resolution (vs a transient failure that can be replayed).
_CONFLICT_RESULTS = {"not_found", "conflict"}
_OK_RESULTS = {"created", "updated", "disabled"}


@shared_task
def handle_hrms_event(event_type: str, payload: dict, event_id: str | None = None):
    logger.info("Processing HRMS event: %s", event_type)

    try:
        if event_type == "hrms.joiner":
            result = _process_joiner(payload)
        elif event_type == "hrms.mover":
            result = _process_mover(payload)
        elif event_type == "hrms.leaver":
            result = _process_leaver(payload)
        else:
            logger.warning("Unknown HRMS event type: %s", event_type)
            result = {"status": "unknown_event"}
    except Exception as e:  # noqa: BLE001
        logger.exception("HRMS event %s failed", event_type)
        result = {"status": "error", "detail": str(e)}

    if event_id:
        _record_event_outcome(event_id, result)
    return result


def _record_event_outcome(event_id: str, result: dict) -> None:
    from django.utils import timezone

    from .models import HrmsEvent

    rstatus = result.get("status", "")
    if rstatus in _OK_RESULTS:
        status = HrmsEvent.Status.PROCESSED
    elif rstatus in _CONFLICT_RESULTS:
        status = HrmsEvent.Status.CONFLICT
    else:
        status = HrmsEvent.Status.FAILED

    HrmsEvent.objects.filter(id=event_id).update(
        status=status,
        result=result,
        error="" if status != HrmsEvent.Status.FAILED else result.get("detail", rstatus),
        processed_at=timezone.now(),
    )


def _process_joiner(payload: dict) -> dict:
    from accounts.models import User

    from .scim import UserProvisionerBackend

    email = payload.get("email", "")
    first_name = payload.get("first_name", "")
    last_name = payload.get("last_name", "")
    employee_id = payload.get("employee_id", "")

    zitadel_result = UserProvisionerBackend().create_user(
        email=email,
        first_name=first_name,
        last_name=last_name,
    )
    if not zitadel_result:
        return {"status": "error", "step": "zitadel_create"}

    User.objects.get_or_create(
        email=email,
        defaults={
            "zitadel_user_id": zitadel_result.get("userId", ""),
            "user_type": "staff",
            "status": "pre_active",
            "metadata": {"employee_id": employee_id, "first_name": first_name, "last_name": last_name},
        },
    )
    return {"status": "created", "email": email}


def _process_mover(payload: dict) -> dict:
    from accounts.models import User

    email = payload.get("email", "")
    updates = {k: v for k, v in payload.items() if k in ("department", "line_manager_id")}

    try:
        user = User.objects.get(email=email)
        if updates:
            meta = dict(user.metadata)
            meta.update(updates)
            user.metadata = meta
            user.save(update_fields=["metadata"])
        return {"status": "updated", "email": email}
    except User.DoesNotExist:
        return {"status": "not_found", "email": email}


def _process_leaver(payload: dict) -> dict:
    from accounts.models import User

    from .scim import UserProvisionerBackend

    email = payload.get("email", "")
    try:
        user = User.objects.get(email=email)
        backend = UserProvisionerBackend()
        if user.zitadel_user_id:
            backend.deactivate_user(str(user.zitadel_user_id))
            backend.terminate_sessions(str(user.zitadel_user_id))
        user.status = "disabled"
        user.save(update_fields=["status"])

        from pam.services import revoke_user_pam_sessions

        revoked = revoke_user_pam_sessions(user=user, reason="leaver")
        return {"status": "disabled", "email": email, "pam_sessions_revoked": revoked}
    except User.DoesNotExist:
        return {"status": "not_found", "email": email}


@shared_task
def activate_pre_active_accounts() -> dict:
    from accounts.models import User

    now = timezone.now()
    activated = 0
    skipped = 0
    candidates = User.objects.filter(status=User.UserStatus.PRE_ACTIVE)
    for user in candidates:
        start_date = user.metadata.get("start_date")
        if not start_date:
            skipped += 1
            continue
        start_dt = timezone.datetime.fromisoformat(start_date)
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.get_current_timezone())
        if start_dt <= now:
            user.status = User.UserStatus.ACTIVE
            user.save(update_fields=["status"])
            activated += 1
    logger.info("Activated %d pre-active accounts (%d skipped, no start_date)", activated, skipped)
    return {"activated": activated, "skipped_no_start_date": skipped}


@shared_task
def finalize_leaver_disable() -> dict:
    from accounts.models import User
    from audit.emit import emit_event

    cutoff = timezone.now() - timezone.timedelta(hours=4)
    finalized = 0
    disabled = User.objects.filter(status=User.UserStatus.DISABLED, updated_at__lt=cutoff)
    for user in disabled:
        emit_event(
            actor_user_id=str(user.id),
            actor_email=user.email,
            action="lifecycle.leaver_finalized",
            entity_type="user",
            entity_id=str(user.id),
            channel="lifecycle",
            result="success",
            metadata={"finalized_at": timezone.now().isoformat()},
        )
        finalized += 1
    logger.info("Finalized %d leaver disable(s)", finalized)
    return {"finalized": finalized}


@shared_task
def purge_unverified_registrations() -> dict:
    from accounts.models import User

    from .scim import UserProvisionerBackend

    cutoff = timezone.now() - timezone.timedelta(days=7)
    purged = 0
    failed = 0
    stale = User.objects.filter(status=User.UserStatus.PENDING, created_at__lt=cutoff)
    for user in stale:
        if user.zitadel_user_id:
            try:
                UserProvisionerBackend().deactivate_user(str(user.zitadel_user_id))
            except Exception as e:  # noqa: BLE001
                logger.warning("Failed to deactivate Zitadel user %s: %s", user.zitadel_user_id, e)
                failed += 1
        user.delete()
        purged += 1
    logger.info("Purged %d unverified registration(s) (%d Zitadel deactivate failed)", purged, failed)
    return {"purged": purged, "zitadel_deactivate_failed": failed}
