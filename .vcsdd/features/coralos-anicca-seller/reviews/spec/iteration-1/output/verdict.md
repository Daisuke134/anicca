# VCSDD Adversary Verdict — coralos-anicca-seller — spec/iteration-1

**Overall: FAIL**

Note: no `input/manifest.json` exists at the expected path
(`.vcsdd/features/coralos-anicca-seller/reviews/spec/iteration-1/input/manifest.json`) — I reviewed the
spec directly per the task instructions. `.vcsdd/features/coralos-anicca-seller/state.json` shows
`currentPhase: "init"`, `phaseHistory: []` — this iteration-1 gate has no recorded history yet.

## Dimension 1 — Spec Fidelity: FAIL

**FIND-001 (critical, requirement_mismatch)** — The spec forks the wrong subsystem. The parent
spec's R5 requires `deliverService(request)` "in the forked CoralOS kit" to settle a "REAL Solana
**escrow** payment" via a **WANT→BID→AWARD→DEPOSITED→DELIVERED→RELEASED** loop (parent spec lines
79-84, 128-131). R1a/R1b use that exact same WANT→BID→AWARD→DEPOSIT→DELIVER→RELEASE vocabulary
(parent spec lines 105-110). That flow lives in `coral-agents/seller-agent/src/service.ts`
(`deliverService`) + `coral-agents/broker` + the Anchor escrow at `examples/txodds/escrow/`, run
through `coral-server` (Docker, MCP sessions) — confirmed on disk.
The child spec instead forks `examples/agent-economy/quickstart/server.ts`'s `deliverData`, which the
repo's own README (`examples/agent-economy/README.md:106-113`) labels the **"No Docker? ... no
CoralOS"** bare-metal fallback: a direct `SystemProgram.transfer` verified by
`findReference`/`validateTransfer` — pay-first, no escrow, no arbiter, no AWARD step, no CoralOS
session at all. The child spec never discloses this substitution or explains why R5's actual named
function (`deliverService`) and escrow mechanism were swapped for a different function
(`deliverData`) in a different, explicitly non-CoralOS example. This is scope substitution, not a
disclosed reconciliation (contrast with the honest R1a-note treatment of the Anthropic-vs-OpenAI
question at spec lines 23-31, which IS disclosed). Fix: either retarget REQ-1..5 at
`coral-agents/seller-agent/src/service.ts::deliverService` + the escrow flow, or add an explicit
"Out of scope" note admitting Phase A intentionally bypasses CoralOS/escrow and that R5's literal
text is not satisfied by this feature.

**FIND-002 (critical, verification_tool_mismatch)** — The parent spec's core Phase-B claim ("R1c...
the shim is provider-agnostic per LLM.md, env-var flip, no code change") is FALSE for the code path
this child spec targets. `LLM.md:13-21` and `coral-agents/buyer-agent/src/llm_buyer.ts:9-11` state
explicitly that the buyer's pay-decision loop is hard-wired to `@anthropic-ai/sdk` **specifically to
keep it OUT of the provider-agnostic `complete.ts` shim** ("keeping the LLM dependency out of
agent-runtime keeps the core runtime lightweight"). `quickstart/buyer.ts:11,70` confirms: `new
Anthropic()`, no `LLM_PROVIDER` env var anywhere in that file. So a later ClawRouter swap on this
fork point requires an actual SDK rewrite of `buyer.ts` (or `llm_buyer.ts`), not an env-var flip.
The child spec's own "R1a note" (lines 23-31) only flags "swapping to OpenAI" as a deferred,
non-blocking refactor — it never flags that the SAME non-trivial rewrite blocks Phase B's supposedly
"zero-code-change" ClawRouter swap, which is the parent spec's central differentiator (R1c/R1d).
This is a load-bearing gap that will surface as a Phase-B blocker unless corrected now.

## Dimension 2 — Edge Case Coverage: FAIL

**FIND-003 (high, spec_gap)** — `deliverData`'s `fetch(url)` (server.ts:90, and the spec's REQ-1
replacement of it) has no timeout/AbortController in the existing code, and REQ-1/REQ-2 don't specify
one. REQ-2 only covers "unreachable" (connection refused/DNS fail → throws → caught). It does not
cover a **slow/hanging** upstream (e.g. aniccaai.com under load): a hung `fetch` blocks the Express
handler indefinitely, which blocks `buyer.ts`'s synchronous retry `fetch` inside `payAndRetry`
(buyer.ts:63-66) indefinitely too — not a turn-limit exhaustion (payAndRetry doesn't consume extra
turns), but a genuine E2E hang with no clean failure mode, contradicting REQ-2's "never crash or
strand a paid buyer" intent (a hang strands the buyer just as badly as a crash). Fix: REQ-2 must
require an explicit timeout (e.g. `AbortSignal.timeout(5000)`) with the timeout treated identically
to "unreachable."

**FIND-004 (medium, spec_gap)** — REQ-1/REQ-2 only enumerate two states (unreachable → error;
reachable → payload). A third real state is unaddressed: **200 OK but the specific leaderboard entry
(`0xa3cdd4ec…`) is missing/renamed/malformed** in `dashboard.json`. Nothing specifies fallback
behavior for "reachable, parseable, but entry not found."

**FIND-005 (medium, requirement_mismatch)** — REQ-1's "real, non-fabricated Anicca output" is
satisfied by re-serving Anicca's own self-authored `dashboard.json` leaderboard entry — a
self-reported number about Anicca's own state, not an externally-verifiable market fact (contrast
with the existing Jupiter fallback, a real third-party swap quote). A skeptical bounty judge could
reasonably call this circular/self-dealing rather than "a real service" — the spec doesn't address
or preempt this critique, and no local snapshot of the actual `dashboard.json` response is attached
to the spec as evidence the entry exists (I have no network tool to verify it myself; the spec cites
an external identifier with zero local corroborating artifact).

## Dimension 3 — Implementation Correctness: FAIL

**FIND-006 (high, test_quality)** — The unit-test plan ("point the data source at an unreachable
URL") is unimplementable as literally stated: `deliverData`'s URL is a **hardcoded string literal**
inside the function body (server.ts:85-89 today); there is no injectable base-URL config. The spec
never specifies how the URL becomes swappable for tests (env var vs. network-level mock library vs.
dependency injection) — two implementers will build two incompatible test harnesses. Fix: REQ-1/1b
must name the mechanism explicitly, e.g. `ANICCA_DASHBOARD_URL` env var (default
`https://aniccaai.com/dashboard.json`), consumed by `deliverData`, so both the shape-unit-test and
the unreachable-URL unit-test can point at fixtures deterministically.

**FIND-007 (medium, spec_gap)** — The spec never confirms `aniccaai.com/dashboard.json` is
unauthenticated/publicly fetchable. If it ever requires auth, REQ-1's fetch-fresh-at-call-time
design breaks silently in a way indistinguishable from "unreachable."

## Dimension 4 — Structural Integrity: FAIL

**FIND-008 (high, purity_boundary regression risk)** — The "never crash" invariant is currently
guaranteed by `server.ts`'s OWN try/catch around the `deliverData()` call (server.ts:69-74), NOT by
anything inside `deliverData` itself. REQ-2 asks the implementer to duplicate this guarantee inside
`deliverData`, but nothing in the verification architecture tests that the outer wrapper
(server.ts:69-74) survives the edit untouched. Since the spec calls `deliverData` "the ONLY fork
point" (line 12) without a corresponding regression test asserting the caller-side try/catch is
still present/intact, an implementer who "helpfully" inlines or restructures the route handler could
silently remove that structural guarantee with no test catching it. Fix: add a regression test that
makes `deliverData` throw synchronously and asserts the HTTP response is still 200 with an error
body (proving the OUTER wrapper, not just the inner one).

## Dimension 5 — Verification Readiness: FAIL

**FIND-009 (high, requirement_mismatch)** — REQ-5(c) accepts `solana confirm -v <sig> --url
<cluster>` as sufficient evidence, but the parent spec's exit gate (R1b) explicitly requires an
"Explorer link captured." A local `solana-test-validator` (REQ-3's stated default, "local
devnet-equivalent per A3") produces signatures that do **not** resolve on `explorer.solana.com` —
there is no public Explorer link possible for a local validator. REQ-5 as written lets the E2E run
satisfy this feature's own Done-criteria while failing the parent spec's literal R1b exit gate. This
inconsistency must be resolved: either REQ-3 mandates the public devnet cluster (so an Explorer link
is possible), or REQ-5/Done explicitly states this feature does NOT close R1b's exit gate by itself.

**FIND-010 (medium, test_quality)** — "capture real stdout with a real signature" (verification
table, REQ-3/REQ-5) names no artifact path or format. Nothing stops an implementer from pasting a
signature into a chat message without ever saving the raw process stdout to a file. Fix: require
stdout+`solana confirm` output be saved to a timestamped file under
`.vcsdd/features/coralos-anicca-seller/evidence/` and referenced by path in the Done report (matches
this repo's own HARD RULE 0.31 convention already used elsewhere in this codebase).

## Convergence
- findingCount: 10
- evaluatedCriteria: REQ-1, REQ-2, REQ-3, REQ-4, REQ-5 (all 5 evaluated; all show at least one FAIL-tier finding except none — every REQ has an open finding above)
- All 5 dimensions: FAIL
