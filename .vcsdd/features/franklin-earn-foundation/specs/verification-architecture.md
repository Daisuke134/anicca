# Verification Architecture — franklin-earn-foundation

## Purity Boundary Map

- **Pure Core (deterministic, side-effect-free, already exists — UNMODIFIED by this feature):**
  - `skills/earn/lib/resolve-identity.mjs` — `resolveEvmPrivateKey`, `resolveSolanaSecret`,
    `loadEvmKey` (fail-closed, never throws, no I/O side effects beyond a read). Already exhaustively
    tested by `runtime/loop/__tests__/resolve-identity.test.mjs`; REQ-001 only WIRES a new caller
    (`earn/run.sh`) to it, it does not change its logic.
  - `runtime/wallet-address-solana.mjs` — derives THIS instance's own Solana base58 address in-process
    from `resolveSolanaSecret()` via `Keypair.fromSecretKey` (fail-closed: unresolvable/malformed secret
    → empty stdout + a stderr warning only, never a crash, never echoes the secret). Already exists,
    unmodified; REQ-002 WIRES a new caller (`sol-trade/run.sh`) to it, exactly like REQ-001 wires
    `earn/run.sh` to `resolve-identity.mjs` — it does not change its logic.
  - `skills/_shared/lib/solana-verify.mjs` — `sigStatus`, `usdcDeltaForSig` (RPC calls are the only
    I/O; both take an injectable `fetchImpl`, making the decision logic itself pure/testable offline).
    Already exists, unmodified; REQ-002 WIRES a new caller (`sol-trade/lib/record-swap.mjs`, below,
    mirroring `clip-promote/record-payout.mjs`'s ALREADY-EXISTING, ALREADY-TESTED call sequence
    verbatim) to it — this is the ONE authoritative delta mechanism this feature defines (FIND-009); it
    does not change `solana-verify.mjs`'s own logic. No `franklin-trading balance` CLI parse is used or
    needed anywhere in this feature (FIND-009/FIND-010: the whole-pass-window delta source and its
    chalk/ANSI-wrapped-stdout parsing risk are both eliminated by construction, not merely hardened).
  - `skills/_shared/lib/ledger.mjs` — `deriveLine`, `isProfitable`, `cumulativeNet` (pure).
  - `skills/_shared/lib/earn-guard.mjs` — `evaluateHalt`, `evaluateScope`, `checkHalt` (pure gate + a
    thin I/O read wrapper). Already exists, unmodified, and already wired at `earn/run.sh:78`; REQ-002
    WIRES a NEW caller — `sol-trade/run.sh`'s own pass boundary — to the same `checkHalt`/CLI
    entrypoint, mirroring the identical one-line idiom `economy/gig/run.sh:62-65` already uses.
  - **New pure code this feature adds**: `skills/earn/sol-trade/lib/parse-pass.mjs` —
    `extractLastSignature(stdout: string): string|null`. Deterministic regex-extraction of a fixed,
    machine-emitted label (`"Signature: <base58>"`) from `franklin-trading`'s own CLI output. This is
    parsing of a fixed format, not judgment (the trading decision itself was already made by the
    model/CLI; this only reads back its own receipt) — consistent with the project's regex-for-judgment
    ban, which targets decision-making, not fixed-format log parsing. (`sol-trade/lib/record-swap.mjs`,
    the other new file, is NOT pure — it orchestrates a network RPC call and a filesystem append, so it
    is listed in the Effectful Shell below, exactly like `record.mjs`/`record-payout.mjs` are; its own
    internal sign-mapping logic, delta>0 → earn_usdc else cost_usdc, reuses `deriveLine`'s existing
    convention and invents no new arithmetic.)

- **Effectful Shell (I/O, external process, network — this feature touches):**
  - `skills/earn/run.sh` (bash) — sources env files, `unset`s `ANICCA_EVM_PRIVATE_KEY` defensively,
    spawns `node resolve-identity.mjs evm`, exports the resolved key, orchestrates existing strategy
    branches (0xwork/hl/x402/token/swap/yield — UNCHANGED by this feature except the
    identity-resolution lines).
  - `skills/earn/sol-trade/run.sh` (bash) — defensively `unset`s `ANICCA_SOLANA_PRIVATE_KEY` before doing
    anything else (mirrors `earn/run.sh`'s new `unset ANICCA_EVM_PRIVATE_KEY`), then spawns
    `node wallet-address-solana.mjs` TWICE (I/O, a read) — once for its own `ANICCA_HOME`, once with
    `ANICCA_HOME` forced to `$HOME/.blockrun` — to derive both THIS instance's own Solana address AND
    the address the external CLI's own wallet custody will actually use, and HALTs (the new
    identity-match guard, plain bash string-equality, no new crypto/derivation logic) before doing
    anything else this pass if they disagree or either is empty; spawns `node earn-guard.mjs check`
    (I/O, filesystem read) at its own pass boundary ONLY after the identity-match guard has passed;
    spawns the external `franklin-trading` CLI (network + its own wallet custody, entirely outside this
    feature's control — confirmed `os.homedir()`-based, no `ANICCA_HOME` awareness of its own); when
    `parse-pass.mjs::extractLastSignature` finds a signature, invokes the new `sol-trade/lib/record-swap.mjs`
    — which itself calls `solana-verify.mjs::sigStatus` (network RPC, `getSignatureStatuses`) then
    `solana-verify.mjs::usdcDeltaForSig` (network RPC, `getTransaction`) then `node lib/record.mjs`
    (I/O, filesystem append) — the ONE authoritative delta mechanism this feature defines (FIND-009),
    degrading to a narrate-only line if the `sigStatus`/`usdcDeltaForSig` RPC call itself
    errors/times out/returns malformed data (FIND-008's convention, re-anchored per FIND-009/FIND-010
    onto the actual sole read-failure-prone call in this graph), never crashing. NO call to
    `franklin-trading balance` is made anywhere in this file or by anything it invokes (FIND-009/FIND-010:
    eliminates both the whole-pass-window delta-contamination risk and the chalk/ANSI-wrapped-stdout
    (`dist/commands/balance.js:13`) parsing risk, rather than hardening a parser this feature does not
    need).
  - `skills/_shared/lib/identity-guard.mjs` `ALLOWED_EARN_SOURCES` — a plain `Set` of strings (not
    itself I/O), gating the effectful `record.mjs` write path. Adding `"sol-trade"` is a one-line data
    change, not new judgment logic.

## Proof Obligations

| ID | Description | Tier | Required | Tool |
|----|-------------|------|----------|------|
| PROP-001 | `resolveEvmPrivateKey`/`loadEvmKey` (existing, unmodified) correctly prioritize env override → ANICCA_HOME file → legacy-owner-only fallback → null | 1 | true | node:test (regression run of existing `runtime/loop/__tests__/resolve-identity.test.mjs`, no new assertions needed) |
| PROP-002 | `earn/run.sh`'s resolved `SIGNKEY` for two distinct fixture `ANICCA_HOME` directories (Franklin-shaped `.automaton/wallet.json` vs. automaton-shaped `.automaton/wallet.json`) always differs and matches each fixture's OWN wallet address, even when a contaminating `BLOCKRUN_WALLET_KEY` is present in a shared sourced `.env` fixture | 1 | true | bash integration test: fixture wallet.json files + fixture `.env`, derive address via `node -e` (never print the key), assert on the derived address only |
| PROP-003 | `earn/run.sh` never writes a raw private-key-shaped string (`0x` + 64 hex chars) to its own stdout/stderr during a full run | 2 | true | property test: capture full stdout+stderr of a fixture run, assert no substring matches `/0x[0-9a-fA-F]{64}/` (format check, not judgment) |
| PROP-004 | Automaton's real resolution (`ANICCA_HOME=~/.anicca` default) is unchanged after REQ-001 — resolves to `0xB9dd3B67921B354c656523d6851537988F31DD56` | 1 | true | fixture test DERIVING the address from the REAL `~/.automaton/wallet.json`'s `privateKey` field (via the same `eth_account`/viem derivation `resolve-identity.mjs`'s callers already use, e.g. `Account.from_key(...).address`, matching `earn/run.sh`'s own `wallet_addr()` helper) and asserting it matches the resolved address for that ANICCA_HOME — never reading a nonexistent `address` field (the real file's only keys are `privateKey`/`createdAt`/`rotatedAt`/`rotationReason`, confirmed by reading the file) and never printing the key itself |
| PROP-005 | A pass whose captured stdout contains a `"Signature: <sig>"` line yields exactly ONE new `earn-ledger.jsonl` line, carrying `sig`/`confirmed:true`/`chain:"solana"`/`source:"sol-trade"`, with `net_usdc` equal to the delta `usdcDeltaForSig` computes for that ONE signature (the SOLE authoritative delta source this feature defines — FIND-009; no `franklin-trading balance` before/after snapshot is read or relied upon) | 1 | true | node:test, calling the new `sol-trade/lib/record-swap.mjs`'s `recordSwap()` DIRECTLY, mirroring `skills/earn/clip-promote/tests/test_record_payout.mjs`'s ACTUAL proven pattern exactly (same imports/injectable-`fetchImpl` technique) — this is the layer that actually proves the `sigStatus` → `usdcDeltaForSig` → `record()` wiring FIND-009 flagged as unproven; ALSO exercised end-to-end via the full `sol-trade/run.sh` bash integration test (fixture `franklin-trading` PATH-stub + `fake_solana_rpc.mjs`-style RPC stub) |
| PROP-006 | A pass whose captured stdout contains NO `"Signature:"` line yields ZERO new `earn-ledger.jsonl` lines (only the pre-existing `trace.jsonl` narrate line) | 1 | true | node:test / bash integration test |
| PROP-007 | A pass with a NEGATIVE USDC delta (from `usdcDeltaForSig`) and a confirmed signature still appends one line, with `earn_usdc:0`, `cost_usdc:\|delta\|`, `net_usdc<0` — proving `record-swap.mjs` deliberately does NOT reuse `record-payout.mjs`'s `delta>0`-only gate, since sol-trade must record losses too (P&L VISIBILITY, not a payout-confirmation check) | 1 | true | node:test, calling `recordSwap()` directly with an injected `fetchImpl` returning a negative `usdcDeltaForSig` result, mirroring `test_record_payout.mjs`'s technique; extends `deriveLine`'s existing sign-mapping coverage, no change to `deriveLine` itself |
| PROP-008 | `record.mjs`'s `assertOwnIdentityOnly()` accepts `source:"sol-trade"` without throwing after the `identity-guard.mjs` allowlist addition, and every PRE-EXISTING allowed source still passes (regression) | 1 | true | node:test, regression run of existing `identity-guard`-adjacent coverage plus one new assertion for `"sol-trade"` |
| PROP-009 | `earn-guard.mjs`'s unconditional `check` call in `earn/run.sh` still HALTs (exit path taken, wake returns 0 without executing any strategy branch) when the resolved wallet address is empty | 1 | true | bash integration test: fixture `ANICCA_HOME` with no `.automaton/wallet.json` at all → resolution returns empty → assert the HALT log line fires and no strategy branch runs |
| PROP-010 | `extractLastSignature` is deterministic and total: given stdout with 0, 1, or N `"Signature: <sig>"` occurrences, it returns `null`, that one sig, or the LAST one respectively; never throws on malformed/truncated input | 1 | true | node:test property-style table (multiple fixed cases, no external fuzzer needed at this scale) |
| PROP-011 | `sol-trade/run.sh` derives THIS instance's own Solana wallet address via `runtime/wallet-address-solana.mjs` (never a hardcoded literal) — two distinct fixture `ANICCA_HOME` Solana secrets resolve to two DIFFERENT addresses, and an unresolvable/malformed secret yields an empty address (fail-closed) | 1 | true | node/bash fixture test: fixture `.automaton/solana.json`/`.solana-session` files, invoke the wallet-address derivation with each fixture `ANICCA_HOME`, assert on the derived address only |
| PROP-012 | `sol-trade/run.sh`'s own pass-boundary `earn-guard.mjs` cumulative check HALTs the pass (skips `franklin-trading start` entirely — no LLM spend, no swap attempt, exit 0, zero new ledger lines) when cumulative net for `{wallet, source:"sol-trade"}` OR the wallet-wide `{wallet}` scope is below reserve, mirroring `earn/run.sh:78`'s existing HALT-on-empty/negative behavior (PROP-009) | 1 | true | bash integration test: fixture `earn-ledger.jsonl` pre-seeded with a negative cumulative net for the fixture Solana wallet, assert the pass exits 0 with NO new `franklin-trading start` invocation and NO new ledger line |
| PROP-013 | `ANICCA_EVM_PRIVATE_KEY`, the ACTUAL highest-priority override on `resolveEvmPrivateKey`'s resolution path (`resolve-identity.mjs:63-67`), never reaches `earn/run.sh`'s own `resolve-identity.mjs evm` invocation even when present in the ambient parent environment (not sourced from any `.env` file) — regression guard for the pollution vector FIND-004 identified (distinct from, and in addition to, PROP-002's `BLOCKRUN_WALLET_KEY` coverage, which the CLI-form call never reads at all) | 1 | true | bash fixture test: set `ANICCA_EVM_PRIVATE_KEY` in the parent shell env (not via any `.env` file), run `earn/run.sh`'s identity-resolution step, assert the resolved address is UNCHANGED from the same fixture without it set |
| PROP-014 | `sol-trade/run.sh`'s identity-match guard HALTs the pass (skips `franklin-trading start` entirely — no LLM spend, no swap attempt, exit 0, zero new ledger lines) BEFORE the cumulative `earn-guard.mjs` check even runs, whenever its own `ANICCA_HOME`-derived Solana wallet address is empty OR does not equal the address derived by forcing `ANICCA_HOME=$HOME/.blockrun` for the SAME `wallet-address-solana.mjs` script — closing the already-live cross-instance leak (FIND-006 / root cause 3) — and does NOT halt when both derivations agree (the Franklin-shaped fixture) | 1 | true | bash integration test, reusing the SAME fixture `franklin-trading` PATH-stub as PROP-012's AC, asserting it is NEVER invoked for (a) an automaton-shaped fixture `ANICCA_HOME` (no resolvable secret) and (b) a fixture `ANICCA_HOME` with its OWN resolvable-but-foreign Solana secret, and IS invoked for (c) a `.blockrun`-shaped fixture whose legacy `.solana-session` matches the forced-derivation fixture |
| PROP-015 | `ANICCA_SOLANA_PRIVATE_KEY` — the Solana twin of `resolveEvmPrivateKey`'s override (`resolveSolanaSecret`'s FIRST check, `resolve-identity.mjs:118-120`) — never reaches EITHER of `sol-trade/run.sh`'s `wallet-address-solana.mjs` invocations (own-`ANICCA_HOME` or forced-`.blockrun`) even when present in the ambient parent environment — regression guard mirroring PROP-013 for the Solana path (FIND-007) | 1 | true | bash fixture test: set `ANICCA_SOLANA_PRIVATE_KEY` in the parent shell env (not via any `.env` file), run `sol-trade/run.sh`'s identity-derivation step, assert both resolved addresses are UNCHANGED from the same fixture without it set |
| PROP-016 | The `sigStatus`/`usdcDeltaForSig` RPC call (via `solana-verify.mjs`, invoked through `record-swap.mjs`) erroring/timing out/returning malformed data causes `sol-trade/run.sh` to record exactly ONE narrate-only `earn-ledger.jsonl` line (`earn_usdc:0, cost_usdc:0`, task prefixed `sol-verify-failed:`) and exit 0 — never a crash, never a `NaN`/`Infinity`-shaped `net_usdc` — mirroring `earn/run.sh:308-319`/`372-381`'s existing abort-degrade convention (FIND-008), re-anchored per FIND-009/FIND-010 onto the actual sole read-failure-prone call in this feature's call graph (no `franklin-trading balance` CLI read exists anywhere in this feature to fail) | 1 | true | node:test, calling `recordSwap()` directly with a `fetchImpl` that rejects/throws for `getSignatureStatuses`/`getTransaction`, asserting a `verify-error` status (never a thrown exception); ALSO exercised at the full bash-integration level via the fixture `franklin-trading` PATH-stub + a `fake_solana_rpc.mjs`-style RPC stub configured to return a non-2xx/malformed response |

## Verification Strategy

- **Tier 0 (no formal proof needed)**: bash orchestration glue (sourcing env files, branching on
  `$STRATEGY`, echoing status lines) in both `run.sh` files — covered incidentally by the Tier 1
  integration tests below; no standalone proof obligation since it carries no independent logic beyond
  wiring pure functions together.
- **Tier 1 (property tests / fuzzing, PRIMARY tier for this feature)**: PROP-001 through PROP-016,
  all via Node's built-in `node:test` (already the project's convention — see
  `skills/earn/lib/__tests__/*.test.mjs`, `skills/earn/clip-promote/tests/*.mjs`) plus bash integration
  harnesses per `run.sh`, using the ACTUAL patterns already proven in this codebase (verified by reading
  the real files — NOT the previously-cited "fake CLI first in `$PATH`" pattern, which does not exist
  anywhere in `skills/earn/clip-promote/tests/test_run.sh` or elsewhere in the repo):
  - Ledger-wiring logic (PROP-005, PROP-007) is tested by calling the NEW `sol-trade/lib/record-swap.mjs`'s
    `recordSwap()` DIRECTLY with an injected `fetchImpl`, mirroring `skills/earn/clip-promote/tests/
    test_record_payout.mjs`'s ACTUAL proven pattern EXACTLY (same imports — `sigStatus`, `usdcDeltaForSig`,
    `record` — same injectable-opts technique). This is the layer that actually PROVES the
    `sigStatus` → `usdcDeltaForSig` → `record()` wiring FIND-009 flagged as never exercised by any prior
    proof obligation; `record.mjs`'s own round-trip is still covered separately by the EXISTING
    `record-solana.test.mjs` (unchanged, PROP-008's identity-guard regression only). `record-swap.mjs`
    has ONE deliberate difference from `record-payout.mjs`: it does NOT reject non-positive deltas
    (`record-payout.mjs`'s `zero-delta` gate), since sol-trade must record losses too (PROP-007).
  - The network layer (`sigStatus`/`usdcDeltaForSig`'s RPC calls) is stood in for at the UNIT level by an
    injected `fetchImpl` passed straight to `recordSwap()` (no server needed, mirrors
    `test_record_payout.mjs`), and additionally at the FULL `sol-trade/run.sh` bash integration test level
    by a LOCAL HTTP Solana RPC stub server bound to a random port and wired in via the `SOLANA_RPC_URL`
    env override — mirroring the ACTUAL proven `skills/earn/clip-promote/tests/fake_solana_rpc.mjs`
    pattern verbatim, so no mainnet RPC call is ever made by a test. No test anywhere in this feature
    stubs `franklin-trading balance`'s stdout, because no code path calls it (FIND-009/FIND-010).
  - The external `franklin-trading` CLI's stdout (needed only for the full `sol-trade/run.sh` bash
    integration test, PROP-005/006/012/014/016) is stood in for by a fixture executable placed first in
    `$PATH` for that one test invocation — an honestly-new technique for this feature (no existing repo
    file stubs an external CLI's stdout this way; this replaces the previously-cited fictional
    precedent). This fixture's `start` subcommand is the ONLY subcommand any test in this feature ever
    invokes or stubs — it has no `balance` subcommand, because REQ-002 never calls `franklin-trading
    balance`.
  - The malice-guard's PII-isolation discipline (PROP-008's `env -i` regression) mirrors
    `skills/earn/clip-promote/tests/test_run.sh`'s ACTUAL proven technique: a PII env var present makes
    a direct `record.mjs` call THROW, and the SAME var stripped via `env -i` (matching how `run.sh`
    itself would invoke `record.mjs`) records cleanly — applied here to the NEW `"sol-trade"` source.
  - `extractLastSignature` (PROP-010) needs neither a CLI nor an RPC stub at all — it is tested with
    literal fixture strings directly (0/1/N `"Signature:"` occurrences).
  - PROP-011 (wallet derivation) and PROP-013 (`ANICCA_EVM_PRIVATE_KEY` non-regression) need only
    fixture files/env vars, no CLI or RPC stub. PROP-012 (sol-trade's own P1 guard) reuses the same
    fixture `franklin-trading` PATH stub above, asserting it is NEVER invoked when the guard HALTs.
  - PROP-014 (the identity-match guard, FIND-006's fix) reuses the SAME fixture `franklin-trading` PATH
    stub, but exercises it against THREE fixture `ANICCA_HOME` shapes in the SAME test file: (a)
    automaton-shaped (no resolvable Solana secret at all — the real, already-live leak), (b) a
    third-party-shaped fixture with its OWN resolvable-but-non-`.blockrun` Solana secret (the
    "resolved-but-foreign wallet" case), and (c) the Franklin/`.blockrun`-shaped fixture (the ONE case
    that must NOT halt). No RPC stub is needed for this PROP — it only needs to prove the PATH-stub was
    or wasn't invoked, before any RPC/swap logic would ever run.
  - PROP-015 (`ANICCA_SOLANA_PRIVATE_KEY` non-regression) mirrors PROP-013's technique exactly, applied
    to `sol-trade/run.sh`'s own identity-derivation step (both the own-`ANICCA_HOME` and
    forced-`.blockrun` invocations) — fixture files/env vars only, no CLI or RPC stub.
  - PROP-016 (RPC read-failure degrade, FIND-008's fix, re-anchored per FIND-009/FIND-010 onto the
    actual sole read-failure-prone call in this feature's call graph — `sigStatus`/`usdcDeltaForSig` via
    `solana-verify.mjs`, NOT `franklin-trading balance`, which this feature never calls) is tested at the
    unit level by injecting a `fetchImpl` into `recordSwap()` that rejects/throws for
    `getSignatureStatuses`/`getTransaction`, asserting a `verify-error` status (never a thrown exception),
    and additionally at the full bash-integration level via the SAME fixture `franklin-trading` PATH stub
    (its `start` subcommand emitting a real-shaped `Signature:` line) plus a `fake_solana_rpc.mjs`-style
    RPC stub configured to return a non-2xx/malformed response — mirroring `earn/run.sh:308-319`/
    `372-381`'s existing `d.get('error') or d.get('abort')`-style detection pattern, asserted against the
    resulting `earn-ledger.jsonl` narrate line and exit code.
- **Tier 2 (lightweight formal methods)**: PROP-003 only — a grep-shaped property check that no
  private-key-looking string ever reaches stdout/stderr. This is a lightweight invariant check, not a
  full formal proof; no Kani/Hypothesis is warranted at this scale (pure string-pattern absence check
  over a bounded, captured output).
- **Tier 3 (strong formal proof)**: none required. No cryptographic primitive, consensus protocol, or
  numerically unstable algorithm is introduced or modified by this feature — signature verification
  and USDC delta computation are delegated unchanged to `solana-verify.mjs`, which is out of this
  feature's modification scope and already carries its own test coverage.

## Regression guardrails (explicit, since two other instances share these files)

- Automaton (`ANICCA_HOME=~/.anicca`) MUST resolve to the SAME address after REQ-001 as before it
  (PROP-004) — this is the primary non-regression gate for the "shared file, per-instance safety"
  constraint given for this feature.
- `earn-guard.mjs`'s fail-closed HALT-on-empty-wallet behavior (the FIND-A fix already in
  `earn/run.sh:71-81`) MUST remain intact after REQ-001's wiring change (PROP-009) — this feature must
  not reintroduce the `[ -n "$WLOW" ] &&` short-circuit class of bug that was already fixed once.
- Every source currently in `identity-guard.mjs`'s `ALLOWED_EARN_SOURCES` MUST still pass
  `assertOwnEarnSource` after adding `"sol-trade"` (PROP-008) — a additive-only allowlist change,
  never a rewrite of the set.
- `ANICCA_EVM_PRIVATE_KEY` (the ACTUAL highest-priority override on `resolveEvmPrivateKey`'s resolution
  path, `resolve-identity.mjs:63-67`) MUST NEVER reach `earn/run.sh`'s own `resolve-identity.mjs evm`
  invocation (PROP-013) — this feature adds a defensive `unset` plus a regression test; `EARN_ALLOW`
  (`run.sh:26`) already omitting this var from the sourced-env allowlist is necessary but was never
  sufficient on its own (nothing previously asserted it as an invariant).
- `sol-trade/run.sh` MUST derive its own Solana wallet address via `runtime/wallet-address-solana.mjs`
  (PROP-011), never a hardcoded literal — the same class of bug (root cause 1, per
  `resolve-identity.mjs`'s own comments) REQ-001 already exists to eliminate on the EVM side.
- `sol-trade/run.sh` MUST gain its own pass-boundary `earn-guard.mjs` cumulative HALT check (PROP-012)
  the moment it starts calling `record.mjs` — per `skills/earn/SKILL.md:80-82`'s own documented
  convention, which REQ-002 must now satisfy, not merely cite.
- `sol-trade/run.sh` MUST gain an identity-match guard (PROP-014) that HALTs BEFORE `franklin-trading
  start` whenever its own `ANICCA_HOME`-derived Solana wallet is empty OR does not equal the wallet
  Franklin's `$HOME/.blockrun`-scoped `franklin-trading` CLI will actually execute against — this is the
  fix for an ALREADY-LIVE production leak (FIND-006 / root cause 3: automaton's own loop recorded 70
  real `franklin-trading start` passes against Franklin's real wallet, `sol-trade.trace.jsonl`,
  2026-07-04 through 2026-07-07), not a theoretical hardening. PROP-011/PROP-012 alone (isolated wallet
  derivation; cumulative-net-for-a-KNOWN-wallet) do NOT exercise this branch — PROP-014 is the required,
  additional, full-integration proof obligation that closes it.
- `ANICCA_SOLANA_PRIVATE_KEY` (`resolveSolanaSecret`'s FIRST check, `resolve-identity.mjs:118-120` — the
  Solana twin of `ANICCA_EVM_PRIVATE_KEY`) MUST NEVER reach EITHER of `sol-trade/run.sh`'s
  `wallet-address-solana.mjs` invocations (PROP-015) — this feature adds a defensive `unset` plus a
  regression test, mirroring PROP-013/REQ-001's EVM-side fix (FIND-007); left unaddressed, a leaked
  value could also defeat the new identity-match guard above by making a foreign instance's own
  derivation spuriously equal Franklin's wallet.
- A `sigStatus`/`usdcDeltaForSig` RPC call (via `solana-verify.mjs`, invoked through the new
  `record-swap.mjs`) that errors/times out/returns malformed data MUST degrade to a narrate-only ledger
  line (PROP-016), mirroring the existing abort/error convention already proven at
  `earn/run.sh:308-319` (swap) and `earn/run.sh:372-381` (yield) — never a crash, never a
  `NaN`/`Infinity`-shaped `net_usdc` reaching `earn-ledger.jsonl` (FIND-008). This feature never calls
  `franklin-trading balance` anywhere — the whole-pass before/after CLI-snapshot delta source and its
  chalk/ANSI-color-wrapped-stdout parsing risk (`dist/commands/balance.js:13`) are ELIMINATED, not merely
  hardened: `usdcDeltaForSig`'s per-signature RPC computation (`solana-verify.mjs:58-81`) is this
  feature's ONE authoritative delta mechanism, wired through the new `sol-trade/lib/record-swap.mjs`
  (mirroring `clip-promote/record-payout.mjs`'s already-proven call sequence) — FIND-009/FIND-010
  resolution.
- No test in this feature ever performs a real on-chain swap, a real RPC call to mainnet, or reads a
  real private key value into an assertion — every PROP above is exercised against fixtures/mocks only
  (mirrors the existing `record-solana.test.mjs` / `resolve-identity.test.mjs` discipline).
