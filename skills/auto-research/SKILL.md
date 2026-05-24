---
name: auto-research
description: Top-level orchestrator that chains the AutoResearchClaw chassis with K-Dense (literature + hypothesis + writeup), Sakana (debate, BFTS branch selection, multi-{{profile.lateness.stakeholders.senderType}} writeup) and Karpathy (refinement) into a daily research-production pipeline. Reads `projects.yaml` (4 seeded topics: AI Entity GDP / Oogiri-bench / AI Responsibility / AI Mindfulness) and round-robins one project per cron run. Submits to arXiv and (weekly) to apply-to-funder. Use when triggered by `auto-research-{literature,hypothesise,experiment,write,grant}` crons or manually with `MODE=<{{profile.lateness.stakeholders.senderType}}> bash scripts/run.sh`.
metadata:
  tags: research, k-dense, sakana, karpathy, autoresearchclaw, arxiv, openalex, bfts, grants
  requires:
    bins: [python3, bash, jq, docker, quarto]
    skills: [apply-to-funder, scientific-writing, literature-review, peer-review]
    chassis: [~/.openclaw/workspace/AutoResearchClaw]
    env: [OPENALEX_EMAIL]
  invariants:
    - Experiments run inside Docker sandbox with no network and a 30-min wallclock; per-project resource ceilings enforced.
    - Any project carrying `human_flags ∈ {wet-lab, expensive-compute, external-data, {{profile.lateness.stakeholders.senderType}}-review}` MUST receive Slack ack before the experiment cron runs.
    - Every citation in a draft is OpenAlex-validated by DOI or arXiv ID; missing → draft held.
    - DRY_RUN=true (env AUTO_RESEARCH_DRY_RUN=true) prints the plan and never invokes K-Dense / Sakana / Docker.
    - Round-robin index lives at ~/.openclaw/workspace/auto-research/.cursor.json — atomic update per run.
---

# auto-research — orchestrator skill

The chassis (AutoResearchClaw) implements the long pipeline. K-Dense, Sakana and Karpathy are reusable
modules. This skill is the **conductor**: each cron invokes one {{profile.lateness.stakeholders.senderType}} on one project, then advances the
round-robin cursor.

## Architecture

```
projects.yaml  ──►  scripts/run.sh  ──►  one {{profile.lateness.stakeholders.senderType}} script  ──►  module call
                                              ├─ literature-pull.py     → K-Dense paper-lookup + database-lookup
                                              ├─ hypothesise.py         → K-Dense hypothesis-generation + Sakana debate
                                              ├─ experiment-bfts.py     → Sakana BFTSManager (Stage 15)
                                              ├─ run-local.sh           → Docker sandbox
                                              ├─ draft-paper.py         → Sakana writeup → AutoResearchClaw chassis Stage 17
                                              └─ draft-grant.py         → apply-to-funder
```

## Modes

```bash
MODE=literature   bash scripts/run.sh   # 01:00 JST
MODE=hypothesise  bash scripts/run.sh   # 02:00 JST
MODE=experiment   bash scripts/run.sh   # 03:00 JST
MODE=write        bash scripts/run.sh   # 04:00 JST
MODE=grant        bash scripts/run.sh   # 05:00 JST Mon
```

`AUTO_RESEARCH_DRY_RUN=true` short-circuits every heavy call (K-Dense, Sakana, Docker, network) and
prints what would have happened.

## Round-robin

`.cursor.json` stores `{ "next_index": <int>, "last_run": "<iso>" }`. Each run reads the cursor, picks
`projects[cursor.next_index % len(projects)]`, runs the {{profile.lateness.stakeholders.senderType}}, then writes cursor+1 atomically.

## projects.yaml schema

```yaml
projects:
  - id: <stable-slug>
    title: "..."
    description: "..."
    arxiv_categories: [<cat>, ...]
    target_venues: [<venue>, ...]
    human_flags: []   # any of: wet-lab, expensive-compute, external-data, {{profile.lateness.stakeholders.senderType}}-review
```

## Human-flag gate

Before invoking `experiment-bfts.py`, the orchestrator checks `human_flags`. If the list intersects
`{wet-lab, expensive-compute, external-data, {{profile.lateness.stakeholders.senderType}}-review}`, it writes a Slack ack request to
`workspace/auto-research/acks/<project>.pending` and **exits without running the experiment**. The
agent layer posts to Slack; only after Slack reaction creates `<project>.ack` does the next experiment
cron actually invoke the BFTS path.

## OpenAlex citation gate

`draft-paper.py` runs every DOI / arXiv ID in the draft through the OpenAlex API
(`https://api.openalex.org/works/doi:<DOI>` or `works/https://arxiv.org/abs/<ID>`). Failures block the
arXiv submitter from running.

## Sandbox (run-local.sh)

Wraps `docker run --rm --network=none --memory=4g --cpus=2 --pids-limit=512 --ulimit cpu=1800 ...`
against the experiment image specified per-project (default `ghcr.io/sakana-ai/research-sandbox:latest`).
Wallclock 30 min. No network. Exit non-zero if image absent.

## Outputs

```
~/.openclaw/workspace/auto-research/
  .cursor.json
  literature/<topic>/<date>.json
  hypotheses/<topic>/<date>.json
  experiments/<topic>/<date>/{plan.json, results.json, logs/}
  papers/<topic>/<date>/{draft.md, draft.pdf, citations.openalex.json}
  grants/<topic>/<date>/{funder, submission.json}
  acks/<topic>.pending
  acks/<topic>.ack
```

## Crons (5)

| name | schedule (JST) | mode |
|---|---|---|
| `auto-research-literature` | `0 1 * * *` | `literature` |
| `auto-research-hypothesise` | `0 2 * * *` | `hypothesise` |
| `auto-research-experiment` | `0 3 * * *` | `experiment` |
| `auto-research-write` | `0 4 * * *` | `write` |
| `auto-research-grant` | `0 5 * * 1` | `grant` |

All use `delivery.mode: announce → channel:{{profile.channels.reportChannel}}`.

## Open issues / host requirements

- **Docker** must be running on the host for `experiment` mode; otherwise `run-local.sh` returns 127.
- **Quarto** is required by `draft-paper.py` for the Quarto render hop; see naist skill for the same caveat.
- AutoResearchClaw chassis location is hardcoded to `~/.openclaw/workspace/AutoResearchClaw`. K-Dense
  and Sakana modules are imported from there (`researchclaw.literature`, `researchclaw.knowledge`,
  `researchclaw.experiment`, `researchclaw.paper_generation`, `researchclaw.pipeline.karpathy_refine`,
  `researchclaw.pipeline.{{profile.lateness.stakeholders.senderType}}_impls._execution` for BFTS Stage 15, `researchclaw.pipeline.{{profile.lateness.stakeholders.senderType}}_impls._paper_writing` for Stage 17).
- **OPENALEX_EMAIL** env should be set so OpenAlex puts you in the polite-pool rate limit.
