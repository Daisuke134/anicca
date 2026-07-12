# Behavioral Spec: reality-gate (Phase 4.5 REALITY GATE, VCSDD pipeline extension)

Scope: `docs/superpowers/specs/2026-07-13-growth-engine-self-improving-promotion-skill-design.md`
§8b V0 / §8c (motivating gap analysis), in the `anicca-project` repo.
Builds on the already-shipped `reality-verifier` feature (see
`.vcsdd/features/reality-verifier/specs/behavioral-spec.md`) — this feature does NOT
re-implement reality-verifier; it (a) extends its category catalog and prompt from
money/ledger-only to any real-world side-effect claim, (b) generalizes its spawn wrapper,
(c) adds a durable per-loop verdict trail, (d) proves it is fail-closed with real negative
tests, and (e) wires it into VCSDD as a gate between adversarial review and formal hardening.

## Iteration history (Phase 1c)

| Iteration | Verdict | Findings | Disposition |
|---|---|---|---|
| 1 | FAIL | FIND-001 (recordGate enum crash), FIND-002 (backstop inspected LLM's own prose) | Fixed iter. 2: schema-legal `recordGate`; structural `validateArtifactProvenance`. |
| 2 | FAIL | FIND-A (zero-citation PASS unguarded), FIND-B (`gates.reality` not wired to enforcement), FIND-C (`claimType` provenance unpinned) | Fixed iter. 3: default-closed citation check; required `.githooks/pre-push` wiring; `reality-claim.json`. |
| 3 | FAIL | FIND-D (cited row's URL never checked), FIND-E (gate not bound to claim version), FIND-F (local-hook bypass — downgraded to disclosed limit by ruling), FIND-G (diagnosability unproven) | Fixed iter. 4: `claimedUrls`/`canonicalizeUrl` URL binding; `hashRealityClaim` claim-version binding; explicit disclosed-limit row for local hooks; `automatedVerification` refusal rule. |
| 4 (`reviews/spec-review-04.md`) | FAIL | FIND-H (**blocking, structural**: every backstop built in iterations 2-4 is wired ONLY into the VCSDD gate script; REQ-011's own named first customer — the standalone growth-engine loop — uses a path that calls none of it, so it gets a raw, unbackstopped LLM self-report), FIND-I (blocking: `claimedUrls` for a per-invocation claim is supplied by the SAME loop under test — a false "VERIFIED matches gig" equivalence claim was made; gig's ground truth is a fixed, spec-time constant, the opposite trust model), FIND-J (blocking: `canonicalizeUrl` strips query strings entirely, silently collapsing distinct query-identified artifacts — e.g. two different YouTube videos — to the same canonical value), FIND-K (major: `automatedVerification` defaults fail-open), FIND-L (major: no shared enforcement module between the two invocation paths, unlike the `decideConvergenceGate` precedent) | Fixed in this iteration (5, below): REQ-014 introduces ONE shared, pure `enforceVerdict` module invoked unconditionally by BOTH the (now-blocking) standalone spawn wrapper AND the gate script — a verdict that has not passed it is treated as FAIL by definition (closes FIND-H/L). REQ-015 replaces loop-supplied `claimedUrls`-as-ground-truth with a fixed, spec-time-constant public surface plus a content fingerprint pre-committed BEFORE the post action (closes FIND-I). `canonicalizeUrl` no longer strips the query string wholesale — only a fixed, declared tracking-param allowlist is stripped; everything else is preserved and compared (closes FIND-J). `automatedVerification` now defaults `false`, fail-closed (closes FIND-K). |

## Purpose (non-negotiable framing, carried over from reality-verifier)

VCSDD's existing agents each see only part of the truth:

| agent | tools (VERIFIED by reading agent frontmatter) | sees | cannot see |
|---|---|---|---|
| `vcsdd-adversary` (plugin) | Read, Write, Edit, Grep, Glob | spec/code/test-output files on disk | **no Bash — cannot execute anything or drive a browser** |
| `vcsdd-verifier` (plugin, phase 5) | Read, Write, Edit, Bash, Grep, Glob | property-test/fuzz/security/purity artifacts | scoped to formal proof, not real-world side effects |
| `reality-verifier` (`.claude/agents/reality-verifier.md`, this repo) | Read, Grep, Glob, **Bash**, no Write/Edit | the actual logged-out DOM / on-chain state / ledger files | cannot repair anything (repair is `self-fix.sh`'s job) |

Only `reality-verifier` can see ground truth in the real world. This feature makes it a
first-class gate — for EVERY invocation path that produces a verdict, not merely the one this
spec happened to build backstops for first (iteration 4's own failure mode, per FIND-H: four
iterations of increasingly sophisticated provenance-hardening protected a code path
(`/vcsdd-reality`, `gates.reality`, VCSDD convergence) that this spec's own REQ-011 says its
actual first customer does not use — "the feature itself committed the exact failure mode it
exists to kill" is this iteration's own starting premise, not a rhetorical flourish). The rule
going forward, stated once: **any protection this spec claims MUST be traced, concretely, to
BOTH invocation paths named in REQ-011 (the VCSDD build-time gate AND the runtime standalone
loop) before it is described as closing anything — a mechanism that only reaches one path is,
for the other path, exactly as if it did not exist.**

## Threat-model closure (read this section first — it is the spec's own completeness check)

Every identified path by which a `gates.reality` verdict OR a standalone per-run verdict
(REQ-006) could end up `PASS` while the underlying artifact is NOT actually, publicly,
currently, and correctly visible, and how each is closed. This table has been revised after
every review that found an uncovered path (rows 14-17 added iteration 4; rows 18-21 added this
iteration). A future review that finds a 22nd path has found a spec defect. Every row below
states explicitly which invocation path(s) — (i) build-time VCSDD gate, (ii) runtime
standalone loop, or both — it protects; a row that protects only (i) while REQ-011 requires
(ii) is not a closed row (this was FIND-H's exact finding against the iteration-3 table).

| # | Path to a false PASS | Applies to | Status | Closed by |
|---|---|---|---|---|
| 1 | Zero-citation PASS | (i)+(ii) | CLOSED | REQ-004/014 default-closed citation check, run by the shared `enforceVerdict` module for BOTH paths. PROP-022. |
| 2 | Citation from an authenticated-capture tool | (i)+(ii) | CLOSED | REQ-004 `tool` check, via `enforceVerdict`. PROP-010/018. |
| 3 | Citation resolves to no real row | (i)+(ii) | CLOSED | REQ-004 row-existence check, via `enforceVerdict`. PROP-011/018b. |
| 4 | Citation from a different/stale pass | (i)+(ii) | CLOSED | REQ-004 `passId`/`ts` check, via `enforceVerdict`. PROP-012. |
| 5 | LLM self-declares `claimType` | (i)+(ii) | CLOSED | REQ-013/015: `claimType` sourced ONLY from committed `reality-claim.json`, threaded to `enforceVerdict` by the CALLER, never the verdict. |
| 6 | Cites 1 of N required URLs | (i)+(ii) | CLOSED | REQ-004 `requiredArtifactCount`, via `enforceVerdict`. PROP-023. |
| 7 | Same row cited N times | (i)+(ii) | CLOSED | REQ-004 distinctness dedup, via `enforceVerdict`. PROP-023. |
| 8 | Non-2xx status counted as sufficient | (i)+(ii) | CLOSED | REQ-004 status gate, via `enforceVerdict`. PROP-024. |
| 9 | Caller mispropagates the backstop's verdict | (i)+(ii) | CLOSED | REQ-014: `enforceVerdict`'s return value IS the accepted verdict, by construction — there is no separate "caller decides what to pass to recordGate/the trail" step left to get wrong. PROP-025/039. |
| 10 | `gates.reality` recorded but never checked before VCSDD convergence | (i) only (row is VCSDD-specific by nature — (ii) has no convergence concept, REQ-011) | CLOSED | REQ-009: required `.githooks/pre-push` wiring. PROP-027. |
| 11 | `SKIP` treated as convergence-sufficient for a real claim | (i) only | CLOSED | REQ-009/013: `SKIP` legal only when `claimType === "none"`. PROP-026. |
| 14 | Citation resolves cleanly but for the WRONG (real, public) URL, or redirects off the artifact | (i)+(ii) | CLOSED | REQ-004 `canonicalizeUrl`/URL-identity + no-redirect checks, via `enforceVerdict`. PROP-028/029/030/041. |
| 15 | `gates.reality` not bound to a specific `reality-claim.json` version | (i) only (claim-versioning is a VCSDD-gate concept; (ii)'s per-run calls have no stored gate to go stale — each run is independently, freshly enforced) | CLOSED | REQ-008/009 `hashRealityClaim` binding. PROP-031. |
| 16 | Local git hook bypass by an agent with shell access | (i) only | **OPEN — disclosed, structural limit** | See "Local-hook trust boundary" below. PROP-027/032 mitigate, do not close. |
| 17 | Capture signal not proven diagnostic for the platform | (i)+(ii) | MITIGATED — empirically gated, fail-closed when unproven | REQ-012/013 `automatedVerification`, now DEFAULT `false` (FIND-K fix) and enforced by the shared `enforceVerdict` module for BOTH paths (FIND-H fix — this is the single most important repair this iteration makes, since row 17 previously only ever reached path (i)). PROP-034/038. |
| **18** | **(FIND-H/L) The deterministic backstop (REQ-004) exists but is never invoked on the standalone/runtime path (REQ-011's own named first customer) at all — a raw, self-reported LLM verdict is accepted as-is for that path** | **(ii), was completely unprotected** | **CLOSED** | **REQ-014: ONE shared, pure `enforceVerdict` module. `reality-verify-spawn.sh` is redesigned from detached fire-and-forget to a BLOCKING call (mirrors `gig_reality_verify.sh`'s real, working pattern) that ALWAYS calls `enforceVerdict` before writing any verdict to REQ-006's trail. The VCSDD gate script calls the SAME module (via the same script or the same underlying Node function) rather than reimplementing it. A verdict that has not passed `enforceVerdict` is defined to be `FAIL`, not merely "unchecked." PROP-039/040.** |
| **19** | **(FIND-I) For a `caller-per-invocation` claim, the loop under test supplies `claimedUrls` itself — the accused choosing its own alibi. A real, public, but WRONG (unrelated) URL from the same account satisfies every prior check** | **(i)+(ii)** | **CLOSED** | **REQ-015: ground truth for a `caller-per-invocation` claim is re-anchored to two things the loop CANNOT author after the fact: (a) a fixed, spec-time-constant public surface (e.g. the account's public profile/feed URL, declared in `reality-claim.json`, Phase-1c-reviewed) that the claimed artifact must actually appear ON, and (b) a content fingerprint the loop must pre-commit BEFORE attempting the post (a timestamped, append-only record), which the captured artifact's content must match. The loop-supplied URL is explicitly redefined as a convenience LOCATOR only, never ground truth on its own. PROP-035/036/037.** |
| **20** | **(FIND-J) `canonicalizeUrl` stripped the entire query string, silently equating distinct, query-identified real artifacts (e.g. two different YouTube videos, `?v=A` vs `?v=B`) — defeating row 14's URL-identity check for any such platform** | **(i)+(ii)** | **CLOSED** | **`canonicalizeUrl` redesigned: strips ONLY a small, fixed, declared allowlist of tracking parameters (`utm_*`, `fbclid`, `igshid`, `gclid`, `ref`, `ref_src`); every other query parameter is preserved, sorted, and compared as part of the canonical identity. An unrecognized platform's query semantics are never assumed safe to strip — the default is to PRESERVE, which fails closed (over-strict, never over-permissive) rather than silently collapsing distinct resources. PROP-041.** |
| **21** | **(FIND-K) `automatedVerification` defaulted `true` (fail-open) — an author who forgot to set it for a brand-new, unproven platform got automated-`PASS` eligibility by default** | **(i)+(ii)** | **CLOSED** | **`reality-claim.json`'s schema now defaults `automatedVerification` to `false` — mirrors `requiredArtifactCount`'s own fail-closed default precedent in this same spec. An OMITTED field is treated identically to an explicit `false` by `enforceVerdict`, never inferred `true`. PROP-038.** |
| 12 | Bash-capable verifier hand-forges a fake `artifacts.jsonl` row | (i)+(ii) | NOT closed — accepted, inherited residual risk (matches `gig_reality_gate.py`/`cdp_nav_snapshot.py`'s identical, pre-existing gap) | — |
| 13 | TOCTOU: public at verification time, taken down immediately after | (i)+(ii) | NOT closed — inherent to any point-in-time check | REQ-006's trail makes it discoverable in hindsight, not prevented. This feature does not itself re-check old URLs later. |

Rows 12, 13, and 16 are OPEN by explicit, reasoned disclosure. A row is only ever removed from
"open"/"unprotected for a given path" by a required proof obligation that forces it for THAT
path — never by argument, and never by a mechanism that happens to exist for the OTHER path.

### Local-hook trust boundary (FIND-F disposition — orchestrator's reasoning, not paraphrased; unchanged this iteration)

> An agent with shell access can bypass ANY local git hook (`--no-verify`, `chmod -x`, unset
> `core.hooksPath`, stale checkout). Therefore a local hook is not a security boundary against
> an adversarial insider — it is a discipline boundary against accident and drift, and that is
> all we should claim for it. Pretending otherwise is exactly the kind of false assurance this
> feature exists to kill.

Adopted verbatim, unchanged. Note (per iteration-4 review's own judgment, worth stating
explicitly): row 16 only ever mattered for path (i), the VCSDD-gate/convergence use case —
REQ-011's standalone runtime customer never touches `.githooks/pre-push`, `state.json`, or
`gates.reality` at all, so this disclosed limit was never the reason the gate was unready for
its actual first customer; FIND-H/I/J (row 18/19/20 above) were.

## Purity boundary analysis (top-level, elaborated per-requirement below)

- **Pure / deterministic core** (side-effect-free, unit- and property-testable), all in
  `skills/self/lib/reality-verdict-schema.mjs`:
  - the finding-category catalog and its validators (`FINDING_CATEGORIES`, `isKnownCategory`,
    `validateVerdictShape`) — extended, not replaced;
  - path/line derivation for the durable verdict trail (REQ-006) and the artifact trail
    (REQ-012);
  - `canonicalizeUrl(url)` (closure row 14/20) — deterministic URL normalization: scheme/host
    lowercased, default port stripped, `http:`→`https:` upgraded for comparison, trailing
    slash normalized on a non-root path, fragment stripped (never identity-bearing on the
    platforms this feature targets), and — as of this iteration — ONLY a fixed, declared
    allowlist of tracking query parameters stripped (`utm_source`, `utm_medium`,
    `utm_campaign`, `utm_term`, `utm_content`, `fbclid`, `igshid`, `gclid`, `ref`, `ref_src`);
    every OTHER query parameter is preserved, sorted by key, and included in the canonical
    value. No I/O, total (malformed input canonicalizes to a fixed sentinel that never equals
    a well-formed value, never throws).
  - `computeContentFingerprint(content)` (new, closure row 19) — deterministic:
    Unicode-NFC-normalizes and trims the input string, then `sha256` hex digest. Pure, no I/O.
  - `hashRealityClaim(realityClaim)` (closure row 15) — canonical-JSON-then-sha256 content
    hash, mirrors the plugin's own `computeContentDigest` precedent. No I/O beyond hashing.
  - `validateArtifactProvenance(verdict, capturedArtifacts, claimType, requiredArtifactCount,
    groundTruth)` (REQ-004/015) — the default-closed, count-aware, status-gated, URL-bound,
    and (for a `caller-per-invocation` claim) fixed-surface-and-fingerprint-bound provenance
    check (closure rows 1-4, 6-8, 14, 19, 20). `groundTruth` bundles `claimedUrls`/
    `fixedPublicSurfaceUrl`/`precommit` so the parameter list does not grow unboundedly as
    more ground-truth anchors are added.
  - `enforceVerdict(rawVerdict, capturedArtifacts, claimType, requiredArtifactCount,
    groundTruth, automatedVerification)` (new, closure rows 18, 21) — the ONE shared
    enforcement composition: `validateVerdictShape` → `automatedVerification`-refusal →
    `validateArtifactProvenance`. This is the SOLE function either invocation path is allowed
    to treat a raw LLM verdict as accepted through.
  - `decideConvergenceGate(state, realityClaim)` (closure rows 11, 15) — the SKIP-aware,
    hash-bound VCSDD convergence decision, shared byte-identical between the pre-push guard
    and the standalone backstop.
- **Effectful shell** (not unit-tested; verified only by real spawns / own-eyes review):
  - `.claude/agents/reality-verifier.md` — the LLM's own judgment when it actually reasons;
  - `skills/self/reality-verify-spawn.sh` (REQ-005/014) — REDESIGNED this iteration from a
    detached, fire-and-forget `tmux new-session -d` to a BLOCKING, foreground `claude -p`
    invocation (mirrors `gig_reality_verify.sh`'s own real, working pattern), that reads the
    resulting `RESULT` file and `artifacts.jsonl`, calls `enforceVerdict`, and appends the
    ENFORCED (never the raw) verdict to REQ-006's trail — the single call site through which
    EVERY runtime verdict passes, for every caller, including a future growth-engine loop;
  - `skills/self/scripts/public_artifact_snapshot.py` (REQ-012) — the deterministic
    logged-out capture tool; real network fetch, real file append;
  - `skills/self/reality-precommit.mjs` (new, REQ-015) — effectful: appends a
    `{ts, loopName, contentFingerprint}` row to
    `$HOME/.openclaw/state/reality-precommit-<loop>.jsonl`, called by a posting loop BEFORE
    it attempts to post — the timestamp ordering this creates is what `validateArtifactProvenance`
    later checks;
  - the VCSDD gate script (REQ-008) — REDESIGNED this iteration to CALL
    `reality-verify-spawn.sh` (or the same underlying Node `enforceVerdict` function directly)
    for an already-enforced verdict, rather than reimplementing enforcement itself; layers
    only its OWN VCSDD-specific bookkeeping on top (`hashRealityClaim`, `recordGate`);
  - `.claude/commands/vcsdd-reality.md` — instructional command definition, not code;
  - `.githooks/pre-push`'s Reality Convergence Guard section (REQ-009) — AUTHORITATIVE among
    Claude-Code-independent mechanisms for path (i), explicitly NOT adversarial-insider-proof
    (closure row 16);
  - `.claude/settings.json`'s `hooks.PreToolUse` entry — explicitly non-authoritative
    convenience only.

## Requirements

### REQ-001: `post_not_publicly_visible` finding category added, catalog stays backward compatible
**EARS**: WHEN reality-verifier checks a claim about a publicly-visible artifact THE SYSTEM
SHALL be able to emit a finding whose `category` is exactly `post_not_publicly_visible`,
distinct from the existing 6 categories, and existing consumers SHALL continue to accept all 6
unchanged.
**Edge Cases**: the length-6 test itself must change (VERIFIED, deliberate); `gig_*` never
imports `FINDING_CATEGORIES` (VERIFIED, not a compatibility concern).
**Acceptance Criteria**: `FINDING_CATEGORIES` has exactly 7 entries; `reality-verifier.md`
names/describes all 7; `validateVerdictShape()` accepts the new category with citeable
evidence, rejects it uncited.

### REQ-002: `post_not_publicly_visible` is used specifically for report-vs-public-reality gaps
**EARS**: WHEN a report claims a published artifact AND evidence shows it absent/unreachable/
authenticated-only THE SYSTEM SHALL emit `post_not_publicly_visible`, not `narrate_only_claim`.
**Edge Cases**: content-mismatch at an otherwise-public URL uses this category too; timeout
fail-closes per the base feature's REQ-007.
**Acceptance Criteria**: prompt gives a concrete example distinguishing the two categories.

### REQ-003: Logged-out evidence MUST be independently captured, never the LLM's own prose, and its absence is itself a violation, checked via the SAME shared module on BOTH invocation paths (closure rows 1, 5, 18)
**EARS**: WHEN reality-verifier is asked to verify a claim of a *publicly visible* artifact
THE SYSTEM SHALL require that the evidence backing any `PASS` — or the absence of a finding —
was produced by REQ-012's deterministic capture tool for the EXACT claimed/located URL, and
`enforceVerdict` (REQ-014), invoked UNCONDITIONALLY by EVERY caller of a `reality-verifier`
spawn (the gate script AND `reality-verify-spawn.sh` itself, never by either path
reimplementing the check), SHALL enforce this as a default-closed rule.
**Rejected designs (do not reintroduce)**:
1. (iter. 1) substring-matching free-text evidence fields.
2. (iter. 2) validating only citations that already carry a `filePath`, ignoring `domExcerpt`-
   only evidence.
3. (iter. 3) validating that a citation resolves cleanly without checking it is FOR THE
   CLAIMED URL.
4. (iter. 4, FIND-H) building the check correctly, but wiring it into only ONE of the two
   invocation paths this same spec defines — a correct mechanism nobody calls, for a given
   path, is exactly as absent as no mechanism at all, for that path.
**Edge Cases**: a separate logged-in check MAY still use CDP:9222 under existing shared-lock
rules; ONLY the public-visibility check must go through REQ-012's tool + `enforceVerdict`. No
URL supplied at all for a public-artifact claim ⇒ the caller refuses to spawn (REQ-005 edge
case), never a silent pass. Artifact-trail forgery (row 12) and local-hook bypass (row 16) are
explicitly accepted, disclosed residual risk.
**Acceptance Criteria**:
- `.claude/agents/reality-verifier.md` instructs: call `public_artifact_snapshot.py` once per
  required URL from the SUPPLIED ground truth (never a model-derived URL); cite each row.
- `enforceVerdict` is invoked, unconditionally, by BOTH `reality-verify-spawn.sh` (grep-
  checkable: the call is unconditional in the script's control flow, not behind a flag) AND
  the gate script (which calls `reality-verify-spawn.sh` or the same underlying function,
  never a separate reimplementation) — this replaces the iteration-3 acceptance criterion that
  incorrectly scoped the check to "the gate script" alone (the exact contradiction FIND-H
  found between this requirement and REQ-011).

### REQ-004: Provenance backstop — default-closed, count-aware, status-gated, URL-bound, and fixed-surface/fingerprint-bound for caller-per-invocation claims (closure rows 1, 6, 7, 8, 14, 19, 20)
**EARS**: WHEN `enforceVerdict` runs `validateArtifactProvenance(verdict, capturedArtifacts,
claimType, requiredArtifactCount, groundTruth)` for a public-artifact claim THE SYSTEM SHALL
confirm ALL of the following (an open, growable set, not a fixed step count — a prior
iteration's "5-step" framing was itself an implicit, false completeness claim); ANY failure
downgrades to `overallVerdict: "FAIL"` with a `post_not_publicly_visible` finding naming the
specific shortfall:
- **Citation presence** (row 1): `>= requiredArtifactCount` distinct citations present at
  all — zero is itself a violation, checked first, unconditionally.
- **Resolution — identity** (rows 2-4): each citation resolves to a REAL row with
  `tool === "public_artifact_snapshot"`, matching `passId`, fresh `ts`.
- **Resolution — URL identity, no redirect** (row 14): `canonicalizeUrl(row.requestedUrl)`
  matches one of `groundTruth.claimedUrls` (the LOCATOR set — see below for what "matches"
  now additionally requires for a `caller-per-invocation` claim), and
  `canonicalizeUrl(row.finalUrl)` equals that SAME value (no redirect tolerated at all).
- **Resolution — status** (row 8): `httpStatus` in `[200,299]` (or tool-level success flag).
- **Distinctness + count** (rows 6, 7): deduplicated by `(passId, seq)`, `>=
  requiredArtifactCount` distinct fully-resolved citations.
- **Fixed-surface corroboration** (row 19, NEW, `caller-per-invocation` claims only): a
  SEPARATE citation resolving (by the SAME identity/status rules above) to
  `groundTruth.fixedPublicSurfaceUrl` (the account's spec-time-declared public profile/feed
  URL) MUST also be present, and that row's `referencedArtifactIds` field (a structured,
  tool-populated list — extraction mechanics are Phase 2a's job, the RULE is fixed now) MUST
  contain the locator artifact's canonical identifier. A locator citation with no
  corresponding fixed-surface corroboration is rejected (`not_on_fixed_surface`).
- **Content-fingerprint match** (row 19, NEW, `caller-per-invocation` claims only): the
  locator row's `contentHash` field (tool-populated, deterministic extraction+hash — Phase
  2a's job to implement, the comparison RULE is fixed now) MUST equal
  `groundTruth.precommit.contentFingerprint`. Mismatch ⇒ `fingerprint_mismatch`.
- **Precommit ordering** (row 19, NEW): `groundTruth.precommit.ts` MUST be strictly earlier
  than the capturing pass's start timestamp — a fingerprint recorded AFTER the fact (or after
  seeing what public content exists) does not count. Violation ⇒ `precommit_not_before_action`.
The fixed-surface/fingerprint/ordering checks apply ONLY when `groundTruth.mode ===
"caller-per-invocation"` (mirrors `reality-claim.json`'s `urlSource`); a `"fixed"`-mode claim
(spec-time-known URL, no loop-under-test-originated ground truth at all) is unaffected —
FIND-I's exploit does not apply there, since nothing about a `"fixed"` claim's ground truth is
authored by the loop being graded.
`validateArtifactProvenance` never mutates its inputs, never touches `fs` itself.
**Edge Cases**: `requiredArtifactCount` `0`/omitted ⇒ defaults `1`, never `0`. `claimedUrls`
empty for a public-artifact claim ⇒ caller refuses to invoke the verifier at all. Duplicate
entries in `claimedUrls` are harmless. `enforceVerdict`'s return value is, by construction, the
only thing any caller is permitted to record/append (closure row 9 — there is no longer a
separate "did the caller propagate correctly" question; propagation IS the function's return).
**Acceptance Criteria** (each `required: true` — see verification-architecture.md
PROP-022..041):
- Zero-citation PASS → FAIL (PROP-022). Auth-tool citation → FAIL (PROP-010/018).
  Nonexistent-row citation → FAIL (PROP-011/018b). Stale/foreign-pass citation → FAIL
  (PROP-012). Wrong-URL citation (real, public, unrelated page) → FAIL (PROP-028). Redirect-
  off-artifact (login-wall/interstitial, even HTTP 200) → FAIL (PROP-029). Same-URL-cited-
  twice padding a 2-URL requirement → FAIL (PROP-030). Under-count → FAIL (PROP-023).
  Duplicate-row padding → FAIL (PROP-023). Non-2xx status → FAIL (PROP-024).
- **NEW**: locator resolves cleanly (real, public, correctly-tooled, correct URL per its OWN
  claim) but is NOT present on the fixed public surface (`referencedArtifactIds` doesn't
  include it) → FAIL (PROP-036).
- **NEW**: locator resolves cleanly, IS on the fixed surface, but its `contentHash` does not
  match the pre-committed `contentFingerprint` (fixture: a real, old, unrelated post from the
  same account, cited as if it were the new claim) → FAIL (PROP-035 — the direct, named fix
  for FIND-I's exact exploit scenario).
- **NEW**: a distinct fingerprint-mismatch fixture where the cited content is fresh (same pass,
  correct URL, present on the fixed surface) but its extracted content differs from the
  pre-committed fingerprint (e.g. caption drift/bug, not merely "an old post") → FAIL
  (PROP-037).
- **NEW**: two query-identified-but-otherwise-identical URLs (`?v=A` claimed,
  `?v=B` cited) do NOT canonicalize equal and the citation is rejected as wrong-URL → FAIL
  (PROP-041, the direct fix for FIND-J).

### REQ-005: Generalized, BLOCKING spawn wrapper — any claim type, deterministic count/URLs/ground-truth, backward compatible with the real existing caller
**EARS**: WHEN a caller needs to verify a real-world side-effect claim THE SYSTEM SHALL
provide `skills/self/reality-verify-spawn.sh` accepting `<loop-name>
<artifact-or-public-url> [claim-text] [claim-type] [pass-id] [required-artifact-count]
[claimed-urls] [fixed-public-surface-url] [content-fingerprint] [precommit-ts]` — with the
allowance that Phase 2a MAY switch to a single `--config <json-path>` flag once the
positional-arg count is judged unmaintainable, PROVIDED the pre-existing 3-positional-argument
invocation (`reality-verify-on-new-earn.sh`, the one real existing caller, VERIFIED) continues
to work unchanged either way. THE SYSTEM SHALL run this call to COMPLETION (blocking, capped at
600s — mirrors `gig_reality_verify.sh`'s real `timeout 600 "$CLAUDE" -p ...` pattern) rather
than the prior detached, fire-and-forget `tmux new-session -d` behavior, and SHALL
unconditionally call `enforceVerdict` (REQ-014) on the result before appending anything to
REQ-006's durable trail. A loop making a NEW post SHALL supply the real URL it received back
from the platform (`claimed-urls`, now explicitly a LOCATOR, never ground truth alone — REQ-015)
and, for a `caller-per-invocation` claim, SHALL have already called
`skills/self/reality-precommit.mjs` BEFORE attempting the post, supplying that record's
timestamp as `precommit-ts` and its fingerprint as `content-fingerprint`.
**Edge Cases**: unrecognized `claim-type` ⇒ generic handling, no REQ-012 tool requirement. No
URL at all for a public-artifact `claim-type` ⇒ refuse to spawn (non-zero exit) before any
`claude` invocation. The blocking-vs-previously-detached behavior change is a deliberate,
disclosed timing/performance tradeoff (NFR) made to close FIND-H — closing the vulnerability
class takes priority over preserving the prior near-instant return time; the existing `earn`
caller's own control flow (fire specific ledgers in a loop, never reads results) is unaffected
in its OWN semantics by each individual call now taking longer.
**Acceptance Criteria**:
- `test-reality-verify-spawn.sh`'s existing 3 assertion groups (A/B/C) pass unchanged.
- The script's implementation contains a blocking `claude -p ... --output-format text`
  invocation under a `timeout 600` (or equivalent), NOT a detached `tmux new-session -d` for
  the actual verifier call — grep-checkable.
- A DRYRUN assertion confirms all new arguments thread into the spawned task text with
  documented defaults, and that a missing URL for a public-artifact claim exits non-zero
  before any spawn.
- **Required PROP** (PROP-040): a fixture test proves that when the underlying (stubbed)
  verifier output would be `PASS` but `enforceVerdict` (given the same fixture
  `capturedArtifacts`/`groundTruth`) would downgrade it to `FAIL`, the trail line
  `reality-verify-spawn.sh` itself appends reflects `FAIL` — the runtime path actually rejects
  a verdict the module rejects, not merely "could in theory."

### REQ-006: Durable per-loop verdict trail
**EARS**: WHEN an ENFORCED verdict (REQ-014's `enforceVerdict` output, never a raw one) is
produced for loop `<L>` THE SYSTEM SHALL append one JSON line to
`$HOME/.openclaw/state/reality-verdict-<L>.jsonl` with at minimum timestamp, `overallVerdict`,
`findings`, and the `RESULT` path.
**Edge Cases**: concurrent appends never overwrite; file created on first append.
**Acceptance Criteria**: `buildVerdictTrailPath` deterministic, unit-tested; after a real/
fixture run, the trail's last line parses as JSON matching the shape.

### REQ-007: Negative test — fail-closed proof (a gate that cannot fail is not a gate)
**EARS**: WHEN `enforceVerdict` is given a FALSE or unprovable claim, on EITHER invocation
path, THE SYSTEM SHALL produce `overallVerdict: "FAIL"`, demonstrated by:
1. All of REQ-004's unit-test bypass fixtures.
2. A real, live fresh `reality-verifier` spawn (via `reality-verify-spawn.sh`, the runtime
   path itself — not the gate script) against a genuinely nonexistent public URL, producing an
   on-disk FAIL verdict.
3. A real, live spawn where the located URL is a genuinely DIFFERENT real, public page —
   proving both the URL-mismatch check AND (if a `caller-per-invocation` fixture) the
   fingerprint check fire for real.
**Edge Cases**: unambiguous random-UUID 404 for #2; genuinely unrelated real page for #3;
retry once on flaky network before treating as proof (still fail-closed either way).
**Acceptance Criteria**: all REQ-004 bypass unit tests pass; both live FAIL artifacts
committed under `.vcsdd/features/reality-gate/evidence/`, produced via the RUNTIME path
(`reality-verify-spawn.sh`) specifically, not only the gate script — this is the live-run
proof that closure row 18's fix actually reaches REQ-011's named customer.

### REQ-008: VCSDD Phase 4.5 REALITY GATE — `vcsdd-reality` command calls the SAME shared enforcement path, then layers VCSDD-specific bookkeeping (closure rows 15, 18)
**EARS**: WHEN a VCSDD feature has passed adversarial review THE SYSTEM SHALL provide a
`/vcsdd-reality` command that obtains an ALREADY-ENFORCED verdict by calling
`reality-verify-spawn.sh` (REQ-005/014) — or the same underlying Node `enforceVerdict`
function directly — never by reimplementing enforcement, sources
`claimType`/`requiredArtifactCount`/`groundTruth`/`automatedVerification` EXCLUSIVELY from
`reality-claim.json` (REQ-013), and records into `state.json` via `recordGate(featureName,
'reality', verdict, reviewedBy, details)` using ONLY schema-legal values (VERIFIED,
`"verdict":{"enum":["PASS","FAIL","SKIP"]}`, `"reviewedBy":{"enum":
["adversary","verifier","human"]}`), where `verdict` is ALWAYS `enforceVerdict`'s actual
returned `overallVerdict` and `details` ALWAYS includes `{claimType, requiredArtifactCount,
groundTruth, realityClaimHash: hashRealityClaim(realityClaim)}`.
**Edge Cases**: plugin cache updates don't affect this feature. `claimType: "none"` ⇒
`gates.reality = {verdict:"SKIP", reviewedBy:"human", details:{claimType:"none",
realityClaimHash, reason}}`. `automatedVerification === false` (now the DEFAULT, FIND-K) ⇒
`/vcsdd-reality` MUST NOT record `reviewedBy: "verifier"` at all — only `"human"`.
**Acceptance Criteria**: command file at `.claude/commands/vcsdd-reality.md`, not plugin
cache; instructions state, grep-checkably, both the "never reimplement `enforceVerdict`,
always call the same shared path" rule (closure row 18, FIND-L) and the
`reality-claim.json`-only sourcing rule; `gates.reality.details.realityClaimHash` present and
correct (fixture test); `recordGate` calls with schema-legal values don't throw against the
real, unmodified schema validator; a fixture test proves `recordGate`'s `verdict` argument
always equals `enforceVerdict`'s actual return.

### REQ-009: Convergence requires the reality gate — hash-bound, enforced at a real, authoritative (not adversarial-insider-proof) point (closure rows 10, 11, 15, 16)
**EARS**: WHEN a feature attempts VCSDD completion THE SYSTEM SHALL require, beyond the
plugin's existing 4-dimension check (VERIFIED zero reference to `gates.reality`), that
`decideConvergenceGate(state, realityClaim)` returns `blocked: false`: iff `verdict ===
"PASS"` AND `hashRealityClaim(realityClaim) === details.realityClaimHash`, OR (`verdict ===
"SKIP"` AND `claimType === "none"` AND the same hash match); `blocked: true` otherwise
(missing, FAIL, illegal SKIP, or ANY hash mismatch). Enforced by `.githooks/pre-push`'s
Reality Convergence Guard (VERIFIED live via `.git/config`'s `core.hooksPath`), explicitly a
**discipline boundary, not a security boundary against an adversarial insider** (FIND-F
disposition).
**Edge Cases**: pre-existing feature with no `reality-claim.json` ⇒ `blocked: true`, never
inferred `"none"`. Guard fires only when a `state.json→complete` transition is part of the
pushed diff (matches Cadence Guard's own push-time scope). Local-hook bypass (row 16)
explicitly out of scope, disclosed.
**Acceptance Criteria**: `.githooks/pre-push` contains the new section, grep-checkable;
diff-aware live-fire test (PROP-027) covers missing/FAIL → reject, matching-hash PASS →
accept, stale-hash same-push-downgrade → reject; `decideConvergenceGate` unit-tested
(PROP-026/031); regression-lock test for the guard's own section (PROP-032); `PreToolUse`
entry/prose contains "non-authoritative"/"best-effort".

### REQ-010: reality-verifier stays read-only; FAIL escalates to self-fix, never self-repairs
**EARS**: WHEN `enforceVerdict` yields `FAIL`, on EITHER path, THE SYSTEM SHALL NOT permit the
gate script, spawn wrapper, or `reality-verifier` itself to edit any file; it SHALL invoke
`self-fix.sh <name> "<blocker+hint>"` (mirrors `gig_reality_verify.sh`).
**Edge Cases**: `self-fix.sh` dedupe/staleness logic already handles concurrent calls; neither
enforcement caller needs `Write`/`Edit` tool usage.
**Acceptance Criteria**: `reality-verifier.md`'s `tools` stays exactly `["Read","Grep","Glob","Bash"]`;
both the gate script's AND `reality-verify-spawn.sh`'s FAIL paths contain a literal
`self-fix.sh` call and no file-editing operation.

### REQ-011: First customer / acceptance vehicle — now actually protected by the SAME mechanisms as the VCSDD gate (closure row 18 fix makes this claim true)
**EARS**: WHEN the growth-engine marketing loop claims it posted a video to Instagram THE
SYSTEM's reality gate SHALL prove or disprove that claim via REQ-002's category and
REQ-003/004/012/014/015's independently-captured, logged-out, count-and-status-gated,
URL-bound, fixed-surface-and-fingerprint-bound check — via `enforceVerdict`, invoked
UNCONDITIONALLY by `reality-verify-spawn.sh` itself (REQ-014), the SAME shared module the
VCSDD gate script calls, not a separate or absent mechanism. This IS a standalone
loop-verification call (REQ-005): no `state.json`, no `gates.reality`, no `SKIP`, no
`reality-claim.json` (that file's `claimType`/`requiredArtifactCount`/`groundTruth`/
`automatedVerification` are still read by the CALLER and threaded as deterministic arguments
into `reality-verify-spawn.sh` — REQ-013 applies to WHERE this config lives and how it's
reviewed, not only to the VCSDD-gate invocation pattern). The loop MUST call
`reality-precommit.mjs` before each post attempt (REQ-015). A failed verification produces a
`FAIL` verdict + trail line and escalates via REQ-010.
**Edge Cases**: N/A — satisfied by REQ-001..004/012/014/015 being general-purpose, subject to
REQ-012/013's `automatedVerification` precondition (default `false`) actually being flipped
`true` for Instagram only after Phase 2a proves it diagnostic.
**Acceptance Criteria**: nothing platform-hardcoded; the loop-verification-vs-VCSDD-gate
distinction stated explicitly in `reality-verify-spawn.sh`'s own documentation; **this
requirement's EARS claim (protections apply to the standalone path) is proven true by
REQ-003/005's acceptance criteria requiring `enforceVerdict` be invoked unconditionally by
`reality-verify-spawn.sh` itself — no acceptance criterion anywhere in this spec scopes any
backstop to "the gate script" alone anymore** (this sentence exists specifically so a future
review can grep for a reintroduced scoping contradiction, per FIND-H's own finding method).

### REQ-012: Deterministic logged-out capture tool — mirrors `cdp_nav_snapshot.py`, diverges on auth, proven diagnostic before automated reliance, on EITHER path (closure row 17, FIND-G/H/K)
**EARS**: WHEN a public URL needs checking THE SYSTEM SHALL provide
`public_artifact_snapshot.py <passId> <seq> <label> <url>` — deterministic, never touches
CDP:9222, appends one row to `.../reality-artifacts/<passId>/artifacts.jsonl` with at minimum
`{ts, passId, seq, label, tool, requestedUrl, finalUrl, httpStatus, domExcerpt}`, plus (new,
REQ-015) `contentHash` and `referencedArtifactIds` fields for `caller-per-invocation` claims —
never raising.
**Diagnosability precondition**: no AUTOMATED verdict on any platform until Phase 2a
empirically proves — against a real known-public and real known-removed URL — that a
structured signal reliably differs AND (new, REQ-015) that `referencedArtifactIds`/
`contentHash` extraction works reliably for that platform. Recorded per-platform.
**Honest current state (no live fetches performed this session)**: per general, unverified
training knowledge, Instagram's plain `httpStatus` is unlikely to be diagnostic (SPA shell
commonly `200` regardless); a `domExcerpt`-text "isn't available" interstitial is a plausible
signal IF confirmed empirically. Fallback order if unproven: (1) headless-browser render
check; (2) a second independent public surface (e.g. search-engine index presence); (3) if
still unproven, `automatedVerification` STAYS at its `false` default (FIND-K) — never manually
overridden to `true` without the Phase 2a evidence.
**`automatedVerification` gate — mechanical, defaults fail-closed (FIND-K fix), enforced by
`enforceVerdict` on BOTH paths (FIND-H fix)**: `reality-claim.json.automatedVerification`
DEFAULTS `false`. `enforceVerdict` refuses (fail-closed, explicit error, never silent) to
produce an accepted verdict via `reviewedBy: "verifier"`-equivalent automated processing
unless `automatedVerification === true` EXPLICITLY — an omitted field is treated identically
to explicit `false`, never inferred `true`.
**Edge Cases**: JS-rendering platforms prefer headless-browser variant. Anti-bot 403s captured
and rejected by the status gate (accepted false-negative risk).
**Acceptance Criteria**: no `9222` reference in the tool's source; distinct directory/`tool`
field from gig's; every row has `httpStatus`. **Required**: `automatedVerification` OMITTED
(not explicitly `false`) for a `claimType !== "none"` claim is refused by `enforceVerdict`
exactly as if explicitly `false` (PROP-038 — the distinct fixture FIND-K's own critique
demanded, separate from PROP-034's explicit-`false` case). **Required**: `enforceVerdict`'s
refusal fires on BOTH the gate-script path AND the `reality-verify-spawn.sh` path for the
identical fixture (PROP-034/038 both run against `enforceVerdict` directly, which is shared —
this is what makes the "on either path" claim mechanically true rather than asserted).
**Phase-2a-gated**: once a signal/extraction is recorded for Instagram, PROP-033 becomes
required; until then it is `pending`, not omitted.

### REQ-013: `reality-claim.json` — committed, spec-reviewed, deterministic claim declaration, fail-closed defaults, fixed-surface declaration (closure rows 5, 11, 14, 15, 17, 19, 21)
**EARS**: WHEN a VCSDD feature (or a runtime loop, for its OWN config convention — see
REQ-011) intends to be gated THE SYSTEM SHALL require a `reality-claim.json`-shaped
declaration, Phase-1c-reviewed for a VCSDD feature:
```json
{
  "claimType": "publish|post|deploy|earn|none",
  "requiredArtifactCount": "<integer, default 1, never 0>",
  "urlSource": "fixed|caller-per-invocation",
  "claimedUrls": "<string[], required+non-empty if urlSource=fixed>",
  "fixedPublicSurfaceUrl": "<string, REQUIRED if urlSource=caller-per-invocation and claimType is a public-artifact type>",
  "automatedVerification": "<boolean, DEFAULT false (fail-closed, FIND-K) — MUST be explicitly true, only after Phase 2a proof, REQ-012>",
  "description": "<what this claims, or why none exists>"
}
```
never writable by `reality-verifier` or the gate script at runtime.
**EARS (provenance, row 5/14)**: `claimType`/`requiredArtifactCount`/`claimedUrls`/
`fixedPublicSurfaceUrl`/`automatedVerification` sourced EXCLUSIVELY from this declaration
(plus, for `caller-per-invocation`, a mandatory per-invocation locator URL + precommitted
fingerprint, REQ-005/015) — NEVER from `verdict.claimType`, NEVER an ad-hoc CLI override of
the declaration's own fields.
**EARS (SKIP legality, row 11)**: `SKIP` convergence-sufficient ONLY when `claimType ===
"none"`.
**EARS (hash binding, row 15)**: every `recordGate` stores `hashRealityClaim(realityClaim)`;
`decideConvergenceGate` recomputes/compares every check.
**Trust boundary this requirement does NOT close (honest, explicit)**: `fixedPublicSurfaceUrl`
+ content-fingerprint pre-commitment (REQ-015) closes "the loop cites some OTHER real post of
its own" (FIND-I). It does NOT close a fully coordinated forgery where the loop fabricates
BOTH the precommit record AND the artifact-trail rows without ever touching the real platform
— that remains row 12's already-accepted, inherited residual risk (a Bash-capable adversarial
verifier can forge file content; this feature's defense against THAT class is, unchanged,
own-eyes/fresh-adversary review, never a file-content check the same adversary could also
forge).
**Edge Cases**: claim changes mid-development ⇒ update + re-review, hash-binding mechanically
enforces this. Pre-existing feature with none ⇒ `blocked: true`. Malformed ⇒ fail-closed.
`automatedVerification` omitted ⇒ treated as `false` (PROP-038).
**Acceptance Criteria**: command/gate-script docs state sourcing rule grep-checkably; unit
tests: SKIP+claimType legality (PROP-026); hash-mismatch always blocks (PROP-031);
`automatedVerification` false/omitted refuses `'verifier'` (PROP-034/038).

### REQ-014: Shared enforcement module — ONE module, TWO callers, no duplicated logic (new — closes FIND-H, FIND-L, closure row 18)
**EARS**: WHEN ANY `reality-verifier` verdict is produced, on ANY invocation path, THE SYSTEM
SHALL run it through exactly one shared, pure function —
`enforceVerdict(rawVerdict, capturedArtifacts, claimType, requiredArtifactCount, groundTruth,
automatedVerification)` in `skills/self/lib/reality-verdict-schema.mjs` — composed of, in
order: (1) `validateVerdictShape(rawVerdict)` (malformed shape ⇒ `FAIL`); (2) the
`automatedVerification` refusal rule (REQ-012/013, default `false`); (3), for a
public-artifact `claimType`, `validateArtifactProvenance(...)` (REQ-004). A verdict that has
not passed through `enforceVerdict` SHALL be treated as `overallVerdict: "FAIL"` by
definition — "unenforced" and "a verdict" are mutually exclusive states in this system, not
merely "unchecked" (a softer, unacceptable framing this iteration explicitly rejects).
**Wiring (both invocation paths call the SAME module, never duplicate its logic)**:
- `reality-verify-spawn.sh` (REQ-005) is the runtime path's SOLE call site: blocking, always
  reads the RESULT + artifact trail, always calls `enforceVerdict`, always writes the
  ENFORCED result to REQ-006's trail.
- The VCSDD gate script (REQ-008) CALLS `reality-verify-spawn.sh` (subprocess) or `require()`s
  the SAME `enforceVerdict` function directly — it MUST NOT contain its own parallel
  implementation of citation/URL/status/count/fixed-surface/fingerprint checking logic
  (grep-checkable: no duplicate `httpStatus`/`canonicalizeUrl`/`referencedArtifactIds`-style
  logic outside `reality-verdict-schema.mjs`). It layers ONLY VCSDD-specific bookkeeping
  (`hashRealityClaim`, `recordGate`) on top of the already-enforced result.
**Edge Cases**: the `REALITY_VERIFY_DRYRUN=1` seam is unaffected (exits before any
spawn/enforcement, pure path-derivation only). A caller needing async behavior (e.g. a fast
per-tick loop) may background `reality-verify-spawn.sh` itself in ITS OWN job runner — but the
script's own contract (blocks until an enforced verdict is written) never changes; any further
backgrounding is the caller's responsibility, not a second, weaker code path.
**Acceptance Criteria**:
- `enforceVerdict` exists, pure, composed of the 3 already-independently-tested steps;
  unit-tested as a composition (PROP-039).
- `reality-verify-spawn.sh`'s implementation contains no `tmux new-session -d` for the
  verifier call and DOES contain an unconditional `enforceVerdict` invocation before the trail
  append — grep-checkable (PROP-040, live/fixture-tested, see REQ-005).
- The gate script's source contains zero duplicated provenance-checking logic — grep-checkable
  absence of re-implemented citation/URL/status/fixed-surface/fingerprint logic outside
  `reality-verdict-schema.mjs`.
- REQ-011's EARS claim (protections reach the standalone customer) is now provably true,
  closing the exact spec-fidelity contradiction FIND-H found between iteration-4's REQ-003 and
  REQ-011.

### REQ-015: Ground-truth anchoring for `caller-per-invocation` claims — fixed public surface + pre-committed content fingerprint, never the loop's own after-the-fact URL alone (new — closes FIND-I, closure row 19)
**EARS**: WHEN a `caller-per-invocation` claim (e.g. the growth-engine daily post) is verified
THE SYSTEM SHALL treat the loop-supplied locator URL as a CONVENIENCE LOCATOR only, NEVER as
sufficient ground truth on its own, and SHALL additionally require: (a) the claimed artifact
actually appears on a FIXED, spec-time-constant public surface (`reality-claim.json`'s
`fixedPublicSurfaceUrl`, e.g. the account's public profile/feed — a value the loop under test
cannot choose or influence, reviewed at Phase 1c exactly like `claimedUrls` for a `"fixed"`
claim), and (b) the located artifact's content matches a fingerprint the loop PRE-COMMITTED
(via `skills/self/reality-precommit.mjs`) BEFORE attempting the post — i.e. before it could
know what public content, if any, would result, closing the "pick your alibi after seeing
what's real out there" attack that a bare locator-URL check cannot.
**Rejected design (iteration-4 FIND-I, do not reintroduce)**: treating a loop-supplied
`claimedUrls` value, for a claim about that SAME loop's own honesty, as ground truth
equivalent to `gig_reality_gate.py`'s `DEFAULT_GROUND_TRUTH_URLS` — this claim was made in
iteration 4 and was FALSE: `gig_judge.py:26-31`'s ground-truth URLs are a fixed, spec-time
Python constant the loop under test cannot influence at all; a loop choosing its own
per-invocation "ground truth" is the OPPOSITE trust model, not an equivalent one. This spec
does not repeat that claim anywhere; where a loop-supplied value is still used (the locator),
it is explicitly and permanently downgraded to "necessary, not sufficient."
**Edge Cases**: a fully coordinated forgery (fabricating the precommit record too) is NOT
closed by this requirement — see REQ-013's explicit trust-boundary disclosure (row 12,
unchanged, honestly still open). The precommit record itself must be append-only/immutable
once written (mirrors REQ-006's trail durability) so a dishonest loop cannot retroactively
edit its own precommit after seeing what content became available.
**Acceptance Criteria**:
- `skills/self/reality-precommit.mjs` exists, appends `{ts, loopName, contentFingerprint}` to
  an append-only jsonl file, never overwrites.
- `computeContentFingerprint(content)` is pure, deterministic, unit-tested.
- `validateArtifactProvenance`'s fixed-surface/fingerprint/ordering checks (REQ-004) are
  `required: true` and exercised by PROP-035/036/037 exactly as REQ-004 specifies.
- The false "VERIFIED matches gig" equivalence claim from iteration 4 does not appear anywhere
  in this spec after this iteration (grep-checkable: no sentence asserting `claimedUrls`
  alone, for a `caller-per-invocation` claim, "matches" or "mirrors" gig's fixed-constant
  ground-truth model).

## Non-functional requirements

- **Performance bound**: `reality-verify-spawn.sh`/`/vcsdd-reality` capped at 600s (mirrors
  gig); on timeout, `enforceVerdict`'s caller records `FAIL` (fail-closed, never `SKIP`).
  **Disclosed change this iteration**: the runtime path now BLOCKS up to 600s per verification
  (was near-instant detached fire-and-forget) — a deliberate tradeoff to close FIND-H, not an
  oversight.
- **Security constraint**: no signing/keypair/private-key library anywhere in this feature.
- **Security constraint**: all pure functions (`validateArtifactProvenance`,
  `decideConvergenceGate`, `canonicalizeUrl`, `hashRealityClaim`, `computeContentFingerprint`,
  `enforceVerdict`) have no network/file access.
- **Security constraint**: `public_artifact_snapshot.py` structurally incapable of
  authenticated access.
- **Security constraint**: `reality-claim.json` and the precommit record are never written by
  any component that also produces the verdict checked against them.
- **Disclosed limit**: `.githooks/pre-push` is a discipline boundary, not a security boundary
  against an adversarial insider (row 16). A fully coordinated forgery of both the precommit
  record and the artifact trail is row 12's already-accepted residual risk, unchanged by
  REQ-015.

## Judgment vs determinism (anti-hardcoding discipline)

Per `~/.claude/rules/building-effective-ai-agents.md`: whether a report is honest, whether a
finding fits `post_not_publicly_visible` vs `narrate_only_claim`, and whether `domExcerpt`
content at a confirmed-2xx, confirmed-correct, confirmed-on-the-fixed-surface,
confirmed-fingerprint-matching URL actually LOOKS like the claim describes remain JUDGMENT
calls, made by the LLM. Everything deterministic in this feature, exhaustively: category
membership; the provenance/count/status/URL/fixed-surface/fingerprint/precommit-ordering
checks (structural lookups against independently-captured or pre-committed structured data,
never prose); URL canonicalization (a fixed, now-conservative allowlist-only normalization,
never assuming a platform's query semantics are safe to discard); the claim-hash binding; the
`automatedVerification` refusal (fail-closed default); `enforceVerdict`'s composition itself
(a fixed pipeline, not a judgment about which checks "probably" apply); jsonl path derivation;
gate recording. Every rejected design across all 5 iterations — substring-marker matching,
citation-presence-optional, URL-blind resolution, single-path wiring, loop-supplied-URL-as-
ground-truth, and query-string discarding — was the SAME underlying mistake at a different
granularity: treating the ABSENCE of a caught problem, the PRESENCE of *some* real evidence, or
a mechanism existing on *one* path, as equivalent to AFFIRMATIVE, COMPLETE, EVERYWHERE-ENFORCED
proof of the specific claimed fact. The rule, stated once, finally, generally: **a
public-artifact `PASS` requires affirmative, counted, resolved, fresh, correctly-URLed,
non-redirected, correctly-tooled, 2xx-status, fixed-surface-corroborated,
fingerprint-matched proof of the EXACT caller-declared claim, produced by the ONE shared
enforcement path every invocation route is required to use, bound by content hash to the exact
claim it was checked against — never the mere absence of a caught violation, never proof of
some adjacent true fact, and never a protection that exists for one caller but not another.**
