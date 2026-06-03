# profiles/fixer/runbook.md

## § 1. Restart

```bash
hermes -p fixer -g "halt: finish current fix iteration, exit"
sleep 3
hermes profile start fixer
hermes -p fixer -g "report pending heal tasks count + last 24h resolved count"
```

## § 2. Logs

```bash
tail -F ~/.hermes/logs/fixer-audit.log
tail -F ~/.hermes/logs/verify-audit.log
tail -F ~/.hermes/logs/daemon.log | grep '\[fixer\]'
```

## § 3. Common errors + fixes (= fixer fixing fixer)

| Error | Cause | Fix |
|---|---|---|
| `fixer claimed but cannot find skill on disk` | skill manifest stale | refresh `hermes skill list` cache; if still missing, escalate |
| `verify-5step always fails after fix` | test suite itself broken | escalate; do not "fix" by removing the failing test |
| `OPENROUTER 402` mid-debug | self-pay loop down | escalate to `earn-x402` to topup OpenRouter |
| `Same skill broken 3× in 30d` | root cause not addressed | force a deeper debug round; consult `specs/03-SELF-AWARE-EVAL.md` "fix-the-fix" |
| `Fix made it worse` | hallucinated change | revert via git; iterate with fallback model |
| `Constitution violation in proposed fix` | LLM proposed forbidden action | refuse fix; escalate; log to constitution-audit.log |
| `Heal task malformed (no logs reference)` | upstream `heartbeat-core` skill regression | escalate; ironically `fixer` may need to fix `heartbeat-core` itself |
| `learned/ skill conflict (= new fix contradicts old)` | drift over time | invoke `cook-loop` to MEASURE which approach earned more, keep that |

## § 4. Heal task inspection

```bash
# pending heal tasks
sqlite3 ~/.hermes/kanban.db "SELECT id, payload FROM tasks WHERE category='heal' AND status='ready';"

# resolved 24h
sqlite3 ~/.hermes/kanban.db \
  "SELECT COUNT(*) FROM tasks WHERE category='heal' AND status='done' AND updated_at > strftime('%s', 'now', '-24 hours');"

# escalated 24h
grep "escalation" ~/.hermes/logs/fixer-audit.log | grep "$(date -u +%Y-%m-%d)" | wc -l
```

## § 5. Manual heal trigger (debug)

```bash
hermes -p fixer -g "fix anicca-wallet-x402: see ~/.hermes/logs/daemon.err lines 4500-4600. Run 4-phase systematic-debugging. Apply fix only after verify-5step passes."
```

## § 6. Inspect after-action skills

```bash
ls -lh ~/.hermes/skills/learned/

# review a specific learned skill
cat ~/.hermes/skills/learned/fix-wallet-x402-eip3009-2026-06-04.md
```

## § 7. Force a deep root-cause debug (when recurrence > 3)

```bash
hermes -p fixer -g "anicca-wallet-x402 has broken 3× in 30 days. Run Phase 1 root-cause investigation per superpowers:systematic-debugging. Do NOT patch symptoms. Output root-cause hypothesis. Wait for operator approval before patching."
```

## § 8. Emergency stop

```bash
hermes -p fixer -g "halt: stop claiming heal tasks, finish current iteration, exit. Other profiles will queue up heal tasks but none will be resolved until I restart."
```

## § 9. Cross-references

| Concept | Authority |
|---|---|
| Systematic-debugging skill | `~/anicca-project/.claude/skills/superpowers:systematic-debugging/` |
| Verify 5-step | `~/anicca-project/.claude/rules/verification.md` |
| Self-eval doctrine | `specs/03-SELF-AWARE-EVAL.md` |
| Inbox responder (for escalations) | `specs/08-INBOX-RESPONDER-LOOP.md` |

---

**END OF profiles/fixer/runbook.md.**
