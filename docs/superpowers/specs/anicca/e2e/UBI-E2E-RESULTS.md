# UBI E2E results — HONEST status (corrected 2026-06-18)

## TRUTH (no overclaim)
**No end-to-end test where a real human RECEIVES money in a usable form is complete.** What is
actually proven so far is ONLY: "anicca can broadcast a real USDC transfer on Base." That is NOT
"a person received basic income and can spend it / get it to their bank."

| TestID | what was ACTUALLY done | what is NOT proven (the gap) | honest status |
|---|---|---|---|
| UBI-E1 wallet | Real on-chain USDC transfer from anicca wallet (0xa3CDd4) to a **throwaway address I control** (0xF4776B, $0.20, tx 0x3d6be651, status 0x1). | A real END USER receiving to THEIR own wallet + using it. Sending to my own test address is NOT a user receiving. | on-chain SEND proven only |
| UBI-E2 email (Crossmint) | Created a Crossmint email-owned smart wallet (0x9557…, owner keiodaisuke@gmail.com) + transferred $0.50 USDC on-chain (tx 0x421f0307). | **The email owner (Dais) CANNOT yet log in and see/withdraw it** — there is NO consumer UI for it, and I did NOT verify any hosted Crossmint login works for an API-created wallet. I earlier told Dais "sign in at crossmint.com" — that was UNVERIFIED / likely wrong. = NOT a usable receive. OVERCLAIM, corrected. | money is in a wallet Dais can't yet touch |
| UBI-E3 bank/PayPay (JP) | nothing | The entire USDC(Base) → JPY → bank/PayPay path. UNVERIFIED which exchange even accepts USDC on Base + allows JPY bank withdrawal. | NOT started / UNVERIFIED |
| UBI-E3 bank (US) | nothing | USDC → USD bank. | NOT started |

## UBI-E1-FULL — wallet PATH end-to-end (form→queue→watcher→send→arrival) — ✅ PASS (2026-06-18)
Not just a raw send: the whole product flow, verified by me.
1. POST to LIVE `https://aniccaai.com/.netlify/functions/income-signup` {method:wallet, wallet:0x36cFc9…} → `{ok:true,recorded:true}` (Supabase status=queued).
2. `~/anicca/skills/earn/ubi-payout-watcher.mjs` read queued → execute-ubi sent real $0.10 → tx 0x007a856f4f83e89cd900c21302cc61e9cccd7114e60ba66145a2dac9c2a2b07b (status 0x1) → Supabase status→paid (204).
3. On-chain balanceOf(0x36cFc9…) = **0.10 USDC** verified.
Recipient key saved /tmp/ubi-wallet-e2e.json (fresh, I control). For a real human they paste their own address; the PATH is proven. Watcher is idempotent (only status=queued).
REMAINING for wallet: a real human submitting THEIR own address + seeing it in their own wallet app (trivial; same path).

## UBI-E2-PAGE — email access/withdraw page — built+live, OTP BLOCKED on Crossmint config (2026-06-18)
- Built `/income/wallet` (Crossmint SDK v4.2.11: CrossmintProvider + Auth + Wallet, email-OTP login → balance → wallet.send withdraw → ExportPrivateKeyButton). Local build green (96 pages). Deployed to prod (PR #89). client key wired via NEXT_PUBLIC_CROSSMINT_CLIENT_KEY (GHA secret + .env.local, NOT committed).
- VERIFIED live: page renders (not config-fallback); camofox opened it, clicked sign-in, the Crossmint modal rendered INLINE (no iframe), accepted keiodaisuke@gmail.com, Submit fired.
- **BLOCKER (honest):** OTP send returns "Failed to send email. Please try again or contact support." Repeated. A patched window.fetch captured ZERO crossmint calls → the auth request is rejected at origin/config before sending, OR uses non-fetch transport. Most likely cause: the **client key (ck_production…) is not authorized for origin aniccaai.com and/or Email login method is not enabled** in the Crossmint console (server-key wallet creation worked because server keys are not origin-scoped).
- **FIX needed (Crossmint console, ~2 min):** crossmint.com/console → project → the client key → add allowed origin `https://aniccaai.com` (+ localhost for dev) → enable **Email** login method. Then re-run this E2E (login as keiodaisuke → OTP via Gmail → see the $0.50 in wallet 0x9557…).
- So email PATH = page done, but NOT usable until the Crossmint client-key origin/email config is set. NOT claiming email done.

## What "done" must mean (no more lies)
A path is done ONLY when a real person, on a named website, taps named buttons, and ends with money
they can SPEND (in their wallet they control, or yen/USD in their bank / PayPay) — verified by that
person seeing it. On-chain transfer alone ≠ done.

## Open research (being answered by a dedicated agent, with citations)
1. Real working USDC(Base) → JPY → MUFG/PayPay path: which JP exchange accepts USDC on the Base network for deposit AND allows JPY bank withdrawal? Exact steps, fees, minimums.
2. US/EN: USDC → USD bank, the simplest real path.
3. Crossmint email wallet: can the end user independently access + withdraw (hosted UI?), or must we build the access page?
