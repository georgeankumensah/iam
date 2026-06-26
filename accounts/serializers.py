from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id", "email", "phone", "first_name", "last_name",
            "user_type", "status", "metadata", "created_at",
            "last_login_at",
        ]
        read_only_fields = ["id", "created_at", "last_login_at"]
