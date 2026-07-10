# Verification Report — franklin-earn-foundation (lean)

Feature: sol-trade P&L recording + per-instance identity safety (REQ-001 EVM wallet-leak fix,
REQ-002 sol-trade realized P&L recording). Fix commit: `3fe382b` (closes 6 adversary blocking
findings). All paths under `/Users/anicca/anicca/`.

## Tests (Phase 2a/2b)
Real GREEN output in `evidence/sprint-1-green-phase.log`; RED baseline in `evidence/sprint-1-red-phase.log`.
- `parse-pass.test.mjs` 5/5 pass (extractLastSignature: LAST sig, ANSI-strip, multi-sig, never-throw)
- `record-swap.test.mjs` 8/8 pass (records win OR loss; NEVER external:true; verify-error path appends nothing; earn_usdc/cost_usdc present)
- `tests/test_run.sh` 9/9 pass — hermetic bash integration (PROP-011..016): Franklin PROCEED+record, non-owner HALT (no CLI call, no ledger write), ambient key does NOT bypass, multi-sig records LAST, verify-error degrades to trace-only
- regression: `identity-guard.test.js` 12/12 pass (unchanged)

## Adversary (Phase 3, fresh Opus, two iterations)
- iteration-1 (`reviews/impl/iteration-1/`): FAIL, 6 blocking findings (FIND-001 ambient-key guard bypass [money-safety]; FIND-002 parse-pass.mjs missing; FIND-003 first-not-last sig; FIND-004 external:true vs own test; FIND-005 no integration tests; FIND-007 no verify-error trace). All independently reproduced by the parent before fixing.
- iteration-2 (`reviews/impl/iteration-2/`): **PASS, 0 blocking**. All 6 CLOSED (static trace + independent test-count re-derivation + call-graph trace confirming the integration suite is genuine, not tautological). 3 new findings, all non-blocking/low (cosmetic / stricter-than-spec, no money-safety impact).

## Real-chain E2E (record-swap against a REAL 8Fpqd on-chain signature)
`verification/security-results/realchain-e2e.log`: fetched a real signature from Franklin's wallet
8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9 via getSignaturesForAddress, ran record-swap.mjs under
`env -i` against a scratch ledger → `status:"recorded", net_usdc:-0.008664, earn_usdc:0,
cost_usdc:0.008664, profitable:false`. Proves sigStatus→usdcDeltaForSig→record over LIVE chain data,
records a real LOSS (the exact case record-payout.mjs's delta>0 gate would miss), and correctly does
NOT claim GATE-0 (profitable:false, no external:true). Real production ledger untouched.

## Proof Obligations (discharge status)

Corrected per converge finding FIND-CONV-002 (the previous version of this section mislabeled all 6 of
its bullets against sol-trade/tests/test_run.sh's own internal scenario lettering instead of
specs/verification-architecture.md's real PROP-001..016 IDs/definitions, and omitted every REQ-001
obligation). This version enumerates all 16 canonical PROPs from verification-architecture.md:71-88 by
their real ID and definition, cites the actual evidence file:line, and states the status this session
independently re-derived by RE-RUNNING every cited test fresh (`node --test` / `bash tests/test_run.sh`,
2026-07-10, on `anicca-mac-mini-1`) rather than trusting the prior claim.

**2026-07-10 hardening follow-up**: the 3 gaps this table previously reported (PROP-002/003/009/013) are
now closed. Details of what was wrong and what changed are in the "Hardening follow-up" section below the
table (kept for audit trail — this is not silently overwritten history).

| ID | Arch definition (short) | Evidence | Re-run result | Status |
|----|--------------------------|----------|----------------|--------|
| PROP-001 | `resolveEvmPrivateKey`/`loadEvmKey` priority order (env override → ANICCA_HOME file → legacy-owner-only fallback → null), regression | `runtime/loop/__tests__/resolve-identity.test.mjs` (all 20 cases, e.g. lines 45-123) | `node --test`: **20/20 pass** | DISCHARGED |
| PROP-002 | Two fixture `ANICCA_HOME` wallet.json files resolve to two DIFFERENT addresses even with a contaminating `BLOCKRUN_WALLET_KEY` in a sourced `.env` | `skills/earn/__tests__/run-identity.test.mjs:48` | `node --test`: **PASS** (fixed 2026-07-10 — test-fixture `PYTHONPATH` portability fix, no production or assertion change) | DISCHARGED |
| PROP-003 | `earn/run.sh` never writes a raw `0x`+64-hex private-key-shaped string to stdout/stderr | `skills/earn/__tests__/run-identity.test.mjs:152` (new test, added 2026-07-10) | `node --test`: **PASS** — real fixture wallet + known private key, full discover-mode run, captures stdout+stderr, asserts no `/0x[0-9a-fA-F]{64}/` match; negative-control-verified (the regex does fail on a deliberately leaked key) | DISCHARGED |
| PROP-004 | Automaton's real resolution (`ANICCA_HOME=~/.anicca` default) unchanged after REQ-001, resolves to `0xB9dd3B67921B354c656523d6851537988F31DD56` | `skills/earn/__tests__/run-identity.test.mjs:69` | `node --test`: **PASS** (354ms, real `~/.automaton/wallet.json` on this machine) | DISCHARGED |
| PROP-005 | A pass whose stdout contains one `"Signature: <sig>"` line yields exactly ONE ledger line with `sig`/`confirmed:true`/`chain:"solana"`/`source:"sol-trade"`, `net_usdc` == RPC-computed delta | `skills/earn/sol-trade/lib/__tests__/record-swap.test.mjs:54` (unit, direct `recordSwap()` call) + `skills/earn/sol-trade/tests/test_run.sh` scenario (a) (full bash integration, fixture RPC delta=0.5) | `node --test record-swap.test.mjs`: **8/8 pass**; `bash test_run.sh`: **9/9 pass** (scenario (a) both sub-assertions ok) | DISCHARGED |
| PROP-006 | A pass whose stdout contains NO `"Signature:"` line yields ZERO new ledger lines (only the pre-existing trace narrate line) | `skills/earn/sol-trade/tests/test_run.sh` scenario (h), lines 264-273 (unlabeled by PROP-ID in the file itself, but its assertion — "no Signature: line (WAIT) -> zero new ledger lines" — is exactly PROP-006's definition) | `bash test_run.sh`: **PASS** (part of the 9/9 total) | DISCHARGED |
| PROP-007 | A pass with a NEGATIVE USDC delta and a confirmed sig still appends one line with `earn_usdc:0`, `cost_usdc:\|delta\|`, `net_usdc<0` (no `delta>0` gate, unlike `record-payout.mjs`) | `skills/earn/sol-trade/lib/__tests__/record-swap.test.mjs:68` (unit) + `verification/security-results/realchain-e2e.log` (a REAL on-chain loss recorded against Franklin's live wallet: `net_usdc:-0.008664`, `profitable:false`) | `node --test`: **PASS** (part of 8/8); real-chain log independently re-read, matches | DISCHARGED |
| PROP-008 | `record.mjs`'s `assertOwnIdentityOnly()` accepts `source:"sol-trade"` without throwing; every pre-existing allowed source still passes (regression) | `skills/_shared/lib/__tests__/identity-guard.test.js:62-79` | `node --test`: **12/12 pass** | DISCHARGED |
| PROP-009 | `earn-guard.mjs`'s unconditional `check` call still HALTs (exit 0, no strategy branch) when the resolved wallet address is empty | `skills/earn/__tests__/run-identity.test.mjs:114` | `node --test`: **PASS** (fixed 2026-07-10 — assertion updated to match `earn/run.sh`'s actual current earlier HALT message; HALT/exit-0/zero-ledger-lines behavior itself unchanged and was never weakened) | DISCHARGED |
| PROP-010 | `extractLastSignature` deterministic/total: 0/1/N `"Signature:"` occurrences → `null`/that sig/the LAST one; never throws on malformed input | `skills/earn/sol-trade/lib/__tests__/parse-pass.test.mjs` (all 5 cases) + `test_run.sh` scenario (f), lines 224-243 | `node --test`: **5/5 pass**; `bash test_run.sh` scenario (f): **PASS** | DISCHARGED |
| PROP-011 | `sol-trade/run.sh` derives THIS instance's own Solana address via `runtime/wallet-address-solana.mjs` (never a hardcoded literal); two distinct fixture secrets → two DIFFERENT addresses; unresolvable/malformed → empty (fail-closed) | `runtime/loop/__tests__/wallet-address-solana.test.mjs` (8 cases — this file's OWN internal labels, e.g. "PROP-012"/"PROP-007"/"PROP-005", belong to a DIFFERENT spec's PROP-numbering scheme, `2026-07-05-equalize-multichain-identity-design.md`; they are NOT franklin-earn-foundation's PROP IDs — cited here only because the file proves the exact same already-existing, unmodified `wallet-address-solana.mjs` derivation + fail-closed behavior this feature's PROP-011 requires) + `test_run.sh`'s own `FRANKLIN_ADDR`/`THIRDPARTY_ADDR` fixture pair (two distinct freshly-generated Solana keypairs resolving to two different addresses, exercised live through scenarios (a)/(d)) | `node --test wallet-address-solana.test.mjs`: **8/8 pass**; `test_run.sh`: **9/9 pass** | DISCHARGED |
| PROP-012 | `sol-trade/run.sh`'s own pass-boundary `earn-guard.mjs` cumulative check HALTs (skips `franklin-trading start` entirely, exit 0, zero new ledger lines) when cumulative net for the fixture wallet is below reserve | `test_run.sh` scenario (e), lines 203-222 (explicitly labeled `PROP-012` in the file) | `bash test_run.sh`: **PASS** | DISCHARGED |
| PROP-013 | `ANICCA_EVM_PRIVATE_KEY` (the real highest-priority override) never reaches `earn/run.sh`'s own `resolve-identity.mjs evm` invocation even when present in the ambient parent env | `skills/earn/__tests__/run-identity.test.mjs:141` | `node --test`: **PASS** (fixed 2026-07-10 — same `PYTHONPATH` portability fix as PROP-002, no production or assertion change) | DISCHARGED |
| PROP-014 | `sol-trade/run.sh`'s identity-match guard HALTs before `franklin-trading start` (exit 0, zero ledger lines) whenever its own vs forced-`.blockrun` Solana-address derivations disagree or either is empty, and does NOT halt when they agree | `test_run.sh` scenario (a) [must-NOT-halt, Franklin-shaped], scenario (b) [halts, automaton-shaped/no secret], scenario (d) [halts, resolvable-but-foreign secret], lines 133-201 | `bash test_run.sh`: **PASS** (all 3 sub-cases green) | DISCHARGED |
| PROP-015 | `ANICCA_SOLANA_PRIVATE_KEY` never reaches EITHER of `sol-trade/run.sh`'s `wallet-address-solana.mjs` invocations even when present in the ambient parent env (mirrors PROP-013 for the Solana path) | `test_run.sh` scenario (c), lines 172-186 (labeled "FIND-001 regression" in the file — the ambient-key-bypass attempt this PROP guards against) | `bash test_run.sh`: **PASS** | DISCHARGED |
| PROP-016 | `sigStatus`/`usdcDeltaForSig` RPC error/timeout/malformed data → exactly ONE narrate-only `sol-verify-failed` trace line, `earn_usdc:0, cost_usdc:0`, exit 0, never a crash/`NaN`/`Infinity` | `skills/earn/sol-trade/lib/__tests__/record-swap.test.mjs:95,102` (unit, both `sigStatus`- and `usdcDeltaForSig`-failure paths) + `test_run.sh` scenario (g), lines 244-261 (labeled `PROP-016` in the file, malformed fake-RPC response) | `node --test`: **PASS** (part of 8/8); `bash test_run.sh` scenario (g): **PASS** | DISCHARGED |

**All 16 of 16 PROPs are now genuinely DISCHARGED** by real, independently re-run, currently-passing
tests (as of the 2026-07-10 hardening follow-up below). The 3 that were open are now closed; their
history is preserved here for audit rather than deleted.

## Hardening follow-up (2026-07-10) — closes PROP-002/003/009/013

This session (a VCSDD builder pass, not the converge review itself) closed the 3 gaps the converge
review + report-correction pass above identified. Each gap, what was wrong, and the exact fix:

- **PROP-003 — was a genuine coverage gap (no test existed).** Closed by adding a new test,
  `skills/earn/__tests__/run-identity.test.mjs:152` ("PROP-003: earn/run.sh never writes a raw
  private-key-shaped string..."). It runs a real `earn/run.sh` discover-mode pass against a fixture
  `ANICCA_HOME` whose wallet.json holds a KNOWN private key (`0x` + `"7".repeat(64)`), captures full
  stdout+stderr, and asserts neither stream contains a `/0x[0-9a-fA-F]{64}/` match. A sanity assertion
  first confirms the fixture key itself DOES match the pattern (the detector is real, not vacuous), and
  the test also confirms the pass reached genuine resolution (the narrate line's `wallet` field equals
  the address derived from the fixture key) rather than trivially passing via an early HALT. Negative-
  control-verified outside the suite: the same regex correctly flags a deliberately-leaked key string.
  No production code changed — this is pure test coverage for an existing (correct) discipline.

- **PROP-002 / PROP-013 — was a test-fixture portability bug, not a production regression.** Root
  cause (independently reproduced): `run-identity.test.mjs` overrides `HOME` to a throwaway fixture dir
  for hermeticity; `earn/run.sh`'s `wallet_addr()` helper shells out to `python3 -c "...from eth_account
  import Account..."`, and on this machine `eth_account` resolves through a `HOME`-keyed user
  site-packages path (`~/Library/Python/3.14/lib/python/site-packages`, confirmed via
  `python3 -c "import eth_account; print(eth_account.__file__)"`), so the HOME-overridden child process
  raised a swallowed (`2>/dev/null`) `ModuleNotFoundError`. Fixed in the TEST FIXTURE ONLY (no
  production-code change): the test now resolves the real `site.getusersitepackages()` path once (under
  the REAL, unoverridden `HOME`, via `execFileSync` at module load) and passes it through as
  `PYTHONPATH` to every fixture `run.sh` invocation. This does not weaken or widen anything the test
  isolates or asserts — `ANICCA_HOME`/`HOME`/wallet-fixture isolation is unchanged; it only restores
  module resolution for the interpreter `run.sh` already spawns. Both `PROP-002`
  (`run-identity.test.mjs:66`) and `PROP-013` (`run-identity.test.mjs:141`) now pass for real, exercising
  their full original address-equality assertions (not a weakened substitute).

- **PROP-009 — was a stale assertion, not a functional regression.** The test asserted
  `assert.match(stdout, /P1 GUARD/)` for the "no wallet.json anywhere" case, but current
  `earn/run.sh:47-50` HALTs EARLIER than the `P1 GUARD` cumulative-net-guard line for this exact case,
  with the message `"[earn] no signing key resolved for this instance (...) -- HALT (fail-closed); never
  fall back to another instance's key."` (confirmed by reading `run.sh` directly and by the test's own
  fresh-run stdout). Fixed by updating the assertion to
  `/no signing key resolved for this instance.*HALT \(fail-closed\)/`, matching the REAL current HALT
  line — the assertion still proves the same fail-closed guarantee PROP-009 requires (HALT fires, exit 0,
  zero ledger lines, zero strategy branches run — the ledger-file-never-created assertion is unchanged),
  just anchored to the earlier, correct HALT point instead of a stale one. Nothing was weakened.

Full fresh re-run after all 3 fixes (`node --test skills/earn/sol-trade/lib/__tests__/*.test.mjs
skills/earn/__tests__/*.test.mjs runtime/loop/__tests__/resolve-identity.test.mjs
runtime/loop/__tests__/wallet-address-solana.test.mjs skills/_shared/lib/__tests__/identity-guard.test.js`
+ `bash skills/earn/sol-trade/tests/test_run.sh`, 2026-07-10, `anicca-mac-mini-1`):

```
node --test (5 files): tests 58, pass 58, fail 0, cancelled 0, skipped 0, todo 0
bash test_run.sh: 9/9 passed
```

No spend cap, identity guard, or the ledger's `external:true` gate was touched or weakened by any of the
3 fixes above — all changes are confined to `skills/earn/__tests__/run-identity.test.mjs` (test file
only).

## Summary
All 16 canonical PROPs from `specs/verification-architecture.md:71-88` are genuinely DISCHARGED by real,
independently re-run, currently-passing tests as of 2026-07-10 (58/58 `node --test` + 9/9
`bash test_run.sh`, full detail in the discharge table and the "Hardening follow-up" section above).
Regression GREEN, fresh Opus adversary PASS (0 blocking) at iteration-2, and a LIVE on-chain E2E confirms
real P&L recording (including a real loss) with no false GATE-0. The feature is implementation-verified
AND all 16 proof obligations are now closed with fresh, reproducible evidence — no PROP is marked
DISCHARGED on the strength of a prior claim alone. Remaining non-blocking findings (FIND-101/102/103) are
cosmetic/stricter-than-spec with no money-safety impact and are recorded for a future cleanup pass, not
blocking convergence.
