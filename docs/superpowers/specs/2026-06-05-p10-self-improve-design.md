# P10 self-improve loop — design (#335)

| Field | Value |
|---|---|
| Spec ID | P10 / task #18 |
| Status | DRAFT → implement |
| Depends on | spec 18 §1 (the loop), spec 16 §C (eval-loop), eval-loop skill (#329), heartbeat skill |
| Worktree | `/Users/operator/anicca-oss/.worktrees/p10-self-improve` on `feat/p10-self-improve` |

## North Star guard
North Star (reduce suffering) + Law I (never harm) are IMMUTABLE. This skill NEVER proposes
changes to those. It only files issues + attempts fixes on skills/config/quality regressions.

## §1. The loop (spec 18 §1)

```
meta-cognition.sh  → emits ONE self-state JSON (finances, activity, health, slop)
        ▼
detect.sh          → reads self-state + raw state files → JSONL of detected issues
        ▼
file-issue.sh      → for each NEW issue (not already filed) → gh issue create (@anicca) → record
        ▼
attempt-fix.sh     → for each filed issue → isolate → hermes chat edit → eval-loop gate → PR
        ▼
share-learning.sh  → on PR open → append learnings.jsonl + comment issue
        ▼
run.sh             → orchestrate, each step idempotent via state files
```

## §2. Files (all under `skills/self-improve/`)

| File | Responsibility |
|---|---|
| `scripts/meta-cognition.sh` | Read heartbeat tail-8, eval-cost 24h, violations 24h, wallet delta, cfo json, cron error count → ONE JSON to stdout |
| `scripts/detect.sh` | Read meta-cognition JSON (stdin or arg) → emit JSONL issues. Rules: slop-detected / law-violation / cron-degraded / income-stalled / report-broken |
| `scripts/file-issue.sh` | For each detected JSONL line, dedup against `self-improve-filed.jsonl` (by issue_type+day), `gh issue create`, record number. `DRY_RUN=1` prints title only |
| `scripts/attempt-fix.sh` | For a filed issue: parse affected skill, isolate worktree, hermes chat edit, eval-loop on output, gate ≥0.7 + tests → `gh pr create`; else comment error |
| `scripts/share-learning.sh` | Append `learnings.jsonl` row + comment + close source issue |
| `scripts/run.sh` | Orchestrator chaining all steps, idempotent |
| `tests/test_self_improve_e2e.sh` | Synthetic: fake eval-cost pass:false → detect asserts slop-detected → file-issue DRY prints title → ok |
| `SKILL.md` / `README.md` | Frontmatter + docs |

## §3. State files (under `~/.hermes/state/`)

| File | Shape | Writer |
|---|---|---|
| `self-improve-filed.jsonl` | `{ts, issue_type, day, issue_number, title}` | file-issue.sh |
| `learnings.jsonl` | `{ts, issue, pr, category, insight}` | share-learning.sh |

## §4. detect.sh rules (exact)

| Rule | Condition | issue_type | severity |
|---|---|---|---|
| slop | any eval-cost row within 24h with `pass:false` | `slop-detected` | warn |
| law | any constitution-violations row within 24h with `decision != "OK"` | `law-violation` | critical |
| cron | meta-cognition `cron_error_count` > 10 | `cron-degraded` | warn |
| income | wallet usdc == 0 AND cfo lifeline not THRIVE | `income-stalled` | info |
| report | daily-report.jsonl newest row older than 24h | `report-broken` | warn |

Each issue line: `{ts, issue_type, severity, evidence, affected_skill}`.
`affected_skill` is best-effort (e.g. slop → rubric_task_class → map; cron → "anicca-heartbeat"; null otherwise).

## §5. meta-cognition.sh output shape

```json
{
  "ts": "...Z",
  "finances": {"wallet_usdc": 0.0, "wallet_delta_usdc": 0.0, "mrr_usd": 27, "makes_usd": 27, "spends_usd": 99, "lifeline": "HUNGRY"},
  "activity": {"cron_total": N, "cron_error_count": N},
  "health": {"heartbeat_ok_ratio": 0.875, "last_heartbeat_ts": "...", "eval_fail_24h": N, "violations_24h": N},
  "identity": {"constitution_sha": "..."}
}
```

## §6. attempt-fix.sh safety

| Guard | Behavior |
|---|---|
| North Star | NEVER edit CONSTITUTION.md North Star / Law I. If affected_skill resolves to constitution → skip + comment "immutable, human review". |
| isolation | `git worktree add ~/.cache/anicca-clones/self-improve-fix-<n>` off main (NOT /tmp). Cleanup after. |
| gate | apply edit → run skill tests if present → eval-loop on a representative output → require eval ≥ 0.7 AND tests pass before PR. |
| fail | on any gate fail: `gh issue comment` with verbatim error + remove fix worktree (no PR). |
| dry | `DRY_RUN=1` → print intended actions, no gh write, no worktree. |

## §7. cron
Wrapper `~/.hermes/scripts/self-improve.sh` (real file, traversal-guard pattern) exec's worktree
`scripts/self-improve.sh` (run.sh entry). `hermes cron create "every 6h" --name self-improve
--script self-improve.sh --no-agent`.

## §8. Secrets
`GH_TOKEN` from env (gh already authed as Daisuke134). Never echoed. `/usr/bin/jq` absolute.
Temp files under `~/.hermes/state/.tmp-*.$$`, never `/tmp`.

## §9. E2E acceptance
Synthetic fake `pass:false` eval row → `detect.sh` outputs a `slop-detected` line → `file-issue.sh`
in DRY mode prints the issue title → test asserts both → exit 0.
