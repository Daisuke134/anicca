# UBI Realtime Demo Runbook (wallet + email, live)

How to demo Anicca paying real basic income, end-to-end, with no human in the loop. Two rails are
already proven live; bank/M-Pesa rails are account-gated (see SKILL.md / tasks #37 #50 #52).

| Rail | Status | Script | Proof |
|---|---|---|---|
| **On-chain wallet** (USDC on Base → recipient address) | ✅ live | `execute-ubi.py` (via `distribute-ubi.mjs`) | real $0.5 USDC tx on Basescan (task #29) |
| **Email wallet** (Crossmint custodial USDC → email) | ✅ live | Crossmint create-wallet + transfer (`ubi-payout-watcher.mjs`) | real USDC to a fresh email (task #30) |
| US bank offramp | ⏳ code-ready | `crossmint-offramp.mjs` | gated on CSE `bankAccountId` (#50) |
| JP bank 振込 | ⏳ code-ready | `gmo-furikomi.mjs` + `bank-payout-watcher.mjs` | gated on 法人/個人口座 (#51/#52/#53) |
| M-Pesa mobile money | ⏳ verified rail | `kotani-payout.mjs` (TODO) | gated on Kotani onboarding (#37) |

## Prereqs (env, never committed — ~/.local/state/life-manager/.env)
- `BLOCKRUN_WALLET_KEY` (or the anicca wallet private key) — funds the on-chain sends, own wallet only.
- `CROSSMINT_API_KEY` + `CROSSMINT_CLIENT_KEY` — email-wallet rail.
- A funded Base USDC balance in anicca's wallet (check before demo).
- `identity-guard` fails CLOSED if any user-PII env (gmail/gcal/google-login) leaks into the process — run the
  payout scripts with a minimal allowlisted env only.

## Demo A — on-chain wallet payout (fastest, fully autonomous)
```bash
cd $LIFE_MANAGER_REPO/skills/ubi
# 1. confirm balance (before)
node -e "import('../_shared/lib/usdc.mjs').then(m=>m.usdcBalance(process.env.ANICCA_WALLET)).then(console.log)"
# 2. send a small real UBI to a demo recipient (anicca's own key signs; no human)
node distribute-ubi.mjs '{"wallet":"<anicca>","source":"demo","task":"demo","earn_usdc":1,"cost_usdc":0,"wake":"demo"}'
#    -> distribute-ubi plans the split (lib/ubi.mjs) and shells execute-ubi.py for the real ERC20 transfer
# 3. VERIFY (fresh evidence, not a claim): balance delta + tx receipt 0x1
node -e "import('../_shared/lib/usdc.mjs').then(m=>m.usdcBalance(process.env.ANICCA_WALLET)).then(console.log)"  # after < before
#    open the tx hash on https://basescan.org/tx/<hash> -> Status: Success, USDC Transfer to recipient
```

## Demo B — email wallet payout (no recipient wallet needed)
```bash
# Recipient supplies only an email. Crossmint mints a custodial USDC wallet tied to that email and
# funds it; the recipient later claims/withdraws. Trigger via the watcher path:
cd $LIFE_MANAGER_REPO/skills/ubi
SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... CROSSMINT_API_KEY=... \
  node ubi-payout-watcher.mjs            # processes queued email recipients once
# VERIFY: the recipient's email receives the Crossmint claim link; Crossmint console shows the USDC
#         credited to that email's wallet (task #30 evidence).
```

## Live demo script (combined, for a recording/stream)
1. Show anicca's Base USDC balance (Basescan).
2. A "person" enters a wallet address OR an email at aniccaai.com/income.
3. Run Demo A or B for that recipient.
4. Show the on-chain tx (Basescan, Status Success) OR the email's Crossmint claim — money arrived,
   no human in the loop, anicca's own funds.
5. Point at the ledger line appended (`state/*-ledger.jsonl`) as the immutable record.

## DO-NOT (money-safety)
- Never auto-resend a failed/uncertain payout — it goes to needs_review (a human confirms before re-send).
- Own-funds only — the identity guard halts if PII env leaks; keep the env allowlist minimal.
- Verify with FRESH evidence (balance delta + receipt 0x1 / Crossmint console), never a bare "sent ✓".
