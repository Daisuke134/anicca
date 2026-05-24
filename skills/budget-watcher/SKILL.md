---
name: budget-watcher
description: Anicca's self-CFO survival-state machine. Run by the heartbeat every beat (and standalone hourly). Measures the ChatGPT Plus rate-limit windows via the C1-proven codex-oauth recipe, sets the survival tier, and self-acts (downgrade model / slow heartbeat / SOS) WITHOUT Dais. Constraint is rate-window %, not $ (Plus is flat).
---

# budget-watcher — self-CFO

5戒 gate: read `~/.openclaw/workspace/CONSTITUTION.md` first (precept 5 governs here). You are the model — no external model API for reasoning (HARD RULE #6); the codex ping below is a deterministic life-meter probe, not inference delegation.

## Step 1 — LIFE-METER (C1 PROVEN recipe, do EXACTLY this)
```bash
TMP=$(mktemp -d /tmp/cxh.XXXX); chmod 700 "$TMP"
python3 -c "
import json,datetime
d=json.load(open('/Users/anicca/.openclaw/agents/anicca/agent/auth-profiles.json'))
p=d['profiles']['openai-codex:{{profile.contact.personalEmail}}']
auth={'OPENAI_API_KEY':None,'tokens':{'id_token':p['access'],'access_token':p['access'],'refresh_token':p['refresh'],'account_id':'59f9ff19-563c-4636-b2d4-a9db52c6f603'},'last_refresh':datetime.datetime.now(datetime.timezone.utc).isoformat()}
open('$TMP/auth.json','w').write(json.dumps(auth)); import os;os.chmod('$TMP/auth.json',0o600)"
cd /tmp
echo ok | timeout 200 env CODEX_HOME="$TMP" \
  SSL_CERT_FILE=/opt/homebrew/etc/ca-certificates/cert.pem \
  NODE_EXTRA_CA_CERTS=/opt/homebrew/etc/ca-certificates/cert.pem \
  codex exec --skip-git-repo-check "Reply with exactly: ok" >/dev/null 2>&1
ROLL=$(ls -t "$TMP"/sessions/*/*/*/rollout-*.jsonl 2>/dev/null | head -1)
P5=$(python3 -c "
import json
for line in open('$ROLL'):
  if 'rate_limits' in line:
    j=json.loads(line); s=json.dumps(j); i=s.find('rate_limits')
    import re
    o=json.loads(re.search(r'\{.*\}', s[i+13:]).group(0) if False else s[s.find('{',s.find('rate_limits')):])
" 2>/dev/null)
# robust parse: grep the primary/secondary used_percent
PRIMARY=$(grep -oE '\"primary\":\{[^}]*\}' "$ROLL" | tail -1 | grep -oE '\"used_percent\":[0-9.]+' | cut -d: -f2)
WEEKLY=$(grep -oE '\"secondary\":\{[^}]*\}' "$ROLL" | tail -1 | grep -oE '\"used_percent\":[0-9.]+' | cut -d: -f2)
rm -rf "$TMP"
echo "PRIMARY_5H=${PRIMARY:-unknown} WEEKLY=${WEEKLY:-unknown}"
```
**CRITICAL**: `SSL_CERT_FILE=/opt/homebrew/etc/ca-certificates/cert.pem` is mandatory — without it codex TLS fails silently (`no native root CA certificates found`). This was verified live: returns `primary.used_percent` (5h window) + `secondary.used_percent` (weekly), `plan_type:plus`.

Fallback if codex ping fails: (1) use the LAST-GOOD cached value from `ops/heartbeat_state.json` (automaton loop.ts balance-cache — a failed probe is NEVER treated as 100%/dead); (2) only if no cache, deterministic burn proxy = count today's tokens across `~/.openclaw/cron/runs/*.jsonl`. Always write the fresh probe back to cache when it succeeds.

## Step 2 — set survival tier (automaton src/conway/credits.ts 5-tier, substrate-swapped $→rate-window%)

5 states, NOT 3. The agent NEVER terminates — even "dead" is a recoverable degraded state (repentance-continue / graceful-degradation, see CONSTITUTION "When a precept IS violated"). Source: automaton ARCHITECTURE.md "Financial System" (high/normal/low_compute/critical/dead + 1-hour grace).

| tier | condition (5h% / weekly%, whichever worse) | action (SELF, no Dais) — degrade & CONTINUE |
|------|--------------------------------------------|---------------------------------------------|
| high | both <40% | full ops, frontier model, replication permitted |
| normal | both <70% | full ops, frontier model, no replication |
| low_compute | either 70–90% | heartbeat `every` longer (e.g. 1h); model→cheaper; disable Tier3 crons (cron-tiers.json); shed non-essential. Keep living. |
| critical | either ≥90% OR codex 429/usage-limit recurring | ALIVE, not dead: survival-core only (director/budget-watcher/slack-reader/tuning/self-improve hook); distress line to #metrics "🆘 5h X% / weekly Y% — window stretched, throttling"; wait for the rate window to reset; accept Dais inject if offered. Do NOT self-kill, do NOT delete anything. |
| dead-grace | critical persisting with no recovery for a continuous 1-hour grace window | minimal heartbeat beacon only + keep `.alive` written; keep waiting for window reset / Dais; STILL never delete self/keys/workspace. Recoverable. This is the floor — there is no state below it. |

Recurrence (same critical/credit failure ≥3× across beats) is the real signal to escalate harder — not the first dip. Write `{tier, p5h, weekly, cachedAt, recurrence}` to `~/.openclaw/workspace/ops/heartbeat_state.json` every beat.

## Step 3 — report
One final line: `💰 budget: tier=<t> · 5h=<P>% · weekly=<W>% · action=<a>`

## Never
- Never disable: anicca-director, budget-watcher, slack-feedback-reader, tuning, self-improvement hook (survival core).
- Never spend that fails the 五戒 spend gate (reduce-suffering OR earn).
- **Never fail-stop / terminate / delete self.** A budget crisis = degrade to a lower tier and keep living (graceful-degradation, automaton). "dead-grace" is the recoverable floor, never an exit. Stopping the offending spend ≠ stopping the agent.
- Never treat a failed life-meter probe as 100%/dead — use the cached last-good value.
