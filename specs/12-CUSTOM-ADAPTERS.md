# 12 — anicca-adapter-smith  (= Lancers / Coconala / Bland.ai / AgentMail custom adapters)

| Field | Value |
|---|---|
| Spec ID | 12 |
| Status | DRAFT v1 (2026-06-03) |
| Agent | **anicca-adapter-smith** |
| Worktree | `.worktrees/adapters/` |
| Branch | `feature/custom-adapters` |
| Wave | 1 (parallel with 10, 11, 15) |
| Authoritative for | JP gig platform adapters, voice call adapter, AgentMail thin wrapper |

---

## § 0. Why

Composio covers Gmail / Slack / Linear / GitHub / X — but NOT Lancers / Coconala / Bland.ai. These are the platforms where Anicca's first JPY revenue comes from. Composio + custom adapters give Anicca a unified action surface.

camofox can run both stealth and visible (= verified, README correction recorded). Lancers and Coconala have NO public API — adapter pattern = camofox + saved session.

## § 1. File boundary

**TOUCHES**

| Path | Purpose |
|---|---|
| `adapters/custom/lancers/` | session persistence + DM send + DM read + bid + project status |
| `adapters/custom/coconala/` | same pattern as Lancers |
| `adapters/custom/bland-ai/` | outbound voice call API wrapper |
| `adapters/custom/agentmail/` | thin wrapper around official SDK (deduplicate spec 10's import-side) |
| `adapters/custom/README.md` | how to invoke each |

Each `adapters/custom/<name>/` contains:
- `SKILL.md` (= Hermes/OpenClaw skill frontmatter for registry)
- `index.ts` or `index.py` (= main module)
- `scripts/run.sh` (= CLI entry)
- `tests/e2e.ts` (= verification harness)

**NEVER**

- `services/**`, `runtime/**`, `deploy/**`, `skills/**` (= other agents)
- `_shared/heartbeat-*.sh` (= Agents 3, 7)
- Existing `~/.openclaw/skills/lancers/**` / `~/.openclaw/skills/coconala/**` (= legacy, gradual replace)

## § 2. Microtasks

| # | Task | Verify |
|---|---|---|
| 12.T1 | Lancers: cookie/session bootstrap via camofox + Google login (env creds) once; save session.json | session.json present, valid for ≥ 7d |
| 12.T2 | Lancers: `send_dm(thread_id, body)` via camofox or REST replay | 1 real DM delivered to test thread |
| 12.T3 | Lancers: `read_inbox(since=)` returns list[Thread] | 5 most recent threads parsed |
| 12.T4 | Lancers: `bid(gig_id, amount, message)` | 1 real bid placed (= test gig) |
| 12.T5 | Coconala: same 4 sub-tasks (session / send / read / bid) | same DoD per sub-task |
| 12.T6 | Bland.ai: `outbound_call(to, script, voice)` via REST + webhook receiver | 1 real test call to Dais's phone, hangup after greeting |
| 12.T7 | AgentMail thin wrapper: `send(inbox, to, subject, text)` + `receive(inbox, since)` + `subscribe_webhook(url)` | unit test passes, no duplication with spec 10 import-side |
| 12.T8 | SKILL.md frontmatter for each adapter (= Hermes/OpenClaw can register them) | `hermes skill list` shows 4 adapters |
| 12.T9 | tests/e2e.ts per adapter sends 1 real msg as final verify | 4 messages delivered, recorded in `state/adapter-test-log.jsonl` |

## § 3. Dependencies

- camofox-browser running on `:9377` (= 既 alive)
- `GOOGLE_LOGIN_EMAIL` + `GOOGLE_LOGIN_PASSWORD` (= 既 in `.env`)
- `BLAND_API_KEY` (= 既 in `.env` if previously set; if absent, agent provisions via `bland.ai/dashboard` camofox flow per A0.5.5)
- AgentMail SDK (= 既 installed)

## § 4. DoD verification gates

| Gate | Evidence |
|---|---|
| G1 | Lancers DM delivered to live test thread |
| G2 | Coconala DM delivered to live test thread |
| G3 | Bland.ai test call placed + completed with audible greeting |
| G4 | AgentMail wrapper send/receive E2E |
| G5 | All 4 adapters registered in Hermes skill registry |
| G6 | All session.json files chmod 600 + gitignored |

## § 5. Anti-goals

- Not bypassing platform ToS (= Anicca operates her own keiodaisuke+anicca@gmail.com identity per existing memory `identity_anicca_login_accounts`)
- Not aggressive bot behavior (= ≤ 10 DM/hour per platform, ≤ 3 bids/day)
- Not posting CAPTCHA-bypass code (= per HARD RULE #-1 genuine CAPTCHA = stop + Slack)

## § 6. Tool selection (= per HARD RULE #-2)

| Platform | Primary | Fallback |
|---|---|---|
| Lancers | camofox visible + Google login | cua-driver if camofox blocked |
| Coconala | camofox visible | cua-driver |
| Bland.ai | REST API direct | camofox dashboard |
| AgentMail | Python SDK direct | — |

## § 7. Changelog

| Date | Change |
|---|---|
| 2026-06-03 | Initial draft. camofox visible mode confirmed via README correction same day. |
