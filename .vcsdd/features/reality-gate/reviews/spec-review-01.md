# VCSDD Adversary — Phase 1c Spec Review

Feature: `reality-gate` (mode: lean) — Phase 4.5 REALITY GATE
Reviewer: fresh-context adversary (zero context from Builder)
Artifacts actually read (paths + line ranges), used as the basis for every finding below:

- `.vcsdd/features/reality-gate/specs/behavioral-spec.md` (1-358, full file)
- `.vcsdd/features/reality-gate/specs/verification-architecture.md` (1-119, full file)
- `.claude/agents/reality-verifier.md` (1-140, full file)
- `skills/self/lib/reality-verdict-schema.mjs` (1-129, full file)
- `skills/self/reality-verify-spawn.sh` (1-69, full file)
- `skills/self/lib/__tests__/reality-verdict-schema.test.mjs` (1-178, full file)
- `skills/earn/gig/scripts/gig_reality_gate.py` (1-119, full file)
- `/Users/anicca/.claude/plugins/cache/vcsdd-claude-code/vcsdd/1.0.0/scripts/lib/vcsdd-state.js` (1-1854; read 1-1536 and 1734-1854 directly, incl. `GATE_PREREQUISITES`, `recordGate`, `module.exports`)
- `/Users/anicca/.claude/plugins/cache/vcsdd-claude-code/vcsdd/1.0.0/scripts/lib/vcsdd-schema.js` (1-349, full file)
- `/Users/anicca/.claude/plugins/cache/vcsdd-claude-code/vcsdd/1.0.0/schemas/vcsdd-state.schema.json` (1-107, full file)
- `/Users/anicca/.claude/plugins/cache/vcsdd-claude-code/vcsdd/1.0.0/hooks/hooks.json` (1-30, full file)
- `/Users/anicca/anicca-project/.claude/settings.json` (1-158, full file — used as the observed, working, real-world convention for how project-level Claude Code hooks are actually configured in this ecosystem)
- `docs/superpowers/specs/2026-07-13-growth-engine-self-improving-promotion-skill-design.md` §8b/§8c/§8d (lines 71-156)
- `/Users/anicca/.claude/rules/building-effective-ai-agents.md` (full file)

No manifest.json was present under `reviews/` for this scope; reviewed directly against the task brief.

---

## Dimension 1: spec_fidelity — **FAIL**

### FIND-001 (BLOCKING) — `recordGate()` calls specified in REQ-008 will crash `writeState()`; the "fully supported, not a hack" claim is false for the values used, only true for the key

`behavioral-spec.md:225-254` (REQ-008) instructs:
```
recordGate(featureName, 'reality', verdict, 'reality-verifier', details)
```
and its edge case (`behavioral-spec.md:243-246`) instructs recording:
```
gates.reality = { verdict: "SKIPPED", reason }
```
REQ-009 (`behavioral-spec.md:257-291`) repeats `"SKIPPED"` as a required, checkable value (`gates.reality.verdict is PASS or an explicitly-reasoned SKIPPED`).

The spec's own "VERIFIED" annotation (`behavioral-spec.md:232-235`) only checked that `recordGate`'s `phase` parameter is unconstrained (true — confirmed by reading `vcsdd-state.js:78-280`, `GATE_PREREQUISITES` keys are a fixed literal set but `state.gates[phase]` itself is not restricted to that set at the JS level). It did **not** check the VALUES `recordGate` is called with against the existing, unmodified state schema:

`vcsdd-state.schema.json:30-54`:
```json
"gates": {
  "type": "object",
  "additionalProperties": {
    "required": ["verdict", "timestamp"],
    "additionalProperties": false,
    "properties": {
      "verdict": { "type": "string", "enum": ["PASS", "FAIL", "SKIP"] },
      ...
      "reviewedBy": { "type": "string", "enum": ["adversary", "verifier", "human"] },
```

`recordGate()` (`vcsdd-state.js:1734-1770`) unconditionally calls `writeState(featureName, state)` (`vcsdd-state.js:1221-1226`), which calls `assertValidDocument('state', state, ...)` (`vcsdd-schema.js:67-73`), which throws on any schema violation. Concretely:
- `verdict: "SKIPPED"` is **not** in the enum `["PASS","FAIL","SKIP"]` → throws.
- `reviewedBy: "reality-verifier"` is **not** in the enum `["adversary","verifier","human"]` → throws.

So the exact `recordGate()` invocation REQ-008 specifies, and the exact `SKIPPED` value REQ-008/REQ-009 make a required, mechanically-checked acceptance criterion, will throw at write time — the gate can never actually be recorded as written. This is not a judgment call; it is a mechanical fact about code that already exists and that this feature does not propose to modify (REQ-008's own edge case says explicitly: "a plugin update never touches" these files, and nothing in this spec proposes editing `vcsdd-state.schema.json`, which lives under the plugin cache anyway and REQ-008 forbids touching).

**Failure scenario**: a Builder implements REQ-008 literally (calls `recordGate(feature, 'reality', 'SKIPPED', 'reality-verifier', ...)`), the gate script throws an uncaught exception, and either (a) the exception is swallowed and the gate silently never records (worse than not building the feature — REQ-008's own edge case says "a MISSING `gates.reality` key never [satisfies the gate]", so a swallowed crash produces exactly the state the spec calls out as *never acceptable*), or (b) the script crashes and blocks the pipeline outright. Either way REQ-008/009's acceptance criteria as literally written are unsatisfiable without either (i) picking a schema-legal value (`"SKIP"` not `"SKIPPED"`, `"verifier"` or `"human"` not `"reality-verifier"`) or (ii) extending the plugin's schema (which REQ-008 explicitly forbids touching).

`routeToPhase`: 1b (spec must be corrected before implementation starts).

---

## Dimension 2: edge_case_coverage — **FAIL**

### FIND-002 (BLOCKING) — the one edge case this whole feature exists to catch (a shadowbanned/failed post still visible to the logged-in owner) is not actually covered by the fail-closed backstop or by either negative-test proof obligation

The task's own framing, and `growth-engine-...-design.md:100-101` ("shadowban/失敗投稿でも本人には見え偽PASSになる"), name the core threat model explicitly: a post that failed/was shadowbanned is still visible to the account owner logged in, so a logged-in check produces a false PASS.

REQ-003's deterministic backstop, as actually specified in `verification-architecture.md:14-21`:
> `enforceLoggedOutEvidence(verdict, claimType)` — pure function: inspects `verdict.findings[].evidence` and `verdict.evidenceReviewed[]` string fields for a fixed marker set (`"9222"`, `"daily-driver"`, `"cloakbrowser"` case-insensitive)... if found, returns... FAIL...; otherwise returns the input verdict unchanged.

This backstop only fires if the LLM's **own self-authored** evidence text happens to literally contain one of three tokens. It is not derived from any independently-captured, non-LLM record of which tool/session was actually used (no CDP-connection log, no structured `fetchMethod` field populated by a deterministic wrapper around the Bash call, nothing like it). A reality-verifier run that used the CDP:9222 daily-driver tab (by mistake, prompt drift, or because the wording "cookie-less browser context" was satisfied by opening a plain non-incognito Chrome window instead) but wrote e.g. `evidence: { domExcerpt: "post visible, 1.2k likes, caption matches" }` — never spelling out "9222"/"daily-driver"/"cloakbrowser" — sails through as an undetected false PASS. This is **exactly** the scenario the task brief calls BLOCKING by name ("an evidence string that merely avoids the literal token '9222' while still using an authenticated context").

Compare this to the pattern REQ-003 explicitly claims to mirror (`behavioral-spec.md:114-117`: "mirroring `gig_reality_gate.py`'s existing pattern of never trusting a fresh judge's self-report on faith alone"). The actual gig pattern (`gig_reality_gate.py:39-96`) is structurally different and stronger: `count_evidence_rows()` counts rows in `trajectory.jsonl` that were **independently written by a separate deterministic navigation helper** (`cdp_nav_snapshot.py`) during the run, scoped by `pass_id` + `min_ts` — i.e. it checks *independently captured, non-LLM-authored* evidence, not the judge's own free-text report. `reality-gate`'s `enforceLoggedOutEvidence` re-inspects the **same self-reported JSON the LLM itself wrote** — there is no independent capture at all. The claimed mirroring is false; the actual mechanism is materially weaker than what it says it copies.

Neither proof obligation closes this gap:
- PROP-010/017 (`verification-architecture.md:66,73`) only prove: *if* the marker is present in the verdict text, it gets caught. That is the trivial case, not the threat model.
- PROP-018 (`verification-architecture.md:74`) is a live spawn against a **genuinely nonexistent** URL — a different failure mode (absent artifact) than the actual threat (existent-but-not-public artifact, visible only to an authenticated session that never admits it was authenticated).

There is no proof obligation, unit test, or live-spawn requirement anywhere in this spec that exercises: "marker absent from the verdict's own text + claim type is public-artifact + evidence describes content that in fact could only have been observed logged-in." REQ-007's "fail-closed proof" therefore proves fail-closed against the *wrong* adversary (a nonexistent artifact) and never proves fail-closed against the *actual* named adversary (a shadowbanned/failed post visible only to the owner).

`routeToPhase`: 1b.

### FIND-003 (MINOR) — false-positive marker collision is an unhandled edge case
`verification-architecture.md:16` — the marker check is a raw case-insensitive substring match for `"9222"` anywhere in any evidence/evidenceReviewed string. A legitimate `domExcerpt` that happens to contain the digits "9222" for an unrelated reason (a view count, an article ID, a timestamp fragment) would trigger a false downgrade to FAIL. Not a security hole (fail-closed is "safe" by the spec's own framing), but the spec's Edge Cases sections for REQ-003 (`behavioral-spec.md:102-119`) never enumerate this false-positive-marker case, and PROP-011's "identity-preserving on non-violating path" property test (`verification-architecture.md:67`) will be exercising exactly this collision risk via fast-check-generated random text without the spec ever having decided what the correct behavior should be.

---

## Dimension 3: implementation_correctness — **FAIL**

Phase 1c standard for this dimension is "are the requirements concrete enough to be implemented unambiguously." FIND-001 and FIND-002 already show two requirements (REQ-008/009's `recordGate` value contract, REQ-003's backstop) that are either internally contradictory (will crash on the exact call specified) or not concrete enough to prevent a trivially-bypassable implementation. One more concrete internal inconsistency:

### FIND-004 (MAJOR) — REQ-003 names a field (`evidence.fetchMethod`) that does not exist anywhere in the schema this feature keeps unmodified, and the verification-architecture's actual implementation silently drops it

`behavioral-spec.md:110-117` (REQ-003 edge case) and `:124-129` (REQ-003 acceptance criteria) both frame the backstop around `evidence.fetchMethod` ("whose `evidence.fetchMethod` (or equivalent tool-call trace) indicates it went through CDP port `9222`..."; "given a verdict whose findings/evidenceReviewed entries reference `9222`... name TBD in Phase 1b, e.g. `enforceLoggedOutEvidence(verdict, claimType)`").

But `reality-verdict-schema.mjs:62-65` (`hasCiteableEvidence`, unmodified by this feature per its own purity map, `verification-architecture.md:12-13`: "unchanged pure structural validator") only ever recognizes `evidence.filePath`, `evidence.txHash`, `evidence.domExcerpt` — there is no `fetchMethod` key in the schema, anywhere, before or after this feature. And `verification-architecture.md:14-21`'s actual description of `enforceLoggedOutEvidence` never mentions `fetchMethod` either — it scans the free-text `evidence`/`evidenceReviewed` **string fields** for markers instead. This directly contradicts `behavioral-spec.md:352-354` ("the CDP-port-9222 evidence-marker backstop (parsing a fixed, structured field the LLM itself wrote — not judging free-text content)"): as actually specified, this backstop **is** judging free-text content (substring-matching over `domExcerpt`/description strings), not parsing a structured field. The spec's own anti-hardcoding justification for why this counts as "determinism, not judgment" does not match what it actually specifies the function to do. This needs to be resolved in Phase 1b/1c before a Builder can implement it unambiguously — right now REQ-003's acceptance criteria and verification-architecture.md describe two different mechanisms.

`routeToPhase`: 1b.

---

## Dimension 4: structural_integrity — **PASS**

Reviewed: the purity boundary map (`verification-architecture.md:7-58`) cleanly separates the pure schema module (`reality-verdict-schema.mjs`, extended in place — `FINDING_CATEGORIES`, `isKnownCategory`, `validateVerdictShape`, plus new `enforceLoggedOutEvidence`/`buildVerdictTrailPath`/`buildVerdictTrailLine`) from the effectful shell (agent prompt, spawn wrapper, new gate script, command file, hooks). This mirrors the already-shipped `reality-verifier` feature's decomposition (confirmed by reading the unmodified `reality-verdict-schema.mjs` and its existing test file) and does not introduce new coupling between the pure core and any I/O. No duplication of the existing 6-category catalog logic — REQ-001 explicitly extends the existing frozen array in place rather than forking it. Naming is consistent with the base feature's conventions (`buildResultPath` → `buildVerdictTrailPath`, same normalization helper reused). This dimension is not where this spec's problems are; the design shape is sound. (The `fetchMethod`/free-text inconsistency from FIND-004 is a content-correctness defect, not a structural/module-boundary defect, and is scored under implementation_correctness above.)

---

## Dimension 5: verification_readiness — **FAIL**

### FIND-005 (MAJOR) — REQ-009's hook mechanism is baked into a required proof obligation as a static content check, while the only test of its actual function is a prose "MUST" with no PROP backing it, and the concrete file/location it requires does not match this ecosystem's own observed, working convention for project-level hooks

`verification-architecture.md:72` (PROP-016): "`.claude/hooks/hooks.json` is present and its `PreToolUse` matcher/handler references the same `gates.reality` field name... (Tier 0, static content assertion / import-and-compare)." This is a required (`required: true`) proof obligation that a Builder can satisfy by writing a syntactically-plausible-but-inert JSON file — the check never fires the hook and observes an actual effect.

`verification-architecture.md:108-115` explicitly concedes: "Whether Claude Code actually composes project-level `.claude/hooks/hooks.json` additively with plugin-level `hooks.json`... is currently an ASSUMPTION (not independently verified this session)... Phase 2b/2c of this feature MUST include one real end-to-end check... before this requirement is considered verified." That "MUST" is prose only — it is not represented anywhere in the Proof Obligations table (`verification-architecture.md:60-74`) as a `required: true` PROP tied to the Phase 6/complete gate, so nothing in the mechanical pipeline actually forces that live check to happen; a Builder can reach Phase 6 with all listed PROPs "proved" while this live check was simply never run.

Compounding this: I read `/Users/anicca/anicca-project/.claude/settings.json:48-144`, which is this very ecosystem's real, currently-working project-level hook configuration. It configures `PreToolUse`/`PostToolUse`/etc. directly under a top-level `"hooks"` key **inside `.claude/settings.json`**, with handler scripts living under `.claude/hooks/scripts/*.sh` — there is no separate `.claude/hooks/hooks.json` file anywhere in that convention. The `.claude/hooks/hooks.json` filename/path this spec requires (`behavioral-spec.md:283-285`, REQ-009 acceptance criteria) instead exactly mirrors the **plugin's own internal packaging file** (`/Users/anicca/.claude/plugins/cache/vcsdd-claude-code/vcsdd/1.0.0/hooks/hooks.json`) — which is a plugin-manifest hook file, a different mechanism from a project's `.claude/settings.json` hooks. The spec never checks which of these two real, differently-shaped, already-observed conventions Claude Code will actually use for *project-level* hook composition before writing a required acceptance criterion that hard-codes one specific (and, per the ecosystem's own precedent, likely wrong) file path.

Because the standalone `verify-reality-gate` backstop script is correctly designed to be authoritative independent of the hook (`behavioral-spec.md:266-277`, `verification-architecture.md:104-107`), this does not break SURVIVABILITY of the convergence enforcement overall — but it does mean the REQUIRED PROP-016/hook acceptance criterion, as currently specified, can be satisfied by an artifact that provides no actual protection, which fails the "verification obligations reflected in the implementation, no unearned PASS" bar for this dimension.

`routeToPhase`: 1b (either drop PROP-016's `required: true` status until the live end-to-end check is itself a required PROP, or fix the file path/mechanism against the ecosystem's own confirmed `.claude/settings.json` convention before Phase 2).

---

## Overall Gate Verdict: **FAIL**

Blocking findings (must be fixed before Phase 1c can pass and Phase 2 can begin):

1. **FIND-001** — `recordGate(feature, 'reality', 'SKIPPED', 'reality-verifier', ...)` as literally specified in REQ-008/009 violates the existing, unmodified `vcsdd-state.schema.json` enum constraints on `verdict` (`SKIP` not `SKIPPED`) and `reviewedBy` (`reality-verifier` not in `["adversary","verifier","human"]`) and will throw inside `writeState()` every time it is called as written.
2. **FIND-002** — the deterministic logged-out backstop (`enforceLoggedOutEvidence`) only catches violations the LLM's own report happens to literally admit to (`"9222"`/`"daily-driver"`/`"cloakbrowser"` substrings); it is not derived from any independently captured evidence (unlike the `gig_reality_gate.py` pattern it claims to mirror), so a shadowbanned/failed-post-visible-to-owner false PASS — the exact threat model this feature exists to close — can bypass it, and no proof obligation in this spec actually tests that bypass.

Non-blocking but must be tracked (MAJOR): FIND-004 (`evidence.fetchMethod` named but nonexistent, contradicts the "structured field, not free text" design claim), FIND-005 (hook mechanism's required proof obligation is a static-content-only check whose real-world file/location convention conflicts with this ecosystem's own observed working pattern). MINOR: FIND-003 (unhandled false-positive marker-collision edge case).

Findings artifact files were not additionally emitted as separate JSON (no `reviews/spec/iteration-N/output/findings/` scaffold or manifest existed for this scope at review time); all findings, evidence citations, and severities are recorded in full above and are considered authoritative for this iteration.
