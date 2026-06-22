from rest_framework import serializers

from .models import OIDCClient


class OIDCClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = OIDCClient
        fields = [
            "id", "client_id", "lifecycle_state", "redirect_uris",
            "post_logout_redirect_uris", "scopes", "compliance_gate_passed",
            "secret_rotated_at", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "client_id_hash", "created_at", "updated_at", "secret_rotated_at"]


class OIDCClientCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OIDCClient
        fields = [
            "client_id", "redirect_uris", "post_logout_redirect_uris",
            "scopes", "owner_id", "granted_system_refs", "metadata",
        ]
