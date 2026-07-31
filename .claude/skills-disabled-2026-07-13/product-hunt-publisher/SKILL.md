---
name: product-hunt-publisher
description: Publish a product to Product Hunt end-to-end via the CloakBrowser daily-driver (Dais's logged-in browser), verify-baked, so we can ship many products with no/minimal human in the loop. Use when launching ANY product on Product Hunt.
---

# Product Hunt Publisher

Ship a product on Product Hunt by driving Dais's **already-logged-in** browser. No re-login, no bot block,
no API. Built from the real 2026-06-26 Life Manager launch — every gotcha below cost a round-trip; follow it.

## NORTH STAR (Dais 2026-06-26)
"ship as many products as possible, make millions, NO human in the loop since YOU VERIFY." Every step here is
**verify-baked**: do the action → confirm it with the browser (screenshot/DOM read) before moving on. Never
report a step done without a browser read proving it.

## BROWSER = the daily-driver, always (HARD 0.39)
Connect over CDP to the running CloakBrowser; never launch a fresh profile, never use camofox here.
```python
from playwright.sync_api import sync_playwright
b = p.chromium.connect_over_cdp("http://localhost:9222")  # the daily-driver
ctx = b.contexts[0]; page = ctx.new_page()                # NEVER close ctx; only your own page
```
PH login = "Sign in" → the bottom-row **Google icon** has `data-test="login-with-google"` (NOT a labeled
LinkedIn/Github/X button — those are the big buttons; Google/Facebook/Apple are small icons under them).
Click it → Google account chooser → pick the right account → returns logged in. Confirm with a body read for
"Submit" / "Ship".

## THE FLOW (producthunt.com)
1. **Entry**: `https://www.producthunt.com/posts/new`. If a draft exists it's listed under
   "Your existing in progress posts: <Name>" — click it to resume; else enter the product URL → Get started.
   The editor URL is `/posts/new/submission` with tabs: Main info / Images and media / Makers / Shoutouts /
   Extras / Connect with Investors / **Launch checklist**.
2. **Main info**: Name (≤40), Tagline (≤60), Links (the primary `url` is where the PH "Visit" button goes —
   for a Telegram-first product point it at the landing page that funnels to Telegram, e.g. aniccaai.com/
   life-manager, NOT a gated /signup), X handle, Description (≤500), up to 3 Launch tags.
3. **Images and media**: a **Thumbnail** (240×240, single) + a **Gallery** (multiple, the FIRST image is the
   social preview). File inputs: `input[type=file]` index 0 = thumbnail (multiple=false), index 1 = gallery
   (multiple=true). Upload with `inp.set_input_files([...])`.
   - Gallery frames: capture from the LIVE product page at a 1270×760 viewport (`page.set_viewport_size`).
4. **Shoutouts**: shout out the real tools used. ★ GOTCHA: a started shoutout's NOTE must be **≥20 characters**
   or the Launch button stays DISABLED (warning "Shoutout note must be at least 20 characters"). Either fill a
   real product + a ≥20-char note, or remove the incomplete shoutout.
5. **Makers / Extras**: add additional makers; write the **first comment** (posted on launch — the maker's story).
6. **Launch checklist**: shows Required (must be 100%) + Strongly Recommended. When Required = 100% AND no
   blocking warnings (e.g. the shoutout-note one), the **"Schedule launch for later"** button enables. There is
   NO "launch right now" — PH launches are **scheduled for a date** and go live at **12:01am PT** that day.
7. **Schedule + DATE strategy**: ranking = a FULL day on the board → schedule for the next **12:01am PT**
   (Tue–Thu best). If today's 12:01am PT already passed, the soonest full-day slot is tomorrow. Confirm the date
   with Dais before committing (irreversible public, HARD 0.27).
8. **Launch + verify**: after it goes live, confirm the live URL (200 + the product page renders) + post the
   first comment immediately.

## ★ FRAGILE SPOTS (where automation is unreliable — 2026-06-26) ★
These are hover/drag/autocomplete UIs that flake under automation. Either solve reliably or hand the single
click to Dais (he's at the browser via VNC 100.99.82.95); never fake them done.
- **Gallery remove/reorder**: the per-image remove (×) only appears on REAL hover and the click target is tiny;
  coordinate clicks, synthetic events, and JS-clicks all missed in testing. Re-uploading does NOT replace — it
  APPENDS (caused 11 mixed images once). RELIABLE: do gallery curation by hand, or upload a clean set into an
  EMPTY gallery only.
- **Shoutout product search**: the autocomplete dropdown is flaky to select via DOM query.
- **Schedule button**: disabled until Required=100% AND the shoutout-note warning is cleared; verify it's
  actually enabled (not just present) before clicking.

## VERIFY-BAKED CHECKLIST (run the browser, don't assume)
- [ ] logged in (body has Submit/Ship) — screenshot
- [ ] Main info saved (read input values back)
- [ ] gallery first image = the intended social preview (Read the screenshot)
- [ ] Launch checklist Required = 100% (read the page)
- [ ] Schedule button ENABLED (not grayed) — read its disabled state
- [ ] after launch: live URL 200 + first comment posted — Read the live page

## ITERATE THIS SKILL
Every PH launch, append new gotchas here. Goal: reduce the human clicks to zero by solving the fragile spots
(reliable gallery curation + shoutout autocomplete + schedule), so the whole flow runs verify-baked, no human.

## ★ GOTCHA (2026-06-26, the one that worked): the "Confirm scheduled date" button needs a REAL click
After picking the date, an `el.click()` via `page.evaluate(...)` does NOT fire React's handler — the modal
stays open ("Pick a launch date" still showing). Use a REAL Playwright click:
`page.get_by_text("Confirm scheduled date").click()` → "Successfully Scheduled!". (Same lesson likely applies
to other React confirm buttons — prefer real Playwright .click() over evaluate el.click() for commits.)
Verified: Life Manager scheduled for Jun 27 12:01am PT. PH launches are changeable ("not locked in").

## ★ X (Twitter) POSTING via Postiz — automation + the hard lesson (2026-06-27) ★
Postiz API posts to X fine (links + video). Recipe:
1. `postiz upload <mp4>` → {id, path}.
2. POST https://api.postiz.com/public/v1/posts, header `Authorization: $POSTIZ_API_KEY` (raw, no Bearer):
   `{"type":"now"|"schedule","date":"<ISO>","shortLink":false,"tags":[],"posts":[{"integration":{"id":"cmm6d7m5703rwpr0yr5vtme3w"},"value":[{"content":"<text + full links>","image":[{"id":"<upload id>","path":"<upload path>"}]}],"settings":{"__type":"x","who_can_reply_post":"everyone"}}]}`
3. ★ VERIFY (the part I got wrong): open the releaseURL / x.com/<handle>, read the `<article>`. The link is
   present as an `a[href*="t.co"]` anchor (X SHORTENS every URL to t.co; the visible text shows "t.me/…"
   truncated with "…" — that is NORMAL and CLICKABLE). Confirm: t.co anchor present + video element present +
   text present. ★ NEVER check for the raw "t.me"/"https" string — false negative. ★
4. ★ POST ONCE. NEVER repost. NEVER consecutive (renzoku = spam). ★ If a previous attempt's status is unclear,
   GO LOOK at the live profile first — do not re-fire. The "compose modal still open" / "POSTED:false" signals
   are UNRELIABLE; the post often landed. (I created duplicate EN tweets by re-firing on a false "failed".)
5. There is NO max-text problem. Full detail + links works. Strip/ellipsis in display is fine — the link works.
