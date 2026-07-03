# profitable-article-writer

One wake → one deeply-researched, visual explainer article → per-platform native monetization → a real
money receipt verified with zero human in the runtime loop (Mode B). This document names no model,
provider, or API key: the skill runs on whatever frontier model the invoking agent already is.

Source spec: `.vcsdd/features/profitable-article-writer/specs/behavioral-spec.md` (REQ-1..16, EARS).
Source verification architecture: `.vcsdd/features/profitable-article-writer/specs/verification-architecture.md`
(PROP-1..15).

## What this skill does (per wake)

1. **Pick a niche/topic** (default: AI-entities). If no viable topic exists, or research would be
   insufficient for a genuinely useful piece, the wake SKIPS — it never emits a thin/slop article (REQ-4b).
2. **Research → decide** (theme, buy-reason-3-lines, free-vs-paid split: What is free, How is paid) →
   **write** (craft layer) → **de-slop**.
3. **Gate the draft**: V0 (render/slop) and V0.5 (a fixed, binary, reproducible craft checklist — REQ-5
   a-e: hook / CTA / payoff-cut / no-run-claims / mechanical readability). Any single FALSE criterion is a
   V0.5 FAIL. Up to 3 fix-and-re-gate rounds; the 4th failure ABORTS the wake with no publish (REQ-14).
4. **Mode A** (AUTONOMY=off, default): stop at a draft, notify the human (URL + screenshot) for review.
   This is an intentional, temporary, supervised bootstrap — it is NOT claimed to satisfy the zero-human
   invariant (REQ-6).
5. **Mode B** (AUTONOMY=on): publish directly, then distribute to reach platforms, with no human
   click/OTP/approval anywhere in the path (REQ-2, REQ-7).
6. **Monetize per rail's native mechanism** (single-purchase / paid subscription / ad-rev / paid
   subscriptions / paid books), with paywall-less rails treated as top-funnel into the paid rails and an
   owned email list (REQ-8).
7. **Verify earn** by climbing V0→V4: DONE for an earn unit is V4 — a real external receipt, confirmed by
   a deterministic anti-fake ledger check AND an independent read (never "it was published" — REQ-9).

## Interface (env-injectable, deterministic test mode)

The pipeline mirrors the founder-loop harness convention: a `_TEST` mode lets every branch be exercised
without a real agent call or network I/O.

| Env var | Meaning |
|---|---|
| `ARTICLE_DIR` | state directory: `STATE.md`, `state/accounts.json`, `state/failures.jsonl`, `state/PUBLISHED` |
| `AUTONOMY` | `on` = Mode B (autonomous publish); anything else (default `off`) = Mode A (draft + notify) |
| `ARTICLE_TEST=1` | deterministic test mode — injected values replace real research/craft/gate calls |
| `ARTICLE_TEST_TOPIC` | injected topic string; empty ⇒ no viable topic (REQ-4b SKIP) |
| `ARTICLE_TEST_RESEARCH` | `sufficient` \| `insufficient` (REQ-4b SKIP if insufficient) |
| `ARTICLE_TEST_V0_RESULTS` | comma list, one `PASS`\|`FAIL` per fix+re-gate round (REQ-14, max 3) |
| `ARTICLE_TEST_V05_RESULTS` | comma list, one `PASS`\|`FAIL` per fix+re-gate round (REQ-14, max 3) |
| `ARTICLE_TEST_MODE` | named deterministic scenario (e.g. `record_earn_only`) for isolated sub-path checks |

`STATE.md` fields written by a wake: `last_wake_result: SKIPPED|DRAFT|PUBLISHED|ABORTED`, `rounds_used`,
`draft_path`, `publish_url` (Mode B only), `notify_path` (Mode A only).

## Layout

```
skills/profitable-article-writer/
├── SKILL.md              this file
├── run.sh                1-wake entrypoint
├── lib/config.sh          declarative constants (loop cost-tier; no LLM in the earn/verify path)
├── gates/v0.sh             render/slop gate
├── gates/v05.sh            V0.5 fixed binary craft checklist gate
├── gates/publish-gate.sh   fail-closed publish wiring (V0 ∧ V0.5 ⇒ publish, else never)
├── identity/accounts.sh    per-install credential registry / self-create-or-flag
└── tests/                  VSDD RED-phase oracle tests, one file per proof obligation (PROP-*)
```

## Purity boundary

- **Deterministic tools**: `record-earn` ledger (reused from founder-loop), render/screenshot verify,
  platform publishers, dedup, git, payout routing.
- **Agent judgment** (the running model, never a hardcoded classifier): niche/topic pick, theme decision,
  buy-reason-3-lines, free/paid split, craft writing, V0.5 craft scoring, per-rail repurposing.
- **External side-effects** (guarded, live-verified): publish (note/X/Substack/Zenn/dev.to), payment
  receipt, account creation.

## Status

Phase 2a (RED). Every script under this directory is an intentionally-unimplemented stub — see the
`NOT_IMPLEMENTED` marker each one prints. Phase 2b (GREEN) implements the real pipeline behind this same
interface so the tests under `tests/` pass without modification.
