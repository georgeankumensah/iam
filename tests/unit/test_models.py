from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

User = get_user_model()


class UserModelTests(TestCase):
    def test_create_user(self) -> None:
        user = User.objects.create_user(email="test@example.com", user_type="staff")
        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.user_type, "staff")
        self.assertEqual(user.status, "pre_active")
        self.assertFalse(user.has_usable_password())

    def test_user_type_choices(self) -> None:
        for choice in ["staff", "board", "nbec", "student", "external", "public"]:
            user = User.objects.create_user(email=f"{choice}@example.com", user_type=choice)
            self.assertEqual(user.user_type, choice)

    def test_email_unique(self) -> None:
        User.objects.create_user(email="dup@example.com")
        with self.assertRaises(IntegrityError):
            User.objects.create_user(email="dup@example.com")

    def test_zitadel_user_id_nullable(self) -> None:
        user = User.objects.create_user(email="test@example.com")
        self.assertIsNone(user.zitadel_user_id)
