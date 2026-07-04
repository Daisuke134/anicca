---
name: ci-failure-triage
description: Classify a CI failure (logs + commit + repo state) as flake, infra, real-break, or dep and emit a typed runx.ci.triage.v1 routing packet for a downstream issue-intake run. Read-only: opens no item, reruns nothing, pages no one.
source:
  type: cli-tool
  command: node
  args:
    - run.mjs
  timeout_seconds: 30
  sandbox:
    profile: readonly
    cwd_policy: skill-directory
inputs:
  logs:
    type: string
    required: true
    description: Raw CI failure output (build/test logs) to classify.
  commit:
    type: string
    required: false
    description: Commit SHA under test, for provenance in the packet.
  repo_state:
    type: string
    required: false
    description: Short repo state hint (clean/dirty/unknown).
  min_confidence:
    type: string
    required: false
    description: escalation_policy.min_confidence; below this the run refuses (needs_agent).
runx:
  category: ops
  input_resolution:
    required:
      - logs
---

# ci-failure-triage

CI failure triage is the first decision in incident response: a fast wrong call
creates noise, and a slow right call burns the production window. This skill
reads a CI failure and makes exactly one call, with cited evidence, so the next
governed step starts from a typed decision instead of a raw log dump.

## What it does

Given the failure `logs` (plus optional `commit` and `repo_state`) and a
`min_confidence` threshold, it classifies the failure as one of:

| verdict | meaning | consequence emitted |
| --- | --- | --- |
| `real-break` | a code defect visible in the logs | routing decision -> `issue-to-pr` |
| `dep` | a dependency / resolution failure | routing decision -> `issue-to-pr` |
| `infra` | runner / network / disk / daemon failure | read-only operator page note |
| `flake` | known-flaky / intermittent, dominant signal | read-only rerun verdict |

The output is a typed `runx.ci.triage.v1` packet:

```json
{
  "schema": "runx.ci.triage.v1",
  "classification": { "verdict": "real-break", "confidence": 0.9, "evidence_refs": ["log:L2", "log:L3"] },
  "routing_decision": { "recommended_lane": "issue-to-pr", "rationale": "..." },
  "handoff": { "seam": "dispatch-by-naming", "downstream": ["issue-intake", "issue-to-pr", "pr-review-note"] }
}
```

## Boundaries (why an operator can trust it)

- **Read-only.** It opens no tracking item, reruns no CI, and pages no operator.
  It produces a classification and a routing decision; a separate
  `issue-intake` / `issue-to-pr` / `pr-review-note` run is the governed
  commencement gate.
- **Evidence-bound.** Every verdict cites the exact log lines (`log:L<n>`) it is
  based on. It refuses to assert a root cause that is not visible in the
  supplied logs.
- **It refuses when it should.** Empty logs, truncated logs, no decisive signal,
  or a computed confidence below `min_confidence` all block the run for a human
  lane (`needs_agent`) and emit no routing.

## Inputs

- `logs` (required): the raw build/test output of the failed CI run.
- `commit` (optional): commit SHA under test, recorded for provenance.
- `repo_state` (optional): short hint such as `clean`, `dirty`, `unknown`.
- `min_confidence` (optional, default `0.6`): refuse below this confidence.

## Output

A single `runx.ci.triage.v1` packet on stdout with `classification` and exactly
one of `routing_decision`, `rerun_verdict`, or `page_note`.

## Harness

Two locked cases (`runx harness .`):

- `real_break_clear_logs` -> sealed, `verdict: real-break`, lane `issue-to-pr`.
- `ambiguous_truncated_logs` -> refused (`needs_agent`), no routing.
