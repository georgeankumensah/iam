"""Drive the HRMS lifecycle pipeline with canonical payloads (IAM-F06).

Stands in for the real HRMS (System 09) so the joiner/mover/leaver flow can be
exercised end-to-end locally. Persists an ``HrmsEvent`` and runs the handler
synchronously (no broker/worker required).

Usage:
    python manage.py hrms_stub --event-type joiner --email jane.doe@clet.gov.gh
    python manage.py hrms_stub --event-type all
"""

from django.core.management.base import BaseCommand
from django.utils import timezone


def _canonical_payload(event_type: str, email: str) -> dict:
    base = {"event_type": event_type, "email": email}
    if event_type == "hrms.joiner":
        base.update({
            "first_name": "Jane",
            "last_name": "Doe",
            "employee_id": "EMP-0001",
            "department": "Registry",
            "start_date": timezone.now().isoformat(),
        })
    elif event_type == "hrms.mover":
        base.update({"department": "Examinations", "line_manager_id": "EMP-0009"})
    elif event_type == "hrms.leaver":
        base.update({"last_day": timezone.now().isoformat()})
    return base


class Command(BaseCommand):
    help = "Emit canonical HRMS joiner/mover/leaver events through the lifecycle pipeline."

    def add_arguments(self, parser):
        parser.add_argument("--event-type", default="all", choices=["joiner", "mover", "leaver", "all"])
        parser.add_argument("--email", default="jane.doe@clet.gov.gh")

    def handle(self, *args, **options):
        from lifecycle.models import HrmsEvent
        from lifecycle.tasks import handle_hrms_event

        which = options["event_type"]
        email = options["email"]
        types = ["joiner", "mover", "leaver"] if which == "all" else [which]

        for short in types:
            event_type = f"hrms.{short}"
            payload = _canonical_payload(event_type, email)
            event = HrmsEvent.objects.create(
                event_type=event_type,
                target_email=email,
                payload=payload,
                signature_valid=True,
                status=HrmsEvent.Status.RECEIVED,
            )
            result = handle_hrms_event(event_type, payload, event_id=str(event.id))
            self.stdout.write(self.style.SUCCESS(f"{event_type}: {result} (event {event.id})"))
