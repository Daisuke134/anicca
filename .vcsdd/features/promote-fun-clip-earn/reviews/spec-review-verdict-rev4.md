# VCSDD Phase 1c — Adversary Spec Review Verdict (RE-REVIEW of REV 4)

- Feature: `promote-fun-clip-earn`
- Spec reviewed: `.vcsdd/features/promote-fun-clip-earn/specs/spec.md` (content = REV 4; header still self-labels "REV 3" — see FIND-401)
- Mode: lean | Reviewer: fresh-context adversary (disk-only, zero builder context)
- **OVERALL VERDICT: PASS** (5 / 5 dimensions PASS — 0 critical, 0 major, 3 minor)

> Scope: (A) did REV 4 actually close FIND-301 / FIND-302 / FIND-303 against the REAL files on disk?
> (B) did the two previously-PASSED dimensions (Spec Fidelity, Structural Integrity) regress?
> (C) did REV 4 introduce any NEW flaw? Every cited file:line below was opened and confirmed.
> **All three REV-3 MAJOR findings are closed and verified against the actual lib + harness code.**
> Three MINOR documentation/precision defects remain; none blocks building → OVERALL PASS.

---

## REV-3 finding closure check (verified against disk — NOT a positive summary)

| REV-3 finding | Closed? | Disk evidence confirming closure |
|---|---|---|
| FIND-301 (RECORD wake inherits PII env → `assertOwnIdentityOnly` throws → DONE silently never fires; scrub duty assigned to no component) | **YES** | Spec §3a (spec.md:58-68) now assigns the duty explicitly to `run.sh`: `env -i PATH HOME SOLANA_RPC_URL EARN_LEDGER node <record.mjs> '<json>' "$LEDGER"`. **Traced against real code**: `record.mjs:19` calls `assertOwnIdentityOnly(line)` (no env override) → `identity-guard.mjs:86-88` reads `process.env` → `findUserPIIEnv` (`:54-58`) tests keys against `USER_PII_ENV_PATTERNS` (`:17-25`). Under `env -i {PATH,HOME,SOLANA_RPC_URL,EARN_LEDGER}` NONE of those keys match any PII pattern → returns `null` → no throw → append proceeds. Harness premise confirmed: `run-skill.mjs:80` builds child env via `scrubPrivateKeys(process.env)` which (`env-filter.mjs:15,28-37`) strips ONLY `*_WALLET_KEY/_PRIVATE_KEY/_PRIV_KEY` and FORWARDS PII — so the `run.sh`-level `env -i` is genuinely necessary and correctly placed. Regression test (spec.md:66-68) exercises BOTH directions (with-`env -i` records; direct call with the PII var throws). |
| FIND-302 (per-step watchdog hard-claims `/opt/homebrew/bin/timeout`; coreutils ships `gtimeout`; test non-constructible) | **YES** | REQ-9 (spec.md:148-157) no longer hard-claims a path: `TIMEOUT_BIN="$(command -v timeout || command -v gtimeout)"` + a pure `node`/`python3`-SIGTERM fallback IF NEITHER exists; each IO step runs `"$TIMEOUT_BIN" "$STEP_DEADLINE_S" <cmd>`; constructible test `"$TIMEOUT_BIN" 1 sleep 5` → 124 (or `STEP_DEADLINE_S=1` + a `sleep 5` step). Corroborated: existing production slots already use bare `timeout` (`earn/video/run.sh:48,75,99,134,139`; `earn/gig/run.sh:91,104,128`), so `timeout` resolves on PATH in this runtime; the `command -v` form is portable and also covers the absence case. |
| FIND-303 (`usdcDeltaForSig` silent on absent-pre — the EXACT acceptance case where first inbound creates the ATA) | **YES** | Spec item 4 (spec.md:76-81) now states verbatim: "find the matching `preTokenBalances` entry **by `accountIndex`**; **if no matching pre entry exists, pre = 0** (this IS the acceptance case…)" and REQUIRES a first-inbound test fixture (post present, NO pre → delta = full post amount). Matches the real Solana `getTransaction` jsonParsed shape (pre/postTokenBalances each carry `accountIndex`, `owner`, `mint`, `uiTokenAmount`); the `owner === wallet` filter and `accountIndex` pairing are well-defined on that shape. |

---

## Dimension 1 — Spec Fidelity: **PASS** (no regression)

The REQ↔lib mapping that PASSED in REV 3 is unchanged and still faithful; REV 4 only edited §3a, item 4,
and REQ-9, none of which break the mapping:
- REQ-8's persisted line (spec.md:138-143) carries `{sig, confirmed:true, chain, source:"promote.fun",
  external:true, earn_usdc>0, wallet}`. The REV-4 `env -i` command passes `wallet` via the JSON arg (not
  env), consistent with `deriveLine` reading `o.wallet` (`ledger.mjs:16`) — so dropping a `WALLET` env var
  from the allowlist loses nothing.
- Exactly ONE recorder remains authoritative (`record.mjs` → `ledger.mjs`); the Python recorder stays
  excluded (spec.md:33-40).
- Evidence reviewed: spec.md:16-68,138-143; `record.mjs:8,14-22`; `ledger.mjs:11-49`; `identity-guard.mjs:30-51`.

## Dimension 2 — Edge Cases: **PASS** (FIND-303 closed)

The absent-pre-balance edge — the very transaction the acceptance gate depends on — is now explicit
(spec.md:76-81) and carries a mandated first-inbound test fixture. The symmetric `usdcBalance` "returns 0
when the ATA does not exist" rule (spec.md:82-84) is now matched by the `usdcDeltaForSig` pre=0 rule, so the
two are consistent. No remaining unhandled boundary in the delta computation.
Evidence: spec.md:76-84,189-191.

## Dimension 3 — Implementation Correctness: **PASS** (FIND-301 closed)

The silent-DONE-block class is closed and the fix is feasible against the real code:
- `record.mjs` (`:6-22`) imports only `ledger.mjs` (uses `fs`/`path`, no env) and `identity-guard.mjs`
  (reads `process.env` solely for the PII scan). It reads the ledger path from `argv[3]` and the wallet
  from the JSON input — so `env -i PATH HOME SOLANA_RPC_URL EARN_LEDGER` strips NO variable record.mjs needs
  and yields a PII-free `process.env`, allowing `assertOwnIdentityOnly` to pass and the append to fire.
- No conflict with REQ-12 "reads wallet from env": the wallet (public base58) travels in the JSON arg, and
  the Solana RPC-verification step (which needs `SOLANA_RPC_URL`/network) is a SEPARATE step that does NOT
  call `assertOwnIdentityOnly`, so it need not run under `env -i` — no cross-step break.
- No cross-wake break: `env -i` wraps ONLY the `record.mjs` subprocess; the LOGIN/CLIP steps in `run.sh`
  keep full env (OTP/Gmail/Composio), so login wakes are unaffected (spec.md:64-65).
Evidence: spec.md:58-68,138-143,163-166; `record.mjs:6-22`; `identity-guard.mjs:54-58,86-97`;
`env-filter.mjs:15,28-37`; `run-skill.mjs:80-101`.

## Dimension 4 — Structural Integrity: **PASS** (no regression)

- Solana adapter still lives in `_shared/lib/solana-verify.mjs` beside the EVM siblings; ONE recorder; the
  new slot mirrors `earn/video/` and its `decide.py` mirrors the genuinely PURE `earn/video/decide.py`
  (confirmed pure: decision-only, no I/O, `earn/video/decide.py:23-43`).
- The REV-3 non-blocking note (harness `run-skill.mjs:82` injects earn-slot env only for `slot==='earn'`,
  so a `clip-promote` wake falls to the generic branch `:101`) is now NEUTRALIZED by REV-4: `record.mjs`
  receives its ledger path from `argv[3]` in `run.sh`'s own `env -i` command, not from a harness-injected
  `EARN_LEDGER`. So the spec no longer depends on the harness branch it never matched.
- Evidence: spec.md:25,29-30,58-68; `earn/video/decide.py:23-43`; `run-skill.mjs:82,101,109-115`.

## Dimension 5 — Verification Readiness: **PASS** (FIND-302 closed; FIND-301/303 DONE-checks runnable)

- FIND-302: the per-step no-human watchdog is now portably constructible (`command -v timeout ||
  command -v gtimeout` + pure fallback, spec.md:148-152) with a runnable 124-test (spec.md:156-157). The
  existing production slots' bare `timeout` usage corroborates PATH availability.
- FIND-301: the DONE acceptance check (`record.mjs`-persisted line satisfies `isProfitable`, spec.md:189-191)
  is now runnable end-to-end because the RECORD subprocess runs under a PII-free env.
- FIND-303: the DONE check `usdcDeltaForSig(sig,wallet) > 0` (spec.md:189) is now runnable for the
  first-inbound/ATA-creating tx via the explicit pre=0 rule + mandated fixture.
- Lib regression gate preserved (spec.md:90-93,194-195): extend `__tests__/ledger.test.js` (real guards at
  `ledger.test.js`) with Solana cases + full-suite green.

---

## Minor findings (do NOT block the build; fix opportunistically)

- **FIND-401 (MINOR, structural / doc).** The spec's title (spec.md:1) and intro (spec.md:3) still self-label
  "REV 3" and describe closing "the REV-2 re-review findings," yet the body already contains the REV-4 fixes
  (§3a `[FIND-301]`, item 4 absent-pre `[FIND-303]`, REQ-9 `TIMEOUT_BIN` `[FIND-302]`). The on-disk revision
  label disagrees with the on-disk content. Bump the header to REV 4 + add a one-line REV-4 changelog so the
  artifact's revision is unambiguous. Evidence: spec.md:1-4 vs spec.md:58-68,76-81,148-157.
- **FIND-402 (MINOR, precision).** Field-path naming is inconsistent for the Solana token-balance amount:
  item 4 writes `post.uiAmount − pre.uiAmount` (spec.md:80) while `usdcBalance` writes `tokenAmount.uiAmount`
  (spec.md:83); the real jsonParsed pre/postTokenBalances field is `uiTokenAmount.uiAmount` (and `uiAmount`
  can be `null` — `uiAmountString` is the always-present form). A builder can resolve this, but the spec
  should name the exact field path to avoid a null-`uiAmount` miscompute. Evidence: spec.md:80,83.
- **FIND-403 (MINOR, dead var).** The `env -i` allowlist includes `EARN_LEDGER="$LEDGER"` (spec.md:63), but
  `record.mjs` reads the ledger from `argv[3]` (`record.mjs:28`), not from `process.env.EARN_LEDGER` —
  the env var is unused by record.mjs (harmless, matches no PII pattern). Drop it or wire record.mjs to read
  it, for clarity. Evidence: spec.md:63; `record.mjs:14,28`.

---

## Conclusion

REV 4 closes all three REV-3 MAJOR findings (FIND-301 / FIND-302 / FIND-303), each verified against the real
`record.mjs` / `identity-guard.mjs` / `ledger.mjs` / `run-skill.mjs` / `env-filter.mjs` code and the real
`getTransaction` jsonParsed shape. Neither previously-PASSED dimension regressed; no NEW critical/major flaw
was introduced. Three MINOR defects remain (stale revision label, token-amount field-path precision, one dead
env var) — none blocks building. **OVERALL: PASS.**
