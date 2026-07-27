# Cloud Agent Loop Inventory

## Purpose and boundary

The row-level inventory is [`cloud-agent-loop-inventory.tsv`](./cloud-agent-loop-inventory.tsv). It is the migration input for TODO #1 of the Life Manager cloud-agent platform spec; it is not the final workload or macOS-dependency classification (TODO #5 and #6 own those decisions).

The inventory includes every canonical Mac Mini user LaunchAgent plist, every OpenClaw cron record including disabled records, the production Life Manager Railway start entrypoint on `origin/main`, and repository `start`/`worker` entrypoints in the current branch. Repository discovery is deliberately scoped to first-party `apps/*/package.json` and `web-apps/*/package.json`; it does not recurse into vendored or nested package trees. Each TSV row has owner, provisional scope, current execution location, trigger, safe entrypoint, observed/declarative state, migration target, and an evidence path.

Secret and personal-data boundary: the generator never exports plist `EnvironmentVariables`, OpenClaw payload bodies, delivery content, prompts, logs, cookies, or credentials. Shell command bodies are redacted; only an executable and at most one syntactically safe declared script path are emitted. Absolute, `~/`, and repository-relative script declarations are retained even when the file is missing; absence is represented separately as `declared_entrypoint_missing` in `state`.

## Measured coverage

| Source | Rows | State summary |
|---|---:|---|
| `~/Library/LaunchAgents/*.plist` | 165 | loaded 147 (including one missing declared entrypoint); installed/not loaded 2; disabled by launchctl 14; parse error 2 |
| `~/.openclaw/cron/jobs.json` | 222 | enabled 92; disabled 130 |
| Railway production entrypoint | 1 | `apps/life-call/package.json#start -> node server.js` exists on `origin/main` |
| Current-branch repository entrypoints | 4 | `apps/api`, `apps/landing`, `apps/x402-agents`, and `web-apps/daily-dhamma-app`; runtime not asserted here |
| **Total** | **392 data rows** | 393 physical TSV lines including the header |

Two installed plists are malformed and remain explicit `parse_error` rows instead of disappearing from the inventory: `ai.anicca.cfo-daily` and `ai.anicca.tsbridge`.

The current refresh moves from the reviewed 334-row snapshot to 392 rows: 63 canonical IDs are added and five absent definitions are removed. The sorted added-ID digest is `7b1bba2b0ea5f9c867c4fbba9bcba73afb4177ed80243007fd2d1ccd01cac5d4`; the sorted removed-ID digest is `a0037d9ac67877089a4a846e4fcaea202992ff2da861cb3313d82a3ceebb6ee2`. The complete current-ID digest is `9f5479da29cb9159925166129606e6fa422b949faa6028d7267b961fba1209bb`. The removed definitions are `ai.anicca.article-d7d8-finalizer`, `ai.anicca.article-diary-digest`, `ai.anicca.disk-autoprune`, `ai.anicca.orca-zenn-finalizer`, and `com.anicca.disk-cleaner`; removal from this current inventory does not delete or stop any process.

`ai.anicca.pipecat-meeting` declares `~/anicca-oss-pipecat/skills/anicca-meeting/run.sh`. The declaration is preserved for migration tracing, while its current absence is recorded as `loaded;declared_entrypoint_missing`; ownership is `Anicca meeting / Pipecat` based on that path.

The 34 non-canonical files beside the plists (`*.disabled*`, `*.bak*`, and drafts) are archived definitions, not installed canonical LaunchAgents, so they are excluded from row counts. `crontab -l` reports no user crontab; OpenClaw `jobs.json` is the cron SSOT. Three live tmux sessions named `anicca-2` through `anicca-4` were inspected and excluded because they are interactive control sessions, not autonomous scheduler definitions.

## Scope and ownership

`scope` is a conservative first-pass classification, not a cutover decision:

- `product_loop_candidate`: earn/content/revenue loops that provisionally move through the DigitalOcean bridge and then into a Life Manager module.
- `product_runtime_candidate`: API, gateway, communication, and agent runtimes that provisionally move to a managed runtime or Life Manager module.
- `operations_support`: sync, backup, health, audit, and monitoring jobs that move to bridge or managed operations.
- `developer_infrastructure`: CI/package/dev services that remain local development infrastructure or move to a managed equivalent.
- `needs_scope_review`: no heuristic decision; TODO #5/#6 must classify it before cutover.

OpenClaw ownership uses the job's `agentId`, defaulting to the Anicca agent when absent. LaunchAgent ownership uses its label namespace and safe entrypoint path. No row is silently assigned to a product module when evidence is insufficient.

## Reproduce and verify

Run from the repository root on the Mac Mini:

```bash
python3 -m py_compile scripts/generate-cloud-agent-loop-inventory.py
python3 scripts/generate-cloud-agent-loop-inventory.py --self-test
python3 scripts/generate-cloud-agent-loop-inventory.py --check >/tmp/cloud-agent-loop-inventory.tsv
diff -u docs/reference/cloud-agent-loop-inventory.tsv /tmp/cloud-agent-loop-inventory.tsv
python3 - <<'PY'
import csv
from pathlib import Path

rows = list(csv.DictReader(Path('docs/reference/cloud-agent-loop-inventory.tsv').open(), delimiter='\t'))
assert len(rows) == 392
assert len({row['inventory_id'] for row in rows}) == len(rows)
assert all(all(row.values()) for row in rows)
assert sum(row['source_type'] == 'launchd' for row in rows) == 165
assert sum(row['source_type'] == 'openclaw_cron' for row in rows) == 222
assert sum(row['source_type'] == 'repository_entrypoint' for row in rows) == 4
print('inventory completeness: PASS (392 unique, complete data rows)')
PY
```

The generator's counts are intentionally tied to the live Mac Mini scheduler sources. A diff after a scheduler change means the TSV must be refreshed and reviewed before subsequent migration TODOs use it.
