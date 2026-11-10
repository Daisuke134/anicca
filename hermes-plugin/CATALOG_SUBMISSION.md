# Catalog submission — life-manager

Target repository: `NousResearch/hermes-agent`
File: `plugin-catalog/life-manager.yaml`
Pin: `722bc06474c30aeb9437384cb14db20e544c4823` added the plugin source and passed `hermes plugins validate --install-deps`. A later commit on this branch only records that pin in this file. Catalog CI should pin a default-branch commit whose `hermes-plugin/` tree matches that commit. The `sha` field below is that plugin commit.

## Entry

```yaml
name: life-manager
title: Life Manager
repo: https://github.com/Daisuke134/life-manager
sha: 722bc06474c30aeb9437384cb14db20e544c4823
subdir: hermes-plugin
version: "1.0.0"
description: "Records commitments a person states, keeps habit streaks, and injects the board before each turn. A daily Automation Blueprint runs an unattended check-in. Disclosure: no network, no credentials, no shell. Stores commitment text, due dates, streaks, nudged session ids, and the last check-in id in the active Hermes profile plugin state only."
maintainer: Daisuke134
tier: community
category: automation
requires_hermes: ">=0.23.0"
docs_url: https://github.com/Daisuke134/life-manager/tree/main/hermes-plugin
readme: true
platforms: []
capabilities:
  provides_tools:
    - life_manager_status
    - life_manager_commit
    - life_manager_complete
    - life_manager_drop
    - life_manager_defer
    - life_manager_checkin
  provides_hooks:
    - pre_llm_call
  provides_middleware:
    - tool_request
  requires_env: []
```

## Pull request description

### What it does

Life Manager is the behavior-change side of [Daisuke134/life-manager](https://github.com/Daisuke134/life-manager), packaged as a Hermes plugin. When someone states a commitment ("I commit to ship the essay tomorrow", "I'll meditate every morning"), a `pre_llm_call` hook stores it and injects the live board — overdue tasks, items due today, and habit streaks — into that turn. The agent can record, complete, defer, or drop items with tools. Daily streaks increment on consecutive days and show 0 after a miss, while the best streak remains. A new habit is due today, not overdue yet.

A skill alone cannot keep this state across sessions or run the check-in when nobody is typing. The plugin does both.

### Surfaces

- Tools: `life_manager_status`, `life_manager_commit`, `life_manager_complete`, `life_manager_drop`, `life_manager_defer`, `life_manager_checkin`
- Hook: `pre_llm_call` (capture high-confidence statements, inject the board, ask about an overdue item once per session)
- Middleware: `tool_request` (trim text, map cadence `everyday` to `daily`)
- Slash command: `/commitments`
- CLI: `hermes life-manager`
- Skill: `life-manager:intervene`
- Automation blueprint: `life-manager:check-in` (public blueprint API; becomes a normal Hermes cron job; default 08:30)
- No desktop bundle, no MCP server, no provider, no login backend
- No privileged capabilities, no built-in tool overrides, no core monkeypatches

`requires_hermes` is `>=0.23.0` in both `plugin.yaml` and this entry (state, cron identity, middleware, and automation blueprints). Version `1.0.0`. No Python dependencies.

### Rule 13 disclosure

- Network calls: none.
- Credentials: none. No environment reads, no dotenv, no auth-store reads, no OAuth.
- Shell commands and background processes: none.
- Reads outside the plugin's own data: none. The hook sees only the `user_message` argument Hermes passes in.
- Stored data: commitment text, kind, cadence, due date, source, dates, streak, best streak, capped nudged session ids, and the last unattended check-in id. Location is the active profile's plugin state (`ctx.state`), not the install tree.
- Telemetry: none, and there is no opt-in switch because nothing is sent.
- Unattended runs: the hook, tools, slash command, and CLI never prompt. `life_manager_checkin` sees `ctx.current_cron_execution()` and returns the board immediately. Failures in the hook inject nothing and leave the turn running.

### Admission notes

- Subdir `hermes-plugin` in the public repo `https://github.com/Daisuke134/life-manager`.
- Submitted by the repository owner.
- Not a fork of a listed plugin and not a skin of a bundled plugin.
- Source only. No binaries, bytecode, or archives.
- English user-facing strings.

## Catalog pull request

The catalog PR against `NousResearch/hermes-agent` was not opened. This checkout can create pull requests only in `Daisuke134/life-manager`. Forking the catalog repo failed:

```text
gh repo fork NousResearch/hermes-agent --clone=false --default-branch-only
failed to fork: HTTP 403: Resource not accessible by integration (https://api.github.com/repos/NousResearch/hermes-agent/forks)
```

Paste the yaml above as `plugin-catalog/life-manager.yaml` and use the pull request description in this file. The `sha` field stays `722bc06474c30aeb9437384cb14db20e544c4823` only while that commit is reachable from the default branch and `hermes-plugin/` at that commit is the validated tree.
