#!/usr/bin/env python3
"""Run one sealed marketplace form intent through the common Terra browser ACI."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
GIG_ROOT = HERE.parent
DEFAULT_RUNNER = GIG_ROOT / "agent-runner/agent_runner.py"
DEFAULT_SCHEMA = GIG_ROOT / "schemas/gig_step_result.schema.json"
DEFAULT_EVIDENCE = Path.home() / "gig/evidence/market-form-operator"


def operate(
    *, provider: str, resource_id: str, form_url: str, sealed_intent: dict[str, Any],
    cdp_base: str,
    runner: Path = DEFAULT_RUNNER, schema: Path = DEFAULT_SCHEMA,
    evidence_root: Path = DEFAULT_EVIDENCE,
) -> dict[str, Any]:
    evidence = evidence_root / f"{time.time_ns()}-{provider}-{resource_id.lstrip('~')}"
    evidence.mkdir(parents=True, exist_ok=False, mode=0o700)
    intent = json.dumps(sealed_intent, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    cdp_base = cdp_base.rstrip("/")
    if not cdp_base.startswith(("http://127.0.0.1:", "http://localhost:")):
        raise ValueError("market_form_operator_requires_local_cdp")
    prompt = f"""Execute one already-authorized marketplace form intent using the current authenticated
browser at EXACT_CDP_ENDPOINT={cdp_base}. Provider={provider}; resource={resource_id}; target={form_url}.
SEALED_INTENT={intent}

Inspect the live page yourself. Open or locate the exact target, understand its current form, fill every
required field from SEALED_INTENT, answer screening questions exactly, handle ordinary validation and
UI feedback, review the final values, and submit exactly once. Do not use hardcoded provider selectors,
do not edit code, do not invent facts, do not change price/scope/content, and do not buy, boost,
subscribe, alter account settings, or open another opportunity. Ordinary navigation and non-financial
acknowledgements are allowed. CAPTCHA, identity, tax and personal legal declarations are blocked.
If a controlled input appends instead of replacing, stop retrying keystrokes: use its native prototype value setter,
dispatch input and change events, blur, then read the live value back. If any live term differs from SEALED_INTENT,
you must not submit. Provider account balances are live observations, not immutable terms: use the current value and
block only when the required charge exceeds the live balance or the provider increased that charge.
A post-submit remaining balance is not the current balance. When the provider shows both numbers, reconcile
current balance = required charge + post-submit remaining balance; do not block merely because the remaining-after
value is lower than the required charge.
When an otherwise optional add-on is validated as required but SEALED_INTENT requests none, choose the provider's
explicit None, Never, or No option; never invent a positive add-on term.
Return ok only after the provider visibly leaves the editable form or shows provider-authored success;
the parent will independently verify the official ID and balance, so never claim those from inference."""
    prompt += """
Use only the provider-owned authenticated persistent DEFAULT browser context already running at the
exact endpoint above. Do not inspect, guess, or use any other CDP endpoint or port. Create a new tab in
that default context when needed. Never create an
isolated/incognito context, never launch another browser/profile, and never perform session restoration
or login; a login redirect means blocked. The installed common Browser ACI is already configured through
BU_CDP_URL and BU_NAME. Run `browser-harness skill` once, then use `browser-harness` with Python on stdin.
Do not search the filesystem for its SKILL.md, search for browser libraries, or build a raw CDP client."""
    environment = os.environ.copy()
    environment.update({"BU_CDP_URL": cdp_base, "BU_NAME": f"market-form-{provider}"})
    completed = subprocess.run([
        sys.executable, str(runner), "--task-class", "browser-lane-agent", "--prompt-stdin",
        "--schema", str(schema), "--evidence-dir", str(evidence),
        "--task-label", "market-form-effect", "--loop", "gig",
        "--workdir", str(Path.home()), "--timeout-seconds", "900",
    ], input=prompt, text=True, capture_output=True, timeout=930, check=False,
       env=environment)
    if completed.returncode != 0:
        raise RuntimeError("market_form_operator_failed")
    summary = json.loads((evidence / "summary.json").read_text(encoding="utf-8"))
    result_path = Path(str(summary.get("result_path") or "")).resolve()
    result_path.relative_to(evidence.resolve())
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result.get("status") != "ok":
        raise RuntimeError("market_form_operator_not_ok")
    for path in evidence.rglob("*"):
        if path.is_file() and not path.is_symlink():
            os.chmod(path, 0o600)
    return result
