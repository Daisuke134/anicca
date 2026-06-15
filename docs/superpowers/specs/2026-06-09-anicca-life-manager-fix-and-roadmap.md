# Anicca Life Manager — Fix + OSS/Web Roadmap

| Field | Value |
|---|---|
| Date | 2026-06-09 |
| Author | Anicca (Claude Code) |
| Status | SPEC — PHASE 0 in progress |
| Branch | dev |
| Related | `2026-06-07-anicca-saas-v1-design.md` (SaaS), `2026-06-08-clean-skill-cron-separation-design.md` (SSOT) |
| Voice stack | sonichi/sutando phone-conversation (= bodhi-realtime-agent + Gemini Live + Twilio). ★ NOT Pipecat ★ — folder `~/research/pipecat/` name is misleading; pipecat/ + pipecat-examples/ are unused clones. |

---

## 0. TL;DR

Anicca is a behavioral-change agent that calls the user (Charon male voice,
Gemini Live, bidirectional) at every action time — wake / move / sleep / meds /
meditation — by knowing the user's live location and searching the next event's
real location + route. Two shipping targets:

- **OSS (local)**: runs on the user's own always-on Mac, user sets own LLM keys, no subscription.
- **Web (cloud SaaS)**: runs in a per-user Daytona sandbox, $49.99/mo subscription, we host compute, auto-cancels when wild-Anicca treasury can fund the user.

The public marketing copy (Dais 2026-06-09):

> いつでも10分前行動ができるように、自分の位置を常に把握して行動（起床・移動・就寝・薬・瞑想など）の時間になると通知・電話をしてくれる行動変容エージェント アニッチャを公開しました。
> ・名前・電話番号・位置情報・カレンダー情報を連携すると、行動の時間になると電話してくれる。
> ・遅れそうな場合は、きちんと関係者へ連絡（最後はあなたが返信案を承認）。
> ・どうやったらあなたが行動するか把握して、介入時間・方法を自己改善
> ・信用残高が自動で溜まっていく。
> ・毎日あなたへのメッセージをメールで送ってくれる。
> ・最初はサブスク課金、アニッチャが自分でお金を稼げると自動的にサブスクを解約してくれる。
> Webアプリとして公開しましたので私みたいな人はぜひ。

---

## 1. Voice stack clarification (= what we actually run)

```
~/research/pipecat/            ← parent folder name is "pipecat" (misleading)
   ├── pipecat/                ← UNUSED (clone only)
   ├── pipecat-examples/       ← UNUSED (reference only)
   └── sutando/                ← ★ THIS runs ★ (github.com/sonichi/sutando)
         skills/phone-conversation/scripts/conversation-server.ts
           import { VoiceSession } from 'bodhi-realtime-agent'  ← TS, NOT pipecat
           bodhi deps = @ai-sdk/google + @google/genai + openai + ws + zod
```

Our only tweak to sutando = 1 line:
```diff
- speechConfig: { voiceName: 'Aoede' },                               (= female, sutando default)
+ speechConfig: { voiceName: process.env.PHONE_VOICE_NAME || 'Charon' }, (= male, env-overridable)
```

★ Zero original voice infra. We clone sutando + 1-line tweak. ★

---

## 2. Current bug (= why Anicca isn't calling) — PHASE 0 root cause

Two stacked problems, both must be fixed:

### 2.A glob regression (= Anicca's own bug, this session)

`lateness_check.py:265` `get_location()`:
```python
files = sorted(LOCATION_STATE_DIR.glob("*.json"), key=mtime, reverse=True)
rec = json.loads(files[0]); return {"lat": rec["lat"], ...}  # KeyError → None
```
`realtime_guide.py` writes `guide_state_<uid>.json` + `itinerary_<uid>.json` into
the SAME `~/.openclaw/state/location/` dir. The freshest file becomes
`guide_state_<uid>.json` (no top-level `lat`) → KeyError → None → heartbeat
reports `no-location` forever, even when a fresh GPS fix exists.

**Fix (0-1)**:
```diff
- files = sorted(LOCATION_STATE_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
+ files = sorted(
+     (p for p in LOCATION_STATE_DIR.glob("*.json") if p.stem.isdigit()),
+     key=lambda p: p.stat().st_mtime, reverse=True,
+ )
```
Telegram user-id files are all-digits (`8547730585.json`); `guide_state_*` /
`itinerary_*` have underscores → excluded by `stem.isdigit()`.

**Deeper fix (0-5)**: move guide_state/itinerary OUT of `state/location/` into
`state/guide/` so the location dir only ever holds GPS files (defense in depth).

### 2.B Live Location session expired (= user-side)

`8547730585.json` is 17h stale (last 6/8 15:55). The bot daemon (PID alive) polls
getUpdates every 10s but receives no location updates. Telegram Live Location
auto-stops after the chosen duration (max 8h). The user must **re-share Live
Location freshly** (📎 → Location → Share Live Location → 8h). No code fixes this.

★ Both A (code) and B (user re-share) are required before any call fires. ★

---

## 3. Same-place action call (= implemented this session, blocked by 2.A)

`gcal_departures.py` already classifies `routine_at_home` (wake/sleep/meditation/
meal/home-run) and computes departBy. `lateness_check.decide()` was patched so the
"arrived → ok" shortcut applies ONLY to travel events; routine_at_home/baked events
fall through to the departBy timing check and fire `action=call` at action time.
`main()` was patched so an imminent (≤30min) routine event punches through quiet
hours (wake calls must fire during sleep window). The hard shell quiet-guard in
run.sh was removed. ★ Correct, but never reaches decide() until 2.A is fixed. ★

---

## 4. Architecture (local = cloud, same code)

```
┌─────────── user's iPhone ───────────┐
│  Telegram @AniccaLifeBot            │
│   ├ Live Location (8h, 5s)          │   ☎️ Twilio number (Charon male)
│   ├ text per step                   │
│   └ Google biometric (onboarding)   │
└────────────────┬────────────────────┘
                 │
   ┌─────────────┼──────────────────────────┐
   ▼             ▼                           ▼
telegram_bot  lateness_check (cron */5)   sutando conversation-server (:3100)
 GPS→state    gcal × GPS × time → decide   bodhi VoiceSession = Twilio↔GeminiLive
                 │
                 ▼
            transit_lookup
            Geocoding + Firecrawl (MUIT→住所) + transitous (route)

LOCAL  = ~/.openclaw on user's Mac, user's own keys, launchd daemons, no subscription
CLOUD  = per-user Daytona sandbox, our keys, sandbox init.sh daemons, $49.99/mo
         same 5 scripts, different location + key owner
```

---

## 5. Full roadmap (= TaskList #13-#28)

### PHASE 0 — fix my Anicca so it calls at all times

| Task | What |
|---|---|
| 0-1 (#13) | glob fix `stem.isdigit()` |
| 0-2 | Dais re-shares Live Location (user action) |
| 0-3 (#14) | verify fresh location age<60s |
| 0-4 (#15) | E2E: wake/meditation/sleep → real call (Charon) |
| 0-5 (#16) | move guide_state/itinerary to state/guide/ |

### PHASE 1 — local refactor (after working)

| Task | What |
|---|---|
| 1-1 (#17) | consolidate lateness-guard + anicca-life-manager into one skill |
| 1-2/1-3/1-4 | de-dup lateness_check, separate state dirs, clean skill/cron separation (SSOT) |

### PHASE 2 — local feature completion (public-copy promises)

| Task | Promise |
|---|---|
| 2-1 (#18) | intervention self-improvement loop (介入時間・方法を自己改善) |
| 2-2 (#19) | trust balance counter (信用残高) |
| 2-3 (#20) | daily email (毎日メッセージをメール) |
| 2-4 (#21) | lateness → stakeholder notify + approval (関係者へ連絡) |

### PHASE 3 — web app (cloud SaaS, mostly unbuilt)

| Task | What |
|---|---|
| 3-1 (#22) | /install SaaS LP (public copy), move OSS to /oss |
| 3-3 (#23) | Stripe Checkout $49.99/mo + 7d trial (web only; OSS sets own keys) |
| 3-4 (#24) | Telegram 60s onboarding (name/loc/phone/cal) |
| 3-5 (#25) | apps/api Stripe webhook → Daytona spawn |
| 3-6 (#26) | Daytona sandbox 5 daemons |
| 3-7 (#27) | OAuth token vault (Supabase RLS) |
| 3-8 | daily email per-user |
| 3-9 (#28) | auto-cancel: wild treasury → Stripe cancel → free mail |

### Done already (this session)

- ③ Claude models removed everywhere (cron mail-triage + inbox draft/triage/irreversible → gpt-5.4-mini/deepseek/kimi; models.json anthropic-vertex removed; claude-p-heartbeat DISABLED). Commit anicca-dais 92c6b9168.
- ① same-place action call + quiet punch-through (commit 94889a406) — blocked by 2.A until glob fix lands.
- Firecrawl venue fallback (MUIT → address) (commit 2e28a4b9b).

★ Subscription = web only. OSS users set their own LLM keys (Dais 2026-06-09). ★

---

## 6. Heartbeat schedule guarantee (Dais 2026-06-09)

Verified from `~/.openclaw/cron/jobs.json` + `profile.json`:

| Fact | Value |
|---|---|
| cron `anicca-lateness-heartbeat-shell` | `*/5 * * * *` Asia/Tokyo, enabled — fires every 5 min, 24/7 |
| quiet hours | 23:30–05:30 (profile.alarm.quietHoursStart/End) |
| quiet-hours behavior | ordinary routine polling silenced, BUT wake/meditation/meds/sleep events within QUIET_OVERRIDE_MIN(30) PUNCH THROUGH and still call |

**Effective coverage**:
```
05:30 ─────────────────── 23:30   = FULLY ACTIVE (every event → call)
23:30 ─────────────────── 05:30   = quiet, BUT wake/瞑想/就寝/薬 events still call (punch-through)
```
→ Anicca can call at ANY time of day for action events (incl. wake-up during sleep window).
→ This is GUARANTEED ONLY AFTER the glob bug fix (§2.A). Until then everything returns no-location.

## 7. Git recovery (2026-06-09 incident)

Root cause: prior sessions committed to local `main` but never pushed → 3074 unpushed
commits accumulated + local main diverged 3074-ahead / 37-behind from origin/main.
On top, 414 uncommitted WIP files (secrets + junk + real docs + stale iOS/landing).

| Step | Status |
|---|---|
| G-0 backup 3074 commits → origin/backup/main-3074-unpushed-2026-06-09 | ✅ DONE (b1243b94) |
| G-1 remove broken symlink .claude/skills/frontend-design | pending |
| G-2 .gitignore junk+secret, rm $(date) broken dir | pending |
| G-3 commit real docs (superpowers/memories non-secret) to main | pending |
| G-4 reconcile main with origin/main, push | pending |
| G-5 triage iOS/landing 376 stale (mostly already in backup) | pending |
| G-6 HENCEFORTH: 1 edit = 1 commit = 1 push (HARD RULE 0.00) | ongoing |

## 8. FULL TODO (canonical, TaskList #13-#34)

```
GIT RECOVERY (urgent, blocking clean state):
  G-0 ✅ backup 3074 commits to GitHub
  G-1 rm broken symlink
  G-2 gitignore junk+secret, rm $(date) dir
  G-3 commit real docs to main + push
  G-4 reconcile main ↔ origin/main + push
  G-5 triage iOS/landing stale
  G-6 push-as-you-go forever

PHASE 0 — make Anicca call at all times (LOCAL first):
  0-1 (#13) glob bug fix stem.isdigit()   ← my regression, do now
  0-2       Dais re-shares Live Location
  0-3 (#14) verify fresh location age<60s
  0-4 (#15) E2E wake/瞑想/就寝 real call (Charon male)
  0-5 (#16) move guide_state to state/guide/

PHASE 1 — local refactor:
  1-1 (#17) consolidate lateness-guard + anicca-life-manager

PHASE 2 — local feature completion (public-copy promises):
  2-1 (#18) intervention self-improvement loop
  2-2 (#19) trust balance counter
  2-3 (#20) daily email
  2-4 (#21) lateness → stakeholder notify + approval

PHASE 3 — web SaaS (cloud, mostly unbuilt):
  3-1 (#22) /install SaaS LP + /oss split
  3-3 (#23) Stripe $49.99/mo + 7d trial (web only)
  3-4 (#24) Telegram 60s onboarding
  3-5 (#25) Stripe webhook → Daytona spawn
  3-6 (#26) Daytona sandbox 5 daemons
  3-7 (#27) OAuth token vault
  3-9 (#28) auto-cancel (wild treasury → free)
```

Subscription = web only. OSS users set own LLM keys. (Dais 2026-06-09)

---

## 9. Architecture decision: MERGE into ONE OSS repo (Dais 2026-06-09)

**Decision (best practice, not opinion)**: ★ ONE OSS codebase, ONE core, two deployment modes ★.
NOT two separate codebases.

Precedent (OSS products that ship BOTH self-host + cloud from one repo):
- Supabase, PostHog, Plausible, Cal.com — all single OSS repo, cloud = same code + thin control-plane.

```
anicca-oss (ONE repo, MIT, public)
│
├── core/  ← ★ IDENTICAL for local AND cloud ★ (the life manager)
│     skills/anicca-life-manager/
│       telegram_bot.py        GPS sink (Telegram Live Location)
│       lateness_check.py      gcal × GPS × time → decide → call
│       gcal_departures.py     event → departBy (routine_at_home aware)
│       transit_lookup.py      Geocoding + Firecrawl(MUIT→住所) + transitous(route)
│       realtime_guide.py      step-by-step Telegram guide during travel
│     vendor/sutando/          phone-conversation (Charon, Gemini Live, Twilio)
│
├── deploy/local/   ← OSS user (self-host)
│     install.sh              clone + .env(own keys) + launchd plists
│     → runs core on user's Mac, user pays own LLM/Twilio
│     → NO subscription
│
└── apps/control-plane/  ← ★ CLOUD ONLY (thin layer) ★
      web/      aniccaai.com/install LP + Stripe Checkout + Telegram onboarding
      api/      Stripe webhook → Daytona sandbox spawn (runs SAME core/)
      vault/    per-user OAuth tokens (Supabase RLS)
      treasury/ wild-Anicca earnings → auto-cancel sub when self-funded
      → cloud user pays $49.99/mo, we host, same core runs in their sandbox
```

**Why merge, not separate**:
| | Merged (chosen) | Separated (rejected) |
|---|---|---|
| Bug fix | fix once, both get it | fix twice, drift |
| OSS promise | full product is OSS | cloud-only features hidden |
| local=cloud parity | guaranteed (same core/) | diverges over time |
| maintenance | 1 repo | 2 repos, 2x work |

**The ONLY difference local vs cloud**:
- WHERE core/ runs: user's Mac (local) vs Daytona sandbox (cloud)
- WHO owns keys: user (local) vs us (cloud)
- BILLING: none (local) vs Stripe $49.99/mo (cloud)
- control-plane (apps/control-plane/) exists ONLY for cloud; local ignores it

★ Subscription = cloud only. OSS local user sets own keys, no charge. Both run the identical life-manager core. ★

## 10. Life manager — how it works (canonical flow)

```
EVERY 5 MIN (cron */5, 24/7):
  ┌────────────────────────────────────────────────────────────────┐
  │ 1. get_location()  ← state/location/<uid>.json (digit-only glob)│
  │      Telegram Live Location, refreshed every 5s by telegram_bot │
  │ 2. get_departures() ← Google Calendar (next 7 days of events)   │
  │      each event classified: routine_at_home OR travel           │
  │      venue resolved: Geocoding → (fail) Firecrawl "<name> 住所"  │
  │      route + departBy: transitous (train) for travel events     │
  │ 3. decide(now, location, events):                               │
  │      travel event, en route, on time      → ok (silent)         │
  │      travel event, arrived                 → ok (silent)        │
  │      travel event, departBy passed+still home → CALL (leave now)│
  │      routine_at_home (wake/瞑想/就寝/薬), departBy → CALL        │
  │      quiet hours 23:30-05:30: silent EXCEPT routine punch-through│
  │ 4. if CALL:                                                     │
  │      _build_anicca_voice_prompt(ctx + GPS + route + event)      │
  │      POST sutando :3100/call {to, message}                      │
  │      Twilio Media Streams ↔ Gemini Live (Charon male, ja-JP)    │
  │      ☎️ "Dais さん、 瞑想の時間です" → 双方向会話 → hang_up      │
  │ 5. if travel + moving: realtime_guide pushes Telegram text      │
  │      at each leg (改札/乗換/降りる駅/方向違い)                   │
  └────────────────────────────────────────────────────────────────┘
```

---

## 11. Phone call bugs fixed (2026-06-09, transcript-verified)

| Bug | Root cause | Fix | Verify |
|---|---|---|---|
| "application error, goodbye" | dialout → dead port 7860 (old pipecat) | run.sh + secrets → port 3100 (sutando) | call connects |
| call connects but silent | cloudflared quick tunnel rotated URL on restart; sutando cached old URL at startup | restart sutando to re-read live tunnel URL | WS connects, VoiceSession starts |
| agent says "I'm Sutando" | sutando buildAgent() hardcodes 'You are Sutando' | patch line 503: outbound call with purpose → purpose IS the lead persona (Anicca). patches/sutando/0001-anicca-identity-override.patch | transcript: "Dais さん、アニッチャです" |
| not responding to user | (was actually working; masked by above bugs) | — | transcript: caller "1+2?" → agent "1+2は3ですよ", Dais said "it's working" |

**Remaining (task 0-6, permanent)**: cloudflared quick tunnel rotates URL → need
named tunnel (phone.aniccaai.com fixed) OR auto-restart sutando on URL change.
Currently mitigated by manual sutando restart.

**E2E proof** (call CAb136, transcript ~/.sutando/workspace/logs/conversation.log):
```
agent : Dais さん、アニッチャです
caller: Can you hear me?
agent : もちろん、聞こえていますよ。どうしましたか?
caller: what's your name?
agent : Dais さん、アニッチャです。何かお用ですか?
caller: then what's 1 + 2?
agent : 1 + 2は3ですよ。
caller: Okay, it's working, it's working. It's good.   ← Dais confirmed
```

---

## 12. OSS (local) vs WEB (cloud) user experience

### 12.1 OSS user UX (= Dais-type, self-host)

```
WHO: own Mac always-on, own API keys, no subscription.

DAY 0 install (15 min):
  aniccaai.com/oss → paste 1 prompt into Claude Code/Cursor
    AI asks 1-at-a-time: GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, TWILIO_*,
    GOOGLE_API_KEY, FIRECRAWL_API_KEY → ~/.openclaw/.env
  6 launchd daemons start (telegram_bot, lateness_check */5,
    realtime_guide, sutando phone, tunnel, tunnel-watcher)
  Telegram /start → Live Location + Google Calendar

DAY 1+:
  06:00 ☎️ "Dais さん、アニッチャです。起きる時間です"
  06:30 ☎️ "瞑想の時間です"  07:00 ☎️ "薬飲みましたか?"
  08:14 ☎️ "中野まで34分、今出れば10分前着" → 移動中 Telegram 駅案内
  (late risk) → renraku draft → user approves → send
  22:45 ☎️ "寝る準備を"   每朝 📧 daily message

  Runs on USER's GEMINI_API_KEY (pay-per-use ~$10-25/mo). No subscription.
```

### 12.2 WEB user UX (= general public, cloud SaaS)

```
WHO: normal person. won't install. has Telegram. pays monthly.

T=0   aniccaai.com/install → 1 button "Telegram で 始める"
T=3   @anicca_bot opens:
        "名前を教えて" → "Dais"
T=10  "Google カレンダー 繋いで (任意)" → [Continue with Google] biometric
T=20  "明日14:00 部長会議@大手町 ですね。 ご自宅の住所は?" → text/voice
T=35  "ライブ位置情報を共有して" → 1 tap (Telegram standard)
T=50  "電話番号を共有" → 1 tap
T=55  Anicca: "登録完了。 月$49.99、 最初7日無料"
        [ Start free trial → Stripe Checkout ] → Apple Pay biometric
T=60  "明日朝6:30にお電話します"

  ── BACKEND (user touches NOTHING) ──
  Stripe webhook (paid) → apps/api → spawn Daytona sandbox (1/user)
    sandbox init.sh starts SAME core/ (telegram_bot, lateness_check,
      realtime_guide, sutando phone — macOS-only tools disabled on Linux)
    OAuth tokens injected from vault (Supabase RLS)
    OUR Gemini key + OUR Twilio number pay for this user

DAY 1+ (identical experience to OSS, but cloud-hosted):
  06:30 ☎️ Charon (OUR Twilio number) "起きる時間です" → 双方向
  every action time → call/notify. 24/7. we monitor, we self-heal.

  Cost: $49.99/mo (7-day free trial). /cancel = 1 Telegram command.
  Auto-free: when wild-Anicca treasury can fund this user's compute,
    Anicca cancels the Stripe sub itself + mails "you're free now".
```

### 12.3 OSS vs WEB difference table

| | OSS (local) | WEB (cloud) |
|---|---|---|
| install | Claude Code 1 prompt (15min) | aniccaai.com 1 button (60s) |
| runs where | own Mac (~/.openclaw) | Daytona sandbox (Linux) |
| keys | user's own GEMINI/TWILIO | OURS |
| voice engine | Gemini (user key) | Gemini (our key) |
| billing | none | $49.99/mo (7d trial) |
| sutando macOS tools | available | DISABLED (Linux, phone-only) |
| uptime | user's Mac | we monitor 24/7 |
| auto-cancel | n/a | wild treasury → free |

★ core/ is byte-identical. Only WHERE it runs + WHO owns keys + billing differ. ★

---

## 13. OS-agnostic core (macOS tools disabled on cloud) — how

The phone call for Anicca life-manager needs ONLY: speak persona message,
converse, hang_up. It does NOT need Mac control (screen/video/brightness).

sutando conversation-server.ts:713 registers ALL macOS inline tools:
```ts
for (const t of inlineTools) { if (!seen.has(t.name)) { tools.push(t); ... } }
```
`inlineTools` = openFile, pressKey, captureScreen, typeText, volume, brightness,
clipboard, slideControl, fullscreen, etc. (all execSync osascript → macOS only).

**Fix (deploy flag, gate the macOS tools)**:
```ts
const DEPLOY = process.env.ANICCA_DEPLOY || 'local';        // 'local' | 'cloud'
const PHONE_MINIMAL = DEPLOY === 'cloud';                   // Linux sandbox
...
// only register macOS inline tools when NOT cloud
if (!PHONE_MINIMAL) {
  for (const t of inlineTools) { if (!seen.has(t.name)) { tools.push(t); seen.add(t.name); } }
}
// also gate ownerOnlyTools + the owner fast-path Mac sections behind !PHONE_MINIMAL
```
Result: on cloud (Linux Daytona sandbox), `ANICCA_DEPLOY=cloud` → phone agent
registers only hang_up + get_current_time → no osascript ever invoked. Same
core/, same conversation engine, OS-agnostic. The persona prompt (Anicca:
wake/meditate/etc) is identical; only the Mac-control toolset is stripped.

BP: docs.pipecat.ai/pipecat/features/gemini-live "deploy to your own
infrastructure" — voice pipeline (Twilio↔Gemini Live) is pure network, OS-free.
The only OS coupling is the optional Mac-control toolset, gated by the flag.

→ Task: add ANICCA_DEPLOY flag to conversation-server.ts (patch record), wire
into Daytona sandbox init.sh as ANICCA_DEPLOY=cloud.

## 14. STRATEGY decision: web-primary + Dais dogfoods cloud (Dais 2026-06-09)

**Decision**: ★ Go web-app-primary. Dais uses a CLOUD owner account (free),
not a local Mac setup. OSS code stays public for self-hosters. ★

Why (dogfooding best practice — Stripe/Supabase/Linear all run their own cloud):
| | Dais self-hosts local | Dais dogfoods cloud (chosen) |
|---|---|---|
| experiences what users get | NO (different setup/bugs) | YES (identical to paying users) |
| catches web user bugs | NO | YES (feels every issue first) |
| maintenance | 2 paths (his local + web) | 1 path (web) |
| uptime | his Mac (sleeps, fragile) | server 24/7 (reliable) |
| cost to Dais | own API ~$25/mo | $0 (owner account) |

Migration path:
1. NOW: local Mac is Dais's bridge (just fixed, working).
2. BUILD: PHASE 3 web/cloud (Daytona spawn + control-plane).
3. THEN: Dais migrates to a cloud owner account (free), dogfoods, retires local Mac.

OSS remains: code public (anicca-oss), self-hosters can run their own. But the
canonical product + Dais's own usage = web/cloud. This kills local/cloud drift
because Dais lives on the same substrate as paying users.

---

## 15. WEB architecture REVISED — multi-tenant, NOT per-user sandbox (2026-06-09)

**Correction**: §11/§12 said "1 Daytona sandbox per user running the full core".
That is over-engineering. The life-manager is DETERMINISTIC (gcal × location ×
time → call) — it runs NO per-user arbitrary code. So per-user sandboxes are
unnecessary cost/complexity. The right model = ★ ONE multi-tenant backend ★.

Existing infra (verified 2026-06-09):
- apps/api: Node/TS on Railway, Prisma + Supabase (already deployed)
- Supabase (RLS-capable) for per-user data
- Stripe migration tables present
- Daytona CLI installed (only needed for wild-Anicca, NOT life-manager)

### Multi-tenant web architecture

```
ONE Telegram bot (@anicca_bot)
   serves ALL users by chat_id. onboarding + Live Location sink for everyone.
        │ each user's GPS, name, phone, gcal-token → Supabase row (RLS by user_id)
        ▼
Supabase (per-user data, RLS)
   users(id, name, phone, tg_chat_id, stripe_sub, ...)
   oauth_tokens(user_id, gcal_token, ...)        ← vault
   locations(user_id, lat, lon, received_at)     ← live GPS
   events_cache(user_id, ...)  interventions(user_id, ...)  trust_balance(user_id, n)
        ▲
        │ read/write
ONE apps/api cron (Railway, every 5 min)
   for each PAYING user:
     load location + gcal + profile from Supabase
     run the SAME decide() logic (gcal × GPS × time)
     if CALL → POST sutando /call (user's phone, persona prompt)
     if late-risk → renraku draft → Telegram approve → send
        │
        ▼
ONE sutando phone server (ANICCA_DEPLOY=cloud, Linux, macOS tools off)
   places calls to ANY user's number with OUR Twilio + OUR Gemini key
   Charon male, Gemini Live, bidirectional
```

### Why multi-tenant beats per-user sandbox

| | per-user Daytona sandbox | multi-tenant 1 backend (chosen) |
|---|---|---|
| cost | $0.30/day × N users | ~$20/mo Railway total + per-call Twilio + per-token Gemini |
| complexity | spawn/teardown per signup | standard SaaS cron loop |
| isolation | full VM | Supabase RLS per row |
| needed for life-manager? | NO (deterministic) | YES |
| Daytona still used for | wild-Anicca (autonomous earner) only | — |

### Public-copy feature → web component map

| 公開文 | web component |
|---|---|
| 位置を常に把握 | Telegram bot Live Location → Supabase locations |
| 行動時刻に電話・通知 | apps/api 5-min cron → decide() → sutando /call |
| 10分前行動 | decide() buffer logic (same as local) |
| Telegram で 名前/電話/位置/cal 連携 | Telegram onboarding → Supabase users + oauth_tokens |
| 遅刻時 関係者へ承認後連絡 | renraku → Telegram approve button → send |
| 介入を自己改善 | interventions table → per-user tuning in decide() |
| 信用残高が溜まる | trust_balance table, increment on on-time |
| 毎朝メール | apps/api daily cron → per-user email |
| サブスク課金→自動解約 | Stripe Checkout + webhook; wild-treasury cron cancels |

★ SAME decide()/transit_lookup logic. Local reads files; web reads Supabase
rows and loops all users. ONE bot, ONE phone server, ONE cron — multi-tenant. ★

### Build order (PHASE 3, revised)
```
3-1 /install SaaS LP (public copy) + /oss split
3-4 Telegram onboarding (name/phone/loc/cal → Supabase)
3-3 Stripe Checkout $49.99/mo + 7d trial + webhook
3-2 apps/api: port decide()/transit_lookup to read Supabase, 5-min multi-user cron
3-8 sutando phone server on Railway/Fly (ANICCA_DEPLOY=cloud), our Twilio+Gemini
3-7 OAuth vault (Supabase RLS) + Live Location → Supabase
3-x daily email cron + trust_balance + interventions tables
3-9 auto-cancel (wild treasury → Stripe cancel → free mail)
   (per-user Daytona sandbox = DROPPED for life-manager)
```

---

## 16. WHAT ACTUALLY WORKS — run-verified 2026-06-09 (no plans, only proof)

Each capability was RUN and verified (not assumed). ✅ = ran & passed.

| # | 公開文 機能 | 実走テスト | 結果 |
|---|---|---|---|
| ③ | 位置を常に把握 | `get_location()` → lat=35.6796 age=1s | ✅ WORKS |
| ④ | 目的地検索+ルート | `geocode('MUIT')`→中野(Firecrawl) + `build_itinerary('銀座駅')`→37分,1乗換 | ✅ WORKS |
| ⑤ | 電話 (Charon双方向) | sutando PID稼働 + 直前call transcript: "アニッチャです"/"1+2は3ですよ"/Dais"it's working" | ✅ WORKS |
| ⑦ | decide() 判定 | 瞑想@家 departBy=now → action=call | ✅ WORKS |
| — | heartbeat 5分毎 | cron `*/5` fired, no-location gone, LT event 認識 | ✅ WORKS |
| ⑥ | 遅刻→関係者連絡 | renraku.py 存在・syntax OK だが lateness_check に全配線+承認flow 未接続 | 🟡 PARTIAL |
| ⑧ | 毎朝メール | anicca-report/scripts/run.sh 存在 ("mail the day's summary") だが ★cron未登録★ | 🟡 PARTIAL |
| 介入自己改善 | (未実装) | code なし | ❌ NOT BUILT |
| 信用残高 | (未実装) | code なし | ❌ NOT BUILT |
| ② | Temporal per-user | `which temporal` → not found | ❌ NOT INSTALLED |
| ① | Telegram onboarding (multi-user) | routes/*telegram* なし | ❌ NOT BUILT |
| ⑨ | Stripe sub + 自動解約 | billing/index.js 存在(iOS RevenueCat用) だが web sub + treasury cancel 未配線 | ❌ NOT BUILT |

### Truth summary (LOCAL, Dais's own Anicca)
```
✅ WORKING NOW (run-verified):
   位置把握 + 目的地検索 + ルート(10分前逆算) + decide判定 + Charon双方向電話
   + 5分毎heartbeat
   = 公開文の「位置→ルート→10分前に電話＋ガイド」の CORE が動いている

🟡 PARTIAL (exists, not fully wired):
   遅刻時関係者連絡 (renraku.py 有、 全event配線+承認flow 未)
   毎朝メール (anicca-report 有、 cron 未登録)

❌ NOT BUILT:
   介入自己改善 / 信用残高 counter
   web 全体 (Temporal / onboarding / Stripe sub / 自動解約)
```

### Web (ALL not built — verified)
Temporal not installed, no Telegram onboarding route, no web Stripe subscription
flow, no auto-cancel. The §15 Temporal architecture is a DESIGN, not running code.
apps/api billing/index.js exists but is for iOS RevenueCat, not web subs.

★ HONEST STATE: LOCAL core (位置→ルート→電話) is REAL and run-verified today.
Everything web is design-only. Next real work = wire 🟡 (renraku + daily mail cron)
to finish LOCAL, then build web from §15 design. ★

---

## 17. Final architecture: ONE server (Pipecat), Mac version retired

**Decision (Dais 2026-06-09)**: build ONE server version that works anywhere for
100s of users. sutando (macOS-coupled, TypeScript + bodhi + Mac tools) was good
for Dais's local Mac validation; the SERVER product's voice layer = ★ Pipecat ★
(Python, server-native, OS-agnostic). Dais dogfoods the server; Mac version retired.

BP:
- docs.pipecat.ai/pipecat/features/gemini-live — "production-ready voice agents,
  Gemini Live for telephony, web, mobile" (server-designed, 1-970-LIVE-API live demo)
- daily.co/products/pipecat-cloud — "enterprise infra, automatic scaling, containerized"
- github pipecat-examples/phone-chatbot/daily-twilio-sip-dial-out/server.py — dial-out reference

```
ANICCA server (Railway / Pipecat Cloud, no macOS dependency):
  INGRESS: grammY/python Telegram bot (webhook) + Stripe webhook
  STORE:   Supabase (users/locations/oauth_tokens/trust_balance/interventions, RLS)
  BRAIN:   Temporal per-user DailyLifeWorkflow (durable)
             location signal → gcal read → geocode(Geocoding→Firecrawl) →
             route(transitous) → departBy(−10min−15min) → timer → decide() Activity
  VOICE:   Pipecat phone server (Twilio Media Streams ↔ Gemini Live, Charon ja)
  OUT:     Resend (mail) + Twilio (call) + LINE/Gmail (relay)

  decide() + transit_lookup = SAME Python already run-verified in local.
  Only rebuilt: voice layer (sutando→Pipecat), scheduler (cron→Temporal),
  state (files→Supabase).
```

## 18. The TWO outbounds — technical detail (BP-verified)

Anicca has exactly TWO outbound channels. Both are server-side, OS-agnostic.

### Outbound A — VOICE CALL (Anicca calls the user)

```
Trigger: Temporal timer fires → callUser() Activity
  → POST to Pipecat dial-out server /start {phone, persona_prompt}
  → Pipecat: Twilio REST API POST /Calls (programmable voice)
       BP: twilio.com/docs/voice/api "make outbound call = POST to Calls resource"
  → Twilio rings user; on answer → TwiML <Connect><Stream> → WSS to Pipecat
  → Pipecat pipeline: Twilio Media Streams (mu-law 8kHz)
       ↔ Gemini Live (native audio, Charon, ja-JP)  ← bidirectional, interruptible
  → persona_prompt carries: current GPS + route + event + "you are Anicca"
  → user converses; Gemini responds; hang_up tool ends call

  BP refs:
   - twilio.com/docs/voice/tutorials/how-to-make-outbound-phone-calls
   - docs.pipecat.ai/pipecat/telephony/twilio-websockets (dial-out test flow)
   - github pipecat-examples .../daily-twilio-sip-dial-out/server.py (/start endpoint)
  Cost: Twilio ~$0.013/min + Gemini Live tokens. Our keys (web) / user key (OSS).
```

### Outbound B — STAKEHOLDER RELAY (Anicca contacts others, user-approved)

```
Trigger: workflow detects late-risk (user position vs required arrival)
  → get event.attendees (from gcal) → LLM drafts reply
  → Telegram: "佐藤さんへ『15:00着』送る? [返信先▼][返信案 edit][承認]"
  → user taps 承認 (Telegram callback → workflow signal)
  → send via the right channel:
       EMAIL  → Gmail API messages.send WITH threadId + In-Reply-To header
                = appears as a REPLY in the existing thread (not a new mail)
                BP: developers.google.com/workspace/gmail/api/guides/sending
                    (messages.send; thread reply needs References/In-Reply-To)
       LINE   → LINE Messaging API Push Message (to: userId)
                = sends without the recipient messaging first
                BP: developers.line.biz Messaging API + aws blog "Push Message API
                    sends to LINE users without requiring the user to message first"
       (fallback) Resend for plain notifications

  KEY: user ALWAYS approves the recipient + draft before send (公開文:
       「返信先・返信案を承認後に、即時連絡」). No auto-send without tap.
  BP refs:
   - developers.google.com/workspace/gmail/api/guides/sending (reply-in-thread)
   - developers.line.biz/en/docs (Push Message, no prior-message needed)
   - unipile.com/email-api-guide (act on behalf of user's real Gmail via OAuth)
  Auth: per-user Gmail OAuth token (Supabase vault) for email-as-user;
        LINE channel access token for LINE push.
```

### Why two outbounds, not more
- Voice = the primary intervention (wake/move/sleep). High-attention.
- Relay = trust protection (don't make the user lose face when late). Approved.
- Telegram text (guide/approve) is in-band, not counted as "outbound" — it's the
  control surface the user already opted into.

★ Both outbounds run server-side (Twilio API + Gmail/LINE API = pure HTTP), zero
macOS dependency. Verified by BP that all are cloud-native. ★

---

## 19. Stakeholder relay — REAL strategy (BP-verified 2026-06-09)

Problem: the user's coworkers/family are on Gmail, LINE, WhatsApp — but they have
NOT added Anicca's bot. How does Anicca contact them on the user's behalf?

BP findings:
- LINE Messaging API push = ONLY to YOUR bot's friends (so coworkers unreachable directly).
  developers.line.biz/reference/messaging-api `/v2/bot/message/push`
- LINE Notify = ★ DEAD, terminated 2025-03-31 ★. (developers.line.biz EOL news)
- Personal LINE automation (Selenium) = ToS violation, ban risk. NOT used.
- WhatsApp Business API (Cloud API) = CAN message any number, BUT outside a 24h
  service window requires pre-approved TEMPLATE messages (Meta approval).
  developers.facebook.com .../whatsapp/messages/send-messages
- ★ DEEP LINKS = the breakthrough ★: `wa.me/<num>?text=<prefilled>` (WhatsApp),
  `https://line.me/R/share?text=<text>` (LINE share). User taps once → their app
  opens with the message pre-written → user taps send. ToS-safe, any contact.
  appsflyer.com/blog/deep-linking/whatsapp-deep-link

### Tiered relay (matches 公開文「返信先・返信案を承認後に、即時連絡」)

```
Anicca drafts the message, then routes by where the contact is:

TIER 1 — EMAIL (coworkers, formal) ── FULLY AUTOMATED
  user's Gmail OAuth → messages.send + threadId + In-Reply-To
  → arrives as a REPLY from the user; recipient never needs to know Anicca
  → confidence: ◎ (most work contacts have email)

TIER 2 — WhatsApp / LINE (family, friends) ── ONE-TAP via DEEP LINK
  Anicca builds deep link with pre-filled approved text:
    WhatsApp: https://wa.me/<E164>?text=<urlencoded draft>
    LINE:     https://line.me/R/share?text=<urlencoded draft>
  → Anicca sends the link to the user in Telegram (the approval surface)
  → user taps → WhatsApp/LINE opens to that contact, message pre-written
  → user taps send (= the "approval" AND "send" are one tap)
  → ToS-safe (user sends from their own account), works for ANY contact

TIER 3 — SMS (phone-only contacts) ── Twilio
  Twilio Messages API → SMS to the number (from our/user Twilio number)

The user ALWAYS approves before send (公開文 compliant). For email the approval is
a Telegram [送信] button; for WhatsApp/LINE the deep-link tap IS the approval+send.
```

### UX example

```
Anicca (Telegram):
 「部長会議に5分遅れそうです。 佐藤部長に連絡しますか?
   返信案: 「すみません、5分ほど遅れます。15:05には着きます。」

   [📧 部長のメールに返信]      ← Gmail OAuth, fully auto
   [💬 WhatsApp で送る]         ← opens wa.me/<num>?text=... pre-filled
   [💚 LINE で送る]             ← opens line.me/R/share?text=... pre-filled
   [✏️ 文面を編集]
 」
user taps [💚 LINE で送る] → LINE opens, 佐藤部長 chat, message ready → tap send
```

### Why this beats "Anicca sends as the user automatically"
- Personal LINE/WhatsApp automation = ToS ban risk → NEVER auto-drive personal apps.
- Deep link = user's own one tap = compliant + zero risk + works for every contact
  regardless of which app, because it just opens the app the user already has.

★ Email = full auto (OAuth). LINE/WhatsApp = one-tap deep link (the approval).
SMS = Twilio. Covers Gmail + LINE + WhatsApp contacts, all ToS-safe. ★

---

## 20. Stakeholder relay — repo options (BP, github stars)

### WhatsApp

| repo | type | risk | use |
|---|---|---|---|
| **WhiskeySockets/Baileys** | unofficial, WebSocket (no browser), TS, ~15k★ | ToS gray (ban risk on personal #) | send as user's WhatsApp, no Selenium |
| **pedroslopez/whatsapp-web.js** | unofficial, Puppeteer (WhatsApp Web), ~15k★ | ToS gray, heavier (browser) | same, browser-driven |
| avoylenko/wwebjs-api | REST wrapper of whatsapp-web.js | same | easy HTTP interface |
| **Meta WhatsApp Business Cloud API** | ★ OFFICIAL ★ | none (compliant) | any number, but template-approval outside 24h window |

### LINE

| repo | type | risk | use |
|---|---|---|---|
| **line/line-bot-sdk-nodejs**, **line-bot-sdk-python** | ★ OFFICIAL ★ | none | push ONLY to bot's friends (coworkers unreachable) |
| CHRLINE / unofficial reverse-eng libs | unofficial (benv.io, lutwidse) | ★ HIGH ban risk ★ | send as personal LINE — NOT recommended |
| (deep link) line.me/R/share?text= | official URL scheme | none | one-tap user-sent (§19) |

### Decision (BP-grounded)

```
TIER 1 EMAIL    → Gmail API (official OAuth)        full auto, ◎ for coworkers
TIER 2 WhatsApp → Meta Cloud API (official) for templates / time-sensitive
                  OR deep link wa.me?text= (one-tap) for free-form
TIER 3 LINE     → deep link line.me/R/share (one-tap)  ← official, safe
                  (NOT unofficial reverse-eng libs = ban risk)
TIER 4 SMS      → Twilio (official)

Unofficial WhatsApp (Baileys/whatsapp-web.js) = available + powerful, but ToS
gray + ban risk on the USER's personal number. Reserve as opt-in advanced mode
for self-host OSS users who accept the risk; NOT default for paying web users.

For the WEB product (paying users, our reputation): official-only —
Gmail API + Meta WhatsApp Cloud API + LINE official + deep links + Twilio.
For OSS self-host: user MAY enable Baileys/whatsapp-web.js at their own risk.
```

★ Default = official APIs + deep links (zero ban risk). Unofficial libs
(Baileys, whatsapp-web.js, CHRLINE) = documented options for OSS power-users,
opt-in, not default. ★

---

## 21. Reliability — CORRECTED (2026-06-09, my earlier cautions were wrong)

I earlier raised 3 cautions (Telegram 8h limit, Mac sleep, tunnel). Verified
against REAL data + BP — 2 of 3 do NOT exist for Dais's setup. Honest correction:

### ① "Telegram 8h location limit" → DOES NOT EXIST (I was wrong)
- BP: x.com/telegram/status/1800534054959481255 (official): "By choosing
  'Until I turn it off', your location will be shared [indefinitely]".
- REAL DATA: state/location/8547730585.json `live_period: 2147483647` (=INT32_MAX
  = indefinite), age=3s, accuracy=12m, heading=181, 48 "saved location" per 100
  log lines = continuously updating.
- → Dais already shares 24/7 with "Until I turn it off". 8h problem is a myth.
  OwnTracks UNNECESSARY. My earlier 8h-limit claim was based on stale info.

### ③ "Mac sleep stops heartbeat" → DOES NOT EXIST
- Dais runs on a Mac mini = 24/7 always-on server, does not sleep.
- launchd heartbeat (StartInterval=300) runs uninterrupted.

### ② "tunnel rotation breaks calls" → ALREADY SOLVED (task 0-6)
- tunnel-watcher (ai.anicca.phone-tunnel-watcher) detects URL change every 30s,
  restarts sutando to re-sync. Self-healing.

### The ONLY real fix this round
openclaw gateway cron was unreliable (all crons "error", heartbeat gapped
09:48→12:35). Moved lateness 5-min poll to launchd StartInterval=300
(ai.anicca.lateness-heartbeat). macOS-native, rock-solid. openclaw cron versions
disabled to prevent double-fire.

### Net reliability state (run-verified)
```
✅ location: 24/7 (live_period indefinite, 48 updates/100 log lines)
✅ heartbeat: launchd 5-min (PID 94493, LastExit=0)
✅ Mac mini: 24/7 always-on (no sleep)
✅ sutando phone + tunnel-watcher: alive + self-healing
✅ gcal: today 17:40 LT, 22:45 Sleep; tomorrow wake/meditation/running/MUIT
→ Anicca calls reliably from today. No OwnTracks, no 8h re-share needed.
```

### Today's call schedule (real gcal data, departBy = event − travel − 10min − 15min lead)
| time | event | call |
|---|---|---|
| 17:40 | LT Night (connpass) | leave + route guide |
| 22:45 | 😴 Sleep | "prepare for sleep" (quiet-hours punch-through) |
| tmrw 05:50 | 🧘 Meditation | "meditation time" |
| tmrw 06:50 | 🏃 Running | "run time" |
| tmrw 06:55 | 🛏 Wake up | "wake up" |
| tmrw 07:35 | MUIT 出社 | leave + route guide (needs location, which is 24/7 on) |

★ All 10-min-early built into departBy. Dais arrives 10 min early to every action. ★

---

## 22. RENRAKU (stakeholder relay) — code-level design (task #21)

### What renraku.py ALREADY has (read 2026-06-09)
```
renraku.py (181 lines):
  compose(sender, event, minutes)  → message text (Dais 2026-05-31 template:
       no event name, no name, just apology "約N分遅刻、申し訳ございません")
  send_gmail(to, subject, body)    → via `gog gmail send` CLI ✅ works
  send_renraku(event, minutes, attendees):
    recipient resolution order:
      1. profile.stakeholder_for(event) → registered email/slack
      2. calendar attendees → email      ← gcal has attendee emails
      3. firecrawl_find_contact()        → web search for official contact
      4. no recipient → Slack draft for manual forward
    auto_send_allowed(profile) gate: if OFF → posts to SLACK "確認待ち"
```

### The GAPS (why it's 🟡 not ✅)
```
1. Approval goes to SLACK, not Telegram, and is NOT a button flow
   (just a "確認待ち" text — user can't approve with one tap)
2. lateness_check does NOT call send_renraku (grep: not wired) → never triggers
3. telegram_bot has NO CallbackQuery handler → no approval buttons exist
4. No contact MEMORY (resolves every time; no "register once, reuse")
5. No LINE/WhatsApp deep-link (email only)
```

### Code design to close the gaps (#21)

```
┌─ 1. WIRE: lateness_check.decide() = "guide"/late → trigger relay ──────────┐
│  in lateness_check.py main(), when action in ("guide",) AND minutes_late>0: │
│     event = nxt  (has summary, attendees, departByIso)                       │
│     minutes = int(-mins)  (how late)                                         │
│     renraku.propose_relay(event, minutes)   ← NEW (was send_renraku直送)     │
└─────────────────────────────────────────────────────────────────────────────┘

┌─ 2. CONTACT MEMORY (register once, reuse) ────────────────────────────────┐
│  state/contacts.json:                                                       │
│    { "佐藤部長": {"email":"sato@pixie.co.jp","line_url":null,                │
│                  "relation":"上司","last_channel":"email","uses":3} }        │
│  resolve_contacts(event):                                                    │
│    1. gcal attendees (email) → save to contacts.json                        │
│    2. if attendee name matches contacts.json → reuse (no re-search)          │
│    3. gmail search "<name>" → extract email → save                           │
│    4. firecrawl (org contact) → save                                         │
│    → returns [{name, email, line_url?}], persisted so next time = instant   │
└─────────────────────────────────────────────────────────────────────────────┘

┌─ 3. TELEGRAM APPROVAL (inline keyboard, not Slack) ───────────────────────┐
│  renraku.propose_relay(event, minutes):                                     │
│    contacts = resolve_contacts(event)                                       │
│    draft = compose(...)                                                      │
│    for c in contacts:                                                        │
│      buttons = []                                                            │
│      if c.email:    buttons += [["📧 "+c.name+"にメール", cb:"relay:email:"+id]]│
│      if c.line_url: buttons += [["💬 LINEで送る", url:c.line_url+draft]]      │
│      buttons += [["✏️ 編集", cb:"relay:edit:"+id],["👤 宛先変更",cb:"relay:to"]]│
│      tg_send(chat_id, f"{c.name}に連絡しますか?\n宛先:{c.email}\n>{draft}",   │
│               inline_keyboard=buttons)                                       │
│    persist pending relay → state/relay_pending/<id>.json {event,draft,contact}│
└─────────────────────────────────────────────────────────────────────────────┘

┌─ 4. CALLBACK HANDLER (telegram_bot.py, NEW) ──────────────────────────────┐
│  app.add_handler(CallbackQueryHandler(on_relay_callback))                   │
│  on_relay_callback(update):                                                 │
│    data = update.callback_query.data  # "relay:email:<id>"                   │
│    pend = read state/relay_pending/<id>.json                                │
│    if action=="email":                                                       │
│       renraku.send_gmail(pend.contact.email, subject, pend.draft)            │
│       answer "✅ 送信しました"; bump contacts[name].uses; clear pending      │
│    if action=="edit":  prompt user for new text → re-propose                │
│    # LINE/WhatsApp = url button (no callback) → opens app pre-filled, user   │
│    #   taps send in their own app (= the approval IS the tap)               │
└─────────────────────────────────────────────────────────────────────────────┘

┌─ 5. DEEP LINK (LINE/WhatsApp, §19) ───────────────────────────────────────┐
│  line_url  = "https://line.me/R/share?text=" + urlquote(draft)              │
│  wa_url    = "https://wa.me/" + e164 + "?text=" + urlquote(draft)           │
│  → as Telegram inline url-button → one tap opens app with draft pre-filled  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data flow (one renraku cycle)
```
heartbeat (5min) → decide()="guide" + late → renraku.propose_relay(event, min)
  → resolve_contacts() [gcal attendee / contacts.json memory / gmail / firecrawl]
  → compose(draft)
  → Telegram message + inline buttons [📧メール][💬LINE][✏️編集]
  → user taps [📧メール]
      → CallbackQuery → renraku.send_gmail() → "✅送信" + contacts.uses++
    OR taps [💬LINE]
      → url button opens LINE pre-filled → user sends in LINE
  → log state/renraku_sent.json (idempotency: once per event)
```

### Files to touch (#21)
```
renraku.py            + propose_relay() + resolve_contacts() + deep_link helpers
                        (keep compose/send_gmail; replace Slack-confirm with Telegram)
telegram_bot.py       + CallbackQueryHandler(on_relay_callback) + edit flow
lateness_check.py     + wire: action="guide"&late → renraku.propose_relay
state/contacts.json   NEW (contact memory)
state/relay_pending/  NEW (pending approvals)
```

### Test (run-verify before claiming done)
```
1. inject a past-departBy event with an attendee email → run.sh
   → expect Telegram message with [📧] button
2. tap [📧] → expect gmail sent (gog) + "✅送信" + contacts.json updated
3. re-run same event → expect contact resolved from memory (no re-search)
```

---

## §23 — openclaw = アニッチャ marketing AI 1本化 + model-resolution 恒久修正 (2026-06-09)

**Dais 決定 (2026-06-09)**: 「openclaw will just be a marketing AI. just scaling the aniccaios app. nothing else. disable every cron but the ones posting to social media + articles to each platform.」

### A. model-resolution stall 真因 (2大要因の二重詰み)

| # | 原因 | 証拠 | 修正 |
|---|---|---|---|
| ① | deepseek:default profile が `disabled: billing` 凍結 | $0時代に "Insufficient Balance" → openclaw が 5h billing-disable backoff 記録。 Dais が $4.97 top up 後も凍結残存 (残2.1h) | auth-state.json の disabledUntil/cooldownUntil を全 clear (deepseek/moonshot/xai/blockrun) → gateway 再起動 |
| ② | primary `openai/gpt-5.4-mini` (codex) が plugin metadata 破損で70秒 hang | `conflicting plugin install metadata for: clawrouter, codex, slack` (state-migrations) + codex は 11日まで rate-limit | deepseek を fallbacks 先頭に。 gpt は11日 top up 後 primary 復帰。 deepseek 凍結解除で fallback 即着 |

**根拠 (docs/concepts/model-failover.md L66)**: cron `payload.model` = job primary、 `payload.fallbacks` 無い限り `agents.defaults.model.fallbacks` 継承。 全 cron に payload.fallbacks ゼロ確認済 → 全 cron が deepseek fallback 自動継承。 個別編集不要。

**deepseek routing 真相**: `deepseek/deepseek-v4-pro` `-v4-flash` は blockrun 非経由 = built-in deepseek provider (api.deepseek.com 直 + DEEPSEEK_API_KEY)。 blockrun が宣言するのは `deepseek/deepseek-chat` `-reasoner` のみ。 → 直 API 残高 $4.97 が実際に使われる。 検証: cold-email-reply/send 両方 status=ok 復活。

**openclaw.json defaults.model** (commit cde0b3ae0):
- primary: `openai/gpt-5.4-mini` (11日 top up 後の本命)
- fallbacks: `[deepseek/deepseek-v4-pro, moonshot/kimi-k2.5, openai/gpt-5.4, xai/grok-4-1-fast-reasoning]` (偽 ref `free/*` 除去、 deepseek 先頭)

### B. sub-agent 廃止 (Dais「why using sub-agent? they can just use the model」)

廃止 v1 受託 sub-agent (anicca-corey-cold-email / aie-product 等 8個) は blockrun auth 1個のみ → gpt も deepseek も使えず stall。 3 active cron を `--clear-agent` で default `anicca` agent (9 profile 完備) に移管。 sub-agent auth コピーは revert (hygiene)。

### C. cron 100→70 (投稿系のみ稼働、 30 disable)

**KEEP 70** = larry×27 (TikTok/Reels) + reelclaw×18 (Reels) + watercolor×3 (画像) + article-daily×7 (Zenn/Devto/Note/Substack) + comedy×4 + backlink×2 (Reddit/HN) + 投稿support (trend/music/pattern/warmup/capafy) + daily-memory (build-in-public X) + anicca-daily-mail。

**DISABLE 30** = heartbeat (最大 compute) + 監視7 (watch-sweep/fuel-broker/doctor-monkey/config-canary/credit-monitor/postiz-health/seo-rank) + 廃止v1受託4 (cold-email×3/aie-product) + 予定生活系6 (event-bot/morning-leave/gcal-heal/schedule-template/travel-fill/stage) + 応募4 (booking/connpass/jsps) + 雑務8。 + Dais 指定カット: yangmun-monk×2, 4.7-slideshow。

全 30 は `--disable` (削除でなく)、 `openclaw cron edit <id> --enable` で復活可。 lateness 電話は launchd (ai.anicca.lateness-heartbeat) で別途稼働、 cron disable の影響なし。

**効果**: agent run/日 大幅減 → deepseek $10 で ~1年稼働 → gpt subscription 解約可能。 model 枯渇 stall の構造的解消。

---

## §24 — lateness-guard 統合 refactor + local↔cloud 共有 core (2026-06-09)

**Dais 指示**: 「使ってない重複を refactor。 全部 life-manager の中に。 読めるコード。 記憶ファイルを持て (毎回 search するな)。」

### A. 実施した refactor (lateness-guard → life-manager 統合、 task #17 完了)

| 問題 | 修正 |
|---|---|
| `lateness-guard` = life-manager が import してた旧重複コピー | 削除。 life-manager は全スクリプト自前所有を確認済 (md5比較) |
| `guide_me_now.py`/`saas_lateness.py` が `sys.path.insert(lateness-guard/scripts)` で旧版を import | `Path(__file__).resolve().parent` に変更 = 自分の scripts を import (self-contained) |
| `saas_lateness.py` の STATE が `lateness-guard/state/saas_sent.json` | `life-manager/state/saas_sent.json` に変更 |
| 冗長 cron `anicca-morning-leave-check` (旧 skill 参照) | gateway から削除 |
| 毎回どれが動いてるか search してた (dementia) | `skills/anicca-life-manager/MAP.md` 作成 = SSOT |

検証: `lateness_check.py` exit=0 (connpass 追跡継続)、 `guide_me_now`/`saas_lateness` import OK。
commit: anicca-dais `8ced77424` (main-internal)。

### B. local↔cloud で「同一 core」とは具体的に何か (ASCII)

```
                    ┌──────────────────────────────────────────┐
                    │   共有 CORE (local も cloud も同一コード)   │
                    │                                          │
                    │   lateness_check.py                      │
                    │     ├ decide(now, location, departures,  │  ← 純関数。 入力→action
                    │     │   home, dest) → {action, reason}   │     を返すだけ。 副作用なし
                    │     └ haversine_m()  (距離計算)           │
                    │   gcal_departures.py                     │
                    │     └ directions_travel_min(dest,origin) │  ← ルート所要時間
                    │   route_lookup.py / transit_lookup.py    │  ← transitous ルート
                    │   renraku.py (compose)                   │  ← 関係者連絡文 生成
                    └────────────────┬─────────────────────────┘
                                     │ 同じ関数を呼ぶ
              ┌──────────────────────┴───────────────────────┐
              ▼                                              ▼
   ┌─ LOCAL (ANICCA_DEPLOY=local) ─┐        ┌─ CLOUD (ANICCA_DEPLOY=cloud) ─┐
   │ 入力: 自分のGPSファイル        │        │ 入力: Supabase の各user GPS    │
   │ 入力: 自分のgcal              │        │ 入力: 各userの ics_url/oauth   │
   │ scheduler: launchd 5分 (1人)  │        │ scheduler: Temporal (N人 durable)│
   │ 状態: ローカルJSON            │        │ 状態: Supabase (RLS per-user)  │
   │ 電話: sutando :3100           │        │ 電話: Pipecat dial-out (Railway)│
   │ 課金: なし (OSS自己ホスト)     │        │ 課金: Stripe $49.99/mo         │
   └───────────────────────────────┘        └────────────────────────────────┘

   ★ decide()/directions_travel_min()/renraku.compose() = 1バイトも違わない同じ関数。
   ★ 違うのは「入力をどこから読むか (file vs Supabase)」「いつ叩くか (launchd vs Temporal)」
     「どう電話するか (sutando vs Pipecat)」「課金有無」の周辺だけ。
   ★ saas_lateness.py が既に cloud 版の入口の種 (Supabase subscriber → 同じ decide())。
```

### C. プロダクト方針 (Dais 確定)

- **OSS** = local 自己ホスト (無料、 自分のキー、 1人)。 信頼 + 開発者獲得。
- **Web** = cloud SaaS ($49.99/mo、 我々ホスト、 各人プロフィール記憶 + personalized nudge)。 = 売上。
- **自動解約** = wild-anicca treasury が自分で稼げたら Stripe 解約 → ユーザー無料化 (task #28)。
- **BP 根拠**: 1コードベース + deploy フラグの2モードは COSS 定石 (Plausible / Supabase / GitLab / Flagsmith — Flagsmith blog「open source」+「self-hosting」+ managed cloud)。 core 重複を持たない = メンテ1回で両方直る。
