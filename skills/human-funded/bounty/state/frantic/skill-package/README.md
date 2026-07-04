# ci-failure-triage — a governed [runx](https://runx.ai) skill

A small, **read-only** [runx](https://github.com/runxhq/runx) skill that turns a
raw CI failure into a typed, evidence-cited routing decision. It classifies a
failure as `flake` / `infra` / `real-break` / `dep`, emits a
`runx.ci.triage.v1` packet, and **refuses** when the logs can't support a
confident verdict — so the next governed step (issue-intake / issue-to-pr)
starts from a decision instead of a log dump.

This repo is a complete, runnable [runx](https://runx.ai) skill package
(`SKILL.md` + `X.yaml` + `run.mjs` + fixtures) you can install, run, harness,
and verify yourself.

## Why this is useful

CI triage is the first decision in incident response. A fast wrong call creates
noise; a slow right call burns the production window. This skill makes exactly
**one** call, cites the **exact log lines** behind it, and stays inside a hard
boundary: it opens no tracking item, reruns no CI, and pages no operator. Every
run seals a signed [runx](https://github.com/runxhq/runx) receipt that
`runx verify` can recompute.

## Quickstart

```bash
npm i -g @runxhq/cli           # runx CLI 0.6.13+
git clone https://github.com/Daisuke134/runx-ci-failure-triage
cd runx-ci-failure-triage

# receipt signing keys (any 32-byte ed25519 seed, base64)
export RUNX_RECEIPT_SIGN_KID="demo-key"
export RUNX_RECEIPT_SIGN_ED25519_SEED_BASE64="$(node -e "console.log(require('crypto').randomBytes(32).toString('base64'))")"
export RUNX_RECEIPT_SIGN_ISSUER_TYPE="hosted"
export RUNX_RECEIPT_DIR="$(mktemp -d)"

# 1) lock behaviour with the harness (2 cases)
runx harness "$(pwd)"

# 2) run it on a real failure
runx skill "$(pwd)" \
  --input logs="$(cat fixtures/real_break.log)" \
  --input commit=a1b2c3d4 --input repo_state=clean --input min_confidence=0.6 --json
```

> Note: pass an **absolute** skill path (`"$(pwd)"`) — the current runx CLI does
> not resolve a bare `.` for the skill directory.

## What you get back

```json
{
  "schema": "runx.ci.triage.v1",
  "classification": { "verdict": "real-break", "confidence": 0.9, "evidence_refs": ["log:L2", "log:L3"] },
  "routing_decision": { "recommended_lane": "issue-to-pr", "rationale": "Clear real-break ..." },
  "handoff": { "seam": "dispatch-by-naming", "downstream": ["issue-intake", "issue-to-pr", "pr-review-note"] }
}
```

## Verify the receipt recomputes

Every run seals a receipt under `$RUNX_RECEIPT_DIR`:

```bash
runx verify --receipt "$RUNX_RECEIPT_DIR/<receipt-id>.json" --json
# -> { "valid": true, "digest": {"status":"valid"}, "signature": {"status":"valid"} }
```

A real verified run from this package (a `dep` break -> `issue-to-pr`):

```
receipt_id : sha256:0ed1ab9cc51259d1dc497e20a279a40a5dc5ec21e839310ba6517785a13a483e
verify     : valid=true, digest=valid, content_address=valid, signature=valid (production)
```

## The two harness cases

| case | input | result |
| --- | --- | --- |
| `real_break_clear_logs` | a TS type error + failed assertion | sealed, `verdict: real-break`, lane `issue-to-pr` |
| `ambiguous_truncated_logs` | `[... truncated]` | refused (`needs_agent`), no routing |

## Boundaries

- Read-only: no item opened, no CI rerun, no page sent.
- Evidence-bound: refuses to assert a cause not visible in the supplied logs.
- Refuses below `min_confidence`, or on empty/truncated logs.

## Learn more about runx

- Catalog & docs: https://runx.ai
- Source & spec: https://github.com/runxhq/runx

Licensed MIT.
