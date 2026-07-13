---
name: clipaffiliates-driver
description: Drive ClipAffiliates (clipaffiliates.com) end-to-end — signup, login, bind/swap USDC-Solana payout wallet, link social accounts, submit clips, read payout status — via the CloakBrowser daily-driver CDP path and the discovered REST API on `api.clipaffiliates.com`. Use when working on Skill 4 clip-rewards earning paths, joining campaigns, swapping payout wallets, or debugging ClipAffiliates flows.
---

# ClipAffiliates Driver Skill

Captures the verified procedures for the ClipAffiliates BETA (2026-06-28).

## Architecture (= what the docs DON'T tell you)

- **Frontend host**: `https://www.clipaffiliates.com` (Next.js app, CSRF cookie set here)
- **API host**: `https://api.clipaffiliates.com` ← **separate subdomain**, Django REST Framework backend
- **Auth**: cookie session via the frontend login, CSRF token in the `csrftoken` cookie
- The `/affiliate/setup` wizard does NOT expose an edit affordance after a step is saved. ★ All re-edits go through the API ★.

## Discovered API endpoints (= the only ones we use)

| method | path (under https://api.clipaffiliates.com) | purpose |
|---|---|---|
| GET  | `/api/users/csrf/` | get CSRF token JSON |
| GET  | `/api/users/me/` | current user (id, email, country, balance, account_type) |
| GET  | `/api/payments/` | DRF root → lists `transactions`, `payouts`, `campaign-deposits` |
| GET  | `/api/payments/crypto/account_status/` | wallet state (read-only) |
| GET  | `/api/payments/crypto/supported_currencies/` | currency list (USDC-Solana is the recommended default) |
| **POST** | **`/api/payments/crypto/save_wallet/`** | ★ bind / swap payout wallet ★ (body: `{wallet_address, wallet_currency:"usdcsol"}`) |
| POST | `/api/payments/crypto/create_payment/` | (brand-side) create campaign deposit |
| GET  | `/api/payments/crypto/payment_status/` | payment progress |
| POST | `/api/payments/crypto/request_withdrawal_secure/` | withdraw balance to wallet |
| GET  | `/api/payments/crypto/withdrawal_balance/` | how much is withdrawable |
| GET  | `/api/payments/crypto/withdrawal_options/` | withdrawal preferences |
| GET  | `/api/payments/crypto/deposit_fee_preview/` | fee preview |
| GET  | `/api/social-accounts/` | linked social handles |
| GET  | `/api/affiliates/stats/my_stats/` | my view / earning stats |
| GET  | `/api/chat/messages/` etc | community chat |

Heuristic for missing endpoints: scrape JS chunks under `/_next/static/chunks/*.js` and grep for `"/api/...` literal strings. That's how `/save_wallet/` was discovered.

## Signup flow (verified 2026-06-28)

```
1. nav https://www.clipaffiliates.com/register?role=affiliate
2. fill #username / #email / #password / #confirmPassword  (React: use Input.insertText via CDP)
3. tick the ToS checkbox
4. click "Create Account"
5. wait for "Check your email" view, then poll AgentMail for "Verify your email — ClipAffiliates"
6. nav to the verification link in the email body  (regex: clipaffiliates\.com/verify-email\?token=...)
7. after "Email verified" → /affiliate/setup
```

★ agentmail.to is **accepted** by ClipAffiliates (= fraud filter lenient; opposite of Instagram which auto-suspends agentmail.to). Verified by this account: `id=5597 username=anicca email=tt-anicca@agentmail.to`. ★

## Login (= the form needs the React-native-setter pattern)

```
nav /login
form: #username (also email) + #password
fill via Input.insertText FAILS silently for this form (React state stays empty).
Use native setter + dispatch:
  const setter = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(el),'value').set;
  setter.call(el,val); el.dispatchEvent(new Event('input',{bubbles:true}));
  el.dispatchEvent(new Event('change',{bubbles:true}));
```

## Swap payout wallet (= the discovered N2 path — use this, NOT the wizard)

```bash
CSRF=$(curl -sS -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
   https://api.clipaffiliates.com/api/users/csrf/ | jq -r .csrfToken)
curl -sS -X POST https://api.clipaffiliates.com/api/payments/crypto/save_wallet/ \
   -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
   -H "Content-Type: application/json" \
   -H "X-CSRFToken: $CSRF" \
   -d "{\"wallet_address\":\"<MY_PUBKEY>\",\"wallet_currency\":\"usdcsol\"}"
# expected 200: {"message":"Wallet saved successfully","wallet_address":"...","wallet_connected":true}
```

Or via the CloakBrowser daily-driver tab (= keeps cookie + CSRF in-browser):
see `scripts/save_wallet.sh`.

## Setup-wizard 3 steps (only the first run goes through the UI)

1. Country (`<select>` — JP is supported). React-native-setter pattern works.
2. Connect Wallet — dropdown opens "USDC (Solana) Recommended" (sole option) + an `input[placeholder="Your wallet address"]`. After Save it collapses with a green check and ★ no Edit affordance ★.
3. Link a Social Account — 4 cards (TikTok / Instagram / YouTube / Twitter-X). Each opens a 2-step modal:
   - Step a: type the social username + Next
   - Step b: shows a unique code like `clipaffiliates-XXXXXX` → add to your social's bio → click Verify.

★ "You won't be able to earn until setup is complete" — earnings are gated on all 3 steps. ★

## Gotchas observed

- `/api/...` paths on `www.clipaffiliates.com` all 404 → API is on `api.clipaffiliates.com` only.
- `/affiliate/settings` page does NOT exist; it renders the setup wizard, even after onboarding.
- The community chat widget is fixed bottom-right (`Community` button) — appears in every page text dump.
- Login form needs native setter (Input.insertText alone fails). Signup form was OK with insertText. (= different React form libs between the two.)
- The sessionStorage `ca_auth_cache_v1` lags behind server state — verify mutations via the API, not the cache.
