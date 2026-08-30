#!/usr/bin/env python3
"""Read the configure response and return its exact CP2 short URL.

The generic edit-link refresh endpoint produces an R link.  CP2 instead must
use the C link returned by the save-config-keys response itself.
"""

from __future__ import annotations

import json
import re
import sys


CP2_URL = re.compile(r"https://api\.capafy\.ai/C[0-9]+$")


def extract(payload: object) -> str:
    if not isinstance(payload, dict):
        raise ValueError("publish-configure returned a non-object JSON payload")
    if payload.get("ok") is not True or payload.get("status") != "configured":
        raise ValueError(
            "publish-configure did not reach configured state: "
            f"status={payload.get('status')!r} error={payload.get('error')!r}"
        )
    url = str(payload.get("review_url") or "").strip()
    if not CP2_URL.fullmatch(url):
        raise ValueError(
            "publish-configure did not return the required CP2 URL "
            "https://api.capafy.ai/C<digits>"
        )
    return url


def main() -> int:
    try:
        print(extract(json.load(sys.stdin)))
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"CP2_URL_ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
