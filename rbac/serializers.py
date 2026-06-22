from rest_framework import serializers

from .models import Role, RoleBinding


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class RoleBindingSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleBinding
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]
