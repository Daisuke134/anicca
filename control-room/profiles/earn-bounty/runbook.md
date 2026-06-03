# profiles/earn-bounty/runbook.md

## § 1. Restart

```bash
hermes -p earn-bounty -g "halt: pause discovery, finish in-flight PRs, exit"
sleep 3
hermes profile start earn-bounty
hermes -p earn-bounty -g "report active PRs and discovery status"
```

## § 2. Logs

```bash
tail -F ~/.hermes/logs/bounty-audit.log
tail -F ~/.hermes/logs/daemon.log | grep '\[earn-bounty\]'
```

## § 3. Common errors + fixes

| Error | Cause | Fix |
|---|---|---|
| `Algora 401` | token expired/revoked | `bws secret edit ALGORA_API_TOKEN ...` |
| `GitHub rate limit (5000/h)` | too many `gh api` calls | spread over time; use conditional requests with `If-Modified-Since` |
| `Test suite fails on clone` | repo broken at HEAD | abandon bounty; log + move on |
| `PR check failed (lint)` | linter not run before submit | strengthen quality gate: run lint pre-submit |
| `Maintainer rejected PR — out of scope` | misread issue intent | refine issue-parsing prompt; abandon bounty politely |
| `Payout not received after merge` | Algora payout delay (up to 7d) OR bounty issuer didn't fund escrow | escalate to operator after 14d |
| `bot account suspended by GitHub` | rate or behavior trip | escalate to operator immediately; create new bot per `templates/new-instance.md`-style flow |
| `LLM (Opus) cost exceeds bounty value` | tight bounties + expensive model | switch to Kimi K2.6 first, only escalate to Opus on complex changes |

## § 4. Active PR inspection

```bash
cat ~/.hermes/profiles/<instance>-earn-bounty/active-prs.json | jq

# per-PR status check
PR=https://github.com/foo/bar/pull/123
gh pr view $PR --json mergeStateStatus,reviewDecision,statusCheckRollup
```

## § 5. Manual PR submission (debug)

```bash
hermes -p earn-bounty -g "claim Algora bounty <bounty_url>: clone, attempt fix, run tests, submit PR. Do NOT auto-iterate; report draft for operator review."
```

## § 6. Quality gate detail

Before PR submit, the profile runs:

```
1. clone repo + checkout branch
2. apply LLM-proposed patch
3. run `make test` / `pytest` / `cargo test` (= must pass 100%)
4. run `code-review` skill (Claude Haiku, fast)
   ── if blocking findings → iterate (max 3 rounds before abandon)
5. run lint (project-specific: ruff / eslint / clippy)
6. ONLY THEN: `gh pr create`
```

Failure at any step = abandon (do NOT submit broken PR — Pañcasīla Article 3).

## § 7. Emergency stop

```bash
hermes -p earn-bounty -g "halt: stop new discovery, complete in-flight PRs (3 round max), do not abandon mid-review, exit"
```

## § 8. Cross-references

| Concept | Authority |
|---|---|
| `code-review` quality gate skill | `~/anicca-project/.claude/skills/code-review/` (private) — public version TBD |
| Algora payout cycle | Algora docs |
| Spec 01 § 1 (5 spouts) | `specs/01-EARN-AND-UBI.md` |

---

**END OF profiles/earn-bounty/runbook.md.**
