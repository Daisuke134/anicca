# B1 NO-MOCK E2E EVIDENCE — real Akash sandbox-2, 2026-06-27

Wallet `akash1ms7gr5sxkv33ra353hg5lu8dm7akljdaamj523` (key `anicca-akash`, test keyring = no-human, no password).
Network sandbox-2 (`rpc.sandbox-2.aksh.pw`), `provider-services v0.11.1`. Everything below is a REAL on-chain tx, not a mock.

## Verified facts (each corrects a wrong assumption)
1. **Funding** — faucet `POST https://faucet.sandbox-2.aksh.pw/faucet {address}` → uakt, NO captcha. ~75 AKT.
2. **ACT mint** — `akash tx bme mint-act <X>uakt`. My 5 AKT + 11 AKT mints were `ledger_record_status_canceled`,
   `cancel_reason: 6` = **BMCancelReasonMinimumMint** (proto: "mint output below minimum threshold"). `bme params`
   `min_mint = 10,000,000 uact`; at `P_mint ≈ 0.66` (AKT≈$0.66) a 11 AKT mint = ~7.3M uact < 10M → canceled+refunded.
   **25 AKT → 16,578,449 uact EXECUTED.** Verify ACT via `akash query bme ledger --owner <addr>` (status executed),
   not bank balances alone (ACT is a non-transferable ledger credit per AEP-76, though it also shows in bank).
3. **Escrow denom = uact REQUIRED** — a uakt-priced deploy → on-chain `Deposit invalid` / `Mismatched (uact != uakt)`.
   `deployment create --deposit 5000000uact` (uact SDL pricing) → **code 0** (no error). uakt is gas only.
4. **dseq location** — in `provider-services tx deployment create -o json` the events are DECODED; dseq is in
   `events[] | select(.type=="akash.deployment.v1.EventDeploymentCreated") | .attributes[] | select(.key=="id") |
   (.value|fromjson).dseq`. The `id` attribute VALUE is a JSON string `{"owner":..,"dseq":".."}`. My old
   `select(.key=="dseq")` returned EMPTY. Verified: tx 6BD4..→4070910, another →4070960.
5. **bid** — providers DO exist (100 bids on sandbox). bid_id path = **`.bid.id`** `{owner,dseq,gseq,oseq,provider,bseq}`,
   `.bid.state=="open"`, `.bid.price.denom=="uact"` (decimal amount). My old `.bid.bid_id` returned null.
6. **lease** — `tx market lease create` → code 0; `.leases[].lease.state == "active"`. (My lease parse was already right.)
7. **send-manifest → 400** from the sandbox test-provider `akash1rk09..` (it bids but does not host). The flow
   create→bid→lease is proven end-to-end on the real chain; container-boot must be confirmed on MAINNET (real provider).

## Outcome
`deploy-akash.sh` + `test-deploy-akash.sh` updated so every parse matches the above; the test fake jq-builds these
real shapes (non-circular). GREEN. Remaining: B1.3 treasury (mint ≥ min_mint off-path) · B1.5 mainnet boot.

## B1.3 treasury — LIVE on sandbox-2 (akt-treasury.sh)
- Ran `akt-treasury.sh` against the real chain: it read uact below buffer, minted 25 AKT, and confirmed via the
  balance delta: **`uact 18139615 → 34673369` EXECUTED**, exit 0. Real, not a mock.
- The LIVE run caught 2 bugs the unit-test mock could not: (1) a global `AKASH_OUTPUT=json` export breaks
  `keys show -a` ("cannot use --output with --address") — removed from both scripts, each call passes `-o json`
  explicitly; (2) `bme ledger records[-1]` is NOT the newest record (an executed mint left records[-1] on an older
  canceled one) — so the mint is confirmed by the uact BALANCE DELTA, never by `records[-1]`.

## deploy-akash.sh — LIVE integration on sandbox-2 (AKASH_IMAGE=nginx)
- Ran the WHOLE `deploy-akash.sh` end-to-end. It passed cert → deployment create → bid poll → lease create →
  lease-active, then exited 1 at `send-manifest failed after retries` (the sandbox test-provider 400s, as expected) —
  printing NO dseq (fail-closed, HARD 0.24). So the full script's parses + flow work on the real chain through
  lease-active; only the manifest→boot needs a real mainnet provider (B1.5).
