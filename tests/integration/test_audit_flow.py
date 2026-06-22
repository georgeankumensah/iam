from django.contrib.auth import get_user_model
from django.test import TestCase

from audit.chain import verify_chain
from audit.emit import emit_event

User = get_user_model()


class AuditFlowTests(TestCase):
    def test_emit_and_anchor(self) -> None:
        event_id = emit_event(
            actor_user_id="00000000-0000-0000-0000-000000000001",
            action="test.action",
            entity_type="test",
            entity_id="test-1",
            channel="test",
        )
        self.assertIsNotNone(event_id)

    def test_chain_integrity(self) -> None:
        for i in range(5):
            emit_event(
                actor_user_id="00000000-0000-0000-0000-000000000002",
                action=f"test.action.{i}",
                entity_type="test",
                entity_id=f"test-{i}",
                channel="test",
            )

        failures = verify_chain()
        self.assertEqual(len(failures), 0, f"Chain verification failed: {failures}")
