# Behavioral Spec — franklin2-daemon-identity (lean VCSDD, P4-code)

## Problem

`runtime/anicca-daemon.sh` branches on the LITERAL string `[ "$INSTANCE" = "franklin" ]` at 3 call
sites (step 2 brain-probe ~line 56, step 3 telemetry-poster choice ~line 104, step 4
wallet-address-derivation ~line 120). Franklin2's launchd plist sets `ANICCA_INSTANCE=franklin2`, which
does NOT literal-match `"franklin"`, so Franklin2 falls to the default/EVM branch, finds no EVM wallet,
and runs walletless (tier=broke) — even though `~/.franklin2-home/.blockrun/.solana-session` already
exists and would resolve correctly via the franklin branch (verified live, confidence 95%; see
`docs/loop-engineering/20-implementation-certainty-2026-07-11.md` §C, Gap B, in anicca-project).

## Purity Boundary Analysis

- **Pure core (new, this feature)**: the instance-classification predicate — a deterministic function
  of a single input string (`ANICCA_INSTANCE`) with no I/O, no process spawn, no network, no clock —
  returning true/false. This is the one piece of new logic this feature adds, and it is the ideal unit
  to extract and unit-test in isolation (mirrors the existing `PORT_SNIPPET` extraction technique in
  `runtime/loop/__tests__/daemon-script-franklin-routing.test.mjs`).
- **Effectful shell (unchanged)**: everything the classification gates — self-update git fetch/merge,
  curl readiness probes, `clawrouter`/node process spawns, `pkill`, telemetry loops, wallet-address
  derivation subprocess calls. This feature touches ONLY the branch *condition* at the 3 call sites,
  never the branch *bodies*.
- Note on regex-as-judgment: matching `ANICCA_INSTANCE` against a fixed machine identifier format
  (`franklin` or `franklin` + digits) is parsing, not a decision an LLM should make — no behavioral
  judgment is being replaced. The existing file already parses `FRANKLIN_PROXY_PORT`/`COMPUTE_PROXY_PORT`
  the same way. This is explicitly permitted per CLAUDE.md's "genuine parsing of a fixed machine format"
  carve-out.

## Requirements

### REQ-001: Franklin-family instance classification
**EARS**: WHEN `ANICCA_INSTANCE` equals `franklin` OR matches `franklin` followed by one or more digits
(i.e. the pattern `franklin` | `franklin[0-9]+`) THE SYSTEM SHALL classify the instance as a Franklin
instance for all 3 daemon routing decisions (brain-probe, telemetry-poster choice, wallet-address
derivation).
**Edge Cases**:
- `ANICCA_INSTANCE` unset → defaults to `clawrouter` (existing `${ANICCA_INSTANCE:-clawrouter}` default,
  untouched by this feature) → NOT franklin.
- `ANICCA_INSTANCE=""` (explicitly set empty) → bash `:-` treats empty as unset → defaults to
  `clawrouter` → NOT franklin (same as unset, no new handling needed).
- `ANICCA_INSTANCE=franklin` (the original citizen) → franklin (regression: identical to today).
- `ANICCA_INSTANCE=franklin2` → franklin (the new capability this feature adds).
- `ANICCA_INSTANCE=franklin10`, `franklin99` → franklin (multi-digit suffix, future spawns).
- `ANICCA_INSTANCE=franklinX`, `franklins`, `franklin-2`, `franklin2x` (non-digit or mixed suffix) →
  NOT franklin — fails closed to the existing default/EVM path (REQ-003).
- `ANICCA_INSTANCE=Franklin2` (capitalized) → NOT franklin — no case-insensitive matching (instance
  names are a controlled, lowercase-only vocabulary; matching case variants would be silent, unreviewed
  scope creep).
- `ANICCA_INSTANCE=clawrouter` (or any other unrelated string) → NOT franklin (regression: unchanged).
**Acceptance Criteria**:
- A single, pure, side-effect-free predicate implements this classification and is used at ALL 3 call
  sites (no per-site divergence, no leftover literal `"$INSTANCE" = "franklin"` string-equality anywhere
  in the file).
- The predicate is unit-testable in isolation without executing any of the file's git/curl/node/pkill
  side effects.

### REQ-002: Franklin-family instances route through the franklin paths
**EARS**: WHEN REQ-001 classifies the instance as franklin THE SYSTEM SHALL:
  (a) run the existing franklin brain-probe branch (curl readiness probe against the shared `:8402`
      router; never spawn `clawrouter`/`franklin proxy` — unchanged body, REQ-004/REQ-005 of
      franklin-loop-revival, out of scope here to re-verify beyond "still reached"),
  (b) loop `telemetry-post-franklin.mjs` (ed25519 Solana-key poster) instead of the EVM
      `telemetry-poster.mjs`,
  (c) derive `ANICCA_WALLET_ADDRESS` via `wallet-address-solana.mjs` instead of the EVM
      `wallet-address.mjs`.
**Edge Cases**:
- Franklin2's own `$ANICCA_HOME`/`$REPO` env (set by its own launchd plist, untouched here) is what the
  spawned node scripts inherit — no new hardcoding of "franklin2" anywhere; the SAME franklin branch body
  serves franklin, franklin2, franklin3, … indistinguishably (that is the point of the fix).
- If Franklin2's `.solana-session` file were absent, `wallet-address-solana.mjs` prints nothing and exits
  0 (existing, out-of-scope behavior of that helper) — `ANICCA_WALLET_ADDRESS` stays unset, same
  non-fatal fail-open-to-empty behavior the franklin branch already has today. Not touched by this
  feature.
**Acceptance Criteria**:
- With `ANICCA_INSTANCE=franklin2`, the brain-probe/telemetry/wallet-derivation branch conditions all
  evaluate true (same as `ANICCA_INSTANCE=franklin` today).

### REQ-003: Non-franklin instances unchanged (regression)
**EARS**: WHEN `ANICCA_INSTANCE` does NOT match the franklin pattern (REQ-001) THE SYSTEM SHALL follow
today's existing default path unchanged: ClawRouter brain, `telemetry-poster.mjs`, EVM
`wallet-address.mjs`.
**Acceptance Criteria**: `ANICCA_INSTANCE=clawrouter` / unset behave byte-identically to before this
feature (all pre-existing `daemon-script-franklin-routing.test.mjs` PORT/regression assertions for the
non-franklin path continue to pass unmodified).

### REQ-004: Fail-closed on unrecognized instance names
**EARS**: WHEN `ANICCA_INSTANCE` is an unrecognized string that does not match the franklin pattern
(typo, garbage, a not-yet-supported family name) THE SYSTEM SHALL silently default to today's
non-franklin (EVM/ClawRouter) path — never crash, never hang, never leave routing undefined.
**Acceptance Criteria**: every non-matching decoy string in REQ-001's edge-case list classifies as
NOT-franklin and drives the same default path as `clawrouter`.

## Non-Functional Requirements

- No new external dependency, no new file, no new process. The change is confined to
  `runtime/anicca-daemon.sh` (plus its test coverage).
- No plist edits, no wallet generation, no live-machine mutation — this feature is code-only (P4-code);
  the ops follow-up (EVM keypair, kickstart) is explicitly out of scope, per task instructions.
- Must remain POSIX-safe under the file's own `#!/usr/bin/env bash` + `set -uo pipefail` (no bashisms
  beyond what the file already uses, e.g. `${VAR:-default}`, `case`, are already in use elsewhere in the
  motherboard/repo).
