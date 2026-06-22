from rest_framework import serializers

from accounts.models import User


class UserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["email", "phone", "user_type", "status", "metadata"]
        extra_kwargs = {"email": {"required": True}}


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["phone", "metadata", "status"]


class BulkImportSerializer(serializers.Serializer):
    users = serializers.ListField(child=serializers.DictField())
    notify = serializers.BooleanField(default=False)
