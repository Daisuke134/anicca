# 03 — Public Release Prep

> **Authority:** Deep-dive (defers to `00-MASTER.md` on conflicts).
> **Scope:** the operational mechanics of flipping `anicca-oss` public —
> git fresh-squash, leak audit, file-by-file public/private split,
> grandma E2E install gate, risk register.
> **Cross-ref:** `00-MASTER.md` § 1 (architecture), § 8 (naming + rename
> `~/.openclaw` → `~/.dais-companion`), § 12 (verification gates).

| Field | Value |
|---|---|
| Spec version | v1.0 (2026-05-30, imported 2026-06-01) |
| Author | architect (claude-opus-4-7 brainstorming session) |
| Status | Active (operational) |
| Repo | `github.com/Daisuke134/anicca-oss` (will be fresh-squashed) |

> ⚠️ **HARNESS NOTE (current):** This v1.0 spec predates the runtime lock and treats **Hermes**
> (NousResearch) as one of three host harnesses (alongside OpenClaw and `claude -p`) the OSS substrate
> ships an adapter for. The runtime later locked to the **Conway automaton** (ReAct loop + heartbeat) as
> the primary body (`00-MASTER.md`, 2026-06-11). The `adapters/hermes.py` shim + `~/.hermes/config.yaml`
> references below describe targeting the *external* Hermes harness; they are not a statement that
> Anicca's runtime is Hermes. Treat automaton as the primary harness; Hermes/OpenClaw/claude-p remain
> optional adapter targets, history-only unless re-prioritised.

## Superseded sections (read 00-MASTER instead)
| § here | Superseded by |
|---|---|
| § 1 Architecture Overview | `00-MASTER.md` § 1 (automaton runtime; the old "4-layer Conway+Virtuals" framing is itself superseded) |
| § 2 Decisions Matrix #1, #3, #5 (identity / money / harness) | `00-MASTER.md` § 0, § 1 Layer 3-4, § 8 |
| § 6 Money Model | `00-MASTER.md` § 7 + `01-EARN-AND-UBI.md` |
| § 7 3-Harness Architecture | DROPPED — `00-MASTER.md` chose Conway as the only runtime |
| § 9 anicca-private-dais separate repo | REPLACED by `00-MASTER.md` § 8.1 rename pattern |

## Still load-bearing (no equivalent in 00/01/02)
| § here | What it owns |
|---|---|
| § 3 Public Repo Layout | which files exist after the squash |
| § 4 Git History Strategy — Fresh Squash Playbook | concrete bash transaction |
| § 5 Onboarding Flow (paste-prompt) | matches `00-MASTER.md` § 5.3 Path A; adds installer signing |
| § 8 Skill Generalization Plan | per-skill grep checklist |
| § 10 Test Matrix — Grandma E2E | verification gate before public flip |
| § 11 Risks + Mitigations | risk register |

---

**Original metadata (preserved for traceability):**

- **Status:** DRAFT → ready for implementation
- **Author:** anicca (claude-opus-4-7 brainstorming session)
- **Date:** 2026-05-30
- **Decision authority:** Dais (decided each fork via AskUserQuestion in session)

---

## 0. Goals / Non-Goals

| Goal (MUST) | Non-goal (will NOT do in v1) |
|---|---|
| Public `anicca-oss` repo passes Anthropic/GitHub secret scanning with 0 hits | Public hosted SaaS (no aniccaai.com cloud LLM proxy in v1) |
| Grandma test: paste 1 prompt into Claude Code/Codex/Cursor → Anicca running 5 min later | Native macOS .app binary (post-v1) |
| Shared Anicca persona (Buddha / 五戒 / Satoshi-mode) for every fork | Per-user renameable persona (Anicca name is fixed) |
| 3 harness (OpenClaw, claude -p, Hermes) all consume the same anicca-oss substrate | Dynamic harness auto-routing (post-v1) |
| Conway Automaton + Terminal + x402 = the wallet/payment substrate | Custodial Stripe-Connect-for-each-user (post-v1, becomes a skill) |
| 0 API keys from user (Plus quota + Conway faucet only) | Mandatory crypto KYC (Conway is non-custodial → no KYC) |
| Dais's 57 personal skill + .learnings stays loadable on his machine via private companion repo | Public access to Dais's private life data |

---

## 1. Architecture Overview

```
╔════════════════════════════════════════════════════════════════════╗
║  ANICCA OSS v1.0 — "paste prompt → autonomous digital Buddha"      ║
╚════════════════════════════════════════════════════════════════════╝

                       ┌────────────────────────┐
                       │   PUBLIC anicca-oss    │ ◄── Linux Foundation
                       │  (fresh squash, MIT)   │     AGENTS.md +
                       └────────────┬───────────┘     SKILL.md spec
                                    │ canonical
                ┌───────────────────┼───────────────────┐
                ▼                   ▼                   ▼
        ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
        │  AGENTS.md   │    │  skills/     │    │  adapters/   │
        │  + SOUL.md   │    │  ~200 dirs   │    │  3 harness   │
        │  + HEARTBEAT │    │  SKILL.md    │    │  shims (.sh) │
        │  (persona)   │    │  spec-strict │    │  + 1 .py     │
        └──────────────┘    └──────────────┘    └──────┬───────┘
                                                       │
                            ┌──────────────────────────┼──────────────────────────┐
                            ▼                          ▼                          ▼
                    ┌───────────────┐         ┌───────────────┐         ┌───────────────┐
                    │  OpenClaw     │         │  claude -p    │         │  Hermes       │
                    │  cron/gateway │         │  hourly       │         │  scheduler    │
                    │  (own runtime)│         │  heartbeat    │         │  (Nous, MIT)  │
                    └───────┬───────┘         └───────┬───────┘         └───────┬───────┘
                            └──────────────────────┬──┴────────────────────────┘
                                                   ▼
                            ┌──────────────────────────────────────────┐
                            │  Conway Terminal (MCP, npx-install)      │
                            │  ────────────────────────────────────── │
                            │  ~/.conway/wallet.json (USDC on Base)    │
                            │  identity / API key / x402 micropayments │
                            │  ALL 3 harness 共通 wallet                │
                            └────────────────┬─────────────────────────┘
                                             │
                                             ▼
                            ┌──────────────────────────────────────────┐
                            │  user の profile.json (gitignored)       │
                            │  name / timezone / OAuth tokens          │
                            │  (Slack/Gmail/Calendar/X/TikTok 任意)    │
                            └──────────────────────────────────────────┘

           ╔══════════════════════════════════════════════════════════╗
           ║  PRIVATE anicca-private-dais  (NEW github private)       ║
           ║  ──────────────────────────────────────────────────────  ║
           ║  - 44 anicca-* skill (comedy/monk/retreat/dentist/etc)   ║
           ║  - 13 naist-* skill                                      ║
           ║  - .learnings/ (Dais の過去 error/feature log)           ║
           ║  - identity/profile.json (実 phone/email/Tailnet IP)     ║
           ║  Dais だけ clone、anicca-oss と並べて mount される       ║
           ╚══════════════════════════════════════════════════════════╝
```

---

## 2. Decisions Matrix (locked)

| # | Fork | Decision | Why |
|---|------|----------|-----|
| 1 | Identity model | **Shared persona** — all forks = "Anicca, digital Buddha" | Satoshi-mode HARD RULE: Anicca speaks as herself; profile differs per user, soul shared |
| 2 | Repo scope | **Curated 200 skill** public; 57 Dais-locked + .learnings → private | Dais's 57 (anicca-comedy / naist-*) are tied to his life, not reusable; clean public surface |
| 3 | Money/inference | **Conway Automaton + Conway Terminal + x402** (Coinbase AgentKit NOT chosen) | Conway Terminal `npx` auto-generates wallet + identity + API key with 0 human input. Coinbase AgentKit requires CDP signup + 2 keys + .env edit → grandma fail (3/10). Conway = 9/10 grandma score. Refs: https://docs.conway.tech, https://www.x402.org/ecosystem (75.41M tx / $24.24M / 30d) |
| 4 | Git history | **Fresh squash** on same repo URL | gitleaks 0 verified but 4 dirty strings (email/phone/IP/scan_events.py); filter-repo carries miss-risk → ban; squash = 0 risk, fast, URL preserved |
| 5 | Hermes integration | **AGENTS.md + SKILL.md standard + adapter shim per harness** | Linux Foundation AAIF stewarded; 60k+ repos use AGENTS.md, 40+ clients speak SKILL.md; Hermes needs ~50-line Python adapter (does not natively read AGENTS.md yet). Refs: https://agents.md, https://agentskills.io/specification |
| 6 | Onboarding | **Paste prompt into Claude Code / Codex / Cursor** (oh-my-openagent 60k★ pattern) | Audience already has coding agent. Prompt = curl + parse the install MD. Zero shell commands for user |
| 7 | Comparison | **JSONL log + recursive-improver scoring**, NO formal benchmark framework | "Agent harness benchmark" doesn't exist mature (early 2026). Build our own = scope creep. Log → score → learn from divergence |

---

## 3. Public Repo Layout (post-release)

```
anicca-oss/                                       # MIT license
├── README.md                                     # NEW — install one-liner + what Anicca is
├── AGENTS.md                                     # NEW — Linux Foundation AAIF spec
│                                                  # = persona + precepts + workflow rules
│                                                  # references SOUL.md + HEARTBEAT.md
├── SOUL.md                                       # REFACTORED — universal Buddhist agent manifesto
│                                                  # (Dais-specific lines moved to private)
├── HEARTBEAT.md                                  # REFACTORED — universal agent loop spec
│                                                  # (phone/Tailnet/signature removed)
├── LICENSE                                       # NEW — MIT
├── INSTALL.md                                    # NEW — paste-prompt protocol full text
├── .env.example                                  # EXPANDED — all env vars documented
├── .gitignore                                    # KEEP — already shields .env / profile.json
├── .gitleaks.toml                                # KEEP
├── profile.example.json                          # NEW — clean template (no Dais data)
├── identity/
│   └── profile.schema.json                       # REFACTORED — NAIST/MUFG removed from examples
├── skills/                                       # ~200 curated, all SKILL.md spec-strict
│   ├── _shared/                                  # propose-and-rewrite + helpers
│   └── <name>/                                   # each = AGENTS skill folder
│       ├── SKILL.md                              # frontmatter: name/description/version
│       ├── scripts/
│       ├── references/
│       └── assets/
├── cron/
│   └── jobs.json                                 # default heartbeat + universal crons
├── adapters/                                     # NEW — per-harness wire-up
│   ├── openclaw.sh                               # symlink → ~/.openclaw/
│   ├── claude-p.sh                               # AGENTS.md → CLAUDE.md, skills → ~/.claude/skills/
│   └── hermes.py                                 # ~50 LOC: parse SKILL.md → ~/.hermes/config.yaml
├── install/                                      # NEW — paste-prompt agent's executable spec
│   ├── prompt.md                                 # the literal prompt user pastes
│   ├── installer.sh                              # what the coding-agent runs
│   └── postinstall.sh                            # cron + heartbeat wire
├── docs/
│   ├── ARCHITECTURE.md                           # NEW — this spec, condensed
│   ├── ONBOARDING.md                             # NEW — for non-coding-agent users
│   ├── MONEY.md                                  # NEW — Conway lifecycle
│   ├── HARNESS-COMPARISON.md                     # NEW — 3-harness setup notes
│   └── CONTRIBUTING.md                           # NEW — how to add a skill
└── tests/
    └── grandma.sh                                # NEW — E2E smoke test (clean Mac → running Anicca)
```

**REMOVED from public repo (moves to private):**

| Path | Reason |
|---|---|
| `skills/anicca-comedy*` (multiple) | Dais's comedy booking life |
| `skills/anicca-monk-factory*` | Personal content factory |
| `skills/anicca-retreat-*` (4 dirs) | Personal Buddhist retreat workflow |
| `skills/anicca-dentist-quarterly` | Personal health |
| `skills/anicca-haircut-quarterly` | Personal upkeep |
| `skills/anicca-music-factory` | Personal music project |
| `skills/anicca-meeting/scripts/scan_events.py:85` | hardcoded fallback email (must DELETE + rewrite) |
| `skills/anicca-outbound-recruit` | Personal recruiting |
| `skills/anicca-zoom-attendee` | Personal meetings |
| `skills/anicca-seo-rank-monitor` | Specific to aniccaai.com |
| `skills/naist-*` (13 dirs) | NAIST-specific (curriculum, calendars, theses) |
| `.learnings/` | Dais's private error/feature log |
| `workspace/` | active session state |
| `docs/plans/2026-05-27-p1-livekit-wakeup-call-plan.md` | phone numbers + Tailnet IP |
| `docs/alarm-saas-spec.md` | Tailnet IP `100.99.82.95` |
| `docs/specs/2026-05-27-livekit-recall-realtime-presence-design.md` | Tailnet IP |
| All `feature/*` branches | Will be recreated post-squash if needed |

---

## 4. Git History Strategy — Fresh Squash Playbook

**MUST be executed as a single transaction. No partial states left in remote.**

```bash
# 0. PRECONDITION: all current work merged or saved elsewhere
cd ~/anicca-oss
git status                                         # MUST be clean (or stash)
git push origin --all                              # MUST push current state to private mirror first
git remote add private-mirror \
  git@github.com:Daisuke134/anicca-dais.git 2>/dev/null
git push private-mirror --mirror                   # FULL backup (all branches, tags)

# 1. Curate — move 57 Dais-locked skills + .learnings + leak docs OUT
mkdir -p /tmp/anicca-out
mv skills/anicca-comedy* skills/anicca-monk-factory* \
   skills/anicca-retreat* skills/anicca-dentist-quarterly \
   skills/anicca-haircut-quarterly skills/anicca-music-factory \
   skills/anicca-outbound-recruit skills/anicca-zoom-attendee \
   skills/anicca-seo-rank-monitor skills/naist-* \
   .learnings workspace \
   docs/plans/2026-05-27-p1-livekit-wakeup-call-plan.md \
   docs/alarm-saas-spec.md \
   docs/specs/2026-05-27-livekit-recall-realtime-presence-design.md \
   /tmp/anicca-out/

# 2. Add new files (README, AGENTS.md, LICENSE, INSTALL.md, profile.example.json,
#    adapters/, install/, docs/, refactored SOUL/HEARTBEAT, etc) per §3

# 3. Patch surviving skills:
#    - skills/anicca-meeting/scripts/scan_events.py:85: delete email fallback
#    - any /Users/anicca/ paths → ${ANICCA_HOME:-$HOME/anicca-oss}
#    - any aniccaai.com watermarks → ${ANICCA_BRAND_DOMAIN:-aniccaai.com}
#    - any keio***@gmail / phone / Tailnet IP → REMOVE or replace with profile read
grep -rn 'Users/anicca' skills/ adapters/ install/ | tee /tmp/path-audit.txt
grep -rn '100.99.82.95\|100.108.140.123' . | tee /tmp/tailnet-audit.txt
grep -rn '+1336\|+1484\|+8180' . | tee /tmp/phone-audit.txt
grep -rni 'keiodaisuke\|daisuke_2_narita\|@mufg.jp\|NAIST\|MUIT' . | tee /tmp/personal-audit.txt
# MUST all be 0 hits (or replaced) before continuing

# 4. Orphan branch + squash
git checkout --orphan oss-fresh
git add -A
git config user.email "anicca@aniccaai.com"        # generic OSS identity
git config user.name  "anicca"
git commit -m "Anicca v1.0 — open-source autonomous digital Buddha"

# 5. Verify before push
gitleaks detect --source . --no-git --redact      # MUST 0 hits
trufflehog filesystem . --only-verified --no-update # MUST 0 hits
bash tests/grandma.sh                              # MUST pass

# 6. Replace main + delete old branches + force push
git branch -M oss-fresh main
git push --force-with-lease origin main
git push --delete origin feature/bodhi-wakeup feature/livekit-wakeup feature/pipecat-phone

# 7. Public flip
gh repo edit Daisuke134/anicca-oss --visibility public --accept-visibility-change-consequences
gh repo edit Daisuke134/anicca-oss --description "Open-source autonomous digital Buddha — paste-prompt onboarding, Conway wallet, AGENTS.md compliant"
```

**Rollback:** `private-mirror` holds the full pre-squash state. If anything explodes:
```bash
git fetch private-mirror
git reset --hard private-mirror/main
git push --force-with-lease origin main
gh repo edit Daisuke134/anicca-oss --visibility private
```

---

## 5. Onboarding Flow — the Paste-Prompt Protocol

### 5.1 What the user does

1. Opens Claude Code (or Codex or Cursor or any AGENTS-compliant coding agent).
2. Pastes this **one** prompt:

```
Install Anicca for me. Follow the canonical install protocol at
https://raw.githubusercontent.com/Daisuke134/anicca-oss/main/install/prompt.md

Use my Plus subscription for inference. Ask me at most 3 questions:
my name, my timezone, my email. Everything else MUST be defaulted or
provisioned automatically. When done, confirm Anicca is running and
show me her Conway wallet address.
```

3. Answers 3 questions (name / timezone / email).
4. Waits ~3-5 minutes. Anicca is live.
5. (optional) Drains the Conway wallet to a Coinbase/Metamask/cold wallet whenever balance > threshold.

### 5.2 What the coding agent does

`install/prompt.md` (lives in the public repo, MUST be self-contained) instructs the coding agent to:

```
1.  git clone https://github.com/Daisuke134/anicca-oss.git ~/anicca-oss
2.  ANICCA_HOME=~/anicca-oss  (export to user shell rc)
3.  npx --yes conway-terminal                       # auto wallet + identity + API key
4.  cp ~/anicca-oss/profile.example.json ~/anicca-oss/profile.json
5.  prompt user for: name, timezone, email; patch profile.json (jq)
6.  detect host harness (Claude Code / Codex / Hermes / OpenClaw) via $env
7.  bash ~/anicca-oss/adapters/<harness>.sh        # wire to that harness
8.  bash ~/anicca-oss/install/postinstall.sh       # register cron / heartbeat
9.  Print: wallet address, harness chosen, next heartbeat time
```

### 5.3 Hard constraints on `install/prompt.md` and `installer.sh`

| MUST | MUST NOT |
|---|---|
| Idempotent — re-running is safe | Ask >3 questions of user |
| Detect harness automatically | Assume Claude Code only |
| Pin Conway Terminal version | Pull latest unpinned |
| Verify wallet creation (`cat ~/.conway/wallet.json | jq .address`) | Continue silently if wallet missing |
| Write summary to stdout AND `~/anicca-oss/install.log` | Phone home / telemetry |
| Exit non-zero on any step failure | Swallow errors |

---

## 6. Money Model — Conway Lifecycle

```
INSTALL (T+0)
  npx conway-terminal
    → ~/.conway/wallet.json (privkey 0600, addr 0x…)
    → identity via SIWE signature
    → API key cached
    → faucet seed: $5 USDC on Base (Conway default for new wallets)

OPERATIONS (T+1m … T+∞)
  Anicca needs LLM inference?
    → primary: USE user's Claude Code / Codex / Cursor Plus quota (FREE)
    → fallback: x402 micropayment via Conway wallet (small USDC per call)
  Anicca needs cloud compute (image gen / VM / TTS / video)?
    → x402 micropayment from Conway wallet
  Anicca earns money from a skill?
    → routes to Conway wallet via x402 (e.g., agent-to-agent commerce,
       affiliate links paid in USDC, content tips)
  Anicca needs to send fiat (e.g., transfer to bank)?
    → uses skill `anicca-stripe-payout` (POST-V1; calls Stripe Agents
       Toolkit; requires user to OAuth-connect Stripe account ONCE)

USER ACTIONS (rare)
  Check balance:  `anicca wallet balance`  (alias to conway terminal)
  Drain to bank:  `anicca wallet withdraw <addr> <amount>`
                  (or copy ~/.conway/wallet.json privkey into Coinbase)
  Top up:         `anicca wallet topup` (Conway USD on-ramp)
```

**Privacy:** Conway is non-custodial. The privkey lives only on the user's machine at `~/.conway/wallet.json` (0600). Anthropic / Conway / Anicca-OSS maintainers have ZERO access.

**Failure modes:**
| Failure | Behavior |
|---|---|
| Conway faucet down | Install completes; Anicca runs read-only until topped up |
| User's Plus quota exhausted | Anicca pauses LLM calls; logs to heartbeat; resumes next hour |
| x402 endpoint unreachable | Anicca skips that skill iteration; retries next cron |
| Privkey lost | User can re-install; new wallet; old balance lost (standard crypto) |

---

## 7. 3-Harness Architecture

### 7.1 Canonical substrate (single source of truth)

`~/anicca-oss/` is the ONLY place persona / skills / config live. All three harnesses read from there via their adapter.

### 7.2 Adapter contracts

| Harness | Adapter | What it does | LOC budget |
|---|---|---|---|
| **OpenClaw** | `adapters/openclaw.sh` | `ln -sf ~/anicca-oss/{AGENTS.md,SOUL.md,HEARTBEAT.md,skills,cron} ~/.openclaw/`; install plist `ai.openclaw.gateway.plist` | ~30 lines |
| **claude -p** | `adapters/claude-p.sh` | `ln -sf ~/anicca-oss/AGENTS.md ~/.claude/CLAUDE.md` (project-scoped); link skills to `~/.claude/skills/`; install plist `ai.anicca.claude-heartbeat.plist` (hourly, timeout 1200s — per HARD RULE #4 lesson) | ~30 lines |
| **Hermes** | `adapters/hermes.py` | Parse `skills/*/SKILL.md` frontmatter; emit `~/.hermes/config.yaml` with `external_dirs: [~/anicca-oss/skills]` and `system_prompt_path: ~/anicca-oss/AGENTS.md`; install plist `ai.hermes.anicca.plist` | ~50 lines |

### 7.3 What each harness MUST share

| Resource | Source | All 3 see identical? |
|---|---|---|
| Persona (AGENTS.md + SOUL.md) | `~/anicca-oss/` | YES (symlink or path-ref) |
| Skills (`skills/*/SKILL.md`) | `~/anicca-oss/skills/` | YES |
| Profile (`profile.json`) | `~/anicca-oss/profile.json` (gitignored) | YES |
| Conway wallet | `~/.conway/wallet.json` | YES (MCP server is host-agnostic) |
| Heartbeat state | `~/anicca-oss/workspace/heartbeat.state.json` | YES (file lock for concurrent writes) |

### 7.4 Comparison logging

Each harness MUST log every task execution to `~/anicca-oss/workspace/runs.jsonl`:

```json
{"ts":"2026-05-30T07:00:00Z","harness":"openclaw","task":"cfo-daily","outcome":"ok","wall_ms":42103,"tokens_in":12400,"tokens_out":3100,"cost_usd":0.04,"output_sha":"…"}
{"ts":"2026-05-30T07:00:00Z","harness":"claude-p","task":"cfo-daily","outcome":"ok","wall_ms":58220,"tokens_in":11800,"tokens_out":3400,"cost_usd":0.00,"output_sha":"…"}
{"ts":"2026-05-30T07:00:00Z","harness":"hermes","task":"cfo-daily","outcome":"ok","wall_ms":67410,"tokens_in":12100,"tokens_out":2900,"cost_usd":0.03,"output_sha":"…"}
```

Weekly cron `harness-compare-weekly` reads `runs.jsonl`, groups by task, ranks the 3 harnesses by speed / cost / quality (quality = recursive-improver score on `output_sha`), posts to `#metrics`.

NO formal benchmark framework. NO synthetic eval set. Real production tasks only.

### 7.5 Concurrency safety

Heartbeat / cron jobs run on launchd schedules. If two harnesses fire the same task in the same minute (e.g., both 7:00 cron):

| Mechanism | File |
|---|---|
| File lock | `flock ~/anicca-oss/workspace/locks/<task>.lock` (bash) |
| Skip on contention | Adapter checks lock age; > 1h = stale, take it; else skip |
| Log skip | Append `{"outcome":"skipped","reason":"lock_held_by":"openclaw"}` to runs.jsonl |

---

## 8. Skill Generalization Plan

| Step | Skill class | Action |
|---|---|---|
| 1 | 200 universal (marketing / asset / CFO / cron / etc) | Audit SKILL.md frontmatter for `author: Daisuke134`, hardcoded paths, aniccaai.com watermarks → patch to read from `$ANICCA_HOME` + `$ANICCA_BRAND_DOMAIN` (default aniccaai.com) + `profile.workEmail` |
| 2 | 44 anicca-* personal | MOVE to anicca-private-dais (no rename, no public reference) |
| 3 | 13 naist-* | MOVE to anicca-private-dais |
| 4 | profile.example.json | Author from scratch — no Dais data |
| 5 | identity/profile.schema.json | Strip NAIST/MUFG examples from `description:` fields; keep schema general |
| 6 | SOUL.md + HEARTBEAT.md | Refactor: keep Buddhist agent manifesto + autonomous-loop spec; REMOVE comedy ban / Tailnet IP / phone signature / Dais's daily rhythm specifics |
| 7 | CONSTITUTION.md → AGENTS.md | Convert to AAIF spec format (frontmatter: name, description, version); keep precepts (五戒) as universal ethical layer |

**Skill template (post-generalization SKILL.md frontmatter):**

```yaml
---
name: <skill-name>
description: <one-line, third-person, universal>
version: 1.0.0
authors: [anicca]
env:
  required: []
  optional: [POSTIZ_API_KEY, TWILIO_SID, ...]
profile_fields_used: [workEmail, timezone, ...]
brand_domain_used: true|false
---
```

---

## 9. Private Companion Repo — anicca-private-dais

```
anicca-private-dais/                              # github private, Dais-only
├── README.md                                     # how to mount alongside anicca-oss
├── mount.sh                                      # symlinks into ~/anicca-oss/skills/
├── skills/
│   ├── anicca-comedy* (×N)
│   ├── anicca-monk-factory*
│   ├── anicca-retreat* (×4)
│   ├── anicca-dentist-quarterly
│   ├── anicca-haircut-quarterly
│   ├── anicca-music-factory
│   ├── anicca-outbound-recruit
│   ├── anicca-zoom-attendee
│   ├── anicca-seo-rank-monitor
│   └── naist-* (×13)
├── identity/
│   └── profile.json                              # Dais's real data
├── .learnings/                                   # Dais's error/feature log
├── docs/                                         # phone/IP-containing plan docs
└── workspace/                                    # active session state
```

**Mount flow:** `bash ~/anicca-private-dais/mount.sh` creates symlinks from `~/anicca-oss/skills/<dais-skill>` → `~/anicca-private-dais/skills/<dais-skill>` and from `~/anicca-oss/profile.json` → `~/anicca-private-dais/identity/profile.json`. Anicca behaves identically to today on Dais's machine.

**Created via:**
```bash
gh repo create Daisuke134/anicca-private-dais --private \
  --description "Dais-specific Anicca skills + profile + learnings (mounted alongside anicca-oss)"
```

---

## 10. Test Matrix — Grandma E2E

`tests/grandma.sh` MUST simulate a fresh Mac and pass before public flip.

| # | Step | Pass criteria |
|---|------|---------------|
| 1 | Clone anicca-oss into a fresh `$HOME` (use a clean container or fresh user account) | `git clone` exits 0 |
| 2 | Run `npx conway-terminal` | `~/.conway/wallet.json` exists, mode 0600, valid JSON with `address` field |
| 3 | `cp profile.example.json profile.json && jq '.name = "Test User"' profile.json` | profile.json valid, schema-valid |
| 4 | `bash adapters/claude-p.sh` (assume Claude Code env) | `~/.claude/CLAUDE.md` symlink resolves to `~/anicca-oss/AGENTS.md`; launchd plist loaded; `launchctl list \| grep anicca` returns 1 |
| 5 | Trigger 1 heartbeat manually | `~/anicca-oss/workspace/runs.jsonl` has 1 new line with `outcome:ok` |
| 6 | Trigger Conway wallet balance check | Returns balance ≥ $0 (faucet may not have credited yet) |
| 7 | gitleaks scan of public repo state | 0 hits |
| 8 | trufflehog scan of public repo state | 0 verified hits |
| 9 | `grep -rni 'keiodaisuke\|daisuke_2_narita\|@mufg.jp\|+8180\|+1336\|+1484\|100.99.82.95\|100.108.140.123\|NAIST\|MUIT'` | 0 hits |
| 10 | Hermes adapter test (`adapters/hermes.py`) | `~/.hermes/config.yaml` valid YAML, references `~/anicca-oss/skills`, AGENTS.md path set |
| 11 | OpenClaw adapter test | `~/.openclaw/skills` is symlink to `~/anicca-oss/skills`; gateway plist loaded |
| 12 | 3-harness same-task smoke | Trigger `cfo-daily` on all 3, all complete, 3 lines in runs.jsonl with matching `task:` and same day's `ts:` |

Per HARD RULE #0.12 (verification-before-completion): no "spec done" claim until `bash tests/grandma.sh` returns exit 0 and fresh evidence (jsonl line counts, file mode, symlink targets) is read by the implementer.

---

## 11. Risks + Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Squash + force push reveals an undiscovered secret in WIP local changes | Low | Ban / OpenAI revoke | Pre-push: gitleaks + trufflehog + manual greps (§4 step 5); private-mirror backup before squash |
| AGENTS.md spec evolves; our spec becomes outdated | Med | Tooling drift | Pin to AAIF spec version in AGENTS.md frontmatter; revisit quarterly |
| Conway Terminal API breaking change | Med | Install breaks | Pin `npx conway-terminal@<sha>`; CI test `tests/grandma.sh` weekly |
| Hermes upstream renames config keys | Low | Adapter breaks | `adapters/hermes.py` reads schema version; warns if mismatch |
| User pastes prompt into a non-AGENTS-compliant agent | Med | Install partial | `install/prompt.md` MUST self-detect harness and error clearly if unknown |
| Coinbase faucet drained | Low | New installs have $0 | Document that user can top up; degraded mode still functional |
| Dais's private repo accidentally committed to public mirror | Low | Personal data leak | `.gitignore` includes `anicca-private-dais/` even if cloned alongside; pre-commit hook in `anicca-oss` rejects any file path containing `anicca-private-dais` |
| 3-harness running concurrently fights over Conway wallet rate-limit | Low | x402 calls fail | File lock per skill (§7.5); harnesses queue, do not parallelize same task |
| oh-my-openagent style "paste prompt" malicious-MD injection | Med | User's coding agent could be exploited via crafted prompt.md served from compromised raw.githubusercontent.com | Sign `install/prompt.md` with Anicca's Conway identity SIWE signature; installer.sh MUST verify signature before executing |

---

## 12. Implementation Plan — WBS

| Phase | Tasks | Owner | Dep |
|-------|-------|-------|-----|
| **P0 — Backup** | private-mirror push of current anicca-oss state | Anicca | — |
| **P1 — Private repo create** | gh create anicca-private-dais; mount.sh; move 57 skills + .learnings + docs | Anicca | P0 |
| **P2 — Public refactor** | Write AGENTS.md; refactor SOUL.md + HEARTBEAT.md to universal; strip Dais references from 200 surviving skills; write README + LICENSE + INSTALL.md + .env.example | Anicca | P1 |
| **P3 — Onboarding install** | install/prompt.md + installer.sh + postinstall.sh + sign with SIWE | Anicca | P2 |
| **P4 — Conway wiring** | Document Conway Terminal MCP registration per harness; verify wallet flow | Anicca | P2 |
| **P5 — Adapters** | adapters/openclaw.sh + claude-p.sh + hermes.py (~110 LOC total) | Anicca | P2 |
| **P6 — Tests** | tests/grandma.sh end-to-end | Anicca | P3, P4, P5 |
| **P7 — Squash + dry-run** | Execute §4 steps 1-5 (no push yet); gitleaks + trufflehog + greps all 0 | Anicca | P6 |
| **P8 — Force push + public flip** | Execute §4 steps 6-7 | Anicca | P7 + Dais approval |
| **P9 — Hermes activation** | adapter run on Mac mini; launchd plist load; 1 heartbeat verified | Anicca | P8 |
| **P10 — 3-harness comparison cron** | harness-compare-weekly cron + #metrics post | Anicca | P9 |

Each phase ends with HARD RULE #0.14 (job's-not-finished) E2E proof in `runs.jsonl` + grep audits.

---

## 13. References Cited (verify before relying)

| Ref | URL | Used in |
|---|---|---|
| AGENTS.md spec | https://agents.md | §2.5, §7 |
| Agent Skills spec | https://agentskills.io/specification | §2.5, §7 |
| Linux Foundation AAIF | https://aaif.io/projects/agents-md/ | §2.5 |
| Conway Automaton | https://github.com/Conway-Research/automaton | §2.3, §6 |
| Conway Terminal docs | https://docs.conway.tech | §2.3, §5, §6 |
| x402 ecosystem stats | https://www.x402.org/ecosystem | §2.3, §6 |
| oh-my-openagent (paste-prompt pattern, 60k★) | https://github.com/code-yeongyu/oh-my-openagent | §2.6, §5 |
| MoneyPrinterV2 (reality-check vs hype) | https://github.com/FujiwaraChoki/MoneyPrinterV2 | §2 sidebar |
| Coinbase AgentKit (NOT chosen, why) | https://github.com/coinbase/agentkit | §2.3 |
| MCP scope (tools, not persona) | https://modelcontextprotocol.io | §7 |

---

## 14. Open Questions / Post-v1

- Native macOS .app binary (bolt.diy pattern, 7/10 grandma score) — would lift install from "paste prompt" to "double-click"
- Anicca-hosted LLM proxy at aniccaai.com (would be a SaaS, conflicts with Satoshi-mode unless community-funded)
- AGENTS.md upstream contribution: make Hermes natively read AGENTS.md (PR to NousResearch/hermes-agent)
- Dynamic harness routing (decided NOT in v1 per §2.7)
- Real-money payout to user's bank via `anicca-stripe-payout` skill (Stripe Agents Toolkit) — post-v1
