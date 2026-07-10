# Profitable-Claude CEO / Life Manager Goal Handover（2026-07-10 09:22 JST）

## Full To-Be ASCII

```text
github.com/Daisuke134/profitable-claude
        |
        v
===============================================================
|                    STARTABLE LOOP REPO                      |
|  clone -> env -> start-all -> status -> evidence mail        |
===============================================================
        |
        +-- bin/start-all.sh
        +-- bin/status.sh
        +-- config/loop-registry.json
        +-- config/ceo-budget-config.json
        +-- ledgers/cost-events.jsonl
        +-- ledgers/loop-evaluations.jsonl
        +-- ledgers/ceo-decisions.jsonl
        +-- ledgers/lessons.jsonl
        |
        v
===============================================================
|                         CEO LOOP                            |
| company portfolio manager                                   |
===============================================================
| reads: each loop cadence / evidence / real revenue / cost    |
|        Claude local token runway / disk / process health     |
| writes: pause / reduce / normal / double_down / spawn        |
|        pass_frequency_multiplier / capital_cap_usd           |
===============================================================
        |
        +------------------------------------------------------+
        |                                                      |
        v                                                      v
============================                       ============================
| MANAGER BUSINESS LOOPS   |                       | EXPLORER LOOP           |
============================                       ============================
| gig                       |                       | pain-point intake       |
| bounty                    |                       | same-day validation     |
| affiliate                 |                       | evidence artifact       |
| video                     |                       | CEO proposal            |
| article                   |                       ============================
| pm / hl trade             |
| capafy                    |
| life-manager              |
============================
        |
        v
Each manager loop owns:
  - domain action
  - search + metrics self-improve
  - self-heal
  - deterministic ledgers
  - evidence mail
  - lessons.jsonl
  - business summary to CEO

life-manager loop
        |
        v
github.com/Daisuke134/life-manager
        |
        v
Telegram + Calendar + Gmail + Phone + Stripe cloud product
        |
        v
product dev + self-heal + product marketing + feedback-to-issue
```

## Current Reality

`profitable-claude` currently has only the startable skeleton: `README.md`, `bin/start-all.sh`,
`bin/status.sh`, `skills/human-funded/README.md`, and documented bounty/affiliate/gig loops.
The full CEO loop, Life Manager business loop, explorer loop, and capafy/article/pm/hl wiring are not
fully present there yet.

Life Manager seed product issues already exist:

- https://github.com/Daisuke134/life-manager/issues/1
- https://github.com/Daisuke134/life-manager/issues/2
- https://github.com/Daisuke134/life-manager/issues/3
- https://github.com/Daisuke134/life-manager/issues/4
- https://github.com/Daisuke134/life-manager/issues/5
- https://github.com/Daisuke134/life-manager/issues/6
- https://github.com/Daisuke134/life-manager/issues/7
- https://github.com/Daisuke134/life-manager/issues/8
- https://github.com/Daisuke134/life-manager/issues/9

Agent-economy context is separate work in `~/anicca`: spawn phase 3 still needs re-review dispatch;
spawn identity VCSDD state needs reconciliation; harness-tooluse-health iteration-4 verdict path was
not found; lending is complete. Franklin LaunchAgent is running with `ANICCA_SPAWN_SAFETY_MARGIN=1.5`
and `free/glm-4.7` model vars. `~/.hermes/state/citizens.json` still equals seed Franklin only.
`citizens-diff-monitor` was restarted; pid is in `~/.hermes/state/citizens-diff-monitor.pid`.

## Compact /goal For Next Claude

```text
/goal `github.com/Daisuke134/profitable-claude` becomes the startable CEO-managed claude-p loop company: `bin/start-all.sh` and `bin/status.sh` expose every managed loop, CEO reads real per-loop cadence/evidence/revenue/cost/runway, writes enforceable pause/reduce/normal/double_down/spawn allocation, and Life Manager runs as one business loop under CEO that improves and markets `github.com/Daisuke134/life-manager` via real GitHub issues and evidence. Read first: this handover, `docs/superpowers/specs/2026-07-08-claude-p-loop-verification-evidence-design.md`, `docs/superpowers/specs/2026-07-10-life-manager-autopilot-product-loop-design.md`, `/Users/anicca/profitable-claude`, `/Users/anicca/Projects/life-manager`; discover adjacent tests/docs as needed.

Done requires machine-checkable evidence: `profitable-claude` has `config/loop-registry.json`, `config/ceo-budget-config.json`, `ledgers/cost-events.jsonl`, `ledgers/loop-evaluations.jsonl`, `ledgers/ceo-decisions.jsonl`, `ledgers/lessons.jsonl`, `bin/ceo-status.sh`, a CEO runner, and deterministic registry enforcement for pause/reduce/double_down; `start-all.sh`/`status.sh` include current loops, at minimum bounty/affiliate/gig plus explicit entries or VCSDD stubs for life-manager, explorer, capafy, article, pm/hl; Life Manager has `skills/human-funded/life-manager/` runner/healthcheck/README/cadence/evidence/report wiring, reads or creates product issues in `Daisuke134/life-manager`, writes feedback/issues/calendar/phone/event/marketing/api-cost/stripe/lessons ledgers, and reports MRR/cost/cadence/evidence/evaluation summary to CEO; explorer either works with pain-point intake -> same-day validation -> CEO proposal artifact, or has an open VCSDD feature proving why it is not LIVE yet.

Verification: run the repo's relevant tests plus `bash bin/status.sh`, `bash bin/ceo-status.sh`, registry enforcement checks for at least paused and normal loops, grep/list checks proving cadence contracts and all managed loops are wired, and evidence-mail/log checks with non-empty evidence or honest `none:<reason>`. For Life Manager, verify the 9 seed issues exist in `Daisuke134/life-manager`, at least one feedback-to-issue path produces a valid issue/update with source/evidence/success_metric, and no fake calendar events, applications, URLs, revenue, or metrics are claimed. If revenue is zero, report zero. Use full VCSDD for code changes; do not weaken/delete required checks; keep an execution-notes file with open items and evidence. Constraints: all cores stay Sonnet unless a verifier/adversary explicitly requires Opus; no submodules, use polyrepo+vendor/copy; use Firecrawl CLI for web search and Context7 CLI for docs/library lookup; no human-in-loop request to Dais; do not implement MAIN/Agent Economy in this run, only record its context. Block only if required credentials/services are unavailable, the same validation fails after three distinct fixes, or a production/billing/auth/schema decision is needed; report exact blocker and smallest next check.
```

