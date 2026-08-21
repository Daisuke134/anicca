#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

/usr/bin/python3 - "$ROOT/scripts" <<'PY'
import sys

sys.path.insert(0, sys.argv[1])
import publication_resume as publication

# The production weekly audit runs under launchd's /usr/bin Python. A receipt
# with exactly the expected number of proofs must validate on that runtime.
publication._validate_asset_proofs(
    {"media": {}},
    "x-post/ja",
    {"asset_proofs": [], "asset_urls": []},
)

# Python compatibility must not weaken the exact-cardinality invariant.
try:
    publication._validate_asset_proofs(
        {
            "media": {
                "headline_image": {
                    "path": "/tmp/headline.png",
                    "sha256": "a" * 64,
                },
                "body_assets": [],
            }
        },
        "note/ja",
        {"asset_proofs": []},
    )
except publication.InvariantError as error:
    assert str(error) == "receipt public asset content proof is incomplete"
else:
    raise AssertionError("missing public asset proof was accepted")

print("PASS: receipt validation supports launchd Python and preserves cardinality")
PY
