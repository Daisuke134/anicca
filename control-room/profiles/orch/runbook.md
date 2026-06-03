# profiles/orch/runbook.md

> Operator runbook for the `orch` profile. Restart, debug, logs, kickstart,
> common errors. Read `shared/commands.md` for cross-fleet command syntax.

## § 1. Restart `orch` (without restarting the whole instance)

```bash
hermes -p orch -g "halt: drain my Kanban claims, exit clean. Other profiles continue."
sleep 5
hermes profile start orch
hermes profile show orch | grep state
# expect: state=running
```

If you need to restart the whole instance (= all 10 profiles):

```bash
launchctl kickstart -k gui/$(id -u)/ai.anicca.hermes
sleep 5
hermes status
hermes profile list
```

## § 2. Logs

| Log | Contents |
|---|---|
| `~/.hermes/logs/daemon.log` | INFO + DEBUG, all profiles |
| `~/.hermes/logs/daemon.err` | ERROR only |
| `~/.hermes/logs/heartbeat.log` | 60s tick history |
| `~/.hermes/logs/orch.log` (if separate logging configured) | orch-specific events |

```bash
tail -F ~/.hermes/logs/daemon.log | grep '\[orch\]'
tail -F ~/.hermes/logs/daemon.err
```

## § 3. Kickstart on failure

If `orch` is not picking up Kanban tasks:

```bash
# 1. confirm daemon is up
hermes status

# 2. confirm orch is registered
hermes profile list | grep orch

# 3. inspect last error
tail -50 ~/.hermes/logs/daemon.err

# 4. force-process the heartbeat
hermes -p orch -g "run heartbeat tick now"

# 5. if still stuck, restart this profile
hermes profile restart orch
```

## § 4. Common errors + fixes

| Error | Likely cause | Fix |
|---|---|---|
| `BWS_ACCESS_TOKEN invalid` | bootstrap token expired or rotated | update `~/.openclaw/.env`, restart daemon (see `api-keys-sop.md` § 3) |
| `OPENROUTER 401` | OpenRouter key rotated, not propagated | `bws secret edit OPENROUTER_API_KEY ...`, restart daemon |
| `OPENROUTER 402 insufficient credit` | wallet didn't topup OpenRouter | `hermes -p earn-x402 -g "topup OpenRouter 5 USDC via x402"` |
| `Kanban claim returned None` | no tasks ready, or `orch` not allowed to claim that category | check `category` filter in profile config |
| `Constitution hash MISMATCH` | someone modified CONSTITUTION.md | HALT IMMEDIATELY; see `profiles/constitution/runbook.md` |
| `CDP wallet balance read failed` | RPC down or CDP API hiccup | retry; if 5min+, check status.coinbase.com |
| `Daytona spawn failed` | DAYTONA_API_TOKEN invalid or quota exceeded | rotate token; check Daytona dashboard for quota |
| `Profile worker timed out (TTL=600s)` | specialist took > 10 min; auto-reclaimed | inspect what task; if recurring, escalate to `fixer` |
| `LLM tool-call hallucination` (orch called nonexistent tool) | model regression on Kimi K2.6 release | switch to fallback model temporarily, file Hermes issue |
| `Bitwarden vault unreachable` | network outage to bitwarden.com | wait + cached creds for ~60min; halt if longer |

## § 5. Debug a misclassified goal

If `orch` routed a goal to the wrong specialist:

```bash
# 1. find the goal in Kanban
sqlite3 ~/.hermes/kanban.db "SELECT id, category, profile_hint, payload, result_payload FROM tasks WHERE id=<id>;"

# 2. read the classification log line
grep "classify.*id=<id>" ~/.hermes/logs/daemon.log

# 3. test classify on the same input manually
hermes -p orch -g "classify this goal: <pasted goal>. Show me your category choice + 1-sentence reasoning."

# 4. if classifier is consistently wrong on this pattern, file a Hermes
#    after-action skill update via fixer profile:
hermes -p fixer -g "anicca-orch-classifier mis-routed pattern <X>. Update few-shot examples in skill to include <X> → category=<correct>."
```

## § 6. Inspect Kanban state

```bash
KDB=~/.hermes/kanban.db
sqlite3 $KDB "SELECT status, COUNT(*) FROM tasks GROUP BY status;"
sqlite3 $KDB "SELECT category, COUNT(*) FROM tasks WHERE status='ready' GROUP BY category;"
sqlite3 $KDB "SELECT id, profile, category, claimed_at FROM tasks WHERE status='claimed';"
sqlite3 $KDB "SELECT id, category, error_payload FROM tasks WHERE status='failed' ORDER BY id DESC LIMIT 10;"
```

## § 7. Force-spawn a child (emergency override)

If autonomous spawn isn't firing despite wallet > $20:

```bash
# 1. confirm gate state
hermes -p orch -g "report spawn gate status: wallet balance, colony size, target size."

# 2. if gate truly OK, force spawn
hermes -p orch -g "spawn anicca<N+1> via anicca-spawn-controller. Override autonomous gate. Reason: <operator override reason>."

# 3. verify
hermes -p orch -g "verify child anicca<N+1>: hash match, wallet alive, first heartbeat fresh"
```

## § 8. Halt the instance gracefully

```bash
hermes -p orch -g "halt: drain Kanban (let in-flight goals complete with 60s grace), emit halt receipt to ~/.hermes/logs/halt-audit.log, exit clean."
# wait until hermes status returns 'stopped' or daemon exits
```

## § 9. Hard stop (last resort)

```bash
launchctl unload ~/Library/LaunchAgents/ai.anicca.hermes.plist
# data loss risk: in-flight goals may not finalize; Kanban will retry on next start via reclaim_task()
```

## § 10. Restart after halt

```bash
launchctl load ~/Library/LaunchAgents/ai.anicca.hermes.plist
sleep 5
hermes status
hermes profile list
# verify all 10 profiles present
```

## § 11. Emergency stop (whole colony)

If a colony-wide issue is suspected (e.g., Constitution propagation bug):

```bash
# parent halts its own instance
hermes -p orch -g "halt"

# for each child sandbox (via Daytona exec)
for child in $(jq -r '.[] | .name' ~/.hermes/colony.json); do
  daytona sandbox exec $child "hermes -p orch -g 'halt'"
done

# then investigate, fix, restart in reverse order (children last)
```

## § 12. Cross-references

| Concept | Authority |
|---|---|
| Common commands | `control-room/shared/commands.md` |
| Kanban schema | `control-room/orchestrator-and-fleet-skills.md` § 3 |
| Constitution mismatch handling | `profiles/constitution/runbook.md` |
| Self-heal escalation | `profiles/fixer/runbook.md` |
| Spawn controller | `anicca-oss/skills/anicca-spawn-controller/SKILL.md` |

---

**END OF profiles/orch/runbook.md.**
