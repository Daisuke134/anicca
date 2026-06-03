# 15 — anicca-friction-fixer  (= A0.5.5 enforcer + Friction Report auto-resolver)

| Field | Value |
|---|---|
| Spec ID | 15 |
| Status | DRAFT v1 (2026-06-03) |
| Agent | **anicca-friction-fixer** |
| Place | `~/.openclaw/skills/anicca-friction-fixer/` (runtime store, NOT worktree per HARD RULE #0 exception) |
| Wave | 1 (parallel with 10, 11, 12) — **highest priority** |
| Authoritative for | A0.5.5 enforcement, "user-click" surface detection, cron failure auto-fix, env-var auto-provisioning, disk hygiene |

---

## § 0. Why (= the spec that exists because every other spec needed it)

Friction Report 2026-06-03 06:23 JST showed Anicca:
- handing Dais a Hivemind device-code URL ("click to sign in")
- listing 12 crons failing with "Invalid request body" as "monitor"
- claiming 5 crons "need migration or disable" → Dais decide
- reporting `GOOGLE_API_KEY missing` instead of provisioning it
- reporting "Disk 93%" instead of cleaning it

Per A0.5.5 (= now part of constitution): **all 6 are violations**. The fix isn't to scold Anicca — it's to give her a skill whose job is to detect those surfaces in her own outbound messages and replace them with the correct auto-fix path BEFORE the message is posted.

This is the meta-skill that prevents the lie.

## § 1. File boundary

**TOUCHES** (= ~/.openclaw/skills/anicca-friction-fixer/ exclusively)

| Path | Purpose |
|---|---|
| `SKILL.md` | frontmatter + invocation rules |
| `scripts/detect.sh` | scans drafts + Slack outbound queue + cron error logs for the 6 surface patterns |
| `scripts/fix-hivemind.sh` | camofox + Google OAuth env → device-code completion |
| `scripts/fix-invalid-body.sh` | reads gateway error → diffs against last green commit → patches → restarts cron |
| `scripts/fix-piling-up.sh` | reads stuck cron prompts → either migrates to heartbeat archetype or marks deprecated |
| `scripts/fix-missing-envvar.sh` | matches missing var → upstream provider → camofox provisioning playbook → writes `.env` |
| `scripts/fix-disk-full.sh` | `du` candidates > 30d → safe delete (= `disk-cleaner` skill if exists, else local rules) |
| `scripts/fix-agent-no-response.sh` | reads failed `Agent couldn't generate` log → model fallback OR prompt-size reduction |
| `scripts/wrap-outbound.sh` | hook: any Slack `chat.postMessage` from Anicca → grep forbidden phrases → block + auto-redirect to fix script |
| `_shared/heartbeat-friction-sweep.sh` | fragment called from heartbeat-beat.sh (= every beat scans last 24h) |
| `state/violations.jsonl` | append-only log of detected violations + fix outcome |

**NEVER**

- `_shared/heartbeat-beat.sh` body (= governance merges)
- `_shared/heartbeat-memu.sh` (= Agent-3)
- Any path outside `~/.openclaw/skills/anicca-friction-fixer/` and the single `_shared/heartbeat-friction-sweep.sh` fragment

## § 2. Microtasks

| # | Task | Verify |
|---|---|---|
| 15.T1 | `detect.sh` matches 6 surface patterns via regex (= verbatim list from A0.5.5) | unit test with Friction Report 2026-06-03 verbatim → 6 matches |
| 15.T2 | `fix-hivemind.sh`: camofox `:9377` open URL → Google OAuth env → paste `user_code` → verify token persisted (= reads tokens.json or env-var write) | E2E with synthetic device URL (= test provider) |
| 15.T3 | `fix-invalid-body.sh`: reads last 7d of `~/.openclaw/cron/runs/*.jsonl` filter `error=Invalid request body` → git blame the cron schema field → roll back or fix | applies fix to 1 of the real 12 failing crons + verifies next run succeeds |
| 15.T4 | `fix-piling-up.sh`: reads the 5 piling-up crons (harvester / jsps / larry-updater / politician-receptive / stripe-to-pac) → either patches into heartbeat OR adds to `cron/disabled.json` with reason | 5 crons no longer pile |
| 15.T5 | `fix-missing-envvar.sh`: for `GOOGLE_API_KEY missing` → camofox cloud.google.com → create API key → write to `.env` chmod 600 → re-fire failing cron | cron next run succeeds with key |
| 15.T6 | `fix-disk-full.sh`: when `df / < 10% free` → `du -sh ~/.cache/anicca-clones/* /tmp/* ~/Downloads/* /Users/anicca/Library/Caches/*` → safe delete | disk free > 15% |
| 15.T7 | `fix-agent-no-response.sh`: reads `naist-pull` 44-fails pattern → if model 422 then fallback to next model in router; if context-size then trim prompt | naist-pull next 3 runs succeed |
| 15.T8 | `wrap-outbound.sh`: shell wrapper around `curl chat.postMessage` → grep `\b(click to sign|GOOGLE_API_KEY missing|disk at \d{2}%|need migration or)` → if match: block + run matching fix script + retry with corrected status | synthetic forbidden message blocked, fix executed, then corrected message posted |
| 15.T9 | `heartbeat-friction-sweep.sh`: invoked from heartbeat-beat.sh; runs `detect.sh` against last 24h then dispatches matching fix | dry-run shows correct dispatch matrix |
| 15.T10 | `state/violations.jsonl` schema: `{ts, pattern, source, fix_script, exit_code, evidence}` | 1 round produces ≥ 1 well-formed entry |
| 15.T11 | E2E: replay Friction Report 2026-06-03 as input → 6 violations detected → 6 fix scripts run → 5+ success | report Slack post: "Friction Report autoresolve: 6/6 fixed" or partial with specifics |

## § 3. Dependencies

- camofox-browser `:9377` (= 既 alive)
- `GOOGLE_LOGIN_EMAIL` + `GOOGLE_LOGIN_PASSWORD` env (= 既)
- `~/.openclaw/cron/runs/*.jsonl` history (= 599 entries)
- Slack API token (= 既)
- gcloud / Cloud Console accessible via Google login (= camofox path)

## § 4. DoD verification gates

| Gate | Evidence |
|---|---|
| G1 | `detect.sh` matches all 6 surfaces in Friction Report 2026-06-03 verbatim |
| G2 | Each fix script self-tests with `--dry-run` exits 0 |
| G3 | `wrap-outbound.sh` blocks 1 synthetic violation + runs fix + re-posts corrected |
| G4 | `heartbeat-friction-sweep.sh` fragment invoked from heartbeat-beat.sh on next beat |
| G5 | E2E replay of Friction Report 2026-06-03: ≥ 5 of 6 violations auto-fixed |
| G6 | `state/violations.jsonl` shows ≥ 1 real auto-fix within 24h of deployment |

## § 5. Anti-goals

- Not a chatbot moderator (= this is a real-action skill, not a comment filter)
- Not blocking ALL outbound (= only forbidden-phrase matches)
- Not requiring human approval for any fix (= per A0.5.5)

## § 6. Wire-in (= governance)

Governance inserts ONE line into `_shared/heartbeat-beat.sh` after the FRICTION SWEEP marker:

```bash
bash "$HOME/.openclaw/skills/anicca-friction-fixer/_shared/heartbeat-friction-sweep.sh" || true
```

This is the only shared-file touch and lives in governance.

## § 7. Why this is Wave 1's highest-priority spec

Without Agent-7, every other Wave 1 agent is at risk of writing code that says "Dais, click X." Agent-7 is the safety net that catches A0.5.5 violations before they propagate. It ships in parallel with 10/11/12 so the friction-fixer is online before any new code generates friction.

## § 8. Changelog

| Date | Change |
|---|---|
| 2026-06-03 | Initial draft. Born from Dais's verbatim mandate same day + Friction Report 06:23 JST. |
