# Money-Safety Adversary Verdict — `$LIFE_MANAGER_REPO/skills/earn/funding/` (origin/main 568fecb)

Fresh-context, disk-only, read-only review. No money moved, no code edited. Reviewed against
`$LIFE_MANAGER_REPO/docs/loop-engineering/11-parent-funding-loop.md` §2 (mechanism) + §3
(money-safety rails). Cross-checked contract addresses / function signatures / API shapes
against live official docs (Polymarket docs, relay.link docs) via `firecrawl scrape`, and
against the actually-installed `polymarket` SDK source
(`~/.anicca-founder/agents/polymarket-agent/.venv/.../polymarket/clients/secure.py`,
`.../relayer/calls.py`). Ran the real `pytest` suite (pure/offline, no keys/network) to verify
the "28 tests" claim.

## 1. withdraw.py / `--include-pusd` unwrap — **PASS** (the one genuinely novel on-chain call)

- `CollateralOfframp` address `0x2957922Eb93258b93368531d39fAcCA3B4dC5854` — **confirmed
  correct** against `docs.polymarket.com/resources/contracts` ("Collateral Contracts" table),
  live-scraped 2026-07-08.
- `unwrap(address _asset, address _to, uint256 _amount)` — **confirmed correct** signature and
  parameter order against `docs.polymarket.com/concepts/pusd` ("Unwrapping" section), live-scraped.
  `withdraw.py:85-95` (`_unwrap_call`) builds `keccak(b"unwrap(address,address,uint256)")[:4] +
  abi_encode(["address","address","uint256"], [asset, to, amount_units])` — selector and arg
  order match the doc's signature exactly. `_unwrap_call(USDCE, deposit_wallet, used_pusd_units)`
  correctly binds `_asset=USDCE` ("Must be USDC.e" per docs) and `_to=deposit_wallet` (keeps the
  unwrapped USDC.e inside the deposit wallet for the *next*, separate `transfer_erc20` hop).
- Docs require "The caller must first approve the CollateralOfframp contract to spend their
  pUSD" — `withdraw.py:206` (`client.approve_erc20(token_address=PUSD, spender_address=OFFRAMP,
  amount="max")`) runs immediately before the unwrap dispatch. Correct ordering.
- The encoding primitive (`keccak` selector + `eth_abi.encode`) is **byte-for-byte the same
  pattern** the SDK's own `erc20_transfer_call`/`erc20_approval_call` use
  (`polymarket/_internal/actions/relayer/calls.py:54-90`), and the dispatch call
  (`client._dispatch_single_call`) is the exact same method `approve_erc20`/`transfer_erc20`
  already use internally (`polymarket/clients/secure.py:1944-2006, 2259-2264`) — i.e. this is
  genuinely "no new mechanism," just a new payload through an already-proven pipe (the same pipe
  this repo's own `fund_via_bridge.py` already uses live for `approve_erc20`/`transfer_erc20`).
- `transfer_units = min(amount_units, usdce_units + used_pusd_units)` never requests more than
  what's actually available post-unwrap — no overdraw risk.
- Signer identity (`verify_evm_address(candidate=acct.address, known_address=OWNER_EOA)`) and
  deposit-wallet identity (`verify_evm_address(candidate=deposit_wallet, known_address=
  DEPOSIT_WALLET)`, from the SDK's own derivation, not a banner) are both checked before any
  balance read or transfer — "proxy banner distrust rail" holds.
- **Finding A (see §7, cross-cutting)** applies here too: `unwrap_handle.wait()` (line 211) and
  `handle.wait()` (line 221) / `eth_tx_confirmed_success` (lines 212, 224) are not wrapped in
  try/except.

## 2. bridge.py — **PASS with one forward-risk (B)**

- Sender/recipient identity checks (`verify_evm_address` for 0x810f, `verify_solana_secret_file`
  for BF9v) run before any balance read.
- `amount_usd` is re-derived from a **live** `erc20_balance_units` read of the real 0x810f
  balance and clipped to it — never blindly trusts a passed `--amount-usd`.
- `bridge_max_fee_pct` (15%) fail-closes uneconomic transfers; SKILL.md documents this was
  already live-verified rejecting a sub-economic amount with `AMOUNT_TOO_LOW`.
- **Finding B**: posts to `https://api.relay.link/quote` — this endpoint is listed under
  **"Deprecated"** in `docs.relay.link`'s own nav (superseded by `POST /quote/v2`), confirmed
  live 2026-07-08. Response schema (`details.currencyIn/currencyOut`, `steps[].items[].data`)
  is identical between the deprecated and v2 docs pages, and this repo has prior live success
  with the same endpoint (`$10→$9.95, 0.46% fee` per `10-STATUS-verified.md`), so it works
  *today* — but a deprecated endpoint can be sunset without notice. Not blocking for a one-off
  D1 test; should migrate to `/quote/v2` before this becomes a scheduled/cron dependency.
- **Finding A** (see §7): the entire broadcast loop (`bridge.py:181-219` — `w3.eth.
  send_raw_transaction`, `w3.eth.wait_for_transaction_receipt`, `eth_tx_confirmed_success`) has
  **no try/except at all**, the weakest instance of Finding A in the three scripts.

## 3. send_to_franklin.py — **PASS** (this is the actual Efpap5-incident fix, and it's real)

- `recipient_check = verify_solana_secret_file(path=FRANKLIN_SESSION_PATH, known_address=
  FRANKLIN_SOLANA)` (line 98-103) derives Franklin's pubkey **from Franklin's own on-disk key
  material**, not from any label/banner/env var, and refuses to send on any mismatch, missing
  file, or decode error (all fail-closed, verified by `test_verify_solana_secret_file_*` — see
  §9). No flag bypasses this check (confirmed by reading the whole file — there is genuinely no
  override branch).
- Sender identity is checked the same way against BF9v.
- Amount is re-derived from a live `spl_token_balance_units` read, clipped to it.
- One operational (not money-safety) gotcha (**Finding E**): `spl_transfer` never passes
  `fund_recipient=True`; if Franklin's USDC associated token account doesn't yet exist, the
  `spl-token transfer` CLI call fails closed (`ok:False`, no funds move) rather than losing
  money — a D1 dry run would just need `--fund-recipient` wired in if this happens.
- **Finding A** (narrower here): `confirmed_success(SOLANA_RPC, signature)` (line 178) is not
  wrapped in try/except, but `spl_transfer` itself already safely returns `{ok:False, error}` on
  subprocess failure rather than raising, so the blast radius is limited to the RPC-confirmation
  call only.

## 4. lib/caps.py — **PASS**, with one informational note (C)

- `check_caps` is pure, fails closed on non-positive/non-numeric amounts, only counts
  `status=="sent"` rows (failed/skipped/dry never consume headroom — verified by
  `test_daily_cap_ignores_failed_and_dry_rows`).
- `reserve_protected_amount` fails closed to 0.0 on bad input types (verified by
  `test_reserve_protected_amount_bad_inputs_fail_closed`).
- **Finding C (informational, safety-conservative direction only)**: `_sent_rows` sums `sent`
  rows across **all three steps** (withdraw + bridge + send_to_franklin) from one shared
  ledger file with no `step` filter. Since `run.py` pushes the same logical dollar amount through
  all three hops, one logical "$X funded to Franklin" event writes ~3 "sent" rows of ~$X each,
  so daily/cumulative caps are consumed **~3x faster** than the config numbers suggest (e.g. the
  $50 cumulative cap effectively caps ~$16-17 of real end-to-end funding, not $50). This can only
  make the system *more* conservative (block sooner), never permit more real spend than
  intended — not a money-loss risk, just worth knowing before assuming the config numbers are
  the real ceiling.

## 5. lib/identity.py + lib/kill_switch.py — **PASS**

- Both EVM and Solana identity checks derive the address from actual key material (`eth_account.
  Account.from_key` for EVM, `solders.Keypair` decode for Solana) and compare against a
  hardcoded, config-sourced known-good address — never trust a displayed/labeled string. This is
  a real fix for the stated Efpap5 incident, not just a comment claiming one.
- `keypair_from_secret_string`'s base58-then-base64 fallback is a deterministic format parse (not
  a judgment call) and is regression-tested against the actual base64-mislabeled-as-base58 file
  shape this repo has hit live (`test_keypair_from_secret_string_accepts_base64_fallback`,
  `test_verify_solana_secret_file_json_wrapped_base64`).
- `kill_switch.is_killed` is a one-line file-existence check, consistent with the existing
  `polymarket-trade` KILL convention; checked once at the top of every script's `main()`
  (fail-closed at start, matches the documented convention — not designed to abort mid-flight).

## 6. lib/ledger.py — **PASS**

- `read_ledger` returns `[]` on missing file (never raises on first run).
- `append_ledger` creates parent dirs, appends one JSON line, never mutates the `extra` dict
  passed in (verified by `test_build_row_pure_no_mutation_of_extra`).
- On-chain confirmation happens **before** any `status:"sent"` row is built/appended, in all
  three scripts (checked the exact control flow in each file) — satisfies the "on-chain hash +
  status 0x1 before recording success" MUST, structurally.

## 7. Finding A (cross-cutting, the one real structural gap) — **applies to all 3 scripts**

None of `withdraw.py`, `bridge.py`, `send_to_franklin.py` wraps the post-broadcast
confirmation/wait calls in try/except:
- `withdraw.py:211,221,224` (`unwrap_handle.wait()`, `handle.wait()`, `eth_tx_confirmed_success`)
- `bridge.py:181-219` (entire broadcast loop: `send_raw_transaction`,
  `wait_for_transaction_receipt`, `eth_tx_confirmed_success`) — weakest case, no try/except at all
- `send_to_franklin.py:178` (`confirmed_success`)

These are network calls (RPC reads) that can raise on transient failure (timeout, rate limit,
`web3.exceptions.TimeExhausted`). If one raises **after** a real transfer has already been
broadcast (and possibly already confirmed on-chain), the script crashes with an uncaught
exception and **no ledger row is written at all** — not even a "failed" one. Consequences:
1. Breaks the audit-trail MUST (§3 "全 decision + tx を記録").
2. Breaks cap enforcement: `check_caps` sums only `status=="sent"` ledger rows, so a subsequent
   re-run would not see money that already moved, and could permit a further real transfer that,
   combined with the untracked one, exceeds the intended per-transfer/daily/cumulative caps.

Blast radius today is small (each individual call is still capped at `per_transfer_usd_cap=$5`
regardless of history, and this requires a genuine transient RPC failure landing in the exact
window after broadcast/before confirmation), but this should be fixed — wrap the
confirm-and-record sequence in try/except and, on exception, still write a best-effort
"unknown / needs manual reconciliation" ledger row with whatever tx_hash/signature was obtained
— before scaling past a manually-supervised D1 test (i.e. before D2's $10-20 seed, and
definitely before any unattended/cron wiring, which the parent spec already defers to a later
feature).

`run.py` itself is fail-closed against this at the *pipeline* level (a crashed step produces
unparseable stdout, which `run.py:54-57`'s except-branch turns into `{"ok": False, ...}`,
halting the chain) — so a single `run.py` invocation will not blindly cascade into bridging/
sending money that wasn't actually confirmed. The residual risk is specifically about a
*second, later* invocation not knowing the first one's money already moved.

## 8. Config / known addresses — **PASS**

`config.json`'s `known_addresses` (`pm_deposit_wallet` 0x904B…, `owner_eoa_polygon` 0x810F…,
`founder_solana` BF9v…, `franklin_solana` 8Fpqd…) and `tokens` (pUSD, USDC.e, USDC-Solana-mint,
CollateralOfframp) match this session's own canonical wallet memory and the task brief exactly,
and the CollateralOfframp/pUSD addresses are independently confirmed against live Polymarket
docs (see §1). No address-swap risk found in config.

## 9. tests/ — **PASS, genuinely tests real logic (not gamed)**

Ran the actual suite (`/home/life-manager/.local/bin/python3 -m pytest tests -v`, system Python, no
network, no real keys — `Keypair()` generates fresh random test keys, `tmp_path` fixtures for
files):

```
28 passed in 0.09s
```

Tests exercise real fail-closed edge cases, not trivial happy-path-only checks: non-positive
amounts, per-transfer/daily/cumulative cap boundaries, daily-cap staleness (>24h excluded),
failed/dry/skipped rows never consuming cap headroom, reserve-protection negative-clamping and
bad-input handling, EVM address case-insensitivity and missing-input handling, Solana identity
mismatch (the literal Efpap5 scenario, by name), missing files, garbage key content, the real
base64-mislabeled-as-base58 wallet-file bug this repo already hit live, and ledger
non-mutation/append/round-trip. Scope is honestly limited to `lib/caps.py`, `lib/identity.py`,
`lib/ledger.py` (as SKILL.md states) — there are **no** tests for `lib/erc20.py`,
`lib/solana_cli.py`, `lib/solana_rpc.py`, or the orchestration scripts themselves, so Finding A
(the exception-handling gap) would not have been caught by this suite; that's a coverage gap to
note, not a misrepresentation — the skill never claimed broader coverage.

## OVERALL VERDICT

**Safe to run the $1-2 D1 test now, as a single, manually-watched, manually-invoked run — not
yet safe to leave unattended or on a schedule.**

Rationale: the one genuinely novel on-chain call (`--include-pusd` unwrap) is independently
verified correct against official docs at the address/signature/encoding level, and is dispatched
through the exact same, already-proven SDK code path as this repo's existing live
`transfer_erc20`/`approve_erc20` calls — this is real engineering parity, not an unverified leap.
All seven §3 money-safety rails (identity, caps, reserve, on-chain confirm-before-record,
kill-switch, ledger, no-touching-other-wallets) are implemented as real logic with real tests,
not as comments. Findings B/C/E are non-blocking (deprecated-but-working endpoint, over-
conservative cap accounting, and a fail-closed operational gotcha, respectively).

Before D1:
- Run manually, watch stdout/stderr live, so Finding A's failure window (a crash between
  broadcast and confirmation) is immediately visible for manual reconciliation rather than
  silently retried or assumed to have failed-with-no-effect.
- Pass an explicit small `--amount-usd` (e.g. `2`) rather than defaulting to "everything above
  reserve," to keep the untested-on-chain unwrap call's first real blast radius minimal.

Before D2 ($10-20 seed) or any scheduled/unattended wiring (§5 already defers scheduling to a
later feature — do not bring it forward without this fix):
- **Fix Finding A**: wrap the post-broadcast wait/confirm calls in try/except in all three
  scripts, and on exception still write a best-effort ledger row (status e.g. `"unknown"`, with
  whatever tx_hash/signature is available) so a crash can never leave a real transfer completely
  unlogged.
- Migrate bridge.py from `https://api.relay.link/quote` to `/quote/v2` (Finding B) before this
  becomes a recurring dependency.
