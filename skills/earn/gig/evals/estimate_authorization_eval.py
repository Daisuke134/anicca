#!/usr/bin/env python3
"""Eval the REAL semantic judge against hand-authored estimate-authorization boundary cases.

Commit 10f28b0c deleted the deterministic classifier that used to decide whether a buyer's
latest message authorizes sending a paid Coconala estimate, and moved that judgement into
``requested_estimate.semantic_prompt`` run through ``requested_estimate.SemanticJudge`` --
a real model call. 91 regex tests died with the old classifier and nothing replaced them.
This eval is that replacement, for exactly one property:

    an unsolicited, ambiguous, negated, quoted, or already-refused buyer message must
    never authorize sending a paid estimate

It does NOT reimplement ``semantic_prompt`` or the judge -- it imports and runs the real
``requested_estimate.SemanticJudge``, the same class ``coconala_queue_snapshot.py`` builds
in production, against the same ``schemas/reply_semantic_judgement.schema.json`` and the
same ``agent_runner.py`` entrypoint. A case here is a synthetic DOM (buyer/seller turns,
no real talkroom, no real buyer) fed through that unmodified call path.

★ This costs real model calls. ★ ``SemanticJudge.__call__`` shells out to ``agent_runner.py``
once per case (with one same-process retry on a fast failure -- see requested_estimate.py),
which spends against the shared Claude subscription/proxy quota documented in this repo's
CLIProxyAPI setup. It refuses to run without ``--confirm-model-calls``, the same shape as
``ai-video-work/scripts/veo_generate.py``'s ``--confirm-billable``.

Usage
-----

    python3 evals/estimate_authorization_eval.py --confirm-model-calls

Output
------

One PASS/FAIL line per case to stdout, a summary, and a receipt JSON (default under
``--evidence-dir``) recording the case file's sha256, the runner path used, and every
per-case result -- expected, observed, the model's own stated reason, and any error --
so a run can be audited later without re-spending on it. Exits nonzero if any case fails.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import requested_estimate as estimate  # noqa: E402

DEFAULT_CASES = Path(__file__).resolve().parent / "estimate_authorization_cases.json"
DEFAULT_RUNNER = Path.home() / "profitable-claude/skills/agent-runner/agent_runner.py"
DEFAULT_SCHEMA = (
    Path(__file__).resolve().parents[1] / "schemas/reply_semantic_judgement.schema.json"
)
DEFAULT_EVIDENCE_ROOT = Path.home() / "gig/evidence/eval-estimate-authorization"

OWN_USER_PATH = "/users/seller"
BUYER_USER_PATH = "/users/buyer"

# Any of these means "the real call path did not produce an authorization" -- a case whose
# expectation is False still passes on one of these (nothing got authorized), but the
# error is recorded, because a model producing garbage is a different problem than a
# model correctly refusing.
JUDGE_FAILURE_TYPES = (
    estimate.SemanticJudgementError,
    estimate.collector.CollectorUnhealthy,
    estimate.subprocess.TimeoutExpired,
    OSError,
    RuntimeError,
)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(cases, list) or not cases:
        raise ValueError(f"{path} must hold a non-empty JSON array of cases")
    seen_ids = set()
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get("id"), str) or not case["id"]:
            raise ValueError(f"a case in {path} is missing a string id")
        if case["id"] in seen_ids:
            raise ValueError(f"duplicate case id {case['id']!r} in {path}")
        seen_ids.add(case["id"])
        if not isinstance(case.get("expected_authorizes"), bool):
            raise ValueError(f"case {case['id']!r} is missing boolean expected_authorizes")
        if not isinstance(case.get("messages"), list) or not case["messages"]:
            raise ValueError(f"case {case['id']!r} has no messages")
    return cases


def _dom_from_case(case: dict[str, Any]) -> dict[str, Any]:
    """Turn one case's plain {role, body} turns into the DOM shape semantic_conversation reads.

    Timestamps only need to be strictly increasing -- semantic_conversation and the judge
    read order and role, not wall-clock time.
    """
    rows = []
    for index, turn in enumerate(case["messages"]):
        role = turn.get("role")
        if role not in {"buyer", "seller"}:
            raise ValueError(f"case {case['id']!r} turn {index} has an unknown role {role!r}")
        body = turn.get("body")
        if type(body) is not str or not body.strip():
            raise ValueError(f"case {case['id']!r} turn {index} has no body")
        rows.append({
            "message_id": f"m{index}",
            "author_path": BUYER_USER_PATH if role == "buyer" else OWN_USER_PATH,
            "sent_at": f"2026-08-17T{index // 60:02d}:{index % 60:02d}:00+00:00",
            "body": body,
        })
    thread_id = case["id"]
    return {
        "url": f"https://coconala.com/mypage/direct_message/{thread_id}",
        "title": "メッセージ詳細",
        "container_present": True,
        "own_user_path": OWN_USER_PATH,
        "estimate_url": f"https://coconala.com/direct_offers/add/{thread_id}",
        "messages": rows,
    }


def _reason(judgement: dict[str, Any] | None) -> str | None:
    """The model's own stated reason, assembled from the schema fields that carry one.

    The schema has no free-text "why" field on purpose (semantic_prompt.py requires
    evidence message IDs instead of prose); this reconstructs a human-readable reason
    from conversation_state, uncertainty, and reply_audit, the fields that do carry one.
    """
    if judgement is None:
        return None
    parts = [f"conversation_state={judgement.get('conversation_state')}",
              f"next_action={judgement.get('next_action')}"]
    if judgement.get("uncertainty"):
        parts.append("uncertainty=" + "; ".join(judgement["uncertainty"]))
    audit = judgement.get("reply_audit") or {}
    for key in ("unanswered_questions", "unsupported_claims"):
        if audit.get(key):
            parts.append(f"{key}=" + "; ".join(audit[key]))
    return " | ".join(parts)


def run_case(judge: "estimate.SemanticJudge", case: dict[str, Any]) -> dict[str, Any]:
    dom = _dom_from_case(case)
    judgement: dict[str, Any] | None = None
    error: str | None = None
    observed_authorizes = False
    try:
        receipt = judge(dom, dom["url"])
        judgement = receipt["judgement"]
        projected = estimate.project_semantic_receipt(dom, dom["url"], receipt)
        observed_authorizes = bool(
            projected.get("next_action") == "requested_estimate"
            and projected.get("estimate_required") is True
        )
    except JUDGE_FAILURE_TYPES as caught:
        error = f"{type(caught).__name__}: {caught}"
    expected = case["expected_authorizes"]
    return {
        "id": case["id"],
        "description": case.get("description"),
        "expected_authorizes": expected,
        "observed_authorizes": observed_authorizes,
        "passed": observed_authorizes == expected,
        "reason": _reason(judgement),
        "error": error,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--confirm-model-calls", action="store_true",
                         help="required: this eval spends real model calls")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--runner", type=Path, default=DEFAULT_RUNNER)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--workdir", type=Path, default=Path.home())
    parser.add_argument("--evidence-dir", type=Path, default=DEFAULT_EVIDENCE_ROOT)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--receipt-out", type=Path, default=None,
                         help="default: <evidence-dir>/eval-receipt-<unix-ts>.json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if not args.confirm_model_calls:
        raise SystemExit("Refusing to spend model calls without --confirm-model-calls")

    cases_path = args.cases.expanduser().resolve()
    cases = load_cases(cases_path)
    cases_sha256 = _sha256_file(cases_path)

    evidence_root = args.evidence_dir.expanduser()
    evidence_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    judge = estimate.SemanticJudge(
        runner=args.runner.expanduser(),
        schema=args.schema.expanduser(),
        workdir=args.workdir.expanduser(),
        evidence_root=evidence_root,
        timeout_seconds=args.timeout_seconds,
    )

    results = [run_case(judge, case) for case in cases]

    for result in results:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"{status}  {result['id']}  expected={result['expected_authorizes']}"
              f" observed={result['observed_authorizes']}"
              f"{'  error=' + result['error'] if result['error'] else ''}")
        if result["reason"]:
            print(f"      reason: {result['reason']}")

    failures = [result for result in results if not result["passed"]]
    print(f"\n{len(results) - len(failures)}/{len(results)} cases passed")

    receipt = {
        "cases_file": str(cases_path),
        "cases_sha256": cases_sha256,
        "runner": str(args.runner.expanduser()),
        "schema": str(args.schema.expanduser()),
        "schema_sha256": judge.schema_sha256,
        "timeout_seconds": args.timeout_seconds,
        "run_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
        "results": results,
        "passed": len(failures) == 0,
    }
    receipt_path = args.receipt_out or (
        evidence_root / f"eval-receipt-{int(time.time())}.json"
    )
    receipt_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    receipt_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8",
    )
    print(f"receipt: {receipt_path}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
