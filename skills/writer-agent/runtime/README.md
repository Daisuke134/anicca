# Article model runner contract

`model-runner.sh` is the only operational process boundary for article model
calls.

```text
model-runner.sh agent  --prompt-file <path>
model-runner.sh judge  --prompt-file <path>
model-runner.sh vision --prompt-file <path> --image <path>
```

Required runtime identity:

```text
ARTICLE_PROVIDER=auto|codex|claude
ARTICLE_RUN_ID=<stable run ID>
ARTICLE_MODEL_LOG=<run-scoped log>
```

- Codex uses `gpt-5.6-luna` with `xhigh`.
- Claude uses `sonnet` with provider-default effort.
- `auto` tries an eligible Codex lane before Claude.
- `judge` and `vision` may fall back after a classified retryable failure
  because they cannot publish.
- `agent` never replays a full prompt after a provider process starts. A
  retryable failure exits 75 and leaves the same run pending.
- Health cooldowns are scoped by provider and mode.
- Exit 64 is invalid input, 69 is a missing fixed provider, and 75 is a
  temporary no-healthy-provider result.
