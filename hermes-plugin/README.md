# Life Manager (Hermes plugin)

Life Manager is a behavior-change plugin for [Hermes Agent](https://hermes-agent.nousresearch.com). It remembers commitments a person actually states, keeps a habit streak, and puts that board in front of the agent before the next reply. A scheduled check-in uses Hermes's Automation Blueprint catalog, so the schedule is an ordinary Hermes cron job rather than a private timer inside the plugin.

`requires_hermes`: `>=0.23.0`

## What it does

On each turn, a `pre_llm_call` hook reads the user message Hermes already passed in.

- Explicit lines such as "I commit to ship the essay tomorrow" and time-bound lines such as "I'll meditate every morning" are stored.
- Bare "I will think about it", questions, refusals, and messages that look like credentials are not stored.
- The same open wording is not stored twice.
- The hook then injects the open board: overdue tasks, items due today, and habit streaks. The "ask once" line is added only the first time in that session.

Tools let the agent record, complete, defer, or drop items when the person says so. Completing a daily habit on consecutive days increases the streak. Missing a day shows the current streak as 0 and keeps the best streak. A habit stated today is due today, not yet overdue.

`tool_request` middleware trims commitment text and maps the cadence alias `everyday` to `daily` before the handler runs.

`/commitments` works in a chat session. `hermes life-manager` does the same from a terminal. Neither command asks a question or waits for input.

## Scheduled check-in

The plugin registers an Automation Blueprint, `life-manager:check-in`, daily at a time the user picks (default 08:30). Scheduling it creates a normal Hermes cron job. The job's prompt calls `life_manager_checkin`.

During cron, `ctx.current_cron_execution()` is set, so the tool records the check-in and returns the board. It does not prompt, and it does not wait. Outside cron the same tool returns the board without recording a scheduled run.

## Install

Copy this directory to the active profile's plugins folder and enable it:

```sh
hermes plugins install /path/to/hermes-plugin
hermes plugins enable life-manager
```

If you are validating a checkout instead of installing:

```sh
hermes plugins validate /path/to/hermes-plugin --install-deps
```

Settings live under `plugins.entries.life-manager.settings`:

| Key | Default | Meaning |
| --- | --- | --- |
| `capture_statements` | `true` | Store high-confidence commitments from the user's words. |
| `max_open` | `30` | Cap on open items. |

## Surfaces

- Tools: `life_manager_status`, `life_manager_commit`, `life_manager_complete`, `life_manager_drop`, `life_manager_defer`, `life_manager_checkin`
- Hook: `pre_llm_call`
- Middleware: `tool_request`
- Slash command: `/commitments`
- CLI: `hermes life-manager` (local CLI). `hermes plugins validate` reports that `register_cli_command` is not wired when the plugin host isolation mode is on; tools, the hook, and `/commitments` still load there.
- Skill: `life-manager:intervene` (short instructions; the board itself is the hook)
- Automation blueprint: `life-manager:check-in`

No privileged `capabilities` are requested. Built-in tools are not replaced.

## Disclosure

- Network: none. The plugin does not call third-party services and does not phone home.
- Credentials: none. It does not read environment variables, dotenv files, Hermes auth stores, or any other credential file. It refuses to store text that looks like a key, token, or password.
- Shell and processes: none. It does not spawn commands or background processes.
- Files outside its own state: none. It does not read the workspace, the transcript database, or other plugins.
- Stored data: commitment text, kind, cadence, due date, source (`stated` or `tool`), created date, last completed date, current streak, best streak, the session ids already nudged (capped), and the last unattended check-in id. Hermes keeps this in the active profile's plugin state via `ctx.state`. It is not written into the plugin install directory. Uninstalling or updating the plugin through Hermes can remove that state with the profile data; the plugin has no separate account.
- Telemetry: none.
- Unattended runs: hooks, tools, the slash command, and the CLI return text or JSON. They do not call `ask_choice`, read stdin, or start a browser sign-in. If state cannot be read, the hook injects nothing and the turn continues.

## Tests

From the repository root, with Python 3.11+:

```sh
python3 hermes-plugin/tests/test_engine.py
```

The tests cover statement capture, streak math, the once-per-session overdue line, unattended check-in, middleware normalization, and the manifest matching `register()`.
