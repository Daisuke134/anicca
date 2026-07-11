#!/usr/bin/env python3
"""gig_judge.py — pure prompt-builder for the gig reality-verifier (feature gig-reality-verify,
増分2b: docs/loop-engineering/26-gig-loop-asis-tobe-plan.md §8). Copy+tweak of
browser-use/benchmark/judge.py (scratchpad/judge_bu.py, VERIFIED raw fetch, 198L,
docs/loop-engineering/25-...bp.md §7 for the exact lines this mirrors).

Deliberate departure from judge.py: judge.py builds `browser_use.llm.messages` objects for an
in-process LLM call. gig_judge is consumed by a *fresh spawned* `claude -p <prompt>` CLI process
(gig_reality_verify.sh), not an in-process LLM SDK call — so this module is a PURE STRING BUILDER
with NO network/LLM call and NO hard dependency on `browser_use`/`pydantic` (stdlib only), per
behavioral-spec REQ-001/REQ-003.

report-skeptical instruction text below is adapted verbatim-in-spirit from judge.py:
  - L148 "be initially doubtful of the agent's self reported success"
  - L101 "the agent reports that the action is completed but the screenshot or page shows the
          action is not actually complete: false"
  - L76  "If the ground truth is not satisfied ... the verdict MUST be false"
  - L90  "VERDICT GUIDELINES: true/false" (binary, not a rubric score — BP §2)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


DEFAULT_GROUND_TRUTH_URLS = [
    "https://coconala.com/mypage/services_lists",
    "https://coconala.com/mypage/received_orders/open",
    "https://coconala.com/mypage/dashboard_provider",
]


@dataclass
class JudgementResult:
    """Plain, dependency-free result shape (behavioral-spec REQ-003). Constructed from the JSON
    dict a fresh-spawned `claude -p` judge prints to stdout — never from pydantic (no browser_use
    dependency required at runtime)."""

    verdict: bool
    reasoning: str | None = None
    failure_reason: str | None = None
    impossible_task: bool = False
    reached_captcha: bool = False

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "JudgementResult":
        if "verdict" not in d:
            raise ValueError("JudgementResult.from_dict: missing required key 'verdict'")
        return cls(
            verdict=bool(d["verdict"]),
            reasoning=d.get("reasoning"),
            failure_reason=d.get("failure_reason"),
            impossible_task=bool(d.get("impossible_task", False)),
            reached_captcha=bool(d.get("reached_captcha", False)),
        )


def _format_claims(claims: list[dict[str, Any]]) -> str:
    if not claims:
        return "(no claims to verify this round — 0 claims found in the recent jsonl rows)"
    lines = []
    for i, c in enumerate(claims, 1):
        # preserve the claim verbatim as compact JSON-ish text so nothing (incl. Japanese/¥) is lost
        parts = ", ".join(f"{k}={v}" for k, v in c.items())
        lines.append(f"  {i}. {parts}")
    return "\n".join(lines)


def build_verifier_prompt(
    claims: list[dict[str, Any]],
    ground_truth_urls: list[str] | None = None,
) -> str:
    """Pure function — no I/O, no LLM call. Returns the prompt text a fresh `claude -p` process is
    given to independently judge whether `claims` (rows self-reported by the gig core in
    shuppin.jsonl / applied.jsonl / earnings.jsonl) are actually true on the real Coconala screen.

    Args:
        claims: recent claim rows (dicts) collected by gig_reality_verify.sh from the gig core's jsonl.
        ground_truth_urls: the real mypage screens to navigate and read as ground truth. If empty/None,
            the DEFAULT_GROUND_TRUTH_URLS (services_lists / received_orders/open / dashboard_provider)
            are used instead — verification is never silently skipped for lack of an explicit URL list.

    Returns:
        A single prompt string (task + report-skeptical judging instructions + response format),
        suitable to pass directly as the `claude -p "<prompt>"` argument.
    """
    urls = list(ground_truth_urls) if ground_truth_urls else list(DEFAULT_GROUND_TRUTH_URLS)
    urls_block = "\n".join(f"  - {u}" for u in urls)
    claims_block = _format_claims(claims)

    return f"""You are the Coconala gig loop's INDEPENDENT reality-verifier (fresh context, no memory
of the gig core's session). Your ONLY job this round is to judge, with a BINARY true/false verdict,
whether the CLAIMS below actually happened on the REAL Coconala screen — never trust the claims by
themselves.

<task>
Navigate the running CloakBrowser daily-driver (CDP :9222, already logged in as mtdc) to EACH of the
ground-truth URLs below. For each page, capture a screenshot via:
  python3 ~/anicca/skills/earn/gig/scripts/cdp_snapshot.py <pass_id> <seq> reality_verify_check
then read the ACTUAL rendered DOM/text (not the claim text) to see what is really there.
</task>

<ground_truth>
The following URLs are the GROUND TRUTH for this judgement. GROUND TRUTH VALIDATION (HIGHEST
PRIORITY): the ground truth takes ABSOLUTE precedence over the claims below. If what you actually
observe on these real pages does NOT satisfy a claim, the verdict for that claim MUST be false.
{urls_block}
</ground_truth>

<claims_to_verify>
{claims_block}
</claims_to_verify>

<evaluation_framework>
IMPORTANT: be initially doubtful of the gig core's self reported success — be sure to verify that
its claims are valid and match the real screen to a tee. This is the same report-skeptical standard
browser-use/benchmark's judge.py uses (be initially doubtful of the agent's self reported success).

- evaluate for action: for each claim, double check whether the claimed action (published a
  listing, delivered an order, settled ¥) actually happened on the real screen. If the required
  state did not actually occur, the verdict should be false.
- If a claim reports the action is completed but the actual screen shows it is not actually
  complete (e.g. still 下書き not 公開, still 取引中 not 納品済, no settled 売上 row): the verdict
  MUST be false for that claim, and therefore for this round.
- Money claims (jpy in earnings.jsonl) require the HIGHEST bar: only judge verdict:true for a money
  claim if you see actual settled evidence (検収完了/支払 + a real amount) on the real 売上/取引管理
  screen. A self-reported earnings.jsonl row alone is NEVER sufficient.
- If ground truth is not satisfied, the verdict MUST be false — ground truth is highest priority.
- Give a BINARY verdict: true or false. Do not produce a rubric score or partial credit — binary
  verdicts are more reliable than middling rubric scores (browser-use benchmark finding).
- If you hit a captcha/login wall that blocks verification, set reached_captcha true and verdict
  false (you could not verify, so do not assume success).
- If the claims list is empty, there is nothing to verify this round — still navigate the ground
  truth URLs, note the real current state, and set verdict true with reasoning noting no claims were
  pending (an empty round is not a failure).
</evaluation_framework>

<response_format>
Respond with EXACTLY this JSON object on stdout and NOTHING ELSE (no markdown fences, no extra text
before or after — the caller parses this line as JSON):

{{
  "reasoning": "<what you actually observed on each ground-truth page vs each claim>",
  "verdict": true or false,
  "failure_reason": "<why claims did not match the real screen, empty string if verdict is true>",
  "impossible_task": true or false,
  "reached_captcha": true or false
}}
</response_format>
"""
