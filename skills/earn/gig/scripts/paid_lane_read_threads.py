#!/usr/bin/env python3
"""Build the readback map from evidence the pass already wrote — spec §0.1.6 (P1a-9c).

Every time the delivery path sends into a paid room it persists
`paid-queue-live-dom.json`. With the ordered messages now included in that file, the
liability lane can prove "our answer sits below theirs" by reading it, instead of opening
the room a second time to ask the same question.

Reading evidence rather than driving the browser is the point, not a shortcut. A second
observation would need a second lease on the shared CDP tab, would happen at a different
moment, and could therefore disagree with the one the send actually produced. It would also
let the observer see things the loop never recorded — and an observer that can manufacture a
readback the loop never earned is exactly the failure mode this lane exists to remove.

Absence is not evidence of an answer. A pass that sent nothing yields an empty map, a file
predating the ordered-messages field yields `seller_after_buyer: False`, and a file that
cannot be parsed becomes an error rather than a silent omission.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

_HERE = Path(__file__).resolve().parent
_EVIDENCE_NAME = "paid-queue-live-dom.json"


def _paid_thread_state():
    spec = importlib.util.spec_from_file_location(
        "paid_thread_state", _HERE / "paid_thread_state.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_thread_states(
    evidence_dir: Path | str, *, with_errors: bool = False
) -> dict[str, Any] | tuple[dict[str, Any], list[str]]:
    """Map talkroom_id to observed state, from every live-dom file under this evidence dir."""
    module = _paid_thread_state()
    states: dict[str, Any] = {}
    errors: list[str] = []

    for path in sorted(Path(evidence_dir).rglob(_EVIDENCE_NAME)):
        try:
            dom = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"{path}: unreadable ({exc.__class__.__name__})")
            continue

        talkroom_id = urlparse(str(dom.get("url") or "")).path.rstrip("/").rsplit("/", 1)[-1]
        if not talkroom_id:
            errors.append(f"{path}: no talkroom id in url {dom.get('url')!r}")
            continue

        try:
            states[talkroom_id] = module.paid_thread_state(dom, talkroom_id)
        except module.NotAPaidTalkroom as exc:
            errors.append(f"{path}: {exc}")

    return (states, errors) if with_errors else states


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", required=True)
    args = parser.parse_args(argv)

    states, errors = read_thread_states(args.evidence_dir, with_errors=True)
    print(
        json.dumps(
            {
                "thread_states": states,
                "rooms_observed": len(states),
                "errors": errors,
                "answered": sorted(k for k, v in states.items() if v.get("seller_after_buyer")),
            },
            ensure_ascii=False,
        )
    )
    # Unreadable evidence is a real problem, but it must not stop the pass from disposing the
    # liabilities it can still account for.
    return 0



_MANIFEST_NAME = "paid-queue-evidence.json"


def read_intents(evidence_dir: Path | str) -> dict[str, str]:
    """Map talkroom_id to what the pass meant to do, from its own send manifests.

    Only a manifest that reports `sent` counts. "We prepared a message" is not "we spoke",
    and treating the two as equal is how a customer waits while the ledger says otherwise.
    """
    intents: dict[str, str] = {}
    for path in sorted(Path(evidence_dir).rglob(_MANIFEST_NAME)):
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not manifest.get("sent"):
            continue
        talkroom_id = str(manifest.get("talkroom_id") or "")
        if not talkroom_id:
            continue
        intents[talkroom_id] = (
            "formal_delivery" if manifest.get("formal_delivery_checkbox") else "answer"
        )
    return intents

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
