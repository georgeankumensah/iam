from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    def create_user(self, email: str, **extra_fields):
        if not email:
            raise ValueError("email is required")
        email = self.normalize_email(email)
        extra_fields.setdefault("user_type", "external")
        extra_fields.setdefault("status", "pre_active")
        user = self.model(email=email, **extra_fields)
        user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, **extra_fields):
        extra_fields.setdefault("user_type", "staff")
        extra_fields.setdefault("status", "active")
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, **extra_fields)
