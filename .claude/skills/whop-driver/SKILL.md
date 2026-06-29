---
name: whop-driver
description: Drive Whop (whop.com) end-to-end as a CLIPPER — login (email magic link), Content Rewards discover, search/pick campaign, link socials, join campaign, submit clip URL, read balance, withdraw. Whop has no public clipper API; this skill handles the iframe-gated postMessage-JWT architecture via CDP attachToTarget + Page.captureScreenshot + coord-click on the CloakBrowser daily-driver (:9222). The daily earn loop calls this skill; never one-shot.
---

# whop-driver

★ Owner: this Claude session (= human-funded Anicca). Account = `anicca` / `myclaude-clip@agentmail.to`, user_id = `user_MMwusqVw1uBFS`. Pairs with `clipaffiliates-driver` + `earn-clip-rewards` + `ig-account-create`. ★

## Why this skill exists (= the BP behind it)

Whop's Content Rewards has NO public clipper-side REST/GraphQL — verified 2026-06-29 by enumerating `docs.whop.com/llms.txt` (106 kB) + the official TS SDK at `github.com/whopio/whopsdk-typescript`. Every clipper action (list campaigns / join / submit clip / read balance) runs in a per-app iframe on `*.apps.whop.com` that authenticates via a JWT injected from the parent `whop.com/core/app/launch/?redirect=…` wrapper using `window.postMessage` (`docs.whop.com/developer/guides/iframe`).

Direct nav to the iframe URL with cookies only = body=0 (= the app loads its splash and waits forever for a postMessage that never arrives).

Until we sniff and replay the iframe's internal fetches (`scripts/sniff_graphql.py`, planned), the only repeatable path is **CDP-driven screenshot + coord-click on the daily-driver**.

## Login flow (verified D-28, D-34)

```bash
PY=/opt/homebrew/bin/python3 ; CDP=~/.claude/skills/ig-account-create/scripts/cdp.py
TID=$($PY $CDP new "https://whop.com/login/")
sleep 6
# fill email via React-aware native setter
$PY $CDP eval "$TID" - <<'JS'
(()=>{function s(el,v){const p=Object.getPrototypeOf(el);const set=Object.getOwnPropertyDescriptor(p,'value').set;set.call(el,v);el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));}
const i=document.querySelector('input[type=email]'); i.focus(); s(i,'myclaude-clip@agentmail.to');
const b=Array.from(document.querySelectorAll('button')).find(x=>['Continue','続ける'].includes((x.innerText||'').trim()));
b.click(); return {filled:i.value};})()
JS
sleep 6
# OTP via AgentMail
OTP=$($PY ~/.claude/skills/ig-account-create/scripts/read_otp.py \
  --inbox myclaude-clip@agentmail.to --key-env AGENTMAIL_API_KEY --match Whop --timeout 60)
# Insert OTP via native setter (input[name=otp], maxlength=6)
$PY $CDP eval "$TID" - <<JS
(()=>{function s(el,v){const p=Object.getPrototypeOf(el);const set=Object.getOwnPropertyDescriptor(p,'value').set;set.call(el,v);el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));}
const i=document.querySelector('input[name=otp]')||document.querySelector('input'); i.focus(); s(i,'$OTP');
return {set:i.value};})()
JS
# advances to /home-feed/ or / on success
```

## Discover campaigns flow (verified D-32, D-34)

```bash
$PY $CDP nav "$TID" "https://whop.com/joined/contentrewards/discover-campaigns-B5C5S1vijHGVt9/app/"
sleep 12   # iframe needs time
$PY $CDP shot "$TID" /tmp/whop-discover.png
# now visually parse the screenshot OR coord-click into a card / "View Program" / "Join Campaign"
# search bar at approx x=572 y=664 in 1920x854 viewport:
$PY $CDP clickxy "$TID" 572 664
$PY $CDP insert "$TID" "Dreamina"
```

## Verified active campaigns (2026-06-29 snapshot, will rotate)

| campaign | brand | category | $/1K views | pool | notes |
|---|---|---|---|---|---|
| Dreamina AI ⭐ | Propaganda ✓ | Technology | $15 | $40,000 | UGC + Clipping, best fit for AI/tech niche |
| COINBASE | ClipHaus ✓ | Product | $6 | $9,000 | crypto brand |
| Roobet | — | Gaming/Gambling | — | — | casino brand |
| Call of Duty Modern Warfare | — | Gaming | — | — | game launch |
| Natura | — | Lifestyle | — | — | beauty/skincare |
| Boxabl | — | Tech/Housing | — | — | modular homes |
| Angelique | — | Lifestyle | — | — | — |

## Gotchas (hard-won)

- **iframe carousel auto-rotates** (~5s interval); a coord-click on the previous hero often lands on the next hero. Strategy: search for the campaign by name first, then click the search-result card (= deterministic position).
- **Cross-origin blocks contentDocument** — `document.querySelectorAll('iframe')[0].contentDocument` is null because iframe is on `*.apps.whop.com`. Use `Target.attachToTarget` + `Runtime.evaluate { sessionId }` to read iframe DOM (= `scripts/iframe_attach.py`, planned).
- **camofox screenshot endpoint is GET** (not POST) with userId+sessionKey query params; `cdp.py shot` for CloakBrowser daily-driver uses POST internally. The two browsers have different screenshot APIs.
- **Whop login = email magic link only** — no password, no captcha visible. OTP arrives at the email used; AgentMail makes this fully autonomous.
- **Whop sub-apps** all live at `/joined/<community>/<app-name-<sluggedID>>/app/`; the iframe behind it is at `<projHash>.apps.whop.com/hub/exp_<expID>`. The exp_ID is stable; the app-name-slug part is too.

## Scripts

| file | purpose | status |
|---|---|---|
| `scripts/login.sh [email]` | Headless login orchestrator: open /login → email → OTP via AgentMail → insert → verify | ✓ DONE 2026-06-29 |
| `scripts/discover.sh <TID>` | Open discover-campaigns sub-app + wait 12s for iframe paint + screenshot | ✓ DONE 2026-06-29 |
| `scripts/iframe_attach.py` | patchright connect_over_cdp + sniff all GraphQL ops (jsonl out) | ✓ DONE 2026-06-29 (initial; iframe data ops still elusive) |
| `scripts/api.sh <op> <body>` | Generic cookie-only GraphQL invoker — full query in body, dumps cookies fresh per call | ✓ DONE 2026-06-29 (PROVEN: fetchInterestedExperienceIds returned real data) |
| `scripts/search_campaign.sh <query>` | Coord-click search bar + type query + return screenshot | TODO |
| `scripts/join_campaign.sh <expOrSlug>` | Click View Program → Join Campaign on a target campaign | TODO (= human walkthrough research in flight) |
| `scripts/submit_clip.sh <campaignId> <postUrl>` | Submit a posted clip URL to a campaign | TODO |

## State (= per-loop persistent)

`~/.smtm/earn-loops/whop/STATE.md`:
- active_campaigns: list of {id, brand, category, cpm, pool, brief_url, joined?, post_template}
- joined_campaigns: list of {id, joined_at, my_clip_urls[]}
- submitted: list of {clip_url, campaign_id, submitted_at, brand_approved?, views?, earned_usdc?}
- balance: latest $X from Whop's nav header

## Adjacent skills

- `clipaffiliates-driver` — companion (USDC payout, dry of campaigns as of 2026-06-29)
- `earn-clip-rewards` — top-level daily loop that CALLS this skill + pipeline + ledger
- `ig-account-create` — CDP driver + cdp_incognito helper, shared infra

## Daily loop integration

```bash
# called from earn-clip-rewards/scripts/daily.sh (via claude -p + launchd):
#   1) ensure logged in (re-login if cookie expired) — uses login.sh
#   2) discover.sh → screenshot + parse campaign cards (LLM-vision optional)
#   3) for each active campaign matching my niche & not yet joined:
#      - join → fetch brand source video URL
#      - run SamurAIGPT/AI-Youtube-Shorts-Generator pipeline
#      - post the resulting 9:16 mp4 to my IG/TikTok/X
#      - submit_clip.sh campaign_id post_url
#      - append ledger row {payout_mode: "usdc_myclaude_self", platform: "whop", ...}
#   4) measure yesterday's submissions (view counts), append to ledger
#   5) write STATE.md, sleep
```

## Open work (= future improvements)

1. `scripts/iframe_attach.py` — sniff Whop's iframe GraphQL once, persist op names + body schema, then move to cookie-only curl daemon.
2. Migrate from camofox to **patchright** (`pip install patchright`, 3.6k⭐, active) for any stealth-needed flows. CloakBrowser daily-driver remains default.
3. Browser context hygiene: disk monitor cron + `Target.disposeBrowserContext` for ephemeral signups (per architecture BP from fork research 2026-06-29).
