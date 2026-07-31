# CORE-a / 8d fresh artifact-only review order

## Role and boundary

You are a fresh independent reviewer, not the builder. Review PR #330 and its committed artifacts only. Do not edit source/spec, commit, push, merge, deploy, rotate credentials, or rerun the production smoke. Read-only test execution is allowed. Never print secrets, auth headers, tokens, PII, or opaque URLs.

Working method (non-negotiable):
1. Restate the goal in one sentence + a "done means" criterion before acting.
2. Read the actual files before forming opinions; verify every path/function you reference exists in this project.
3. Name your riskiest assumption and check it first, while it is cheap.
4. The diff is a claim; execution is evidence. Run the project's build/lint/tests and report their real output.
5. Label claims VERIFIED (ran it) / REASONED (read it) / ASSUMED (unchecked) — never upgrade one silently.
6. Before finishing: re-read the original request; every requirement met, nothing promised-but-undone.

## Source of truth

- Repo: `/Users/anicca/anicca-project`
- Review worktree: `/Users/anicca/anicca-project/.worktrees/lm-p0-order8d`
- PR: `https://github.com/Daisuke134/anicca-products/pull/330`
- Head: `a22b6bd26d9403c70bc717538bdf420c1d04b56c`
- Base: `origin/dev`
- Spec: `docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md`, row `8d CORE-a` and §10.2–10.3
- Evidence: `.vcsdd/features/life-manager-daily-preflight/evidence/daily-preflight-20260721T055121Z.json`
- Builder result: 9 required dependencies, 7 pass, 2 fail, nonzero exit. Failures are Resend `GET /domains` HTTP 401 and Maps `directions_not_ready` after a Routes read succeeded.

Use CodeGraph before broad text search because `.codegraph/` exists. Use `gh` for GitHub and `crwl` or Context7 for external primary documentation. Keep command output compact.

## Review questions

1. Trace the actual production email-send path. Is Resend `GET /domains` a valid readiness proxy for the credential used by `POST /emails`? Verify API-key permission semantics from official Resend primary documentation. A restricted key must not be treated as ready unless a read-only check can prove the exact send capability without sending.
2. Trace the actual production travel/maps fallback. Does runtime require both Routes and legacy Directions, or accept either successful provider result? Compare that exact contract with the preflight implementation and evidence.
3. Confirm every declared dependency has success/failure/timeout contract coverage and every non-pass makes process exit nonzero. Confirm timeouts abort in-flight requests rather than only changing the reported status.
4. Confirm the smoke is read-only: no call dialing, email sending, calendar writes, Telegram notifications, location writes, or discovery sends.
5. Check redaction/serialization for secret, token, URL query, email address, phone, chat ID, and provider response leakage. The committed evidence must contain no reusable secret or raw PII.
6. Confirm Telegram webhook, Composio calendar, Telnyx call readiness, location freshness, discovery state, Gemini model, and Maps checks match the dependencies used by the real DAILY runtime rather than merely returning HTTP 200.
7. Run the targeted unit tests and the smallest relevant full verification. Report exact command, exit code, pass/fail count, and coverage if available. Do not run production smoke.
8. State whether PR #330 can merge as-is. Treat spec row `8d` as pending unless all production dependencies are truthfully green with reproducible L1/L2/L3 evidence.

## Required output

End stdout with this compact block:

```text
FINAL_VERDICT: PASS | FAIL
MERGE: YES | NO
BLOCKERS: <count>
FINDINGS:
- [severity] file:line — finding — required correction
VERIFICATION:
- <command> => exit <n>, <result>
PRIMARY_SOURCES:
- <title> | <url> | <one-sentence supporting fact>
```

If there are no blockers, say `BLOCKERS: 0`. Do not mark 8d done and do not modify the PR.
