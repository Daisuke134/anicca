# verification-architecture.md — gig-reality-verify (VCSDD-lean)

## Purity Boundary Map
- **Pure Core**: `gig_judge.py::build_verifier_prompt(claims, ground_truth_urls)` — deterministic
  string construction, no I/O, no side effects, fully unit-testable. `gig_judge.py::JudgementResult`
  (dataclass) — deterministic construction/validation from a dict.
- **Effectful Shell**: `gig_reality_verify.sh` (file I/O on `~/gig/*.jsonl`, subprocess spawn of a
  fresh `claude -p` which itself drives CDP :9222 browser + LLM inference + `cdp_snapshot.py`
  screenshot capture, writes `~/gig/audit-reality.jsonl` and
  `~/.openclaw/state/.gig-core-selfheal-request.json`). `auditor.sh` (orchestration, unchanged
  deterministic part + new call to the effectful shell).

## Proof Obligations

| ID | Description | Tier | Required | Tool |
|----|-------------|------|----------|------|
| PROP-001 | `build_verifier_prompt` is pure (same inputs → same output, no I/O) | 1 | true | python unit test (manual assertions, no framework dep) |
| PROP-002 | Prompt contains report-skeptical phrases (doubtful, ground truth, mismatch→false) | 0 | true | string-containment test |
| PROP-003 | `JudgementResult.from_dict` round-trips minimal valid dict; raises on missing `verdict` | 1 | true | python unit test |
| PROP-004 | `gig_reality_verify.sh` is syntactically valid bash | 0 | true | `bash -n` |
| PROP-005 | `gig_reality_verify.sh` stdout is JSON-only (structural check on script source: work/logging goes to `>&2` / a log file, not bare `echo` to stdout mid-script) | 0 | true | grep/static review (documented in test, not a runtime harness — see "Verification Strategy" below) |
| PROP-006 | `auditor.sh` deterministic block is unchanged (regression) + calls the new script after it | 0 | true | diff / grep ordering check |
| PROP-007 (full E2E, live) | fresh `claude -p` judge, run against the REAL live 3 published listings, returns `verdict:true` and a JSON row lands in `~/gig/audit-reality.jsonl` | 1 | true (best-effort within session budget; if not run, explicitly disclosed as unexecuted — never fabricated) | live run of `gig_reality_verify.sh` against :9222 |

## Verification Strategy
- **Tier 0** (no formal proof needed): shell syntax validity (`bash -n`), static structural greps
  (flag presence, ordering, stdout-cleanliness pattern), report-skeptical phrase presence in the
  prompt string. Deterministic, cheap, exhaustive by direct read.
- **Tier 1** (property/example-based tests, plain Python asserts — this repo's existing convention
  per `skills/self/tests/test_gig_ts_parser.py`, not pytest/hypothesis): purity of
  `build_verifier_prompt` (same input twice → identical output, no side effects observable),
  `JudgementResult` dict round-trip + required-field enforcement.
- **Tier 2**: not applicable — no numeric/algorithmic invariant needing lightweight formal methods
  here (this is prompt-construction + shell orchestration, not a computation with mathematical
  properties).
- **Tier 3**: not applicable — no safety-critical concurrency/protocol requiring strong formal proof.
- **Live E2E (out-of-band from unit Tiers, BP-mandated)**: the true acceptance bar for this feature —
  per `docs/loop-engineering/26-...md` §8 — is that a *fresh spawned* `claude -p` process, given the
  real 3 live published Coconala listings as claims, independently reaches `verdict:true` by
  navigating :9222 and reading the real DOM (not by trusting jsonl text). This is executed as a real
  side-effecting run (subprocess + LLM + browser), documented honestly in the Green-phase evidence
  whether it was run to completion within this session or not (no fabricated PASS —
  `feedback_i_am_the_final_verifier_never_claim_earning_without_external_tx`,
  `feedback_never_claim_working_without_own_eyes_verification`).
