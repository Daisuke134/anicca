# Phase 1c Spec Review — anicca-agent-economy — iteration 1

**Verdict: FAIL** (spec_fidelity: FAIL, verification_readiness: FAIL)

Reviewer: fresh-context VCSDD Adversary (Sonnet). Disk-only review, no Builder context. Reviewed:
`specs/behavioral-spec.md`, `specs/verification-architecture.md`, plus direct inspection of
`~/anicca/skills/economy/gig/{lib,gig.mjs,__tests__,package.json}`, `~/anicca/runtime/loop/{index,
tier,context,config,prompt,liquidity,balance}.mjs`, `~/anicca/skills/registry.json`, this feature's
`state.json`, and the cited prior-round evidence files under `evidence/`.

## Summary

The three requirement groups (REQ-101..103 concurrency hardening, REQ-201..203 catalog eligibility
gate, REQ-301..302 research spike) are individually well-formed EARS statements with real edge
cases, and every cross-reference to prior rounds (p0/p1/p2.2 verdicts, p2.2-security-fixes*.md)
checks out against real files — no hallucinated citations. That said, both reviewed dimensions FAIL
on concrete, evidenced grounds below; a single blocking finding is sufficient for FAIL and there are
six.

## spec_fidelity — FAIL

1. **FIND-001 (critical)** — `BOOTSTRAP_RESERVE_USDC`'s fallback default is asserted to be "a
   documented safe default value" but no such value is documented anywhere in either spec file. The
   codebase's own analogous `COMPUTE_RESERVE_USDC` is concretely defaulted to `5` in
   `runtime/loop/context.mjs:39` — REQ-201 doesn't even reference this existing pattern, let alone
   supply its own number.
2. **FIND-002 (critical)** — REQ-201's "every live slot tagged risky" edge case (and PROP-201e)
   requires unnamed "always-available" slots to survive filtering even when literally everything,
   including `report`/`cook`, is risk-tagged. `filterCatalog`'s stated 4-input signature (balance,
   slot names, risk tags, threshold) has no way to produce this — an undefined 5th signal or hardcoded
   allowlist would have to be invented at Phase 3 with zero spec authority for which slots qualify.
3. **FIND-003 (critical)** — the existing `liquidity.mjs::liquidityDirective` steer already tells a
   low-balance agent to "CLOSE a profitable HL position" via `hl_trade` — the exact slot REQ-201 names
   as its own capital-risking example to hide at low balance. Below both `COMPUTE_RESERVE_USDC` and
   `BOOTSTRAP_RESERVE_USDC` simultaneously, an agent could be told by the prompt to close a position via
   a tool that the same wake's catalog gate has just removed from its menu — a real, unaddressed
   functional deadlock with financial-loss potential (an open position, possibly losing, becomes
   unclosable).

## verification_readiness — FAIL

4. **FIND-004 (critical)** — the Purity Boundary Map and Tier-1 labels for PROP-101a/b/d claim the
   lock-staleness predicate is pure and testable "without touching the filesystem or real wall-clock
   sleeps (fake nowMs/mtimeMs injected)." Direct inspection of `lib/lock.mjs`'s `acquire()` (staleness
   inlined as `Date.now() - stat.mtimeMs > staleMs` inside an fs-calling function) and the real
   `__tests__/lock.test.mjs` (real `fs.mkdtemp`/`fs.utimes` + real `setTimeout` waits of `staleMs*3`,
   `staleMs+30`) shows this is Tier 2 by the document's own definitions, not Tier 1. No REQ-101
   acceptance criterion actually mandates extracting an isolated pure function — only a non-binding
   parenthetical does — so this purity/tier classification is inaccurate and unenforceable as written.
5. **FIND-005 (high)** — PROP-203b tells the Phase-3 adversary to expect "only the already-existing
   'you decide' framing" in `prompt.mjs`. The real, current `prompt.mjs` already contains forceful
   ranking/steering text ("your FIRST action this wake MUST be economy/gig", "Prefer this over
   re-yielding surplus", "Do this BEFORE hl_trade / yield / anything else") — this mischaracterizes the
   baseline a fresh adversary is told to diff against, risking a false-negative PASS on REQ-203's own
   "bookkeeping, not judgment" principle.
6. **FIND-006 (medium)** — `state.json` shows this feature still formally at Phase 1b with all 21
   proof obligations `pending`, yet `evidence/p2.2-security-fixes-round3.md` (same day) already
   documents a complete RED→GREEN cycle AND a live testnet re-proof for exactly REQ-101/102/103. The
   spec is transparent that it codifies already-written code, but the Gate/PROP-103b language never
   states the Phase-3 adversary must independently re-run its OWN live transactions rather than accept
   the builder's own prior self-report as sufficient Tier-3 evidence.

## Positive evidence (dimensions are not blanket-rejected)

- REQ-301/302 (research spike) are concretely EARS-formed, falsifiable, and correctly Tier-0 scoped;
  no issues found there.
- REQ-103's edge case naming of the 5 existing test files (`store/decide/lock/gig/ensure-agent-id
  .test.mjs`) and the `viem`-requires-`npm install` gap were verified accurate against
  `skills/economy/gig/package.json` and the actual absence of `node_modules` in the main tree.
- `runtime/loop/index.mjs`'s cited line ranges (registry read ~L104-118, `fetchUsdcBalance` call
  ~L192) are accurate and structurally compatible with inserting a per-wake filter call between them.
- `store.mjs` and `gig.mjs`'s `applyAndSave` genuinely implement the REQ-102 target behavior described
  (re-read-fresh-then-mutate-then-save under a dedicated `_board` lock) — this was verified by reading
  control flow, not by grepping for "lock".

## Route

All findings route to Phase 1a/1b (spec revision) before this increment proceeds to Phase 2/3.
