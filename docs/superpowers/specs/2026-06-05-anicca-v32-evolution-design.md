# Anicca v3.2 Evolution — Design Spec

**Date**: 2026-06-05
**Author**: Anicca (with Dais as co-architect)
**Status**: DRAFT — awaiting user review
**Branch**: dev
**Related memory**: `feedback_superpowers_is_hard_rule_zero`, `feedback_crons_use_mini_models_only`, `feedback_openclaw_doctor_fix_rolls_back_cron_model_clears`, `feedback_finish_job_never_advance_unverified`

---

## 0. TL;DR

3 independent subsystems, one umbrella spec, three implementation plans:

| # | Subsystem | One-line goal |
|---|-----------|----------------|
| ① | **Persistent Phone Session** | Tap `phone` on Moshi → resume the same Claude Code conversation forever, no reconnects |
| ② | **Cron Verification Gate** | Every post-producing cron runs through fail-closed pre-publish + post-publish gates that LLM cannot bypass |
| ③ | **Frontier Model Routing** | Interactive chat = Opus 4.7 / GPT-5.5; cron + heartbeat + background = DeepSeek v4-pro / GPT-5.4-mini. One source of truth, doctor-fix-safe |

After this spec is approved, each subsystem gets its own `writing-plans` → `executing-plans` cycle (Tasks #2/#3/#4).

---

## 1. Mission

Anicca is currently a **generation-only agent** in three painful failure modes:

1. **Conversation discontinuity** — Phone tap = fresh shell = lost context. Dais has to re-onboard Anicca every tap. Violates A0.1 mandate 11 ("Anicca is executor of first resort").
2. **Unverified posts** — TikTok English channel got a Japanese video, music was missing, nobody noticed. The 5-step verification skill exists but lives in operator memory, not in skill code. Violates HARD RULE 0.12 + 0.14.
3. **Cheap-model chat** — Interactive sessions inherit `gpt-5.4-mini` from the cron-tuned default. Dais talks to Anicca with cron quality. The good models (Opus 4.7, GPT-5.5) are registered but never selected for chat.

The fix is structural, not procedural. **Skill code, not LLM discipline, enforces the gates.**

---

## 2. Scope

**In scope** (this spec):
- Design for the three subsystems above
- Files touched, success criteria, risks per subsystem
- Implementation order + dependencies

**Out of scope** (separate efforts):
- Heartbeat redesign beyond model swap
- New cron skills
- Anicca v3.2 colony architecture (multi-profile per instance) — already specified in `feedback_anicca_multi_profile_per_instance_colony`
- Browser-side stealth changes
- Postiz / TikTok account additions

---

## 3. Subsystem ① — Persistent Phone Session

### 3.1 Current state

| Component | Path | Behavior |
|---|---|---|
| `phone` binary | `/Users/anicca/bin/phone` | Every tap → `tmux new-session -s phone-<unix_ts>` (NEW session) |
| zsh interceptor | `~/.zshrc` (lines marked "Anicca tmux phone interceptor") | Catches `tmux attach -t phone` and rewrites to NEW session — defeats default tmux attach |
| Moshi mobile config | Moshi app → SSH to Mac Mini → executes `tmux attach -t phone` | Drives the interceptor |
| Claude Code session storage | `~/.claude/projects/-Users-anicca-anicca-project/` | Conversations persist on disk per directory |
| Claude Code resume flags | `claude -c` (most recent in cwd) / `claude -r <id-or-name>` (specific) / `--name "phone"` (named, resumable) | Available but never invoked by phone flow |

**Why current design**: Comment in shell config says "fresh shell that supports scroll in the Moshi terminal" — old Moshi version had a scroll bug with reattaching to existing tmux session with backscroll buffer. Tradeoff: scroll works, context dies every tap.

### 3.2 Goal (REVISED 2026-06-06 — Dais multi-session requirement)

| Property | Target |
|---|---|
| Tap latency | ≤ 2 s from Moshi tap to a usable Claude prompt |
| Each tap = NEW independent session | A fresh `claude` process with a brand-new conversation UUID. No `--continue` by default — the previous conversation in this dir is NOT reloaded. Dais explicitly wants spawning, not resuming, as the dominant flow. |
| Concurrency | Dais opens N Moshi tabs → N concurrent independent Claude sessions, all alive at the same time, all persistent on Mac Mini. Tab 1's typing does not leak into tab 2. |
| Disconnect tolerance | Wi-Fi → LTE switch, sleep, idle — every running session stays alive, mosh roams transparently. Re-opening Moshi does not kill any other tab's session. |
| Reattach | `phone ls` shows all live sessions on Mac Mini. `phone <name>` from a fresh tab reattaches to an existing one when Dais wants the old conversation back. |
| Goal device topology | iPhone (Moshi, N tabs) + Mac Mini. MacBook becomes optional, not required. |

### 3.3 Design — REVISED approach: **Mosh + per-tap unique tmux session + per-session unique Claude UUID, no `--continue`**

```
Each Moshi tab is its own mosh connection.
Each mosh connection spawns its own tmux session.
Each tmux session spawns its own Claude conversation.
All N coexist on Mac Mini, all survive disconnect.

Tab 1                Tab 2                Tab 3
[Moshi]              [Moshi]              [Moshi]
  │                    │                    │
  │ mosh UDP           │ mosh UDP           │ mosh UDP
  ▼                    ▼                    ▼
mosh-server #A      mosh-server #B      mosh-server #C
  │                    │                    │
  ▼                    ▼                    ▼
~/bin/phone (no arg)   ~/bin/phone           ~/bin/phone
  │                    │                    │
  ▼                    ▼                    ▼
SESSION=phone-<ts1>  SESSION=phone-<ts2>  SESSION=phone-<ts3>
tmux new-session -s phone-<tsX> -c ~/anicca-project
  │                    │                    │
  ▼                    ▼                    ▼
zshrc detects MOSHI_PHONE=1 + CLAUDE_AUTOSTARTED unset
  │                    │                    │
  ▼                    ▼                    ▼
exec claude --name "phone-<tsX>" \
            --session-id "$(uuidgen)" \
            --model claude-opus-4-7 \
            --max-budget-usd 10
  │                    │                    │
  ▼                    ▼                    ▼
fresh Opus 4.7      fresh Opus 4.7      fresh Opus 4.7
conversation A      conversation B      conversation C
(independent)       (independent)       (independent)
```

**Why per-tap unique session, NOT named singleton**:
- Dais explicitly wants N concurrent independent Claude conversations (e.g., one for ops, one for research, one for code).
- A singleton `phone` session would force all tabs to share one Claude process — input from tab 1 visible to tab 2 (tmux broadcasts). Not what Dais wants.
- Per-tap = `phone-<unix_ts>` (timestamp) keeps names unique and chronological for `phone ls`.

**Why mosh, not raw SSH** (unchanged from earlier analysis):
- Raw SSH disconnects on Wi-Fi → LTE switch (carrier IP change kills TCP).
- Mosh uses UDP + state-sync → handles roaming, screen sleep, intermittent connectivity transparently (mosh.org official).
- `mosh-server` runs per-user, no privileged daemon. SSH auth still gates the login.

**Why `--session-id "$(uuidgen)"` instead of `--continue`**:
- `claude --continue` reloads the most-recent conversation in `cwd` → every tab would resume the SAME conversation → not independent.
- `claude --session-id <UUID>` (per cli-reference) starts a brand-new conversation with a known ID → independent + later resumable by ID.
- Conversation transcripts persist under `~/.claude/projects/-Users-anicca-anicca-project/<uuid>.jsonl` → Dais can later `claude -r <uuid>` if he wants to revisit any specific tab.

**Reattach to an old session**:
- `phone ls` → tmux ls filtered to `phone-*` (shows all running tabs by timestamp)
- `phone phone-1780812345` → reattaches the named tmux session (mosh + tmux already handle reconnection cleanly)
- `phone kill phone-1780800000` → terminate a specific stale session

**Scroll behavior**:
- Modern Moshi (≥ 1.4) renders tmux alternate-screen correctly → scroll works in fresh per-tap sessions (the historical 2024 scroll bug only hit `tmux attach` on a session with backscroll history; new sessions are clean).
- Verification: open 2 tabs simultaneously, scroll independently in each on iPhone.

### 3.4 Files touched

| Path | Change |
|---|---|
| `/Users/anicca/bin/phone` | Full rewrite for multi-session: no-arg = spawn `phone-<unix_ts>` (new tmux + new claude UUID); `phone ls` = list running phone-* sessions; `phone <name>` = reattach; `phone kill <name>` = terminate; `phone last` = reattach the most recent (convenience) |
| `~/.zshrc` | Remove the existing tmux interceptor function (lines marked "Anicca tmux phone interceptor"). Add MOSHI_PHONE=1 + CLAUDE_AUTOSTARTED unset detection that runs `exec claude --name "$TMUX_SESSION" --session-id "$(uuidgen)" --model claude-opus-4-7 --max-budget-usd 10 OPENCLAW_CONTEXT=interactive` (the last is for subsystem ③ routing) |
| `/etc/ssh/sshd_config` on Mac Mini | `ClientAliveInterval 60` + `ClientAliveCountMax 5` (defense in depth even with mosh) |
| Mac Mini package | `brew install mosh` (one-time setup) |
| iPhone client | Verify Moshi's mosh support; if absent, recommend Blink Shell or Termius (both have native mosh). This is the one step that needs Dais's physical iPhone action (App Store install) — pre HARD RULE #-2 exception (physical movement). |
| Moshi mobile app config (or Blink/Termius) | Change SSH command from `tmux attach -t phone` to invoke `mosh user@host`. If Moshi cannot run mosh client directly, switch iOS terminal app. |
| New: `/Users/anicca/bin/phone-cleanup` | Daily cron, kills `phone-*` tmux sessions that have been idle (no attached client) > 7d. Does NOT kill currently-attached sessions. |
| New: `/Users/anicca/bin/phone-status` | Convenience: shows session count, model, budget remaining per active session (read from `~/.claude/projects/...`) |

### 3.5 Success criteria

- [ ] Moshi tab 1 tap → ≤ 2 s → fresh Opus 4.7 conversation, cursor ready
- [ ] Moshi tab 2 (new tab) tap → ≤ 2 s → SECOND fresh Opus 4.7 conversation, independent of tab 1 (different conversation UUID, different topic, no input bleed)
- [ ] Moshi tab 3 same again → THIRD independent session
- [ ] Lock iPhone 10 min while tab 2 was active → unlock → tab 2's conversation still alive, no reconnect prompt, scroll history intact
- [ ] Switch Wi-Fi → LTE mid-typing in tab 2 → mosh roams, typing resumes in the same conversation
- [ ] Force-quit Moshi → reopen → tabs gone from app UI but `phone ls` on Mac Mini shows all N sessions still running. `phone phone-<ts>` from a new tab reattaches.
- [ ] `phone ls` after 1 day → all sessions Dais started today visible, with timestamps
- [ ] No accidental conversation merging — Tab A's Claude `--session-id` ≠ Tab B's
- [ ] (Future / MacBook optional) `ssh anicca-mac-mini-1 -t 'tmux attach -t phone-<ts>'` can attach from MacBook to the same session as a fallback path

### 3.6 Risks

| Risk | Mitigation |
|---|---|
| Moshi mobile doesn't natively support mosh client | Use Blink Shell or Termius on iPhone instead (both have mosh built-in). User feedback gate — if Moshi is non-negotiable, fall back to SSH + ServerAliveInterval + tmux + claude --continue (loses roaming) |
| Claude Code internal idle timeout kills process | Verify with `claude --bg` (background session) which is explicitly long-lived. If foreground `claude` dies, switch to `claude --bg --name phone` + `claude attach phone` from the tmux pane |
| Multiple clients race on same tmux pane | tmux handles this natively (broadcast input mode); document for user that two attached sessions see each other's typing |
| Mosh-server not installed on Mac Mini | `brew install mosh` is a 1-step install, included in implementation plan |

### 3.7 Open questions for implementation plan

- Does the user's current Moshi mobile app support mosh, or must we switch iOS client? (Need to inspect ~/Library/Application Support/Moshi or ask)
- Is `claude --bg` more appropriate than foreground `claude --continue` for survival across SSH reconnects?

---

## 4. Subsystem ② — Cron Verification Gate

### 4.1 Current state

```
CRON trigger (jobs.json)
    │
    ▼
cron-codex.sh wrapper (budget + entrypoint)
    │
    ▼
LLM reads SKILL.md
    │
    ▼
[step 0] propose-and-rewrite.sh ── ah_check (14d anti-repeat, exit 2 = SKIP)
    │
    ▼
[step 1-5] LLM writes content, picks winner
    │
    ▼
[step 6] publisher script (post-x-direct.sh / 06-postiz-publish.sh / post-tt-camofox.sh)
    │  ├─ post-x-direct.sh sources verbatim-guard.sh → vg_check (PRE-POST only, exit 1 = stop)
    │  └─ 4.7-slideshow-factory: NO gate, NO verify
    │
    ▼
[step 7] X-useful ONLY: ah_record + HTTP 200 check
    │
    ▼
Slack report
```

**Gaps identified by research agent**:

| Gate | Pre-publish | Post-publish | Skills covered |
|---|---|---|---|
| `verbatim-guard.sh vg_check` | ✅ | ❌ | only `anicca-x-useful` + `seo-gate` |
| `ah_check` (14d repeat) | ✅ | ❌ | only `anicca-x-useful` |
| `brand-lock-gate.sh` (integration ID + lang) | ⚠️ exists but **not auto-invoked** | ❌ | none in production loop |
| `verify-public-state.sh` (live feed snapshot) | ❌ | ⚠️ exists but **orphaned** | none |
| Account/lang/audio/metadata match | ❌ | ❌ | **none** ← TikTok incident |

### 4.2 Goal

Every posting skill, with no exceptions, must:

1. **Pre-publish gate** (fail-closed): account match, language match, asset presence, caption sanitization, integration-ID lock. Exit non-zero → no post.
2. **Post-publish verify** (fail-closed with bounded retry): live feed snapshot within 5 min, account match, detected language match, asset integrity. Exit non-zero → no success report, escalate to Slack.
3. **Auto-fix loop** (bounded): network 5xx → retry ≤ 2; caption sanitization issue → 1 rewrite; everything else → escalate human (Slack URGENT) and stop. No infinite fix loops.

### 4.3 Design — Recommended approach: **Two shared library scripts + mandatory source**

```
~/.openclaw/skills/_shared/lib/
  ├─ pre-post-gate.sh    ← NEW, source-able + standalone-executable
  ├─ post-verify-gate.sh ← NEW, same
  ├─ verbatim-guard.sh   ← existing, vg_check stays
  └─ propose-and-rewrite.sh ← existing, ah_check stays

~/.openclaw/skills/<posting-skill>/post-x-direct.sh (or platform equiv)
  │
  ├─ source pre-post-gate.sh
  ├─ ppg_check --platform X --account "@aniccaxxx" \
  │            --integration-id "$X_INTEGRATION_ID" \
  │            --language "ja" \
  │            --caption-file caption.txt \
  │            --asset-manifest manifest.json
  │   exit code 0 = ok, 1-3 = STOP (lang mismatch / acct mismatch / asset missing)
  │
  ├─ [actual POST call]
  │
  ├─ source post-verify-gate.sh
  └─ pvg_verify --platform X --post-id "$POST_ID" \
                --expected-caption-head "$(head -c 40 caption.txt)" \
                --expected-language "ja" \
                --timeout 300 --max-retries 2
      exit code 0 = verified live, 4+ = NOT live or wrong content → escalate
```

**Why shared lib over per-skill duplication**:
- Single source of truth (HARD RULE 0.17)
- One bug fix = all skills fixed
- `vg_check` precedent already follows this pattern (verbatim-guard.sh sourced everywhere it's used)

**Why `_shared/lib/` over `cron-codex.sh` wrapper**:
- Each posting skill has skill-specific metadata (account, integration ID, language, niche persona). Wrapping at cron level loses this binding.
- LLM can still reason about failures inside the skill ("verify failed → caption too long → rewrite shorter") — this is the legitimate place for skill-level intelligence.

**Platform-specific verifiers** (called by `pvg_verify` based on `--platform`):

| Platform | Verifier strategy |
|---|---|
| X (Twitter) | X API `GET /tweets/<id>` → check `text`, `lang` field |
| TikTok via Postiz | Postiz API `GET /posts/<id>` (state=PUBLISHED ≠ enough) + camofox snapshot of `tiktok.com/@<account>` feed → grep first 40 chars of caption |
| YouTube | YouTube Data API `videos.list` → title/locale match |
| Slideshow → TikTok | Same as TikTok + frame-count check (≥ 6 images) + audio presence (`ffprobe` on locally-cached upload) |

### 4.4 Files touched

| Path | Change |
|---|---|
| `~/.openclaw/skills/_shared/lib/pre-post-gate.sh` | NEW — `ppg_check` function + standalone CLI |
| `~/.openclaw/skills/_shared/lib/post-verify-gate.sh` | NEW — `pvg_verify` function + platform-specific verifier dispatchers |
| `~/.openclaw/skills/_shared/lib/verify-x.sh`, `verify-tiktok.sh`, `verify-youtube.sh` | NEW — platform-specific live-feed checkers |
| `~/.openclaw/skills/anicca-x-useful/post-x-direct.sh` | Add `ppg_check` + `pvg_verify` calls; keep existing `vg_check` |
| `~/.openclaw/skills/4.7-slideshow-factory/06-postiz-publish.sh` | Add both gates |
| `~/.openclaw/skills/4.7-slideshow-factory-ja/06-postiz-publish.sh` | Add both gates |
| `~/.openclaw/skills/anicca-cafe-slideshow*/` (TikTok) | Add both gates |
| All other posting skills found by `grep -lr "post-x-direct\|postiz-publish\|post-tt-camofox" ~/.openclaw/skills/` | Add both gates |
| `~/.openclaw/skills/_shared/lib/lib-test/` | NEW — bats-style tests for the gates (fixtures for pass/fail cases) |

### 4.5 Success criteria

- [ ] Inject a Japanese caption into the English TikTok skill → `ppg_check` exits non-zero, no post happens, Slack #content-metrics has URGENT alert
- [ ] Force a publish to succeed but verifier sees nothing on feed (mock) → `pvg_verify` exits non-zero, no success report sent, URGENT alert sent
- [ ] Network 5xx from Postiz → ≤ 2 auto-retries, then escalate
- [ ] Every posting skill in `~/.openclaw/skills/` sources `_shared/lib/pre-post-gate.sh` (verified by `grep -L "pre-post-gate" ~/.openclaw/skills/*/post-*.sh` returns empty)
- [ ] Existing successful posts continue to succeed (no regression — run 1 cron of each migrated skill manually post-deploy)

### 4.6 Risks

| Risk | Mitigation |
|---|---|
| `pvg_verify` blocks success report waiting for live feed; if verifier itself is broken, all posts look like they failed | Verifier has its own self-test cron (daily); if 3 consecutive false negatives detected, gate bypassed with WARN (not silent) |
| Postiz API doesn't expose enough metadata for verification | Already in our memory (HARD RULE #16) — fall through to camofox snapshot, which is slower but ground truth |
| Adding gates breaks skills mid-flight (during a release) | Roll out skill-by-skill, not all at once. Start with `4.7-slideshow-factory-ja` and `-en` since that's where the TikTok incident occurred |

### 4.7 Open questions for implementation plan

- camofox feed snapshot adds ~30 s per post; is that acceptable for daily-volume cron, or only for high-stakes ones (TikTok)?
- For X posts, is the X API rate limit headroom enough to add a verify call after every post? (Likely yes — verify is GET, posts are rare per skill)

---

## 5. Subsystem ③ — Frontier Model Routing

### 5.1 Current state (VERIFIED 2026-06-06 via `jq ~/.openclaw/openclaw.json`)

```
~/.openclaw/openclaw.json   (live values)
  agents.defaults.model.primary   = "moonshot/kimi-k2.5"   ← NOT gpt-5.4-mini
  agents.defaults.model.fallbacks = [
    "xai/grok-3-mini-fast",                                ← Dais never mentioned
    "deepseek/deepseek-v4-pro",
    "claude-cli/claude-sonnet-4-6"                         ← expensive, last
  ]
  heartbeat.isolatedSession=true, directPolicy=allow, NO model override
  → heartbeat inherits primary = kimi-k2.5

~/.openclaw/cron/jobs.json   (197 jobs total)
  166 jobs        model = null  →  inherit primary = kimi-k2.5
   15 jobs        model = "deepseek/deepseek-v4-pro"   (OK, cheap)
   11 jobs        model = "openai/gpt-5.4-mini"        (OK, cheap)
    5 jobs        model = "claude-sonnet-4-6" or "claude-cli/claude-sonnet-4-6"  ★ VIOLATION
                  per memory `feedback_crons_use_mini_models_only`
                  these 5 need audit + migrate to primary
                  (job IDs: 4cfdfe32, 73d4a8c2, 94c788fe + 1 cli variant = 4-5 entries)

Phone session
  starts `claude` with no --model flag
  → inherits Claude Code CLI bundle default (Sonnet 4.5/4.6), NOT openclaw config
  → quality OK but expensive on Anthropic, AND not the frontier reasoning Dais wants

Telegram / Slack direct-chat surfaces with Anicca
  anicca-telegram-bot/ exists but SKILL.md state = "Scaffold only. Ready to install
  when Dais provides bot token." → NOT LIVE.
  slack-feedback-reader runs in heartbeat (kimi-k2.5).
  → there is no live frontier-model chat surface today (subsystem ① phone Claude
    Code is the closest thing — see Plan #10 future spec for true direct chat)

doctor --fix
  per memory `feedback_openclaw_doctor_fix_rolls_back_cron_model_clears`:
  rewrites job-level overrides back to defaults.primary on every run.
  Patch Y (143-job bulk clear) was wiped by ONE doctor --fix run on 2026-06-05.
  → routing config MUST be defaults-side, not jobs-side, OR doctor must learn the new key
```

### 5.1.1 Dais's stated target state (2026-06-06 voice memo verbatim)

> "all the cron models should be as default GPT 500 for mini and then falling back to like
>  Kimi or DeepSeq or Cloud Sonnet. Cloud Sonnet should be the last one because I don't
>  want them to use that a lot."

Interpreted (HARD RULE 0.20 — decide, don't ask):

| Layer | Target value |
|---|---|
| `defaults.model.primary` | `openai/gpt-5.4-mini`  (swap from kimi-k2.5) |
| `defaults.model.fallbacks` | `["moonshot/kimi-k2.5", "deepseek/deepseek-v4-pro", "claude-cli/claude-sonnet-4-6"]` |
| Drop from fallbacks | `xai/grok-3-mini-fast` (Dais never mentioned, and primary swap reduces fallback pressure) |
| 5 sonnet-override cron | Audit → migrate to primary (default behavior), OR justify in `MODEL_OVERRIDE_REGISTRY.md` if frontier genuinely needed |
| Phone Claude Code (interactive chat) | `--model claude-opus-4-7` explicit on every `phone` invocation (see subsystem ①) — this is Dais's "direct chat with Anicca" surface for the v3.2 window, until Telegram bot ships (Plan #10 future) |
| Telegram bot (when launched, Plan #10) | Anthropic API direct, Opus 4.7 |

### 5.2 Goal

| Surface | Model | Why |
|---|---|---|
| Phone session, Claude Code TUI, MacBook ssh | `claude-cli/claude-opus-4-7` | Dais talks to Anicca → needs frontier reasoning |
| Cron, heartbeat, background skills | `deepseek/deepseek-v4-pro` | Cost-controlled, sufficient quality for templated work (HARD RULE) |
| Specific exceptions (writing code, judging code, deep research) | Per-skill override allowed | Some cron jobs need frontier reasoning; should be explicit, justified, listed |

Plus: **survive `doctor --fix`** — the routing config must not be the thing doctor rewrites.

### 5.3 Design — REVISED: **Set sensible defaults + frontier opt-in only where Dais actually chats**

Dais clarified 2026-06-06: he was not asking for a complex context-aware router. The real ask is (a) cron defaults set right (cheap, sonnet-last), and (b) the surfaces where he actually talks to Anicca (phone Claude Code now, Telegram bot future) use frontier explicitly.

```
~/.openclaw/openclaw.json   (target)
  agents.defaults.model = {
    "primary":   "openai/gpt-5.4-mini",                    ← Dais target
    "fallbacks": [
      "moonshot/kimi-k2.5",
      "deepseek/deepseek-v4-pro",
      "claude-cli/claude-sonnet-4-6"                       ← LAST, rarely hit
    ]
    // optional, doctor-safe forward-compat:
    // "interactive": "claude-cli/claude-opus-4-7"
    // (only used if a future code path opts in; doctor --fix doesn't know
    //  about this key so it survives)
  }

Cron / heartbeat / background skill (197 jobs)
  → inherit defaults.model.primary = gpt-5.4-mini
  → fallback chain: kimi → deepseek → sonnet
  → NO interactive key needed (cron = default surface)

Phone Claude Code (subsystem ① — Dais's current direct-chat surface)
  ~/bin/phone wraps `claude --model claude-opus-4-7 --max-budget-usd 10`
  → frontier reasoning at chat surface, explicit flag, doctor-safe (doctor
    doesn't touch shell scripts)

Telegram bot direct chat (Plan #10 future spec)
  → Python listener calls Anthropic API with model=claude-opus-4-7 directly
  → bypasses openclaw entirely for chat path (config-safe, billing-clear)

Why this is simpler than the original §5.3 proposal:
- No OPENCLAW_CONTEXT env var router (over-engineered for current need)
- No openclaw binary modification (we'd have to rebuild + risk regression)
- Each surface declares its own model at invocation time (CLI flag or SDK param)
- doctor --fix can wipe job-level overrides all day — phone wrapper + Telegram
  listener are untouched
```

**5 sonnet-override cron audit checklist** (part of #6 execute):

| Job ID prefix | Plan |
|---|---|
| 4cfdfe32 | Read cron message + skill, decide: does it really need frontier? If yes → register in MODEL_OVERRIDE_REGISTRY.md with rationale + switch to `deepseek/deepseek-v4-pro` (still strong, cheap). If no → remove override, let it inherit gpt-5.4-mini. |
| 73d4a8c2 | Same audit |
| 94c788fe | Same audit |
| 4cfdfe32-cli-variant | Same audit |
| (any 5th if discovered) | Same audit |

**Why split keys on `agents.defaults.model`, not new top-level config**:
- doctor --fix only knows to reset `agents.defaults.model.primary` (legacy behavior). New keys (`interactive`) are invisible to it → survive.
- Eventually doctor should learn about `interactive` too — file an issue against openclaw upstream as part of plan ③.

**Why env var, not parent-process detection**:
- Parent-process detection (`ps -o ppid` walking up to find cron vs sshd) is fragile and platform-specific
- `OPENCLAW_CONTEXT` is explicit, greppable, testable, future-proof

**Per-job override (the 4 existing crons)**:
- Stays. `jobs.json[].model` continues to win over defaults
- Document in `~/.openclaw/docs/MODEL_OVERRIDE_REGISTRY.md` (NEW): why each override exists, who owns it, when to revisit. Each entry must justify why frontier is needed for that specific cron.

**Claude Code CLI flag passthrough** (subsystem ① compatibility):
- Phone session: `claude --model claude-opus-4-7 --continue` — explicit, doctor-safe (doctor doesn't touch shell scripts)

### 5.4 Files touched

| Path | Change |
|---|---|
| `~/.openclaw/openclaw.json` | Add `agents.defaults.model.interactive`; verify `primary` is `deepseek/deepseek-v4-pro` post-Phase-1 |
| `~/.openclaw/skills/_dispatcher/cron-codex.sh` (or equivalent entry wrapper) | Export `OPENCLAW_CONTEXT=cron` |
| `~/.openclaw/skills/_dispatcher/SKILL.md` | Document context contract |
| openclaw router code path (inside openclaw binary or `~/.openclaw/services/`) | Read `OPENCLAW_CONTEXT` env, pick the right defaults key |
| `~/.openclaw/docs/MODEL_OVERRIDE_REGISTRY.md` | NEW — list of allowed per-job overrides with rationale |
| `~/bin/phone` (subsystem ①) | Phone shell autostart sets `OPENCLAW_CONTEXT=interactive` + uses `claude --model claude-opus-4-7` |
| `~/.openclaw/skills/_shared/lib/model-policy.sh` | NEW — defines the public contract, sourced by anything that runs `claude` or `openclaw` |
| Upstream openclaw repo issue | NEW — request `doctor` to preserve `agents.defaults.model.interactive` |

### 5.5 Success criteria

- [ ] Phone tap → Claude Code starts with `claude-opus-4-7` (verified by `claude /model` slash command inside session)
- [ ] Manual cron fire of any unmodified posting cron → uses `deepseek/deepseek-v4-pro` (verified by openclaw log)
- [ ] `openclaw doctor --fix` run → `defaults.model.interactive` survives, override registry survives
- [ ] No ChatGPT Plus quota burn during 1-day cron sweep (verified by counting non-mini OpenAI calls in `~/.openclaw/logs/` — should be 0 unless an override is registered)

### 5.6 Risks

| Risk | Mitigation |
|---|---|
| `doctor --fix` learns to wipe `interactive` too in a future openclaw update | Subsystem ② post-verify-style canary: daily cron diffs current `openclaw.json` against last-known-good `openclaw.json.last-good`. Alert Slack URGENT on drift. |
| Phone session in worktree/macbook ssh forgets to export `OPENCLAW_CONTEXT=interactive` | Default is `cron` (cheap) — safe failure mode. Explicit export added via `~/.zshrc` global, not per-shell. |
| Opus 4.7 rate-limited / billing exhausted | Fallback chain unchanged → automatic graceful degradation to Sonnet 4.6 then DeepSeek |
| Cost shock: chat now bills frontier | Budget guard: `claude --max-budget-usd` on phone autostart, e.g., `--max-budget-usd 10` per session (configurable) |

### 5.7 Open questions for implementation plan

- Does the openclaw binary (1.5 months old per `feedback_crons_use_mini_models_only`) need `npm install -g openclaw@latest` first to pick up router behavior?
- Where exactly is the openclaw model router? (Plan ③ research step before coding)

---

## 6. Implementation order & dependencies

```
┌───────────────────────────────────────┐
│  spec approved (this doc)              │
└────────────────┬──────────────────────┘
                 │
       ┌─────────┴─────────┐
       ▼                   ▼
┌─────────────┐    ┌─────────────────────┐
│ Plan ③      │    │ Plan ②              │
│ Model route │    │ Verify gate         │
│ (1-2 days)  │    │ (3-5 days)          │
└──────┬──────┘    └──────┬──────────────┘
       │                   │
       │  ③ unblocks ①    │
       │  (phone uses     │
       │   interactive)   │
       │                   │
       ▼                   │
┌─────────────┐            │
│ Plan ①      │            │
│ Phone       │            │
│ persistent  │            │
│ (2-3 days)  │            │
└──────┬──────┘            │
       │                   │
       └─────────┬─────────┘
                 ▼
       all 3 in production
       verify end-to-end:
       - Tap phone → opus + persistent
       - Run TikTok cron → gate blocks bad post
       - Cost report → no Anthropic burn on cron
```

**Why ③ before ①**: Phone wrapper hardcodes `--model claude-opus-4-7`, which depends on the conceptual contract from ③ (chat = frontier). ③ also has the smallest blast radius (one config file + audit) so it's a good warm-up.
**Why ② parallel to ③**: Disjoint files. ③ touches `openclaw.json` + 5 cron overrides; ② touches `_shared/lib/` + per-skill source-line additions.

**REVISED execution order based on Dais's 2026-06-06 ask to validate phone first**: spec correction (#5) → plan all three in writing → execute ① first so Dais can validate multi-session on phone immediately → then ③ → then ②. This trades a small dependency cost (phone wrapper temporarily uses a hardcoded model string) for a fast user-visible win.

---

## 7. Cross-cutting concerns

| Concern | Decision |
|---|---|
| Worktree usage | ② and ③ touch `~/.openclaw` runtime store — main-direct edit OK per HARD RULE #0 exception, but full SDD flow still required. ① touches user-level dotfiles + `/usr/local/bin` — also no worktree, same rule. |
| Backup before destructive change | `openclaw.json.bak-pre-v32-routing` before ③; full backup of all touched skill files before ② |
| Rollback plan | Each plan has a single `git revert` + `cp <backup> <target>` rollback step in its `executing-plans` checklist |
| Testing strategy | ① manual on iPhone + MacBook. ② bats-style unit tests on the gate libraries + canary cron with intentional bad input. ③ openclaw log inspection + `claude /model` slash command verification. |
| Code review | Each plan gets `superpowers:requesting-code-review` post-implementation, then `codex-review` per HARD RULE 0.12 |

---

## 8. Out of scope (explicit non-goals) + named follow-up specs

**Out of scope for this spec**:

- Adding new posting platforms (X / TikTok / YouTube only for ② migration)
- Anicca v3.2 multi-profile colony (separate effort, memory `feedback_anicca_multi_profile_per_instance_colony`)
- Heartbeat autonomy redesign beyond the model swap
- openclaw binary modifications (we adapt around it, not change it)

**Named follow-up specs (queued, NOT in this spec)**:

- `2026-MM-DD-anicca-direct-chat-surface-design.md` — Telegram bot launch + Anthropic API direct call + Claude Code subscription deprecation evaluation. Goal: Dais talks to Anicca on iPhone Telegram, not through Claude Code TUI. Triggered when ① is live and Dais wants to evaluate dropping Claude Code sub. Task #10 in TODO list.
- Future: iOS terminal app evaluation if Moshi blocks mosh/multi-tab UX. (Likely path: switch to Blink Shell.)

---

## 9. Open questions for the user before plans start

1. **Phone iOS client**: Is Moshi non-negotiable, or open to switching to Blink/Termius for native mosh support?
2. **Budget cap**: What's the per-session `--max-budget-usd` for phone chat? ($5? $10? unlimited?)
3. **Verify gate rollout**: Migrate all posting skills at once, or canary on `4.7-slideshow-factory-en` first (incident skill) then fan out?
4. **Override registry**: For the 4 existing cron-level model overrides, audit and shrink to 0, or keep with documented justification?

---

## 10. Self-review checklist (done before user review)

- [x] No placeholders / TODOs in the body
- [x] All three subsystems have: current state / goal / design / files touched / success criteria / risks
- [x] Implementation order is explicit (revised 2026-06-06 to put ① first per Dais)
- [x] Out-of-scope is explicit
- [x] Open questions are gathered at the bottom, not littered inline
- [x] Aligned with HARD RULE #0 (SDD-first), 0.12 (verification), 0.14 (job not finished), 0.17 (single source of truth), 0.20 (minimize human loop), `feedback_crons_use_mini_models_only`, `feedback_openclaw_doctor_fix_rolls_back_cron_model_clears`
- [x] Aligned with brainstorming skill: decomposed into independent subsystems, each ready for its own `writing-plans` cycle
- [x] 2026-06-06 Q&A revisions applied: (a) §5.1 primary corrected to kimi-k2.5 from gpt-5.4-mini, (b) §5.1.1 Dais target state added, (c) §5.3 simplified (no env-router), (d) §3 phone design switched to per-tap independent multi-session, (e) §8 named Telegram direct-chat as follow-up spec, (f) §6 execution order revised to ① first
