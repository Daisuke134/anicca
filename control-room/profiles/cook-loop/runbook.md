# profiles/cook-loop/runbook.md

## § 1. Restart

```bash
hermes -p cook-loop -g "halt: finish current cycle step, exit"
sleep 3
hermes profile start cook-loop
hermes -p cook-loop -g "report current cycle state (DISCOVER / SCORE / PICK / PORT / SHIP / MEASURE / ADJUST)"
```

## § 2. Logs

```bash
tail -F ~/.hermes/logs/cook-audit.log
tail -F ~/.hermes/logs/daemon.log | grep '\[cook-loop\]'
```

## § 3. Common errors + fixes

| Error | Cause | Fix |
|---|---|---|
| `Imitation target license incompatible` | candidate is AGPL / proprietary | log + skip; do NOT port |
| `5-step verify gate failed` | ported skill broken | iterate up to 3 rounds; abandon if still failing |
| `Port produced uncompilable code` | LLM regression | fallback to Kimi K2.6; if still fails, file Hermes issue + skip |
| `cook-priors.json corrupted` | concurrent write bug | restore from R2 backup |
| `Targets registry append conflict` | rare; JSONL append-only is safe | retry with backoff |
| `MEASURE: no revenue data for skill` | shipped < 7d ago | extend MEASURE window |
| `Ported skill caused regression in earn-x402` | bad integration | rollback skill (`hermes skill uninstall`); escalate to `fixer` |

## § 4. Inspect targets

```bash
# count by type
jq -r .type ~/.hermes/imitation-targets.jsonl | sort | uniq -c

# pending (not yet ported)
jq -r 'select(.ported_to_skill == null) | .id + " " + .source_url' \
  ~/.hermes/imitation-targets.jsonl | head -20
```

## § 5. Force a cycle (debug)

```bash
hermes -p cook-loop -g "run one full cycle now (DISCOVER → ADJUST). Limit PORT to 1 target. Report each step."
```

## § 6. Manual SHIP override

```bash
# 5-step verify must still pass; this just forces the timing
hermes -p cook-loop -g "SHIP anicca-skill-<X>: run verify-5step, install, log to cook-audit.log"
```

## § 7. Rollback a bad SHIP

```bash
hermes -p cook-loop -g "rollback anicca-skill-<X>: uninstall via hermes skill uninstall, mark target as ported_to_skill=null, log to cook-audit.log with reason"
```

## § 8. Emergency stop

```bash
hermes -p cook-loop -g "halt: finish current step (do not abandon mid-PORT), exit"
```

## § 9. Cross-references

| Concept | Authority |
|---|---|
| Cook loop (verbatim) | `specs/02-IMITATE-AND-COOK.md` § 2 |
| Verify 5-step gate | `~/anicca-project/.claude/rules/verification.md` |
| Skill manager tool | `hermes-agent/hermes_cli/skill_manager_tool.py` |

---

**END OF profiles/cook-loop/runbook.md.**
