# Frontier Model Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cron + heartbeat default = `openai/gpt-5.4-mini` (cheap); chat surfaces (phone Claude Code now, Telegram bot future) = frontier (Opus 4.7 explicit). Sonnet drops to LAST fallback only. The 5 cron-level sonnet overrides shrink to 1 (mail-triage justified per HARD RULE #6).

**Architecture:** Single source of truth = `~/.openclaw/openclaw.json::agents.defaults.model`. Phone uses `--model claude-opus-4-7` at the CLI flag layer (subsystem ① already shipped). Per-cron overrides are exceptions, each must be listed in `~/.openclaw/docs/MODEL_OVERRIDE_REGISTRY.md` with rationale. Doctor `--fix` only knows the `primary` and `fallbacks` keys, so any future `interactive` key is doctor-safe.

**Tech Stack:** jq, openclaw CLI, bash.

**Pre-flight verified 2026-06-06**:
- Current: `primary=moonshot/kimi-k2.5`, `fallbacks=[xai/grok-3-mini-fast, deepseek/deepseek-v4-pro, anthropic/claude-sonnet-4-6]`
- 5 sonnet-override crons identified: x-buildinpublic-daily, x-engagement-quote, anicca-yt-long-en, anicca-yt-long-ja, anicca-mail-triage
- cron-codex.sh dispatcher at `~/.openclaw/skills/_dispatcher/scripts/cron-codex.sh`

---

## File Structure

| File | Change |
|---|---|
| `~/.openclaw/openclaw.json` | Swap primary + reorder fallbacks (drop grok) |
| `~/.openclaw/openclaw.json.bak-pre-v32-routing-20260606` | NEW (backup) |
| `~/.openclaw/cron/jobs.json` | Edit 4 of 5 sonnet override crons via `openclaw cron edit` (mail-triage stays) |
| `~/.openclaw/docs/MODEL_OVERRIDE_REGISTRY.md` | NEW — explicit log of allowed per-cron overrides + rationale |
| `~/.openclaw/skills/_dispatcher/scripts/cron-codex.sh` | Add `export OPENCLAW_CONTEXT=cron` for future routing infra (no behavior change today) |
| `~/.openclaw/skills/anicca-config-canary/SKILL.md` | NEW — daily canary cron that diffs openclaw.json vs .last-good and alerts on doctor wipe |
| `~/.openclaw/cron/jobs.json` | NEW canary cron entry (anicca-config-canary-daily) |

---

## Tasks

### Task 1: Backup openclaw.json

- [ ] Run `cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak-pre-v32-routing-20260606` + verify file size > 0.

### Task 2: Swap primary + reorder fallbacks via jq

- [ ] Apply edit:
```bash
jq '.agents.defaults.model = {
  "primary": "openai/gpt-5.4-mini",
  "fallbacks": [
    "moonshot/kimi-k2.5",
    "deepseek/deepseek-v4-pro",
    "anthropic/claude-sonnet-4-6"
  ]
}' ~/.openclaw/openclaw.json > ~/.openclaw/openclaw.json.new && \
mv ~/.openclaw/openclaw.json.new ~/.openclaw/openclaw.json
```
- [ ] Verify with `jq '.agents.defaults.model' ~/.openclaw/openclaw.json`.

### Task 3: Write MODEL_OVERRIDE_REGISTRY.md

- [ ] Create `~/.openclaw/docs/MODEL_OVERRIDE_REGISTRY.md` listing the 1 retained override (anicca-mail-triage) + rationale + revisit date.

### Task 4: Migrate 2 X-useful sonnet crons → primary (drop override)

- [ ] `openclaw cron edit 94c788fe-42d8-4eab-903c-ce991e673013 --json '{"model": null}'` (x-buildinpublic-daily)
- [ ] `openclaw cron edit ee9c031f-5539-4df4-a39b-246ff933b62a --json '{"model": null}'` (x-engagement-quote)
- [ ] Verify with `openclaw cron get <id>` — model field gone or null.

### Task 5: Migrate 2 yt-long sonnet crons → deepseek/deepseek-v4-pro

- [ ] `openclaw cron edit 4cfdfe32-eb9e-47d1-90ea-236ce8757cee --json '{"model": "deepseek/deepseek-v4-pro"}'`
- [ ] `openclaw cron edit 73d4a8c2-5132-406a-bda3-5508f2d32951 --json '{"model": "deepseek/deepseek-v4-pro"}'`
- [ ] Verify each.

### Task 6: Confirm mail-triage stays on sonnet (registered exception)

- [ ] `openclaw cron get d15ebeb3-0aa9-4d16-9e9a-c177453a96a4` — confirm model = `anthropic/claude-sonnet-4-6`.
- [ ] Verify presence in `MODEL_OVERRIDE_REGISTRY.md`.

### Task 7: Add `OPENCLAW_CONTEXT=cron` to cron-codex.sh

- [ ] Edit `~/.openclaw/skills/_dispatcher/scripts/cron-codex.sh` near the top:
```bash
export OPENCLAW_CONTEXT=cron
```
- [ ] No-op today (no consumer); forward-compat hook for future router. Commit with rationale.

### Task 8: Create anicca-config-canary daily cron

- [ ] Write skill + cron entry: daily 03:30 JST, diff `openclaw.json` vs `openclaw.json.last-good`, Slack URGENT on drift, otherwise overwrite `.last-good`.

### Task 9: Sanity smoke — run one migrated cron, verify exit 0

- [ ] `openclaw cron run 94c788fe-42d8-4eab-903c-ce991e673013` (x-buildinpublic-daily, now on primary).
- [ ] Read tail of run log; exit 0 = primary swap healthy.

### Task 10: Commit + push

- [ ] Mirror `~/.openclaw/openclaw.json` (sanitized — drop secrets) + cron-codex.sh + MODEL_OVERRIDE_REGISTRY.md to repo for tracking.
- [ ] `git add` + commit + push.
