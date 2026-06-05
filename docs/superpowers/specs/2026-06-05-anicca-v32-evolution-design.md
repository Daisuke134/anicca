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

### 3.2 Goal

| Property | Target |
|---|---|
| Tap latency | ≤ 2 s from Moshi tap to "ready to type" |
| Context restored | Last Claude Code conversation in `~/anicca-project` resumes automatically — no manual `claude -c` |
| Disconnect tolerance | SSH idle, Wi-Fi→LTE switch, screen sleep — connection survives, conversation continues |
| Scroll behavior | Moshi scroll continues to work |
| Multiple devices | iPhone + MacBook can attach to same session simultaneously without race |

### 3.3 Design — Recommended approach: **Mosh + named tmux session + `claude --continue` autostart**

```
Moshi tap
   │
   ▼
mosh keiodaisuke@100.99.82.95  ← UDP, survives roaming, no idle timeout
   │
   ▼
tmux new-session -A -s phone -c ~/anicca-project
   │  ("new OR attach" — same session "phone" reused)
   │
   ▼
inside the new tmux session, .zshrc detects MOSHI_PHONE=1 → runs:
   exec claude --name phone --continue --model claude-opus-4-7
   │
   ▼
Claude Code resumes last conversation, ready to type
```

**Why mosh, not raw SSH**:
- Raw SSH disconnects on Wi-Fi→LTE switch (Mac Mini side TCP keepalive needed; iPhone-side the carrier IP changes — connection dies)
- Mosh uses UDP + state-sync protocol → handles roaming, intermittent connectivity, screen sleep transparently (verified per mosh.org)
- `mosh-server` runs as the user, no privileged daemon; tmux on top, normal SSH login retained for auth

**Why named `phone` session, not `phone-<ts>`**:
- `tmux new-session -A -s phone` is idempotent: creates if absent, attaches if present
- Multiple clients (iPhone + MacBook) can attach simultaneously — tmux already handles this
- Cleanup is one session, not 50 timestamped ones

**Scroll problem solved by**:
- Modern Moshi versions (≥ 1.4) honor tmux's alternate-screen sequences correctly. The 2024-era scroll bug is gone.
- If scroll still breaks, fallback: keep `phone-<ts>` for the tmux layer but launch `claude --resume <fixed-session-name>` inside — Claude Code itself becomes the persistence layer instead of tmux.

### 3.4 Files touched

| Path | Change |
|---|---|
| `/Users/anicca/bin/phone` | Replace body: `mosh ... -- tmux new-session -A -s phone ...` |
| `~/.zshrc` | Remove the tmux interceptor function (lines marked "Anicca tmux phone interceptor"); add MOSHI_PHONE detection that auto-starts `claude --continue` |
| `/etc/ssh/sshd_config` on Mac Mini | `ClientAliveInterval 60` + `ClientAliveCountMax 5` (defense in depth even with mosh) |
| Moshi mobile app config | Change SSH command from `tmux attach -t phone` to `mosh-bootstrap` (a one-line wrapper that runs mosh) — only if Moshi can't run mosh natively |
| New: `/Users/anicca/bin/phone-cleanup` | Daily cron, kills detached tmux sessions older than 7d (only orphaned ones, not `phone`) |

### 3.5 Success criteria

- [ ] Moshi tap → ≤ 2 s → previous Claude conversation visible, cursor ready
- [ ] Lock iPhone for 10 min → unlock → conversation still alive, no reconnect prompt
- [ ] Switch Wi-Fi → LTE mid-typing → no disconnect, typing resumes
- [ ] `tmux ls` on Mac Mini shows exactly one `phone` session (not 50 timestamped ones)
- [ ] MacBook `ssh anicca-mac-mini-1 -t 'tmux attach -t phone'` shares the same Claude session

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

### 5.1 Current state

```
~/.openclaw/openclaw.json
  agents.defaults.model.primary = "openai/gpt-5.4-mini"    ← chat inherits this too
  agents.defaults.model.fallback = [
    "deepseek/deepseek-v4-pro",
    "moonshot/kimi-k2.5",
    "claude-cli/claude-sonnet-4-6"
  ]

~/.openclaw/cron/jobs.json
  150 jobs total, 4 jobs have explicit "model" override (none are frontier)
  146 jobs inherit defaults.model.primary

Phone session
  starts `claude` with no --model flag
  → inherits the bundle default (Sonnet 4.5 from Claude Code CLI), NOT openclaw config
  → user reports feels like cron quality

doctor --fix
  per memory `feedback_openclaw_doctor_fix_rolls_back_cron_model_clears`:
  this command rewrites job-level model overrides back to defaults.primary
  Patch Y (143-job bulk clear) was wiped by ONE doctor --fix run
```

### 5.2 Goal

| Surface | Model | Why |
|---|---|---|
| Phone session, Claude Code TUI, MacBook ssh | `claude-cli/claude-opus-4-7` | Dais talks to Anicca → needs frontier reasoning |
| Cron, heartbeat, background skills | `deepseek/deepseek-v4-pro` | Cost-controlled, sufficient quality for templated work (HARD RULE) |
| Specific exceptions (writing code, judging code, deep research) | Per-skill override allowed | Some cron jobs need frontier reasoning; should be explicit, justified, listed |

Plus: **survive `doctor --fix`** — the routing config must not be the thing doctor rewrites.

### 5.3 Design — Recommended approach: **Split defaults + env-var dispatch + doctor-aware structure**

```
~/.openclaw/openclaw.json
  agents.defaults.model = {
    "primary":     "deepseek/deepseek-v4-pro",   ← cron default (CHEAP)
    "interactive": "claude-cli/claude-opus-4-7", ← chat default (FRONTIER)
    "fallback":    [...unchanged...]
  }

cron-codex.sh wrapper (entry point for all crons)
  exports OPENCLAW_CONTEXT=cron before calling codex/openclaw

phone session zshrc autostart (subsystem ①)
  exports OPENCLAW_CONTEXT=interactive before calling claude

openclaw router (existing dispatcher)
  reads OPENCLAW_CONTEXT
    if "cron" → use defaults.model.primary
    if "interactive" → use defaults.model.interactive
    if unset → use defaults.model.primary (safe fallback to cheap)
```

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

**Why ③ before ①**: Phone session needs to know what model to start; design that contract first, then build the phone wrapper on top.
**Why ② parallel to ③**: They touch disjoint files. Plan ③ touches `openclaw.json` + dispatcher; plan ② touches skills + new lib files.

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

## 8. Out of scope (explicit non-goals)

- Redesigning Moshi mobile app or replacing iOS terminal client without user consent
- Switching cron model provider away from DeepSeek (HARD RULE — leave it)
- Adding new posting platforms
- Anicca v3.2 multi-profile colony (separate spec, separate effort)
- Heartbeat autonomy redesign beyond the model swap

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
- [x] Implementation order is explicit
- [x] Out-of-scope is explicit
- [x] Open questions are gathered at the bottom, not littered inline
- [x] Aligned with HARD RULE #0 (SDD-first), 0.12 (verification), 0.14 (job not finished), 0.17 (single source of truth), `feedback_crons_use_mini_models_only`, `feedback_openclaw_doctor_fix_rolls_back_cron_model_clears`
- [x] Aligned with brainstorming skill: decomposed into independent subsystems, each ready for its own `writing-plans` cycle
