# Behavioral Spec — franklin-earn-foundation

Mode: lean. Scope: fix THREE grounded loop-foundation bugs (root causes 1-3 below; REQ-001 fixes root
cause 1, REQ-002 fixes BOTH root cause 2 and the ALREADY-LIVE cross-instance leak in root cause 3) so
Franklin (EVM `0x3EcCAD24794ca298D25378E9902A251322ea8749`, Solana
`8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9`) actually earns for itself and can see its own win/loss
record — and so no OTHER instance can spend its own model budget trading Franklin's real wallet. This
is NOT a funding task and NOT a trading-strategy task — Franklin already holds $11.39 and its baseline
strategy is intentionally left untouched.

## Grounded root causes (verified in this session, exact paths + line numbers)

1. **Wallet identity leak** — `skills/earn/run.sh:26-33` sources `$HOME/.openclaw/.env` (confirmed to
   contain `BLOCKRUN_WALLET_KEY=` — automaton's own key, address `0xB9dd3B67921B354c656523d6851537988F31DD56`,
   derived from `~/.automaton/wallet.json`) into its own process env, then `run.sh:40,46` derives the
   signing key with `PKVAR="${PKVAR:-BLOCKRUN_WALLET_KEY}"` / `SIGNKEY="${!PKVAR:-}"` — a **plain env
   read that never consults `ANICCA_HOME`** (confirmed: `grep ANICCA_HOME skills/earn/run.sh` → zero
   matches). Franklin's own launchd loop (`~/Library/LaunchAgents/ai.anicca.franklin-loop.plist`) sets
   `ANICCA_HOME=/Users/anicca/.blockrun`, whose `.automaton/wallet.json` holds Franklin's REAL key
   (address `0x3EcCAD24794ca298D25378E9902A251322ea8749`, verified by deriving the address from the
   file — never printing the key). Because `run.sh` ignores `ANICCA_HOME` entirely, every wake of
   `earn/run.sh` under Franklin's loop signs `hl-trade` / `yield` / `x402` / `token-launch` / `0xwork`
   with **automaton's key**, not Franklin's own — Franklin's earn slot trades on someone else's wallet.
   `skills/earn/lib/resolve-identity.mjs` already implements the correct, already-tested, ANICCA_HOME-
   gated resolution (`resolveEvmPrivateKey`/`loadEvmKey`) and is already wired correctly into
   `skills/economy/gig/run.sh:50` (`SIGNKEY=$(node .../resolve-identity.mjs evm)`) — `earn/run.sh` is
   the one caller that still does it the old, unsafe way.

2. **P&L feedback gap** — `skills/earn/sol-trade/run.sh` (confirmed, no `record.mjs`/ledger call
   anywhere in the file) runs `franklin-trading start --trust ...` and appends ONLY a narrate line to
   `state/sol-trade.trace.jsonl` (`run.sh:43-54`). `skills/earn/SKILL.md:80-82` documents this
   explicitly: *"Not yet wired: hl-trade, sol-trade, x402-sell ... Once any of them starts calling
   record.mjs/record_ledger_line-style writes, add the one-liner above at its own pass boundary"* — i.e.
   the project's OWN convention requires that the moment sol-trade starts calling `record.mjs` (this
   feature's own change), it MUST ALSO gain its own pass-boundary `earn-guard.mjs` cumulative
   fail-closed HALT check, mirroring the one-line idiom already live at `earn/run.sh:78` and
   `economy/gig/run.sh:62-65`. REQ-002 below carries BOTH the ledger-wiring AND this guard obligation —
   ledger-wiring alone would surface real losses without the accompanying stop-loss the project's own
   convention mandates. A real Jupiter swap executed by the
   `franklin-trading` CLI (`@blockrun/franklin-trading@0.2.4`, `dist/tools/jupiter.js`) prints a
   `Signature: <sig>` line + Solscan link to stdout on success (verified by reading the installed
   package source, `dist/tools/jupiter.js:342` — plain text, never chalk/ANSI-wrapped). This signature
   is the ONLY signal this feature needs: `skills/_shared/lib/solana-verify.mjs`'s existing,
   already-tested `sigStatus(sig)` (confirms on-chain) and `usdcDeltaForSig(sig, wallet)` (RPC
   `getTransaction`, summing ONLY that ONE signature's own pre/postTokenBalances for our wallet —
   verified: `solana-verify.mjs:49-81`) is this feature's SOLE authoritative delta source (FIND-009
   fix — see REQ-002). A whole-pass `franklin-trading balance` before/after CLI snapshot is
   deliberately NOT used and NOT read anywhere by this feature: it would also pick up any unrelated
   transfer landing in the same window (e.g. a concurrent UBI distribution or gas top-up), silently
   corrupting the recorded `net_usdc`, AND its real stdout is chalk-color-wrapped
   (`dist/commands/balance.js:13`, confirmed) — eliminating it also eliminates that ANSI-parsing risk
   entirely (FIND-010 fix) rather than merely hardening a parser this feature does not need. Today
   neither the signature nor the RPC-verified delta is ever captured, so
   `skills/earn/state/earn-ledger.jsonl` never gets a `sol-trade` line, `isProfitable()`
   (`skills/_shared/lib/ledger.mjs`) never sees it, and nothing downstream (self-eval, future
   evolve-style P&L attribution) can ever see Franklin's actual win/loss track record on Solana. The
   `wallet` identifier this new ledger line carries (and the address `usdcDeltaForSig` sums a delta
   against) MUST itself be derived per-instance via `runtime/wallet-address-solana.mjs` — the EXISTING,
   already-correct ANICCA_HOME-gated Solana address-derivation script — never hardcoded, or this feature
   would silently reproduce the identical hardcoded-identity anti-pattern (root cause 1 above) on the
   Solana side.

3. **Cross-instance Solana CLI-execution-wallet leak — ALREADY LIVE, not merely theoretical** — the
   external `franklin-trading` CLI (`@blockrun/franklin-trading@0.2.4`, globally installed) never
   consults `ANICCA_HOME` at all for its OWN wallet custody: `BLOCKRUN_DIR = path.join(os.homedir(),
   '.blockrun')` (confirmed, installed package's `dist/config.js:15`), and its bundled `@blockrun/llm`
   dependency's `setupAgentSolanaWallet()` reads `SOLANA_WALLET_FILE = path.join(os.homedir(),
   '.blockrun', '.solana-session')` (confirmed, `node_modules/@blockrun/llm/dist/index.js:4793-4794`) —
   the EXACT same raw secret file `resolve-identity.mjs::resolveSolanaSecret()`'s own legacy branch
   reads (`resolve-identity.mjs:132-134`), but that legacy branch only fires for the ONE `ANICCA_HOME`
   that equals `$HOME/.blockrun` (Franklin's own instance). Since every instance on this Mac shares the
   SAME OS `$HOME=/Users/anicca` (only `ANICCA_HOME` differs, per each instance's own launchd plist),
   `franklin-trading start` ALWAYS executes against Franklin's real, already-funded wallet
   (`8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9`) no matter which instance's loop invokes it — there is
   NO instance-scoping inside the CLI itself. `skills/registry.json:204-214` marks `earn/sol-trade`
   `status:"live"` with a `riskNote` claiming "the Franklin-Trading CLI trades the instance's own
   Solana bankroll end-to-end" — this claim is FALSE for any instance other than Franklin, and the
   CURRENT, unfixed `skills/earn/sol-trade/run.sh` (confirmed by reading the file in full) has ZERO
   identity or guard logic today: it goes straight from the kill-switch check (`run.sh:15-18`) to
   `franklin-trading start` (`run.sh:40`), with no `wallet-address-solana.mjs` call and no
   `earn-guard.mjs` call anywhere in the file. The result, confirmed by reading
   `/Users/anicca/.anicca/skills/earn/state/sol-trade.trace.jsonl` (automaton's OWN body,
   `ANICCA_HOME=/Users/anicca/.anicca` per `com.anicca.daemon.plist`): 70 `"live-pass"` entries from
   `2026-07-04T02:23:08Z` through `2026-07-07T07:02:32Z` (today) — automaton has ALREADY, repeatedly, in
   production, spent its own model budget invoking `franklin-trading start` against Franklin's real
   wallet. REQ-002's identity-match guard below closes this ONLY if it fires at the FULL
   `sol-trade/run.sh` pass-boundary level, in the correct order (identity-match check BEFORE
   `franklin-trading start`), and ONLY if the spec's own proof obligations actually exercise that exact
   integration path (see PROP-014 in verification-architecture.md) — testing
   `wallet-address-solana.mjs` in isolation (PROP-011) or the cumulative earn-guard for a KNOWN wallet
   (PROP-012) each leaves this specific, already-happening failure mode unverified. (Note:
   `registry.json`'s stale `riskNote` text is a separate, out-of-scope honesty fix — this feature's own
   guard makes the underlying risk moot regardless of that file's wording; `registry.json` is not in
   this feature's Files-in-scope table and is not touched here.)

## Purity boundary analysis (summary — full map in verification-architecture.md)

- **Pure core (unmodified by this feature, already tested):** `skills/earn/lib/resolve-identity.mjs`
  (`resolveEvmPrivateKey`, `loadEvmKey`), `runtime/wallet-address-solana.mjs` (derives THIS instance's
  own Solana base58 address from `resolveSolanaSecret()`, fail-closed, never echoes the secret —
  REQ-002 WIRES a new caller, `sol-trade/run.sh`, to it, exactly like REQ-001 wires `earn/run.sh` to
  `resolve-identity.mjs`), `skills/_shared/lib/solana-verify.mjs` (`sigStatus`,
  `usdcDeltaForSig` — REQ-002 WIRES a new caller, `sol-trade/lib/record-swap.mjs` (new, below),
  mirroring the ALREADY-EXISTING, ALREADY-TESTED `skills/earn/clip-promote/record-payout.mjs` call
  sequence verbatim (`sigStatus(sig)` -> `usdcDeltaForSig(sig, wallet)` -> `record.mjs`'s `record()`) —
  this is the ONE authoritative delta mechanism this feature defines (FIND-009 fix); it does not
  change `solana-verify.mjs`'s own logic), `skills/_shared/lib/ledger.mjs` (`deriveLine`, `isProfitable`),
  `skills/_shared/lib/earn-guard.mjs` (`evaluateHalt`, `checkHalt` — already wired at `earn/run.sh:78`;
  REQ-002 wires a SECOND caller, `sol-trade/run.sh`'s own pass boundary, to the same CLI entrypoint).
- **New pure code this feature adds:** a small, directly unit-testable parser that extracts the LAST
  base58 Solana signature from a `franklin-trading` pass's captured stdout (deterministic parsing of a
  fixed machine-emitted label `"Signature: <sig>"` — NOT judgment; the model already decided to trade,
  this only reads its tool's own receipt), plus reuse of `deriveLine`'s existing earn/cost-from-delta
  arithmetic (no new arithmetic invented).
- **Effectful shell (this feature touches):** `skills/earn/run.sh` (identity resolution wiring, PLUS a
  defensive `unset ANICCA_EVM_PRIVATE_KEY` before invoking `resolve-identity.mjs evm` — strategy
  branches unchanged), `skills/earn/sol-trade/run.sh` (defensive `unset ANICCA_SOLANA_PRIVATE_KEY`;
  derives its own Solana wallet address AND, separately, the wallet Franklin's own `$HOME/.blockrun`
  resolution would derive, HALTing on an identity-mismatch BEFORE anything else this pass; only then
  adds its own pass-boundary `earn-guard.mjs` cumulative check; adds one call to the new
  `sol-trade/lib/record-swap.mjs` — `sigStatus(sig)` -> `usdcDeltaForSig(sig, wallet)` -> `record.mjs`'s
  `record()`, the SOLE delta mechanism this feature defines (FIND-009) — degrading to a narrate-only
  line if that RPC call itself errors/times out (FIND-008's convention, re-anchored onto the correct
  call per FIND-009/FIND-010; no `franklin-trading balance` CLI call is made or parsed anywhere in
  this feature)), `skills/_shared/lib/identity-guard.mjs`
  (adds `"sol-trade"` to `ALLOWED_EARN_SOURCES` — a one-line allowlist entry, not a judgment change).

## Files in scope (spec boundary — nothing else is touched)

| File | Change |
|---|---|
| `skills/earn/run.sh` | Replace the raw `SIGNKEY="${!PKVAR:-}"` env read with the gated `resolve-identity.mjs evm` resolution (mirrors `economy/gig/run.sh:50`), and export the resolved key under `$PKVAR` so every existing child (`execute-swap.py`, `execute-0xwork.py`, `hl-trade/hl.py`, `execute-yield.mjs`, `execute-invest.mjs`, `ensure-gas.mjs`, `token-launch/launchpad.py`) transparently signs with the resolved key. Defensively `unset ANICCA_EVM_PRIVATE_KEY` before invoking `resolve-identity.mjs evm` (mirrors the existing PII-var unset loop at `run.sh:30-33`) so a stray/ambient value of the ONE env var that overrides the ANICCA_HOME-gated file resolution at HIGHER priority (`resolve-identity.mjs:63-67`) can never silently take precedence. No other line in `run.sh` changes. |
| `skills/earn/sol-trade/run.sh` | Defensively `unset ANICCA_SOLANA_PRIVATE_KEY` (mirrors `earn/run.sh`'s new `unset ANICCA_EVM_PRIVATE_KEY`, REQ-001) before deriving any Solana address. Derive THIS instance's own Solana wallet address via `runtime/wallet-address-solana.mjs` (ANICCA_HOME-gated, never hardcoded), AND separately derive the wallet address `franklin-trading`'s own wallet custody will actually execute against by invoking the SAME `wallet-address-solana.mjs` a second time with `ANICCA_HOME` forced to `$HOME/.blockrun` (reusing the existing, unmodified script — no new derivation logic invented). HALT (exit 0, no swap attempt, no LLM spend, zero new ledger lines, reason `identity-mismatch`) unless both derived addresses are non-empty AND equal — this is the guard that stops any non-Franklin instance (root cause 3's already-live automaton leak) BEFORE `franklin-trading start` is ever invoked. ONLY THEN call `skills/_shared/lib/earn-guard.mjs`'s pass-boundary cumulative check (`node earn-guard.mjs check "$WALLET" "sol-trade" "$LEDGER"`, mirroring `earn/run.sh:78` / `economy/gig/run.sh:62-65`) and HALT (same exit-0/zero-new-lines contract) if it fails. Otherwise extract the pass's own last swap signature from its stdout via `lib/parse-pass.mjs`; when (and only when) a signature is present, call the new `lib/record-swap.mjs` (using the derived wallet address) — the SOLE delta mechanism this feature defines (FIND-009): it confirms the signature via `solana-verify.mjs::sigStatus`, computes the delta via `solana-verify.mjs::usdcDeltaForSig`, and appends via `lib/record.mjs`. No `franklin-trading balance` CLI call is made anywhere in this file (FIND-009/FIND-010: eliminates the whole-pass-window contamination risk AND the chalk/ANSI-wrapped-stdout parsing risk, rather than hardening a parser this feature does not need). If the `sigStatus`/`usdcDeltaForSig` RPC call itself errors, times out, or returns malformed data, degrade to a narrate-only `sol-verify-failed:<reason>` line (mirroring `earn/run.sh:308-319`/`372-381`'s existing abort convention), never crashing and never recording a `NaN`-shaped delta. |
| `skills/earn/sol-trade/lib/parse-pass.mjs` (new) | Pure signature-extraction helper (unit-testable in isolation). |
| `skills/earn/sol-trade/lib/record-swap.mjs` (new) | Mirrors the ALREADY-EXISTING, ALREADY-TESTED `skills/earn/clip-promote/record-payout.mjs` call sequence verbatim (`sigStatus(sig)` -> `usdcDeltaForSig(sig, wallet)` -> `record.mjs`'s `record()`, same imports, same injectable-`fetchImpl` opts) with ONE deliberate, documented difference: `record-payout.mjs` rejects any delta that is not `> 0` (status `zero-delta`) because a promote.fun payout is a pure "did we get paid" check; `record-swap.mjs` accepts ANY confirmed delta (positive, negative, or zero) and maps its sign into `earn_usdc`/`cost_usdc` per REQ-002's Edge Cases (`delta>0` -> `earn_usdc:delta,cost_usdc:0`; `delta<=0` -> `earn_usdc:0,cost_usdc:\|delta\|`), because sol-trade's purpose (root cause 2: P&L VISIBILITY) requires winning AND losing passes to be equally visible, not gated on profitability. Returns a status string (`bad-args`/`unconfirmed`/`verify-error`/`recorded`) for `run.sh` to branch on; never throws. |
| `skills/_shared/lib/identity-guard.mjs` | Add `"sol-trade"` to `ALLOWED_EARN_SOURCES` (one line). |
| Tests (phase 2a) | New fixtures under `skills/earn/sol-trade/lib/__tests__/` (pure `extractLastSignature` table tests, no CLI/RPC needed) + node:test direct calls to `recordSwap()` mirroring `skills/earn/clip-promote/tests/test_record_payout.mjs`'s ACTUAL proven pattern EXACTLY (same injectable-`fetchImpl` technique, fixture JSON in, ledger file out) covering: confirmed+positive-delta -> recorded (PROP-005), confirmed+negative-delta -> recorded with `net_usdc<0` (PROP-007), unconfirmed -> not recorded (existing edge case), and `fetchImpl` throwing/erroring -> `verify-error` status, never a thrown exception (PROP-016, retargeted per FIND-009/FIND-010 from the retired balance-CLI-parse mechanism to the actual sole RPC call this feature makes) + node:test direct calls to `record()` mirroring `skills/earn/lib/__tests__/record-solana.test.mjs`'s ACTUAL round-trip pattern for the identity-guard allowlist regression (PROP-008, no CLI/RPC stub needed at this layer) + a bash integration test for `sol-trade/run.sh`'s own pass-boundary guard/wiring reusing the ACTUAL proven `skills/earn/clip-promote/tests/fake_solana_rpc.mjs` local-HTTP-RPC-stub pattern (bound to a random port, wired via `SOLANA_RPC_URL`) for the network layer, plus a temp-`$PATH` fixture `franklin-trading` executable (a new technique for this feature — no existing repo file stubs an external CLI's stdout this way) for the CLI-output layer — this fixture's `start` subcommand is the ONLY subcommand this feature's tests ever invoke; no fixture `balance` subcommand exists or is needed, since no code path in this feature calls `franklin-trading balance` (FIND-009/FIND-010); THREE fixture `ANICCA_HOME` shapes for `sol-trade/run.sh`'s identity-match guard (PROP-014) — automaton-shaped (no resolvable Solana secret), a third-party-shaped fixture with its own resolvable-but-foreign Solana secret, and a `.blockrun`-shaped (Franklin) fixture — asserting the fixture `franklin-trading` PATH-stub is invoked ONLY for the Franklin-shaped case, plus a fixture asserting `ANICCA_SOLANA_PRIVATE_KEY` set in the ambient parent env never survives into either `wallet-address-solana.mjs` invocation (PROP-015); a regression fixture test for `earn/run.sh`'s identity resolution (two fixture `ANICCA_HOME` dirs, one Franklin-shaped, one automaton-shaped, plus a third fixture asserting `ANICCA_EVM_PRIVATE_KEY` set in the ambient parent env never survives into the resolution step). |

**Explicitly NOT touched:** `skills/earn/lib/resolve-identity.mjs`, `runtime/wallet-address-solana.mjs`,
`skills/_shared/lib/earn-guard.mjs`, `skills/_shared/lib/solana-verify.mjs` (all four already correct,
unmodified — this feature only WIRES NEW callers to them: `sol-trade/run.sh` directly for the first
three, `sol-trade/lib/record-swap.mjs` for `solana-verify.mjs`, exactly like REQ-001 wires `earn/run.sh`
to `resolve-identity.mjs`), `skills/_shared/lib/ledger.mjs`, `skills/earn/lib/record.mjs`,
`skills/earn/clip-promote/record-payout.mjs` (read only, as a reference pattern to mirror — never
modified), `skills/economy/gig/*`, `skills/self/spawn/*`, any other
instance's runtime state (`~/.anicca`, `~/.automaton`, `~/.openclaw`), and any `.worktrees/*` copy of
these files (the canonical source is `~/anicca/skills/...`, synced to each `$ANICCA_HOME/skills/` by
`runtime/anicca-daemon.sh`). No file under `@blockrun/franklin-trading`'s installed package
(`dist/commands/balance.js` included) is invoked anywhere by this feature except `franklin-trading`'s
own `start` subcommand (unchanged, already the case before this feature).

## Requirements

### REQ-001: earn/run.sh resolves its signing key per-instance via ANICCA_HOME, never via ambient env
**EARS**: WHEN `skills/earn/run.sh` runs under any instance's loop (with that instance's `ANICCA_HOME`
set in its process environment) THE SYSTEM SHALL derive the signing key EXCLUSIVELY through
`resolve-identity.mjs evm`'s ANICCA_HOME-gated resolution (own `$ANICCA_HOME/.automaton/wallet.json`,
falling back to the legacy `$HOME/.automaton/wallet.json` ONLY when `ANICCA_HOME` resolves to the
default owner's `$HOME/.anicca`) and SHALL export that resolved value under the `$PKVAR`-named
variable (default `BLOCKRUN_WALLET_KEY`) so it — not any value sourced from `$HOME/.openclaw/.env` or
`/opt/anicca.env` — is what every downstream child process reads.

**Edge Cases**:
- `ANICCA_HOME=/Users/anicca/.anicca` (unset/default, automaton's own home): resolution falls through
  to the legacy `$HOME/.automaton/wallet.json` path exactly as it does today — automaton's wake MUST
  keep signing with `0xB9dd3B67921B354c656523d6851537988F31DD56` (zero regression).
- `ANICCA_HOME=/Users/anicca/.blockrun` (Franklin's own home, set by its own launchd plist): resolution
  MUST read `/Users/anicca/.blockrun/.automaton/wallet.json` and sign with
  `0x3EcCAD24794ca298D25378E9902A251322ea8749` — even when `$HOME/.openclaw/.env`'s
  `BLOCKRUN_WALLET_KEY` (automaton's key) is present and sourced into the process env; that ambient
  value MUST be overridden, never merged or preferred.
- `ANICCA_EVM_PRIVATE_KEY` present in the ambient process environment BEFORE `earn/run.sh` invokes
  `resolve-identity.mjs evm` (the ACTUAL highest-priority override on this exact call path —
  `resolveEvmPrivateKey`'s FIRST check, `resolve-identity.mjs:63-67` — NOT `BLOCKRUN_WALLET_KEY`, which
  this CLI-form call never reads at all): `earn/run.sh` MUST proactively `unset` this variable before
  invoking `resolve-identity.mjs evm` (mirroring the existing PII-var unset loop at `run.sh:30-33`) so a
  stray/inherited value can never silently take priority over the per-instance file resolution. Today
  `EARN_ALLOW` (`run.sh:26`) already omits `ANICCA_EVM_PRIVATE_KEY` from the sourced-env allowlist — this
  feature pins that omission (plus the new defensive `unset`) as a MUST-NEVER-REGRESS invariant, since
  nothing enforced it before this fix.
- `resolve-identity.mjs evm` returns nothing (no wallet.json / unreadable / malformed shape — e.g. a
  wallet.json using `private_key`/`address` snake_case instead of the expected `privateKey`, observed
  at `~/.franklin-instance-2/.automaton/wallet.json`, which is NOT Franklin's real EVM home): `SIGNKEY`
  and the derived wallet address MUST both be empty — this is a fail-CLOSED case, not a crash.
- Empty/unresolved `SIGNKEY` (and therefore empty wallet address): `earn-guard.mjs`'s existing
  unconditional `check` call (`run.sh:78`) MUST still fire and HALT the wake (fail-closed) exactly as
  it does today — this feature must not weaken that guard.
- No private key value is ever written to stdout, stderr, or any ledger/trace file during resolution
  (mirrors `resolve-identity.mjs`'s own documented R5 discipline).

**Acceptance Criteria**:
- Two fixture `ANICCA_HOME` directories (one shaped like automaton's `~/.anicca`, one shaped like
  Franklin's `~/.blockrun`, each with its own `.automaton/wallet.json`) resolve to two DIFFERENT
  signing addresses when `earn/run.sh`'s identity-resolution step runs with each `ANICCA_HOME`, even
  when both fixtures also have a shared, contaminating `BLOCKRUN_WALLET_KEY` present in the sourced env.
- Automaton's real resolution path (`ANICCA_HOME` unset/`~/.anicca`) still derives
  `0xB9dd3B67921B354c656523d6851537988F31DD56` from `~/.automaton/wallet.json` (non-regression,
  verified by DERIVING the address from the file's `privateKey` field via the same `eth_account`/viem
  derivation `resolve-identity.mjs`'s callers already use — e.g. `Account.from_key(...).address`,
  matching `earn/run.sh`'s own existing `wallet_addr()` helper — never by reading a nonexistent
  `address` field on the real file, whose only keys are `privateKey`/`createdAt`/`rotatedAt`/
  `rotationReason` (confirmed by reading the real file), and never by printing the key itself).
- Franklin's real resolution path (`ANICCA_HOME=~/.blockrun`) derives
  `0x3EcCAD24794ca298D25378E9902A251322ea8749` from `~/.blockrun/.automaton/wallet.json`.
- A run with no resolvable identity produces an empty `SIGNKEY`/wallet AND the wake still exits 0 via
  the existing P1 guard HALT path (never a hard crash, never a fallback to a stale/ambient key).
- A fixture run with `ANICCA_EVM_PRIVATE_KEY` set in the parent shell's ambient environment (simulating
  a leaked/inherited override, NOT sourced from any `.env` file) still resolves the SAME per-instance
  address as the same fixture without it set — proving the higher-priority override
  (`resolve-identity.mjs:63-67`) never reaches `earn/run.sh`'s own `resolve-identity.mjs evm` invocation.

### REQ-002: sol-trade proves its own instance identity, guards its own cumulative loss, and wires real swap outcomes into the shared earn ledger
**EARS**: WHEN a `sol-trade/run.sh` pass begins THE SYSTEM SHALL first derive THIS instance's own
Solana wallet address via `runtime/wallet-address-solana.mjs` (ANICCA_HOME-gated, never hardcoded) AND
independently derive the wallet address the external `franklin-trading` CLI's own wallet custody will
actually execute against this pass (by invoking the SAME `runtime/wallet-address-solana.mjs` a second
time with `ANICCA_HOME` forced to `$HOME/.blockrun` — the one home the CLI's own `os.homedir()`-based
wallet setup always reads regardless of the caller's real `ANICCA_HOME` — reusing the existing,
already-correct derivation rather than inventing a new one), HALTING the pass (skip `franklin-trading
start` entirely — no LLM spend, no swap attempt, exit 0, zero new ledger lines, reason
`identity-mismatch`) UNLESS both derived addresses are non-empty AND equal (i.e. THIS instance's own
`ANICCA_HOME` resolution and Franklin's own `$HOME/.blockrun` resolution agree — which, by construction
of `resolve-identity.mjs`'s existing priority order, is true ONLY for the instance whose own
`ANICCA_HOME` literally IS `$HOME/.blockrun`); ONLY THEN SHALL THE SYSTEM evaluate
`skills/_shared/lib/earn-guard.mjs`'s cumulative fail-closed check for that wallet (both the
`{wallet, source: "sol-trade"}` scope and the wallet-wide `{wallet}` scope) against the shared
`earn-ledger.jsonl`, HALTING the pass (same skip/exit-0/zero-new-lines contract) if either scope reports
HALT; OTHERWISE, WHEN the pass's `franklin-trading start` invocation executes a real, on-chain-confirmed
Jupiter swap (its own stdout contains a `"Signature: <base58 sig>"` line, extracted via
`sol-trade/lib/parse-pass.mjs::extractLastSignature`) THE SYSTEM SHALL call the new
`sol-trade/lib/record-swap.mjs` (mirroring `clip-promote/record-payout.mjs`'s already-proven call
sequence verbatim), which SHALL verify that signature is confirmed on-chain via
`skills/_shared/lib/solana-verify.mjs::sigStatus(sig)` and compute this pass's USDC delta via THE SAME
MODULE's `usdcDeltaForSig(sig, wallet)` — summing ONLY that one signature's own pre/postTokenBalances for
the derived wallet — as the SOLE authoritative delta source (FIND-009: no `franklin-trading balance`
before/after CLI snapshot is read or relied upon anywhere in this mechanism, since a whole-pass window
would also pick up any unrelated transfer landing in that window, silently corrupting `net_usdc`; this
also eliminates FIND-010's chalk/ANSI-wrapped-stdout parsing risk entirely, since that CLI subcommand is
never invoked), and append exactly one line to `skills/earn/state/earn-ledger.jsonl` via
`skills/earn/lib/record.mjs` — carrying `sig`, `confirmed: true`, `chain: "solana"`,
`source: "sol-trade"`, `wallet` (the address derived in the first clause above), and
`earn_usdc`/`cost_usdc` derived from that delta's sign — so a losing pass is exactly as visible in the
ledger as a winning one. If the `sigStatus`/`usdcDeltaForSig` RPC call itself errors, times out, or
returns malformed data (an infrastructure failure, not a fact about the trade), `record-swap.mjs` SHALL
report a `verify-error` status and `sol-trade/run.sh` SHALL degrade to a narrate-only line rather than
crashing or recording a malformed delta (see Edge Cases) — this is the ONE read-failure degrade path
this requirement defines.

**Edge Cases**:
- `runtime/wallet-address-solana.mjs` cannot resolve THIS instance's own Solana secret for its own
  `ANICCA_HOME`, AND that `ANICCA_HOME` is also not Franklin's own `$HOME/.blockrun` (automaton's REAL
  shape, confirmed: no `~/.anicca/.automaton/solana.json` exists and
  `ANICCA_HOME=/Users/anicca/.anicca` != `.blockrun`): the own-derived address is empty, the
  identity-match guard (above) HALTS on it BEFORE `franklin-trading start` is ever invoked and BEFORE
  the cumulative `earn-guard.mjs` check even runs — this is fail-CLOSED, not a crash, never a fallback
  to a hardcoded address. This is the SPECIFIC branch that stops the already-live cross-instance leak
  (root cause 3): it MUST be asserted at the FULL `sol-trade/run.sh` integration level — a fixture
  `franklin-trading` PATH-stub asserted NEVER invoked — not merely by calling
  `wallet-address-solana.mjs` in isolation and observing empty stdout (PROP-011 alone proves the
  LOW-LEVEL derivation is empty; it does NOT prove the FULL pass boundary actually stops before the CLI
  runs).
- A hypothetical (not currently live) instance whose OWN `$ANICCA_HOME/.automaton/solana.json` resolves
  a real, non-empty Solana secret, but whose `ANICCA_HOME` is NOT Franklin's own `$HOME/.blockrun`: this
  instance's own-derived wallet address is real but has NO relationship to the wallet the
  `franklin-trading` CLI's own `os.homedir()`-based wallet setup will actually execute against this pass
  (confirmed: the CLI's bundled `@blockrun/llm` dependency's `setupAgentSolanaWallet()` reads
  `$HOME/.blockrun/.solana-session` unconditionally —
  `node_modules/@blockrun/llm/dist/index.js:4793-4794` — never `ANICCA_HOME`-gated). The identity-match
  guard MUST still HALT here (the two derived addresses differ) — "some wallet resolved" is NOT
  sufficient; it must be THE wallet the CLI will actually use.
- `ANICCA_SOLANA_PRIVATE_KEY` present in the ambient process environment BEFORE `sol-trade/run.sh`
  invokes `wallet-address-solana.mjs` (the ACTUAL highest-priority override on this exact call path —
  `resolveSolanaSecret`'s FIRST check, `resolve-identity.mjs:118-120` — the Solana twin of REQ-001's
  `ANICCA_EVM_PRIVATE_KEY` override): `sol-trade/run.sh` MUST proactively `unset` this variable before
  BOTH `wallet-address-solana.mjs` invocations (this instance's own, AND the forced-`$HOME/.blockrun`
  one) so a stray/inherited value can never silently override either derivation — mirroring REQ-001's
  defensive `unset ANICCA_EVM_PRIVATE_KEY`. This matters MORE now that the identity-match guard exists:
  a leaked `ANICCA_SOLANA_PRIVATE_KEY` set to Franklin's real secret would otherwise let ANY instance's
  own-derivation spuriously MATCH Franklin's wallet and defeat the identity-match check entirely — the
  exact class of contamination FIND-004 already identified and closed on the EVM side.
- The cumulative `earn-guard.mjs` check for this instance's own Solana wallet (scope
  `{wallet, source:"sol-trade"}` OR `{wallet}`) reports HALT (cumulative net below reserve, or an
  unparseable/untrustworthy ledger line for this wallet): the pass MUST stop BEFORE invoking
  `franklin-trading start` at all — no LLM spend, no swap attempt — and exit 0, exactly the one-line
  CLI idiom (`node .../earn-guard.mjs check "$WALLET" "sol-trade" "$LEDGER"`) `earn/run.sh:78` and
  `economy/gig/run.sh:62-65` already use at their own pass boundaries (per `skills/earn/SKILL.md:80-82`'s
  own documented convention: any skill that starts calling `record.mjs` must add this guard at its own
  pass boundary). This check runs ONLY after the identity-match guard above has already passed.
- The `sigStatus`/`usdcDeltaForSig` RPC call (via `solana-verify.mjs`, invoked through
  `record-swap.mjs`) itself errors, times out, or the RPC response is malformed — an INFRASTRUCTURE
  failure, distinct from "sigStatus reports the tx unconfirmed" below (a definitive on-chain fact,
  correctly recorded as silence): `sol-trade/run.sh` MUST degrade to a narrate-only line (mirroring the
  existing abort/error convention already proven at `earn/run.sh:308-319`'s swap-abort branch and
  `earn/run.sh:372-381`'s yield-abort branch — detect the `verify-error` status `record-swap.mjs`
  returns, record `task: 'sol-verify-failed:<reason>'` with `earn_usdc:0, cost_usdc:0`, exit 0) — NEVER
  crash the pass-boundary shell glue, and NEVER pass an unparseable/undefined delta into `record.mjs`
  (which would otherwise let `ledger.mjs:deriveLine`'s `Number(o.earn_usdc ?? 0)` silently coerce garbage
  to `NaN`/`0` rather than refusing to record a trustworthy line). This is the SOLE read-failure degrade
  path REQ-002 defines — no `franklin-trading balance` CLI read is performed or relied upon anywhere in
  this feature (FIND-009/FIND-010 resolution: the whole-pass balance-snapshot delta source and its
  chalk/ANSI-color-wrapped-stdout parsing risk, `dist/commands/balance.js:13`, are ELIMINATED, not merely
  hardened, since `usdcDeltaForSig`'s per-signature RPC computation is this feature's ONE authoritative
  delta mechanism).
- No `"Signature:"` line anywhere in the pass's stdout (the agent judged WAIT, per its own baseline
  strategy): ZERO new lines are appended to `earn-ledger.jsonl` this pass — the existing
  `state/sol-trade.trace.jsonl` narrate-only line (`run.sh:43-54`) is unchanged and remains the sole
  record of a no-trade pass.
- A `"Signature:"` line is present but `sigStatus()` (called via `record-swap.mjs`) reports it
  unconfirmed (a real, definitive on-chain fact — not the RPC-failure edge case above): no ledger line
  is appended (a dropped/failed tx must never masquerade as a completed pass); the reason is logged to
  stderr only.
- Multiple `"Signature:"` lines appear in one pass's stdout (a multi-step swap chain in a single
  session): only the LAST signature is recorded — one ledger line per pass, matching the append-only,
  one-line-per-pass convention every other earn skill already follows.
- The pass's USDC delta is NEGATIVE (the agent bought INTO a position, not yet realized): a line is
  still appended (`earn_usdc: 0`, `cost_usdc: |delta|`, `net_usdc < 0`) — this is a cost-basis event,
  not a claimed realized loss; downstream readers must be able to tell the two apart by `net_usdc`'s
  sign alone (no separate "realized" flag is invented by this feature).
- `source: "sol-trade"` is not yet on `identity-guard.mjs`'s `ALLOWED_EARN_SOURCES`: without this
  feature's one-line allowlist addition, `record.mjs`'s `assertOwnIdentityOnly()` would THROW (fail
  LOUD, visible in `run.sh`'s stderr) rather than silently drop the line — this feature adds the entry
  so the write path succeeds for Franklin's own Solana wallet (no user PII involved).
- This feature makes NO claim about GATE-0 (`isProfitable()` / `external: true`) for `sol-trade` lines
  — a same-wallet swap is not proven external revenue, so `external` is never set by this wiring;
  scope is P&L VISIBILITY only, not a new GATE-0 classification (that is a distinct, future decision).

**Acceptance Criteria**:
- Given a fixture `ANICCA_HOME` whose `.automaton/solana.json` (or legacy `.solana-session`, for
  Franklin's own home) resolves to a KNOWN base58 address, `sol-trade/run.sh`'s wallet-derivation step
  (via `runtime/wallet-address-solana.mjs`) resolves to that SAME address — never a hardcoded literal —
  and a fixture with NO resolvable secret yields an empty address (fail-closed). (This AC alone only
  proves the LOW-LEVEL derivation in isolation — see the FULL-INTEGRATION ACs immediately below for the
  actual pass-boundary guarantee.)
- Given a fixture `ANICCA_HOME` shaped like automaton's REAL home (no `.automaton/solana.json`, and NOT
  shaped like `.blockrun`), running the FULL `sol-trade/run.sh` pass boundary HALTS BEFORE invoking
  `franklin-trading start` — asserted via the fixture `franklin-trading` PATH-stub NEVER being invoked
  (not merely that `wallet-address-solana.mjs` alone prints nothing) — exits 0, and appends ZERO new
  `earn-ledger.jsonl` lines. This is the specific, already-live leak (root cause 3) this AC exists to
  close.
- Given a fixture `ANICCA_HOME` that is NOT `.blockrun`-shaped but DOES resolve a real (fixture)
  non-empty Solana secret via its own `.automaton/solana.json`, the SAME full pass boundary STILL HALTS
  before invoking `franklin-trading start` (the derived wallet does not equal the address derived by
  forcing `ANICCA_HOME=$HOME/.blockrun` for the same script) — proving the guard checks IDENTITY MATCH,
  not merely non-emptiness.
- Given the Franklin-shaped fixture `ANICCA_HOME` (`.blockrun`-shaped, its Solana secret readable via the
  SAME legacy `.solana-session` path the real CLI's own wallet setup reads), the identity-match guard
  does NOT halt (both derivations resolve to the SAME fixture address) — proving the guard is
  fail-closed for every instance EXCEPT the rightful owner, never fail-closed unconditionally.
- Given a fixture `earn-ledger.jsonl` whose cumulative `net_usdc` for `{wallet: <fixture Solana
  address>, source:"sol-trade"}` (or the wallet-wide scope) is already below the reserve, running
  `sol-trade/run.sh` (with the identity-match guard passing, Franklin-shaped fixture) HALTS before
  invoking `franklin-trading start` (asserted via the fixture PATH stub never being invoked / no new
  `trace.jsonl` "live-pass" line) and exits 0 without appending any new `earn-ledger.jsonl` line.
- A fixture run with `ANICCA_SOLANA_PRIVATE_KEY` set in the parent shell's ambient environment
  (simulating a leaked/inherited override, NOT sourced from any `.env` file) still resolves the SAME
  per-instance address (for both the own-`ANICCA_HOME` and forced-`.blockrun` derivations) as the same
  fixture without it set — proving the override never reaches either `wallet-address-solana.mjs`
  invocation.
- Given (a) a fixture `franklin-trading` executable placed first in `$PATH` for that one test
  invocation (a new, self-contained technique for this feature — no existing repo file stubs an
  external CLI's stdout this way) whose `start` output contains a real-shaped `Signature: <sig>` line,
  and (b) a LOCAL HTTP Solana RPC stub bound to a random port and wired in via `SOLANA_RPC_URL`
  (mirroring the ACTUAL proven `skills/earn/clip-promote/tests/fake_solana_rpc.mjs` pattern) reporting a
  confirmed status and a positive USDC delta, running `sol-trade/run.sh` appends exactly ONE new line to
  `state/earn-ledger.jsonl` with `sig`/`confirmed: true`/`chain: "solana"` and `net_usdc` equal to the
  stub's delta — proving the FULL `sigStatus` -> `usdcDeltaForSig` -> `record()` wiring inside the new
  `record-swap.mjs`, closing FIND-009's core complaint that no requirement previously mandated this call
  graph.
- `record-swap.mjs`'s own `recordSwap()` function, called directly with an injected `fetchImpl`
  (mirroring `clip-promote/tests/test_record_payout.mjs`'s ACTUAL proven pattern exactly), exercised with
  a NEGATIVE delta from `usdcDeltaForSig`, appends exactly one line with `net_usdc < 0` (`earn_usdc: 0`,
  `cost_usdc: |delta|`) — proving `record-swap.mjs`'s ONE deliberate difference from
  `record-payout.mjs` (which would reject this same delta as `zero-delta`): sol-trade accepts and records
  ANY confirmed delta, win or loss, per P&L-VISIBILITY scope. No CLI/RPC stub needed at this layer, only
  the injected `fetchImpl`.
- Given the fixture LOCAL HTTP Solana RPC stub (wired via `SOLANA_RPC_URL`, mirroring
  `fake_solana_rpc.mjs`) configured to error/time out/return malformed JSON for `getSignatureStatuses` or
  `getTransaction` on a pass whose stdout DOES contain a `Signature:` line, `sol-trade/run.sh` records
  exactly ONE narrate line (`earn_usdc:0, cost_usdc:0`, task prefixed `sol-verify-failed:`) and exits 0 —
  never a line with a `NaN`/`Infinity`-shaped `net_usdc`, and never a crash. No `franklin-trading
  balance` CLI call is made or parsed anywhere in this AC or elsewhere in this feature (FIND-009/FIND-010
  resolution — see REQ-002 EARS/Edge Cases).
- A fixture `start` output with NO `Signature:` line appends ZERO new lines to `earn-ledger.jsonl`
  (the pre-existing trace.jsonl line is the only side effect, unchanged).
- `record.mjs`'s `assertOwnIdentityOnly()` accepts `source: "sol-trade"` without throwing after the
  `identity-guard.mjs` allowlist change (regression-safe for every other existing allowed source),
  verified using the SAME `env -i` PII-isolation technique `clip-promote/tests/test_run.sh` already
  proves (a PII env var present THROWS on a direct `record.mjs` call; the same var stripped via
  `env -i` records cleanly) applied to the new `"sol-trade"` source.

## Non-functional requirements

- **Performance**: identity resolution and pass-output parsing are pure, in-process, sub-millisecond
  operations at wake scale (one wake every N minutes) — no new latency budget needed.
- **Security / money-safety**: no private key material is ever logged, echoed, or written to any
  ledger/trace file (existing R5 discipline, unchanged). The `earn-guard.mjs` cumulative fail-closed
  HALT (`run.sh:78`) must keep firing unconditionally regardless of this feature's changes (regression
  requirement, not new behavior), AND this feature adds the SAME cumulative fail-closed HALT at
  `sol-trade/run.sh`'s own pass boundary (new behavior, REQ-002), so a losing Solana trading loop can
  never run unbounded once its losses become ledger-visible. `ALLOWED_EARN_SOURCES` remains an explicit
  allowlist (no wildcard), so any earn source this feature does not explicitly add (`"sol-trade"`) stays
  rejected by default. `ANICCA_EVM_PRIVATE_KEY` — the actual highest-priority override on
  `resolveEvmPrivateKey`'s resolution path (`resolve-identity.mjs:63-67`) — MUST NEVER reach
  `earn/run.sh`'s own `resolve-identity.mjs evm` invocation (REQ-001); `sol-trade/run.sh` MUST derive its
  own Solana wallet address via `runtime/wallet-address-solana.mjs` (REQ-002), never a hardcoded literal.
  `ANICCA_SOLANA_PRIVATE_KEY` — the Solana twin of that same override, `resolveSolanaSecret`'s FIRST
  check (`resolve-identity.mjs:118-120`) — MUST NEVER reach `sol-trade/run.sh`'s own
  `wallet-address-solana.mjs` invocations either (REQ-002's new edge case, mirrors REQ-001). AND
  `sol-trade/run.sh` MUST HALT before invoking `franklin-trading start` whenever its own derived Solana
  wallet does not equal the wallet Franklin's `$HOME/.blockrun`-scoped `franklin-trading` CLI will
  actually execute against — the identity-match guard that closes the already-live cross-instance leak
  (root cause 3), since the external CLI itself performs NO `ANICCA_HOME` scoping of its own (confirmed:
  `os.homedir()`-based `BLOCKRUN_DIR`/`SOLANA_WALLET_FILE`, `@blockrun/franklin-trading@0.2.4`'s
  `dist/config.js:15` and its bundled `@blockrun/llm`'s `dist/index.js:4793-4794`).
- **Safety constraint (colony-wide)**: automaton (`ANICCA_HOME=~/.anicca`) MUST be non-regressed by
  REQ-001 — verified by an explicit fixture test asserting its resolved address (derived from the
  private key, never a nonexistent `address` field) is unchanged. No other
  instance's identity, cron job, or `~/.openclaw`/`~/.anicca` runtime state is modified by this
  feature. Symmetrically, automaton MUST be POSITIVELY STOPPED (not merely "unchanged") from executing
  `franklin-trading start` under REQ-002 — this feature's identity-match guard is the fix for the
  ALREADY-LIVE leak documented in root cause 3 (70 real `franklin-trading` passes recorded under
  automaton's own `ANICCA_HOME` since 2026-07-04), verified by an explicit full-integration fixture test
  asserting the fixture `franklin-trading` PATH-stub is NEVER invoked when the fixture `ANICCA_HOME` is
  automaton-shaped.
