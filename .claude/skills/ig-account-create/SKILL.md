---
name: ig-account-create
description: >
  Create a NEW Instagram account FULLY AUTONOMOUSLY (ZERO human) by driving the running
  CloakBrowser daily-driver (CDP :9222). Proven E2E 2026-06-29 → live account @aiclipsvault
  with NO phone and NO captcha — email-only signup using a real Gmail PLUS-ADDRESS
  (keiodaisuke+<tag>@gmail.com), OTP auto-read via `gog gmail` (incl. SPAM). Any AI runs it.
triggers:
  - create instagram account
  - new ig account
  - ig account creator
metadata:
  status: WORKING — proven E2E NO-HUMAN (account @aiclipsvault created 2026-06-29, email-only, 0 phone, 0 captcha)
  browser: CloakBrowser daily-driver (CDP localhost:9222), residential SoftBank IP
  human_in_loop: NONE (email-only Gmail plus-address; OTP auto-read via gog gmail). Phone path is a fallback only.
  canonical_location: ~/.agents/skills/ig-account-create  # symlinked into BOTH ~/.claude/skills and ~/.openclaw/skills (Claude + OpenClaw load the SAME skill, synced)
  general_purpose: true  # NOT coupled to affiliate. Creates an IG account for ANY use.
  family:
    - ig-account-create (this — CREATOR: signup + profile icon/name/bio)
    - warmup-instagram (WARMER: 7d humanized activity before commercial posts)
    - reelclaw/post-video-to-instagram.sh (POSTER: Postiz instagram-standalone)
---

# ig-account-create

★ **Canonical = `~/.agents/skills/ig-account-create/`**, symlinked into both `~/.claude/skills/`
and `~/.openclaw/skills/` → **Claude (dev) and OpenClaw (#1 Anicca) load the SAME skill, synced**
(edit once, both get it). This is the shared-skill pattern (like `chatgpt-imagegen`). ★

★ **GENERAL skill** — creating an IG account is its own capability, reusable in ANY context
(affiliate / content / clip / brand). It is NOT part of any earn skill; earn skills CALL it. ★

## A COMPLETE account = signup + profile (icon + name + bio)
Creating the login is only half. A real account needs: **display name** (set at signup ✓), **profile icon**
(avatar — generate $0 via `chatgpt-imagegen`, upload via profile-edit), and **bio** (niche one-liner;
the affiliate/CTA link goes here AFTER warmup, never day-0). The CREATOR's job ends at: account live +
icon + name + bio set. Then WARMER (warmup-instagram ~7d) BEFORE the POSTER adds commercial content.

★ HONEST STATUS 2026-06-29: profile icon + bio are NOT yet automated — `scripts/setup_profile.py` is a
TODO (does NOT exist). @aiclipsvault currently has name only (no icon/bio). To finish "end to end", BUILD
setup_profile.py: nav `/<handle>/` → "プロフィールを編集" → set 自己紹介(bio) textarea + アイコン変更
(file-chooser intercept, same technique as ig-reels-poster's video upload) → 保存. Until built, the
creator is signup-complete but profile-incomplete. ★

## The IG skill family (creator → warmer → poster)
| skill | role | location |
|---|---|---|
| **ig-account-create** (this) | signup + profile (icon/name/bio) | `~/.agents/skills/` (shared) |
| **warmup-instagram** | 7d humanized warmup before commercial posts | `~/.openclaw/skills/` (TODO: share via ~/.agents) |
| **IG poster** | publish video/slideshow via Postiz instagram-standalone | `reelclaw/post-video-to-instagram.sh` (TODO: generalize + share) |

Replaces the old `~/.openclaw/skills/instagram-account-factory` (stub: SMS+iPhone+Surfshark hardware
farm, D-01 blocked, never worked). The daily-driver browser path is the working one.

Autonomously create a NEW Instagram account through the **running CloakBrowser
daily-driver** (the browser Dais watches; CDP on `localhost:9222`). We attach with
**raw per-page CDP** (playwright connect_over_cdp takes ~56s with ~40 tabs; raw page-ws
attaches in ~100ms). We only ever open/drive a **new tab** — never touch or close
Dais's tabs.

## ★ THE NO-HUMAN WAY (proven 2026-06-29, @aiclipsvault — use THIS, not the old phone path) ★
The whole point: **any AI, even a low-intelligence model, follows these steps and it just works — zero human.**

1. **Email = a real Gmail PLUS-ADDRESS** → `keiodaisuke+<uniquetag>@gmail.com` (e.g. `+aiclips1`).
   - Gmail delivers every `+tag` variant to the same `keiodaisuke@gmail.com` inbox → **infinite unique
     addresses**, and IG does NOT treat Gmail as disposable (so NO suspension, NO appeal).
   - ★ This replaces agentmail.to ★ (agentmail = disposable → IG auto-suspends → appeal hell; aiclipper.daily died this way). NEVER use agentmail for IG.
2. **Email OTP is auto-read via `gog gmail`** (NOT AgentMail): `gog gmail search --account keiodaisuke@gmail.com "instagram in:anywhere newer_than:1h" --max 3 --plain`.
   - ★ IG's OTP email often lands in **SPAM** → you MUST use `in:anywhere` (plain inbox search misses it). ★
3. **NO phone, NO captcha needed.** IG email-signup completed with email-OTP ALONE (account went live, no phone step, no text-CAPTCHA). Do NOT preemptively do the phone flow. (If IG ever forces phone: fallback = `read_sms_otp.py` reads the code from macOS chat.db — Dais's number forwards SMS there; still zero relay.)
4. **IP must be residential, non-VPN.** Daily-driver egress = SoftBank JP (clean). VPN/datacenter → instant suspend.
5. **Logged-in already?** The daily-driver usually has another IG logged in → `emailsignup` redirects to `/`. Use **`cdp_incognito.py`** for an isolated context (own cookie jar) — it works even while another IG is logged in. (DO NOT log anyone out.)

## Env
| var | use |
|---|---|
| `AGENTMAIL_ANICCA_API_KEY` | read the email confirm code (inbox `tt-anicca@agentmail.to`) |
| `CAPSOLVER_API_KEY` | (optional) solve the text-CAPTCHA via ImageToText to drop that tap |
| — phone — | Dais relays the WhatsApp/SMS code; no env key (no SMSPool yet) |

## Scripts
| file | what |
|---|---|
| `scripts/cdp.py` | raw-CDP driver. cmds: `new [url]`, `nav <tid> <url>`, `shot <tid> <out.png>`, `eval <tid> <jsfile\|->`, `text <tid>`, `url <tid>`, `clicksel <tid> <css>`, `clickxy <tid> <x> <y>`, `insert <tid> <text>`, `key <tid> <key>`, `close <tid>` |
| `scripts/cdp_incognito.py` | isolated browser context (own cookie jar) for signup while another IG is logged in. cmds: `new <url>` (prints CTX_ID + TID), `list`, `close <ctx_id>`. ★ FIXED 2026-06-29: the browser-ws was 403 'remote-allow-origins' — now uses `suppress_origin=True`, works on Dais's browser. ★ |
| `scripts/read_sms_otp.py` | ★ phone-OTP fallback ★ — reads a 6-digit code from macOS chat.db (Dais's iPhone forwards SMS): `read_sms_otp.py --match Instagram --digits 6 --since-seconds 180 --timeout 90`. Zero human. |
| `scripts/ig_dob.py` | DOB helper (custom combobox). NOTE: options carry a JP suffix (`1995年`/`7月`/`10日`) and the YEAR list is long → must `scrollIntoView` the option before clicking (see Proven flow step 2). |
| email OTP read | use `gog gmail` (NOT read_otp/AgentMail for IG): `gog gmail search --account keiodaisuke@gmail.com "instagram in:anywhere newer_than:1h" --max 3 --plain` → grab the 6-digit code. Needs `GOG_KEYRING_PASSWORD` in env. |

Run all with `/opt/homebrew/bin/python3` (has `websocket-client`).

## Proven flow — NO-HUMAN, end to end (re-run verbatim; screenshot each step)
```
PY=/opt/homebrew/bin/python3 ; CDP=~/.claude/skills/ig-account-create/scripts/cdp.py
set -a; . ~/.openclaw/.env; set +a   # provides GOG_KEYRING_PASSWORD, CAPSOLVER_API_KEY
TAG=aiclips$RANDOM ; EMAIL="keiodaisuke+$TAG@gmail.com"   # unique Gmail plus-address per account

# 0. ISOLATED context (the daily-driver usually has another IG logged in → plain new-tab redirects to /):
#    $PY scripts/cdp_incognito.py new "https://www.instagram.com/accounts/emailsignup/"
#    → prints CTX_ID + TID. Use that TID for all steps. (cdp_incognito uses suppress_origin=True.)
# 1. fill the 4 VISIBLE inputs via React-safe NATIVE SETTER (set ''→dispatch input→set value→dispatch input+change):
#    [0]=email ($EMAIL), [1]=password, [2]=name ("AI Clips Daily"), [3]=username (aria="ユーザーネーム").
#    ★ Autocomplete corrupts the email field (turns @gmail.com / adds chars) → always native-set it last + re-verify value == $EMAIL. ★
# 2. DOB (custom DIV[role=combobox], 年/月/日): click the combobox → option text has a JP SUFFIX
#    ("1995年","7月","10日"). The YEAR list is long → scrollIntoView the "1995年" element, wait, THEN click its rect.
# 3. username: pick until the red "使用できません" clears (try aiclips.daily/aiclipsvault/…); native-set, wait 2.5s, check.
# 4. click 送信 (DIV[role=button] text=送信) via clickxy on rect center.
# 5. email OTP (NO AgentMail — use gog gmail, code often in SPAM):
#    gog gmail search --account keiodaisuke@gmail.com "instagram in:anywhere newer_than:1h" --max 3 --plain
#    → grab the 6-digit code → click the VISIBLE code input → `insert` it (NOT native setter) → click 次へ (it shows a spinner ~5-10s).
# 6. ★ NO phone, NO captcha appeared — account goes LIVE on email alone. ★ (Fallback if forced: read_sms_otp.py.)
# 7. PROFILE SETUP (a COMPLETE account, see below): set icon + bio (name already set at signup).
# 8. verify: $PY $CDP nav $TID https://www.instagram.com/<username>/ ; shot → "投稿0件 フォロワー0人" + handle = LIVE.
#    save ~/.cloak/ig-<handle>.json {username,name,email,pw,dob,status:LIVE,ctx}.
```
★ Proven result 2026-06-29: @aiclipsvault LIVE, email keiodaisuke+aiclips1@gmail.com, OTP 420195 (from SPAM), 0 phone, 0 captcha, 0 human. ★

## Gotchas (hard-won)
- **Target the VISIBLE input** `getBoundingClientRect().height>0` — the old signup form stays in DOM (hidden) and `querySelector('input')` grabs the wrong one.
- **Code fields need `Input.insertText`** (trusted typing); the React native-setter trick works for the signup form but the code field clears on submit if set that way.
- **Custom comboboxes** (DOB, country) need **trusted CDP mouse clicks** (`clickxy` on rect center), not JS-dispatched clicks; pick the **visible** listbox among several.
- **送信/次へ are `DIV[role=button]`**, not `<button>` — match by text, click rect center.
- connect_over_cdp is slow with many tabs → we use raw page-ws; never `close` Dais's tabs.

## State / creds
Per-account JSON at `~/.cloak/ig-<handle>.json` (email, pw, dob, username, bio_link, status).
Proven account: `~/.cloak/ig-ai-shigoto-lab.json` → **@aishigoto.labo** (LIVE).

## Next to fully de-human
1. Real-email source (Gmail / custom domain) instead of agentmail.to → no suspension/appeal.
2. CapSolver ImageToText for the text-CAPTCHA tap.
3. SMSPool (real-SIM OTP) for the phone code → zero human.
4. 7-day warmup before first affiliate post (per instagram-account-factory).
