
from django.http import JsonResponse

SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "IAM Token Claims Schema",
    "description": "Custom claims injected into Zitadel tokens via Actions V2 complementToken target",
    "type": "object",
    "properties": {
        "user_type": {
            "type": "string",
            "enum": ["staff", "board", "nbec", "student", "external", "public"],
            "description": "The user's type, determining their role category and policy group",
        },
        "portal_access": {
            "type": "array",
            "items": {"type": "string", "pattern": "^[a-z0-9-]+$"},
            "description": "List of system project IDs the user has role grants for",
        },
        "permissions": {
            "type": "array",
            "items": {"type": "string", "pattern": "^[a-z0-9-]+:[a-z_]+$"},
            "description": "List of permission strings (system:role) derived from active grants",
        },
    },
    "required": [],
    "additionalProperties": False,
}


def iam_claims_schema(request):  # noqa: ARG001
    return JsonResponse(SCHEMA, status=200)
