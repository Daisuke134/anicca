# Iteration 2 — Spec Revision Note

- **feature**: trading-polymarket-spawn
- **phase**: 1c (spec review re-submit)
- **iteration**: 2
- **addressing**: iteration-1 FAIL (13 findings: 4 critical, 3 high, 6 medium)
- **timestamp**: 2026-07-01

## Changes made to behavioral-spec.md and verification-architecture.md

### FIND-001 (CRITICAL): Wallet isolation — child shares $HOME so reads parent wallet
**Fix**: All runtime modules (`proxy.mjs`, `execute-yield.mjs`, `hl.py`, `anicca-daemon.sh` ensure_brain)
resolve the wallet from `process.env.HOME + "/.automaton/wallet.json"` — not from `$ANICCA_HOME`.
REQ-R1 now documents this explicitly. REQ-S5 now launches the child daemon with `HOME=$CHILD_HOME`,
causing the entire child process tree to read `$CHILD_HOME/.automaton/wallet.json`. REQ-R2 acceptance
criteria updated to reference `$HOME` isolation, not `$ANICCA_HOME`. PROP-R6 added to integration
test suite to verify child `$HOME` = `$CHILD_HOME` and wallet path ≠ parent.

### FIND-002 (CRITICAL): INV-7 earn gate — skeleton REQ-G2 cannot verify on-chain settlement
**Fix**: pm-trade no longer uses the skeleton's REQ-G2 three-check gate for earn recording.
REQ-T8 now defines a dedicated `settle-verify.py` on-chain verification path:
- Polymarket: `eth_getLogs` on Polygon for USDC Transfer to our wallet matching resolved market.
- Hyperliquid: HL REST API clearinghouseState realizedPnl delta verification.
Earn row is written ONLY when `settle-verify.py` returns `{verified: true}`. PROP-T26 added.
Anti-slop table updated to reference `settle-verify.py` instead of REQ-G2.

### FIND-003 (CRITICAL): riskGate purity contradiction — current_balance and edge not in signature
**Fix**: `riskGate` signature is now `riskGate(risk_state, position_usdc, current_balance, edge, config)`
in both the Purity Boundary table (behavioral-spec) and Pure Core table (verification-architecture).
REQ-T4 now explicitly states: the effectful shell reads `current_balance` from RPC and receives `edge`
from the model's REQ-T3 output, then passes both as explicit args before calling `riskGate`.
No RPC call or file read occurs inside `riskGate`. PROP-T6 and PROP-T11 updated accordingly.

### FIND-004 (CRITICAL): Child runs on parent brain — :8402 single port, key from parent HOME
**Fix**: REQ-S5 now assigns `CHILD_PORT` (free port in 8403..8499). Child is launched with
`HOME=$CHILD_HOME COMPUTE_PROXY_PORT=$CHILD_PORT`. The child's `anicca-daemon.sh` ensure_brain
derives the key from `$HOME/.openclaw/.env` → `$HOME/.automaton/wallet.json` (both under $CHILD_HOME).
With `$CHILD_PORT` ≠ 8402, ensure_brain finds nothing there and starts its own ClawRouter on
`$CHILD_PORT` using the child's wallet. REQ-S5 documents the isolation mechanism in detail.

### FIND-005 (HIGH): REQ-R5 wrong module name + fail-open
**Fix**: REQ-R5 now correctly names `execute-yield.mjs` (not `yield-keeper.mjs`) as the module
with the surplus calculation. Fail behavior changed to fail-SAFE: when `reserved.json` is absent
or stale AND `earn/pm-trade` is a live registered slot, `execute-yield.mjs` deploys $0 (holds all
idle USDC as reserved). Legacy behavior (no trading slot registered) unchanged. PROP-R5 updated
to cover all 3 cases. INT-T21 added.

### FIND-006 (HIGH): Spawn double-seed TOCTOU
**Fix**: REQ-S2 now includes step (a-pre): acquire exclusive `flock -n` on `$ANICCA_HOME/state/spawn.lock`
before reading spawn-log and before writing the "initiated" row; release after step (e). If lock
cannot be acquired, abort with `spawn_lock_held`. PROP-S14 added.

### FIND-007 (HIGH): Geoblock Kalshi reroute needs KYC + flag not detected
**Fix**: REQ-T10 now explicitly states Kalshi MUST NOT be used for real stakes (SSN/identity KYC
required = J8 violation). Real-stake fallback for US-jurisdiction instances is Hyperliquid perps
only (via `hl.py`; no identity KYC required with an EVM wallet). Menu.json now requires `kyc_required`
field; `install.sh` provisions all venues with `kyc_required: true` and `jurisdiction_ok_for_real: false`
by default (fail-closed). Belt-and-suspenders check: venue with `kyc_required: true` is never
selected for real stake even if `jurisdiction_ok_for_real: true` is set.

### Medium findings also addressed:
- **FIND-008**: REQ-T5 `market_p` fixed to "mid price" (`(best_bid + best_ask) / 2`) consistently with REQ-T3.
- **FIND-009**: REQ-T6 now specifies exact adversary PASS file path (`$ANICCA_HOME/loops/earn-pm-trade/adversary-pass.json`) and schema.
- **FIND-011**: REQ-R2 corrected — `ensure-solana-wallet.mjs` creates `solana.json` (ed25519), NOT `wallet.json`. EVM key gen is REQ-S2(c) step (secp256k1 via viem `generatePrivateKey`).
- **FIND-012**: REQ-S3 adds step (c) for `pip3 install` from `requirements.txt` during child provisioning. NFR-1 updated to mention `requirements.txt`.
- **FIND-013**: REQ-T7 removes Hyperliquid from `pm.py`; Hyperliquid dispatched to existing `hl.py` (which enforces SL+TP). `pm.py` covers Polymarket + Kalshi CLOBs only.
