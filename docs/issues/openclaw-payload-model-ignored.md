# OpenClaw cron: `payload.model` field silently ignored by runner

## Summary

`cron.payload.model` is documented as a per-job model override, but the
cron runner never honors it. Every cron we have in `jobs.json` with
`payload.model = "moonshot/kimi-k2.5"` (or any value) is executed with
the agent's `defaults.model.primary` instead.

## Repro

1. Set up a cron with explicit override:
   ```bash
   openclaw cron edit <id> --message "test" --session isolated
   ```
   Manually patch `jobs.json` to set `"model": "deepseek/deepseek-v4-pro"`.
2. Fire the cron: `openclaw cron run <id> --wait --expect-final`.
3. Read the resulting rollout under
   `~/.openclaw/agents/<agent>/agent/codex-home/sessions/.../rollout-*.jsonl`.

## Expected

`session_meta.model_provider` and rollout-level `model` should reflect
the `payload.model` value (`deepseek/deepseek-v4-pro`).

## Actual

`session_meta.model_provider = "openai"` and rollout `model = "gpt-5.4-mini"`
regardless of what `payload.model` is set to. The override is dropped
silently — no warning is logged.

Concrete repro logged 2026-06-04 18:20 JST: cron `anicca-earn-bounty`
(id `1730c972-acd1-4677-bed4-26d18fb749bd`) and `anicca-wallet-balance`
(`d4036615-b32f-4b2d-beb7-7947ff4696b4`) both set `"model": "moonshot/kimi-k2.5"`
but ran on `gpt-5.4-mini`. Rollout files:
- `~/.openclaw/agents/anicca/agent/codex-home/sessions/2026/06/04/rollout-2026-06-04T18-20-55-019e91ef-8c62-7c70-9afc-ce09f5e1558c.jsonl`
- `~/.openclaw/agents/anicca/agent/codex-home/sessions/2026/06/04/rollout-2026-06-04T18-20-50-019e91ef-7540-7c02-91d5-da98c003f506.jsonl`

## Proposed fix

In `dist/run-executor.runtime-*.js::executeCronRun`, when `params.job.payload.kind === "agentTurn"`, propagate `payload.model` into the isolated-session model resolution chain *before* falling through to `agents.defaults.model.primary`. Today the override is read (`const modelOverrideRaw = ... payload.model`) but isn't passed to the spawn call.

## Impact

- Breaks per-cron model cost control (cheap mini cron forced onto expensive primary).
- Defeats the `fallbacks` chain when primary is unhealthy: operators set
  `payload.model = "deepseek/deepseek-v4-pro"` to bypass a broken primary
  and the override is silently dropped.
- Surfaced in our cron-rat-proof incident review (anicca-products commit
  `b802f4b4`, spec `docs/superpowers/specs/2026-06-04-cron-rat-proof-architecture-design.md` §1.2).
