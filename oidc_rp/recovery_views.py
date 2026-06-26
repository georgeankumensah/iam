from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from accounts.recovery import generate_recovery_codes, remaining_codes, verify_recovery_code
from core.responses import error_response, success_response


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def me_recovery_codes(request):
    if request.method == "POST":
        codes = generate_recovery_codes(request.user)
        return success_response(data={
            "codes": [c["masked"] for c in codes],
            "message": "Store these securely. They will not be shown again.",
        })

    remaining = remaining_codes(request.user)
    return success_response(data={"remaining": len(remaining), "codes": remaining})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def me_recovery_codes_verify(request):
    code = request.data.get("code", "")
    if not code:
        return error_response(message="code is required", status_code=400)

    if verify_recovery_code(request.user, code):
        return success_response(data={"verified": True}, message="Recovery code accepted")
    return error_response(message="Invalid or already-used recovery code", status_code=400)
