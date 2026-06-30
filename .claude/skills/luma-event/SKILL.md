---
name: luma-event
description: Create (or edit) a public event on Luma (lu.ma) end-to-end, fully autonomously, by driving the running CloakBrowser daily-driver over CDP (:9222). Use whenever you need to publish ANY Luma event — a hackathon, meetup, workshop, AMA, launch party — not just one specific event. Triggers: "make a Luma event", "create a lu.ma page", "publish this on Luma", "set up the hackathon on Luma". Model-agnostic: this skill calls NO LLM API and names no model — the running agent supplies the judgment (title, date, copy) in natural language; the skill supplies the deterministic browser mechanism + the Luma-specific gotchas.
---

# luma-event — publish any event on Luma autonomously

You (the running agent) decide WHAT the event is — title, date, venue, body copy — from the
user's request. This skill gives you the reliable MECHANISM to put it on Luma with zero human
in the loop, plus the non-obvious gotchas that will otherwise silently corrupt the event.

## What you need (all already present on this host)

| Need | Where |
|---|---|
| Running browser w/ host's Google login | CloakBrowser daily-driver, CDP at `http://127.0.0.1:9222` |
| Deterministic page driver | `cdp.py` (bundled in this skill dir) — raw CDP, drives ONE tab at a time |
| Email OTP reader (for Luma login) | `gog gmail search ... -a <host-email>` with `GOG_KEYRING_PASSWORD` from `~/.openclaw/.env` |
| Screenshots | `cdp.py shot` → read the PNG with your image tool, then decide coordinates |

The method is **look → decide → act**: screenshot, read it, choose coordinates/values, act,
re-screenshot to verify. Never trust a blind action; always verify against a fresh screenshot.

## cdp.py command reference

```
python3 cdp.py newtab <url>     open a NEW tab (never touches the host's other tabs), set active
python3 cdp.py use <targetId>   switch active tab (find ids via /json — see below)
python3 cdp.py nav <url>        navigate active tab
python3 cdp.py url              print {url,title} of active tab
python3 cdp.py shot <path.png>  screenshot active tab
python3 cdp.py eval '<js>'      run JS, returns JSON value (use to find element coords)
python3 cdp.py find '<text>'    locate first element containing text -> center x,y
python3 cdp.py click <x> <y>    REAL mouse click at viewport coords
python3 cdp.py type '<text>'    insert text into focused field (good for text inputs/contenteditable)
python3 cdp.py keys '<chars>'   real keystrokes (rarely needed; AVOID on time fields — see gotchas)
python3 cdp.py press <Enter|Tab|Escape|Backspace>
```
List page tabs + ids:
`curl -s http://127.0.0.1:9222/json | python3 -c "import sys,json;[print(t['id'],t.get('url','')[:70]) for t in json.load(sys.stdin) if t.get('type')=='page']"`

## The flow (do these in order; verify each with a screenshot)

1. **Pre-flight**: `df -h /` (disk), confirm `curl -s http://127.0.0.1:9222/json/version` returns a
   browser. The daily-driver may have many of the host's own tabs open — NEVER close or reuse them.
   Always `newtab`.
2. **Open the create page**: `cdp.py newtab "https://lu.ma/create"`. Screenshot.
3. **Log in if prompted** (a "Welcome to Luma / Lumaへようこそ" modal): use **email-OTP** (most
   reliable under automation — the Google popup handshake is fragile, see gotchas):
   - click the email field → `type '<host-email>'` → click "Continue with email / メールアドレスで続ける"
   - read the 6-digit code: `GOG_KEYRING_PASSWORD=$(grep '^GOG_KEYRING_PASSWORD=' ~/.openclaw/.env|cut -d= -f2-) gog gmail search "from:luma newer_than:1h" -a <host-email>` — the code is in the SUBJECT line.
   - click the first of the 6 code boxes → `type '<code>'` (auto-distributes). Dismiss any
     "create passkey / パスキー" prompt with "Later / あとで".
4. **Title**: click the event-name field (a `textarea`) → `type '<title>'`.
5. **Date**: click the start-date text → a calendar opens → click the target day number. Luma
   auto-sets the end date to the same day.
6. **Time** ⚠️ READ THE GOTCHA: click the start-time → a **dropdown list of times** appears →
   scroll it (`element.scrollIntoView`) and **click the desired time row**. Repeat for end-time
   (its rows read like `"17:00 3h"` = absolute time + duration). DO NOT set time via JS value or
   `keys` — it won't commit (see gotchas).
7. **Location**: click "Add Event Location / イベント場所を追加" → `type '<venue name>'` → pick the
   Google-Places autocomplete row that matches. For hybrid (in-person + online), keep the physical
   venue and state the online option in the description (Luma's location is effectively one mode).
8. **Description**: click "Add Description / 説明を追加" → `type` each paragraph, `press Enter`
   twice between paragraphs → click "Done / 完了".
9. **Visibility / price**: default is Public + Free — confirm on screen (公開 / 無料). Adjust only
   if the user asked.
10. **Create**: click "Create Event / イベント作成". The URL becomes
    `luma.com/event/manage/evt-...`. Get the **public** short URL from the manage page (the
    `lu.ma/xxxxxxx` share link) — `cdp.py eval` for the element whose text matches `/lu\.ma\//` or
    read it from the share card.
11. **VERIFY (mandatory)**: `cdp.py nav` to the public URL and screenshot. Confirm the rendered
    title, **date AND time**, venue, and description are correct for a public visitor. The time is
    the #1 thing that silently reverts — check it explicitly.

## Editing an existing event
From the manage page click "Edit Event / イベントを編集" (right-side panel), scroll to the field,
change it (times via the dropdown!), click "Update Event / イベントを更新", then re-verify on the
public page.

## GOTCHAS (these cost real time if skipped)

- **CDP 403 origin**: connecting a websocket to a page target returns `403 Rejected ... origin`.
  Fix = connect with NO Origin header. `cdp.py` already does this (`suppress_origin=True`). Do not
  use Playwright `connect_over_cdp` against the daily-driver — it enumerates ALL tabs and times out
  when many are open.
- **Time field DOES NOT accept JS value or typed digits.** Setting `input[type=time].value` via a
  native setter updates the DISPLAY but Luma submits its own React state → the event is created with
  the OLD time. Typing digits also misfires. The ONLY reliable way is to **click the time, then
  click a row in the dropdown list**.
- **Google OAuth popup is fragile under automation**: it opens a popup, and the callback closes it
  via `window.opener.postMessage`. If you touch/navigate the main tab before the popup finishes,
  the handshake breaks and you stay logged out. Prefer **email-OTP**. If you must use Google, drive
  the popup to completion and DO NOT touch the main tab until the popup closes itself.
- **Never touch the host's other tabs.** Always `newtab`; the daily-driver is the human's live
  browser.
- **Coordinates come from screenshots/`getBoundingClientRect`, not guesses.** The title wrapping to
  2 lines shifts every row below it down — re-locate after the title changes.

## Worked example (proves this skill, 2026-07-01)
Created **"Tokyo AI Agent Hackathon — Agents That Earn"**, Sat 2026-07-11 14:00–17:00 JST, venue
Tokyo Innovation Base, public + free, host Daisuke Narita (keiodaisuke@gmail.com).
Public URL: **https://lu.ma/atfpxptu** · manage: `luma.com/event/manage/evt-rghccE7HQWbDMxn`.
The time-field gotcha above was discovered here (event first published at the wrong 06:30 time, then
fixed via the dropdown). Full copy + design: `docs/superpowers/specs/2026-07-01-tokyo-ai-earn-hackathon-design.md`.
