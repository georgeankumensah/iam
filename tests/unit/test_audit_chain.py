from django.test import TestCase

from audit.chain import compute_hash_chain_ref


class AuditChainTests(TestCase):
    def test_compute_hash_chain_ref(self) -> None:
        h1 = compute_hash_chain_ref("0" * 64, {"action": "test", "id": 1})
        self.assertEqual(len(h1), 64)

        h2 = compute_hash_chain_ref(h1, {"action": "test", "id": 2})
        self.assertEqual(len(h2), 64)
        self.assertNotEqual(h1, h2)

    def test_same_input_same_hash(self) -> None:
        event = {"action": "test", "id": 1}
        h1 = compute_hash_chain_ref("0" * 64, event)
        h2 = compute_hash_chain_ref("0" * 64, event)
        self.assertEqual(h1, h2)

    def test_different_input_different_hash(self) -> None:
        h1 = compute_hash_chain_ref("0" * 64, {"action": "test1", "id": 1})
        h2 = compute_hash_chain_ref("0" * 64, {"action": "test2", "id": 1})
        self.assertNotEqual(h1, h2)
