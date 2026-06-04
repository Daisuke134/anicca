# OpenClaw cron: LLM refusal text classified as `status: ok`, fallback never fires

## Summary

When a cron's spawned agent (gpt-5.4-mini in our case) returns a text
refusal instead of calling `exec_command`, OpenClaw treats the turn as a
successful agent turn and records `status: ok`. The configured fallback
chain (`agents.defaults.model.fallbacks`) never fires because the runner
sees a "successful" reply.

## Repro

1. Configure a cron with `payload.kind = "agentTurn"`, `sessionTarget = "isolated"`, and a message that requires `exec_command`:
   ```
   bash $HOME/.openclaw/skills/<skill>/scripts/run.sh
   ```
2. Force the runner to use gpt-5.4-mini (current default).
3. Fire 5-10 times.

## Expected

If the agent never calls `exec_command` and returns only text, that
turn should be classified as a failure (e.g. `status: model-refusal`)
so the fallback chain can attempt the next model in the list.

## Actual

About 30% of fires return refusal text like:
- `resources/read failed: unknown MCP server 'openclaw'`
- `この turn では shell 実行経路が提供されていない…`
- `実行できませんでした…`

These are recorded as `status: ok`. No fallback model is tried. The
cron's scheduled work doesn't happen. Real run logs: `:x:` and
`:warning:` lines in our Slack #metrics 2026-06-04 18:20-12:37 JST batch.

## Proposed fix

Two parts:

1. **Detector.** In `dist/isolated-agent-D9XUbXHy.js`, after the turn
   completes, check whether the agent invoked any tool (`exec_command`,
   `read`, `write`). If `payload.toolsAllow` contains `exec` but no
   `exec_command` call was made and the final assistant text matches
   a configurable refusal regex (`unknown MCP server`, `実行環境`, etc.),
   classify the turn as `status: model-refusal`.

2. **Fallback hook.** When `status: model-refusal` is returned, trigger
   the same fallback path that 5xx / provider errors trigger. This needs
   a small change in the cron run-record loop to treat
   `model-refusal` as retryable (with a 1-step model-fallback budget so
   we don't infinitely retry).

## Impact

- Without this fix, cron reliability is a coin flip on every fire.
- Our `anicca-cron-doctor` workaround (Slack scrape + re-fire) costs
  one extra LLM round-trip per refusal — fixing this upstream would
  eliminate that overhead for everyone.

Reference: anicca-products spec
`docs/superpowers/specs/2026-06-04-cron-rat-proof-architecture-design.md` §1.1.
