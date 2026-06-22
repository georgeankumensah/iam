import logging

from celery import shared_task

logger = logging.getLogger("iam.lifecycle.tasks")


@shared_task
def handle_hrms_event(event_type: str, payload: dict):
    logger.info("Processing HRMS event: %s", event_type)

    if event_type == "hrms.joiner":
        return _process_joiner(payload)
    elif event_type == "hrms.mover":
        return _process_mover(payload)
    elif event_type == "hrms.leaver":
        return _process_leaver(payload)
    else:
        logger.warning("Unknown HRMS event type: %s", event_type)
        return {"status": "unknown_event"}


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
        return {"status": "disabled", "email": email}
    except User.DoesNotExist:
        return {"status": "not_found", "email": email}
