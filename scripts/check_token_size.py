#!/usr/bin/env python3
"""CI gate: check that Zitadel token size does not exceed a given threshold.

Usage:
    python scripts/check_token_size.py [--max-bytes 4096]

Reads the ``iam_zitadel_token_size_bytes`` Prometheus gauge from the live
/metrics endpoint and fails with exit code 1 if the value exceeds the limit.
"""

import argparse
import re
import sys
from urllib.request import urlopen

DEFAULT_MAX_BYTES = 4096
DEFAULT_METRICS_URL = "http://localhost:8000/health/metrics"


def main() -> int:
    parser = argparse.ArgumentParser(description="CI gate for Zitadel token size")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES, help="Max allowed token size in bytes")
    parser.add_argument("--metrics-url", default=DEFAULT_METRICS_URL, help="Prometheus /metrics endpoint URL")
    args = parser.parse_args()

    try:
        resp = urlopen(args.metrics_url, timeout=10)
        text = resp.read().decode()
    except Exception as e:
        print(f"ERROR: Could not fetch metrics from {args.metrics_url}: {e}")
        return 2

    match = re.search(r"iam_zitadel_token_size_bytes\s+([\d.e+-]+)", text)
    if not match:
        print("WARNING: iam_zitadel_token_size_bytes not found in metrics (no tokens issued yet) — skipping")
        return 0

    current = float(match.group(1))
    print(f"Current Zitadel token size: {current:.0f} bytes (limit: {args.max_bytes})")

    if current > args.max_bytes:
        print(f"FAIL: Token size {current:.0f}B exceeds limit of {args.max_bytes}B")
        return 1

    print("PASS: Token size OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
