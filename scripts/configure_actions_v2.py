#!/usr/bin/env python3
"""Configure Zitadel Actions V2 complementToken target and execution.

Creates a REST-call target pointing at the Django complement-token endpoint
and binds it to the ``preaccesstoken`` function so every access token gets
custom claims (user_type, portal_access, permissions).

Usage:

    source .venv/bin/activate
    python scripts/configure_actions_v2.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django

django.setup()

from django.conf import settings

from core.zitadel import ZitadelError, zitadel

TARGET_NAME = "iam-complement-token"
TARGET_ENDPOINT = settings.ACTIONS_TARGET_ENDPOINT
FUNCTION_CONDITION = "preaccesstoken"


def main():
    z = zitadel()

    print(f"Creating Actions V2 target: {TARGET_NAME} -> {TARGET_ENDPOINT}")
    try:
        result = z.create_actions_target(
            name=TARGET_NAME,
            endpoint=TARGET_ENDPOINT,
            timeout="10s",
            target_type="restCall",
            interrupt_on_error=False,
        )
        target_id = result.get("id", "")
        signing_key = result.get("signingKey", "")
        print(f"  Target created: {target_id}")
        if signing_key:
            print(f"  Signing key (hex): {signing_key}")
            print("  Set env: ZITADEL_ACTIONS_SIGNING_KEY=<key>")
    except ZitadelError as e:
        if e.status == 409:
            print("  Target already exists (skipping)")
            return
        print(f"  ERROR: {e}")
        sys.exit(1)

    print(f"Setting execution for {FUNCTION_CONDITION} -> {target_id}")
    try:
        z.set_actions_execution(FUNCTION_CONDITION, [target_id])
        print("  Execution set.")
    except ZitadelError as e:
        print(f"  ERROR: {e}")
        sys.exit(1)

    print("Done.")


if __name__ == "__main__":
    main()
