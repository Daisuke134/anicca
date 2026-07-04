# Purity Boundary Audit — profitable-article-writer, Sprint 1

Mode: strict. Phase 5. Audits the boundary between deterministic code and agent judgment (per
building-effective-ai-agents: the MODEL judges via right-altitude prompts; NEVER hardcode a regex/if-else for a
decision).

## Declared Boundaries

Per `specs/verification-architecture.md` §Purity boundary map:

- **Deterministic tools:** record-earn ledger, render/screenshot verify (V0), publishers, payout routing, dedup,
  registry credential gating, git, `json_escape`, V0.5 criterion (e) readability (arithmetic).
- **Agent judgment (non-deterministic):** niche/topic pick, theme, buy-reason-3-lines, free/paid split, craft
  writing, **V0.5 criteria (a)-(d)** (hook / CTA / payoff-cut / no-run-claim), per-rail repurposing.
- **External side-effects:** publish, payment receipt, account creation (all Sprint 2+).

## Observed Boundaries

Audited against the actual Sprint-1 source:

- `gates/v05.sh`: criteria (a)-(d) are delegated to the running agent via the `judge_v05` request/response hook
  (`ARTICLE_JUDGE_V05_RESPONSE`); the script emits a judgment-request artifact and parses only the agent's own
  verdict lines (`V05_CRIT_x: true`) — it NEVER greps the draft body to decide (a)-(d). Unwired ⇒ fail-closed to
  false. This matches the declared boundary (judgment is the model's, not a hardcoded classifier). ✅
- Criterion (e) is genuine arithmetic (sentence-length %), a fixed computable metric — correctly on the
  deterministic side. ✅
- `run.sh` topic/research decisions in Sprint 1 use injected test values; the real content-gen + topic-pick are a
  documented hook (`generate_draft`) deferred to Sprint 2 — the boundary (agent judges, tool records) is preserved.
- No hardcoded regex/keyword classifier makes any product decision anywhere in the tree (grep-confirmed; this was
  the Phase-3-round-1 blocker, now fixed).

## Summary

The purity boundary is respected: every product DECISION is the agent's (right-altitude, hook-delegated), every
deterministic operation is genuine parsing/arithmetic/bookkeeping. Residual: the live `judge_v05` model call and the
real content-gen hook are unwired in Sprint 1 (fail-closed when absent) and are wired at Sprint 2 — that wiring must
preserve this boundary (no regex judgment) and will be re-audited then.
