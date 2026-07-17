# PATCHES — aniccaai.com rebuild + UBI + Akash + ramp + LM (GROUNDED v2, code-reviewed 2026-06-17)

SSOT = spec `30-master-vision-products-ubi-2026-06-17.md`. JP copy = **アニッチャ** (not "Anicca").
**v2 = rewritten after a superpowers:code-reviewer audit caught fabricated paths/symbols in v1.**
Ground truth verified against the real repo (see "REPO REALITY" each set). Provider API request+response
schemas marked **[VERIFY@STEP]** must be re-pinned from live docs (ctx7/firecrawl) right before coding that
step — do NOT ship the curl bodies as-is. Apply in spec §10 STEP order. Re-run code-reviewer per step.

═══════════════════════════════════════════════════════════════════════════
## PATCH SET E — Life Manager LOCAL (STEP 1, FIRST) — GROUNDED
═══════════════════════════════════════════════════════════════════════════
REPO REALITY (verified ~/anicca):
- **Canonical dir = `skills/life/`** (has `ask/ask.js`, `call/call.js`, `locate/`, `notify/notify.js`, `travel/travel.js`). `skills/anicca-life-manager/` = only MAP.md/SKILL.md/scripts/test (doc wrapper) → NOT the code home.
- `travel/travel.js` ALREADY: `listEvents()` → `detectMissingTravelBlocks()` → `getTravelDurationSec(origin,dest)` → `insertEvent()`. **Travel auto-register exists.** Has `--dry-run`.
- `ask/ask.js` ALREADY: `main`, `gogSend({to,subject,body})`, `postNetlify(action,body)`. **Ask-when-unknown exists.** exports module.
- `call/call.js` ALREADY: phones user ~15min before each calendar event (Telnyx+Gemini/Charon). BUT **phone is hardcoded `+818046270314`** + reads `process.argv`.
- `notify/notify.js` ALREADY: stakeholder notify (has __tests__).
- `gog` CLI = `/opt/homebrew/bin/gog` (real), used by ask.js for gcal/gmail.

So STEP 1 = mostly **GLUE existing pieces into a scheduled loop + parameterize identity**, not greenfield.

WHAT'S MISSING (the actual work):
- **E1 onboarding state** — NEW `skills/life/profile.json` schema: `{name, phone, gcalAccount, gmailAccount, homeAddress?, telegramChatId?}`. `install.sh` runs `anicca life setup` (a NEW `skills/life/setup.js`) that: prompts name/phone, runs `gog` Google OAuth (gcal+gmail), writes profile.json. Replace call.js hardcoded `+818046270314` → read `profile.phone`.
- **E2 travel** — REUSE `travel/travel.js` as-is (already inserts leave-by blocks into gcal). Just call it on schedule.
- **E3 ask** — REUSE `ask/ask.js` (location unknown → `gogSend` mail / Telegram → reply parsed via `postNetlify`).
- **E4 scheduler (the core missing glue)** — NEW `skills/life/loop.js` + a cron entry. Loop = every 5 min: `travel.js` (refresh leave-by) → find next event (incl travel) starting in ≤15min → if found & not yet called → `call/call.js <profile.phone> <event>`. Cron in `~/.openclaw/cron/jobs.json`: `{"id":"life-loop","schedule":"*/5 * * * *","cmd":"node ~/anicca/skills/life/loop.js"}`.
- **E5 late** — REUSE `notify/notify.js`: predicted-late → draft stakeholder mail → Dais approves via mail reply / Telegram (the ONE allowed human gate, spec §5) → send.
- **E2E (no-mock)** = real gcal event + loop fires → Dais's real phone rings 15min before → he acts. Verify: Telnyx call-id + Gemini audio stream present + gcal travel block inserted.
TDD: write loop.js "next-event-incl-travel ≤15min" selector test (RED) first.

═══════════════════════════════════════════════════════════════════════════
## PATCH SET A — aniccaai.com copy (STEP 3) — GROUNDED
═══════════════════════════════════════════════════════════════════════════
REPO REALITY (verified apps/landing):
- i18n dict `lib/i18n.ts`: top-level keys are `hero/twoCta/empire/empireProducts/...` — **NO `home`/`lm`/`theProducts`**. Product dict = **`empireProducts.products`** (EN ~31-48, JA ~233-250), includes an `alarm` entry. Names are literal "Anicca …".
- Nav = `components/site/Navbar.tsx` (renders `#vision` + `#how-it-works` + locale toggle) AND `components/site/LaunchNav.tsx`. **Neither has The-Bet/Start/Products/GitHub items** → these are ADDED, not "removed".
- Pages `app/life-manager/` (+ `LifeManagerBody.tsx`) AND `app/lm/` ALREADY exist. `app/dais/` does NOT.

PATCH (grounded):
- A1 — ADD new top-level keys `home`, `lm`, `dais` to BOTH `en` and `ja` blocks in `lib/i18n.ts`. **Exact TS shapes** (so consumers + inference hold):
  ```ts
  home: { hero:{h1:string; sub:string; ctaStart:string; ctaGithub:string};
          bet: { title:string; body:string }[];           // length 3
          timeline: { k:string; v:string }[];              // length 3
          start: { local:{steps:string[]; earn:string; cta:string}; cloud:{host:string; steps:string[]; cta:string}; note:string };
          ubi: string; }
  lm: { hero:{h1:string; sub:string}; how:string[]; cta:[string,string] }
  dais: { hero:{h1:string; sub:string} }   // product rows reuse empireProducts.products
  ```
  Copy strings = the APPROVED EN/JA text (home/lm/dais) from the chat of 2026-06-17, JP = アニッチャ. GitHub link both START cards = https://github.com/Daisuke134/anicca.
- A2 — `/life-manager`: **MODIFY existing** `app/life-manager/LifeManagerBody.tsx` to render `lm.*` copy (do not create a 2nd page). Decide `/lm` route: redirect → `/life-manager` (it's the onboarding client; keep as the app, /life-manager = marketing).
- A3 — `/dais` (NEW `app/dais/page.tsx`): hero from `dais.hero`; product rows = map over **`empireProducts.products`** (real key), **filter out `alarm`**. JA display name = render-time map "Anicca X" → "アニッチャ X" (do NOT mutate the dict — the empire dashboard reuses it).
- A4 — Nav: in the canonical nav (confirm Navbar vs LaunchNav by which the home layout imports) ADD items [The Bet(#bet), Start(#start), Products(/dais), GitHub]. No /dashboard or anicca-web-app links exist to remove. /me stays login-gated (unchanged).

═══════════════════════════════════════════════════════════════════════════
## PATCH SET B — UBI rails (STEP 5) — GROUNDED, mechanism corrected
═══════════════════════════════════════════════════════════════════════════
REPO REALITY (verified ~/anicca/skills/earn):
- Real distributor = `skills/earn/distribute-ubi.mjs`, signature `distribute(rawLine, opts)`, CLI = `node distribute-ubi.mjs '<fundingLine JSON>'` (NO `--daily --split` flags). Splits via `buildRecipients`+`planUbi` (`lib/ubi.mjs`), reads child wallets + `UBI_HUMAN_WALLETS` env.
- Actual on-chain transfer = **Python** `skills/earn/execute-ubi.py` (web3.py, ERC-20 `transfer` selector `0xa9059cbb`, Base), shelled from the mjs. `lib/usdc.mjs` = **read-only** (`usdcBalance`,`delta`) — there is **NO `transferUsdcBase`**.
- `netlify/functions/ubi-webhook.js` does NOT exist.

PATCH (grounded):
- B1 P-ubi-claim (Crossmint, cat 1,2,3,5): NEW `skills/earn/claim.mjs`. Reuse the EXISTING Python transfer path (shell `execute-ubi.py` with the Crossmint-created recipient address) — do NOT invent a JS `transferUsdcBase`. Crossmint calls **[VERIFY@STEP]**: confirm create-wallet request body + **response field for address** + transfer endpoint/calldata from live docs before coding. Reconcile to ONE transfer mechanism (Python).
- B2 P-ubi-offramp: Bridge.xyz **[VERIFY@STEP]** — full flow needs customer-create → KYC link → external_account-create → transfer (+ idempotency key); NOT a one-shot. Kotani **[VERIFY@STEP]** — pin real REST routes (spec §14 anchor-slugs ≠ routes).
- B3 P-ubi-daily: do NOT invent flags. EITHER add a real CLI wrapper to `distribute-ubi.mjs` that accepts `--daily`/`--split` and maps to `distribute()/planUbi`, OR a thin `skills/earn/ubi-daily.mjs` that builds the fundingLine + calls `distribute()`. Cron: `{"id":"ubi-daily","schedule":"0 9 * * *","cmd":"node ~/anicca/skills/earn/ubi-daily.mjs"}`. Reconcile the 10/10/80 split with the real `planUbi` recipient model (it differs — unify first).
- B4 broadcast (v2): animals=sanctuary earmark; aliens=cosmic escrow + METI.
- B5 NEW `apps/landing/netlify/functions/ubi-webhook.js` (Kotani/Bridge callback receiver).

═══════════════════════════════════════════════════════════════════════════
## PATCH SET C — Akash fast spawn (STEP 4) — GROUNDED, greenfield
═══════════════════════════════════════════════════════════════════════════
REPO REALITY: `~/anicca/cloud/` does NOT exist (greenfield). Akash Console API auth/endpoints/SDL/escrow all **[VERIFY@STEP]** (review flagged `Bearer`/`/v1/deployments`/`/v1/leases`/`waitForBids` fields as UNVERIFIED; spec §14 `deploy.ts` vs patch `spawn.mjs` disagree).
PATCH (to author at STEP 4, after pinning live Akash Console-API docs via ctx7 `/websites/akash_network`):
- NEW `~/anicca/cloud/` : `spawn.mjs` (create→bids→lease), `sdl.yaml` (slim image), `warmpool.json` (state) + `pool.mjs` (pre-lease N at boot; assign on USDC arrival). Funding/escrow step (USDC→shelter) explicit. Reconcile spec §14 to the chosen entrypoint.

═══════════════════════════════════════════════════════════════════════════
## PATCH SET D — fiat ramp how-to (STEP 3) — NEAR-PERFECT, 2 fixes
═══════════════════════════════════════════════════════════════════════════
- NEW `apps/landing/content/how-to-cash-out.{en,ja}.md` + **a render route** (NEW `app/how-to-cash-out/page.tsx` reading the md, or inline the copy) — else the link 404s (no `content/` md renderer exists today).
- 🇯🇵 JP: PayPay→Binance(buy SOL)→MetaMask→swap→USDC@anicca Base wallet (relay.link). Receive: anicca→Binance→sell→SOL→PayPay. **★ CRITICAL: separate the Solana deposit address from the EVM/Base address. Sending SOL to an `0x…` EVM address LOSES funds. The Binance EVM addr `0xdbad…` is for USDC(Base) receive ONLY; SOL uses Binance's Solana deposit address (different). Copy must label each chain explicitly. ★**
- 🇺🇸 US: human USDC(Base)→anicca wallet; anicca USDC(Base)→user wallet. Direct, daily.

═══════════════════════════════════════════════════════════════════════════
## must-fix-before-coding checklist (from the review)
═══════════════════════════════════════════════════════════════════════════
1. [spec] Mark §3 (anicca web-app pay flow) SUPERSEDED by §10 CUT. ✅ (done in spec v-next)
2. [spec] Delete the false "we already have lib/usdc.mjs + transferUsdcBase / UBI distributor" claims → state the real Python mechanism + `skills/earn/` paths. ✅
3. [B/C] Pin Crossmint/Bridge/Kotani/Akash request+RESPONSE schemas from live docs at each STEP. [VERIFY@STEP]
4. [A] empireProducts (not theProducts) + exact TS shapes + real nav file + reconcile existing /life-manager,/lm.
5. [D] add render route + fix Solana-vs-EVM address fund-loss copy.
6. [E] canonical `skills/life/`; profile.json onboarding schema; loop.js scheduler; param the phone; reuse travel/ask/notify.
7. Re-run code-reviewer per STEP until that step's patch = PICTURE-PERFECT, THEN code, THEN E2E (final check only).
