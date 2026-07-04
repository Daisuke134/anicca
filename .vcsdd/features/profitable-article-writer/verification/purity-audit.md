# Purity Boundary Audit — profitable-article-writer, Sprint 1 + Sprint 2 + Sprint 3 (2.5)

## Sprint-3 boundary: real-publish is a TOOL, not a decision

`note-publish-live.py` makes no judgment call — it deterministically confirms already-decided state (price=500,
type=有料, eyecatch present, ≥1 figure) and either clicks or refuses. The DECISION (which draft, when, whether
to publish at all) is made by the human/main-agent invoker, not the tool. This is correctly on the deterministic
side of the boundary: no hidden judgment, no hardcoded classifier deciding content quality — that decision
already happened at V0/V0.5 (Sprint 1-2) before this tool is ever invoked. `note-verify-live.py` is likewise
pure verification (HTTP fetch + string match), no judgment.

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

## Sprint-2 observed boundaries

- `generate_draft`'s real-content hook (`ARTICLE_REAL_DRAFT_PATH`) takes the running agent's OWN already-authored
  content verbatim — the agent judged (research, theme, craft) BEFORE invoking this deterministic hook; the hook
  itself makes no writing decision, only a file-copy. Boundary preserved. ✅
- `gates/v05.sh`'s (e) readability arithmetic was found (Phase-3 round-2, FIND-002) to use byte-wise `tr`, risking
  incorrect Japanese-punctuation splits under a C/POSIX locale — this was a DETERMINISM bug (wrong arithmetic), not
  a purity-boundary violation (it never became a hidden judgment call); fixed with a locale-independent python3
  `re` split. No regex/keyword was introduced to make a *decision* — the split is still pure counting. ✅
- The live `judge_v05` model call (criteria a-d) remains UNWIRED in Sprint 2 (same as Sprint 1): the request/response
  hook exists and fails closed to FALSE when no response is supplied. Wiring the live call is a Sprint-3+ item and
  MUST continue to route through this hook, never a hardcoded classifier, when it lands.
- Real note.com publish (`lib/note-set-eyecatch.py`, `lib/note-set-single-price.py`) are EXTERNAL SIDE-EFFECTS
  (browser automation), correctly on that side of the boundary — no product judgment lives in these scripts; they
  execute a decision (single-¥500, not membership) that was made at the contract/design layer, not invented here.

## Summary

The purity boundary is respected across Sprint 1 + Sprint 2: every product DECISION is the agent's (right-altitude,
hook-delegated), every deterministic operation is genuine parsing/arithmetic/bookkeeping/browser-execution of an
already-made decision. Residual: the live `judge_v05` model call is still unwired (fail-closed) — wiring it in a
future sprint is the next purity-relevant item to re-audit.
