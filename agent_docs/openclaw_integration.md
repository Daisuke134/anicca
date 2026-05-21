# OpenClaw Integration

## Anicca Agent

| Item | Value |
|------|-------|
| Home | `/Users/anicca/.openclaw/` |
| Config | `/Users/anicca/.openclaw/openclaw.json` |
| Cron | `/Users/anicca/.openclaw/cron/jobs.json` |
| Profile | full (all tools enabled) |
| Model | anthropic/claude-opus-4-6 |

## Communication

| Method | Command | Use |
|--------|---------|-----|
| Agent turn | `openclaw agent --message "..." --deliver` | Through Anicca's brain |
| Direct post | `openclaw message send --channel slack --target "C091G3PKHL2" --message "..."` | Bypass brain |

## Gateway

- Runs on Mac Mini 24/7
- Restart after config changes: `openclaw gateway restart`
- **jobs.json 編集後は restart 必須**

## Workspace Files

| File | Location |
|------|----------|
| IDENTITY.md | `/Users/anicca/.openclaw/workspace/` |
| SOUL.md | `/Users/anicca/.openclaw/workspace/` |
| AGENTS.md | `/Users/anicca/.openclaw/workspace/` |

## Auth Token Migration

- `openclaw models auth setup-token` updates `main` agent only
- **`anicca` agent requires manual auth-profiles.json update**
- After update: `openclaw gateway restart`

## Rules

| Rule | Detail |
|------|--------|
| MCP tools (`mcp__*`) | CC-only, not available in OpenClaw |
| Slack posting | Use `slack` tool (profile:full) or CLI |
| VPS | Disabled (2026-02-18 migration complete) |

## OpenClaw TUI Troubleshooting

### "gateway not connected"

**Root cause: MacBook has stale VPS tunnel on port 18789.**

```bash
lsof -i :18789                              # Who holds port?
launchctl list | grep -E "(openclaw|tunnel)" # List tunnels
```

| Correct State | Value |
|--------------|-------|
| MacBook gateway.remote.url | `ws://127.0.0.1:18789` |
| MacBook LaunchAgent | `ai.openclaw.tunnel.plist` (Mac Mini only) |
| Mac Mini gateway.bind | `"loopback"` (never change) |
| VPS gateway | `systemctl --user disable openclaw-gateway` |

**Forbidden:** `bind: "tailnet"` / keeping VPS tunnel / `stop` without `disable`

## Sentinel Strings (CC ↔ OpenClaw)

| Sentinel | Meaning | Used By |
|----------|---------|---------|
| `WAITING_FOR_HUMAN` | Needs manual input (API key, approval) | Both |
| `TASK_COMPLETE` | Task finished successfully | OpenClaw → CC |
| `TASK_FAILED` | Task failed, needs attention | OpenClaw → CC |
| `CONTEXT_HANDOFF` | Passing context between agents | CC → OpenClaw |

## Worktree Templates

### STATUS.md
```markdown
# Worktree Status
| Item | Value |
|------|-------|
| Branch | feature/<name> |
| Agent | CC / OpenClaw |
| State | in-progress / blocked / done |
| Last Updated | YYYY-MM-DD HH:MM |
```

### PLAN.md
```markdown
# Worktree Plan
## Goal
<one-line objective>
## Tasks
- [ ] Task 1
- [ ] Task 2
## Boundaries
Files touched: <list>
Files NOT touched: <list>
```
