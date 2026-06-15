# Plan: 2026-06-04 cron rat-proof (Phase A only this session)

Spec: `docs/superpowers/specs/2026-06-04-cron-rat-proof-architecture-design.md`

## Phase A (本 session、 ~30 min)

### Step A-1: backup state (2 min)

```bash
cp ~/.openclaw/cron/jobs.json ~/.openclaw/cron/jobs.json.bak-phaseA-$(date +%Y%m%d-%H%M%S)
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak-phaseA-$(date +%Y%m%d-%H%M%S)
ls -la ~/.openclaw/cron/jobs.json.bak-phaseA-* ~/.openclaw/openclaw.json.bak-phaseA-* | tail -2
```

### Step A-2: flip 2 crons to systemEvent (3 min)

```python
import json, pathlib
p = pathlib.Path.home() / ".openclaw/cron/jobs.json"
data = json.loads(p.read_text())

WALLET_SE = "[anicca-cron-wallet] In main session: run `bash $HOME/.openclaw/skills/anicca-wallet/scripts/balance.sh` and post stdout JSON to Slack #metrics."
BOUNTY_SE = "[anicca-cron-bounty] In main session: run `bash $HOME/.openclaw/skills/anicca-earn-bounty/scripts/run.sh` and post tail stdout to Slack #metrics. If exit code != 0, post stderr verbatim with prefix ':x:'."

for j in data["jobs"]:
    if j["id"] == "d4036615-b32f-4b2d-beb7-7947ff4696b4":
        # wallet-balance → systemEvent main
        j["sessionTarget"] = "main"
        j["payload"] = {"kind": "systemEvent", "text": WALLET_SE, "timeoutSeconds": 180}
    if j["id"] == "1730c972-acd1-4677-bed4-26d18fb749bd":
        # earn-bounty → systemEvent main
        j["sessionTarget"] = "main"
        j["payload"] = {"kind": "systemEvent", "text": BOUNTY_SE, "timeoutSeconds": 600}

p.write_text(json.dumps(data, indent=2, ensure_ascii=False))
print("flipped both to systemEvent")
```

Expected: `flipped both to systemEvent`

### Step A-3: fire + observe (5 min)

```bash
# wallet
openclaw cron run d4036615-b32f-4b2d-beb7-7947ff4696b4 --wait --wait-timeout 4m --timeout 240000 --expect-final
# bounty
openclaw cron run 1730c972-acd1-4677-bed4-26d18fb749bd --wait --wait-timeout 10m --timeout 600000 --expect-final
```

### Step A-4: verify (AC-1, AC-2)

| Pass | summary に含む文字 |
|---|---|
| AC-1 wallet | `usdc_balance` or `address` or `0x` |
| AC-2 bounty | `scan` or `select` or `bounty` |

### Step A-5: branch on result

| 結果 | 次 |
|---|---|
| Both pass | Step A-6 (= commit + push) |
| 1 or 0 pass | Iteration B (= codex exec wrapper) |

### Step A-6: commit + push (3 min)

```bash
cd ~/.openclaw && \
git -c commit.gpgsign=false add cron/jobs.json && \
git -c commit.gpgsign=false commit -m "feat(cron): flip wallet-balance + earn-bounty to systemEvent/main

Per spec docs/superpowers/specs/2026-06-04-cron-rat-proof-architecture-design.md
Path 1 = systemEvent → main session, leveraging Anicca's full tool stack
(MCP plugins, all credentials, persistent session). Replaces brittle
isolated agentTurn sandbox that triggered 18:20 refusal incident.

Refs: AC-1 + AC-2 verified in same session" && \
git push

cd /Users/anicca/anicca-project && \
git add docs/superpowers/specs/2026-06-04-cron-rat-proof-architecture-design.md \
        docs/superpowers/plans/2026-06-04-cron-rat-proof.md && \
git commit -m "docs(cron): rat-proof architecture spec + Phase A plan" && \
git push
```

## Phase B (only if Phase A fails)

### Step B-1: create dispatcher dir

```bash
mkdir -p ~/.openclaw/skills/_dispatcher/scripts
```

### Step B-2: write `cron-exec.sh` wrapper

```bash
#!/usr/bin/env bash
# Usage: cron-exec.sh <skill-relative-script> [args...]
# Runs the skill script via `codex exec` with full sandbox + MCP plugins.
set -euo pipefail

SCRIPT_REL="${1:?usage: cron-exec.sh <skill/scripts/x.sh> [args...]}"; shift
ABSPATH="$HOME/.openclaw/skills/$SCRIPT_REL"
[ -f "$ABSPATH" ] || { echo ":x: not found: $ABSPATH" >&2; exit 2; }

set -a
. "$HOME/.openclaw/.env" 2>/dev/null || true
set +a

LOG=$(mktemp /tmp/cron-exec.XXXXXX.log)
if timeout 300 bash "$ABSPATH" "$@" >"$LOG" 2>&1; then
    tail -10 "$LOG"
    exit 0
else
    EXIT=$?
    echo ":x: cron failed (exit=$EXIT):"
    tail -20 "$LOG"
    exit "$EXIT"
fi
```

### Step B-3: rewrite cron prompts to call wrapper

```python
# payload.message =
#   "exec で 必ず実行: bash $HOME/.openclaw/skills/_dispatcher/scripts/cron-exec.sh anicca-wallet/scripts/balance.sh"
```

### Step B-4: fire + verify

Same as A-3 + A-4. If still fail → Phase C.

## Phase C (last resort; only if A and B both fail)

### Step C-1: launchd plist for both crons

```xml
<!-- ~/Library/LaunchAgents/ai.anicca.wallet-balance.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>ai.anicca.wallet-balance</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string><string>-lc</string>
    <string>bash $HOME/.openclaw/skills/anicca-wallet/scripts/balance.sh 2>&amp;1 | tee /tmp/wallet.log; curl -s -X POST -H "Content-Type: application/json" --data "{\"text\":\"$(tail -3 /tmp/wallet.log | jq -Rsa .)\"}" "$SLACK_WEBHOOK_URL"</string>
  </array>
  <key>StartCalendarInterval</key>
  <array>
    <dict><key>Hour</key><integer>0</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Hour</key><integer>6</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Hour</key><integer>12</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Hour</key><integer>18</integer><key>Minute</key><integer>0</integer></dict>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>HOME</key><string>/Users/anicca</string>
    <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
  </dict>
  <key>StandardOutPath</key><string>/Users/anicca/.openclaw/logs/wallet-balance.out.log</string>
  <key>StandardErrorPath</key><string>/Users/anicca/.openclaw/logs/wallet-balance.err.log</string>
</dict>
</plist>
```

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.anicca.wallet-balance.plist
launchctl kickstart -k gui/$(id -u)/ai.anicca.wallet-balance
```

### Step C-2: disable OpenClaw cron entries

```python
for j in data["jobs"]:
    if j["id"] in ("d4036615-…", "1730c972-…"):
        j["enabled"] = False
        j["description"] += " [migrated to launchd 2026-06-04]"
```

## Phases D-F (out of scope this session, queued)

- D: anicca-cron-doctor skill (= self-heal nightly)
- E: spec → plan → impl for 234 cron path migration
- F: OpenClaw upstream PR for refusal-as-error classification
