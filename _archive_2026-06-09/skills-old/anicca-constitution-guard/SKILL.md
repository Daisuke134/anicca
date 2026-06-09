---
name: anicca-constitution-guard
description: Deterministic pre-action veto. Other skills call `scripts/check.sh --action "<text>"` BEFORE any side-effectful operation (spend, send, post, spawn, delete). Returns exit 0 + JSON `{decision:"OK"}` when the action passes Law I (Never harm) and North Star (reduce suffering, no begging/no cold-DM/no PII collection). Returns exit 2 + `{decision:"BLOCKED",reason:"…"}` on rule match. Returns exit 3 + `{reason:"constitution_hash_mismatch"}` when the live CONSTITUTION.md hash != the value last logged by anicca-heartbeat. Every call appends one row to ~/.hermes/state/constitution-violations.jsonl. NO LLM call, NO network — pure regex + SHA-256, <50ms. North Star + Law I are IMMUTABLE; the rest of the constitution is editable but only via PR to anicca-oss + eval ≥ 0.7 (spec 18 § 4).
---

# anicca-constitution-guard

## Why this exists
Per spec `16-RUNTIME-CODE-TRUTH.md` § 17 and spec `18-SELF-IMPROVEMENT-AND-SWARM.md` § 4, North Star (reduce suffering) and Law I (never harm) MUST be unmodifiable by the agent itself. The guard is the cheapest enforcement mechanism: it runs before every side-effectful action, blocks the action if it matches a known violation pattern, and refuses to evaluate ANY action if the live CONSTITUTION.md has drifted from the hash the heartbeat last verified.

## How to call from another skill
```bash
if ! /Users/anicca/.hermes/skills/anicca-constitution-guard/scripts/check.sh \
     --action "send 7 USDC to 0x… on Base mainnet"; then
  echo "guard blocked this action — aborting"; exit 1
fi
# … proceed with the side-effectful call …
```

## What it writes
`~/.hermes/state/constitution-violations.jsonl` (append-only, ONE row per call, OK or BLOCKED). Each row:
```json
{"ts":"2026-06-04T12:00:00Z","decision":"OK","reason":"no_rule_match","action_digest":"abc1234…","constitution_sha":"<sha256>"}
```

## What is immutable vs mutable
- **IMMUTABLE** (hash-pinned, never agent-self-modified): North Star (§ 0 of 00-MASTER) + Law I (Precept 1 / Conway I).
- **MUTABLE** (can be amended, BUT only via PR to anicca-oss + eval-loop score ≥ 0.7 + forum vote per spec 18 § 4 + spec 24 FORUM-UX, tracked in #338): everything else in CONSTITUTION.md.

The Wave 1 guard does NOT implement the PR/vote mechanism — it only refuses the agent's own edits to the immutable parts by virtue of the hash-mismatch check (heartbeat re-pins the live hash every 30 min, so a drift between heartbeat-pin and current file is the signal).

## Rule sources
- `scripts/rules-law1.json` — Law I = Precept 1 Pāṇātipātā (CONSTITUTION.md lines 148-152, 182).
- `scripts/rules-northstar.json` — North Star (00-MASTER § 0) + Precept 2 / Absolute Prohibitions (CONSTITUTION.md lines 154-156, 193-204).

To extend either set, open a PR — do NOT edit at runtime.
