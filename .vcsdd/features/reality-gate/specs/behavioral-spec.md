# Behavioral Spec: reality-gate (Phase 4.5 REALITY GATE, VCSDD pipeline extension)

Scope: `docs/superpowers/specs/2026-07-13-growth-engine-self-improving-promotion-skill-design.md`
§8b V0 / §8c (motivating gap analysis), in the `anicca-project` repo.
Builds on the already-shipped `reality-verifier` feature (see
`.vcsdd/features/reality-verifier/specs/behavioral-spec.md`) — this feature does NOT
re-implement reality-verifier; it (a) extends its category catalog and prompt from
money/ledger-only to any real-world side-effect claim, (b) generalizes its spawn wrapper,
(c) adds a durable per-loop verdict trail, (d) proves it is fail-closed with real negative
tests, and (e) wires it into VCSDD as a gate between adversarial review and formal hardening.

**Escalation notice**: this feature hit the max Phase 1c review iteration limit (5) with 2
blocking findings remaining and was granted ONE bounded, scope-limited iteration 6 by the
orchestrator (`.vcsdd/features/reality-gate/escalations/escalation-01-spec-review.md`), strictly
limited to FIND-M + FIND-N (+ majors FIND-O/FIND-P). This iteration adds NO scope beyond
those four findings.

## Iteration history (Phase 1c)

| Iteration | Verdict | Findings | Disposition |
|---|---|---|---|
| 1 | FAIL | FIND-001 (recordGate enum crash), FIND-002 (backstop inspected LLM's own prose) | Fixed iter. 2: schema-legal `recordGate`; structural `validateArtifactProvenance`. |
| 2 | FAIL | FIND-A (zero-citation PASS unguarded), FIND-B (`gates.reality` not wired to enforcement), FIND-C (`claimType` provenance unpinned) | Fixed iter. 3: default-closed citation check; required `.githooks/pre-push` wiring; `reality-claim.json`. |
| 3 | FAIL | FIND-D (cited row's URL never checked), FIND-E (gate not bound to claim version), FIND-F (local-hook bypass — downgraded to disclosed limit by ruling), FIND-G (diagnosability unproven) | Fixed iter. 4: `claimedUrls`/`canonicalizeUrl` URL binding; `hashRealityClaim` claim-version binding; explicit disclosed-limit row for local hooks; `automatedVerification` refusal rule. |
| 4 | FAIL | FIND-H (backstop wired only into the gate script, never the runtime path REQ-011 names as first customer), FIND-I (`claimedUrls` for a per-invocation claim is loop-self-supplied — a false "matches gig" equivalence claim was made), FIND-J (`canonicalizeUrl` collapsed query-identified artifacts), FIND-K (`automatedVerification` fail-open default), FIND-L (no shared enforcement module) | Fixed iter. 5: `enforceVerdict` shared module reaching both paths; fixed-surface + pre-committed-fingerprint ground truth; allowlist-only query canonicalization; fail-closed default. |
| 5 (`reviews/spec-review-05.md`, FINAL scheduled iteration — hit max, escalated) | FAIL, 2 blocking | Independently CONFIRMED FIND-H/I/J/K/L are structurally, genuinely fixed (not restated). NEW: **FIND-M (blocking, the inverse bug)** — `enforceVerdict`'s composition ran the `automatedVerification` refusal BEFORE `validateArtifactProvenance`, so the entire provenance backstop never executed for Instagram (the named first customer, `automatedVerification` correctly defaults `false` for it pre-Phase-2a) — the gate could only ever emit synthesized `FAIL`, and REQ-010 routed every such FAIL to `self-fix.sh` unconditionally, meaning a perfectly healthy, honestly-posting loop would self-fix forever. **FIND-N (blocking)** — `pass-id` was a caller-suppliable CLI argument, and the caller is the loop under test, letting it pre-stage a forged `artifacts.jsonl` row under a self-chosen `passId` before the verifier even runs — deviating without justification from `gig_reality_verify.sh:100-105`'s own precedent (internal generation, never caller-supplied). **FIND-O (major)** — capture-tool network-timeout/empty-body/soft-404 behavior unspecified. **FIND-P (major)** — REQ-014's "no duplicated provenance logic" acceptance criterion had no forcing proof obligation. | Fixed in this iteration (6, below), scope strictly bounded to these four findings per the escalation ruling. `enforceVerdict` redesigned around **three** outcomes (`PASS`/`FAIL`/`CANNOT_VERIFY`), reordered so `validateArtifactProvenance` ALWAYS runs; `automatedVerification` now governs only whether a clean result may be recorded as `PASS` (else `CANNOT_VERIFY`), never whether the checks run at all. REQ-010 routes `FAIL`→self-fix, `CANNOT_VERIFY`→a human-review queue, never self-fix. `pass-id` is now generated internally by `reality-verify-spawn.sh`, never accepted from any caller. Capture-tool failure modes (network error, empty body, unproven soft-404) are explicitly `CANNOT_VERIFY`. A grep-level PROP now forces the no-duplicate-logic claim. |

## Purpose (non-negotiable framing, carried over from reality-verifier)

VCSDD's existing agents each see only part of the truth:

| agent | tools (VERIFIED by reading agent frontmatter) | sees | cannot see |
|---|---|---|---|
| `vcsdd-adversary` (plugin) | Read, Write, Edit, Grep, Glob | spec/code/test-output files on disk | **no Bash — cannot execute anything or drive a browser** |
| `vcsdd-verifier` (plugin, phase 5) | Read, Write, Edit, Bash, Grep, Glob | property-test/fuzz/security/purity artifacts | scoped to formal proof, not real-world side effects |
| `reality-verifier` (`.claude/agents/reality-verifier.md`, this repo) | Read, Grep, Glob, **Bash**, no Write/Edit | the actual logged-out DOM / on-chain state / ledger files | cannot repair anything (repair is `self-fix.sh`'s job) |

Only `reality-verifier` can see ground truth in the real world. This feature makes it a
first-class gate — for EVERY invocation path that produces a verdict, and for a verdict space
wide enough to distinguish **"I caught you lying" from "I could not get a diagnostic read"**
(iteration 5's own lesson: a gate built only to fight false-PASS can, by symmetric mistake,
collapse into a gate that can never legitimately PASS at all — "always-FAIL" is exactly as
broken, for a healthy loop, as "always-PASS" is for a dishonest one, and this spec spent four
iterations hardening only the first failure mode while silently building the second). The rule
going forward, stated once: **any protection this spec claims MUST be traced, concretely, to
BOTH invocation paths named in REQ-011, AND its output space MUST let a genuinely healthy claim
reach `PASS` once the checking apparatus can actually vouch for it — a mechanism that can only
ever emit `FAIL` for its own named customer is not "fail-closed," it is broken in the opposite
direction.**

## Threat-model closure (read this section first — it is the spec's own completeness check)

Every identified path by which a verdict could end up WRONG — either a false `PASS` (rows
1-21) or a false, indefinitely-recurring `FAIL` where the true state is "cannot tell" (rows
22-23, new this iteration) — and how each is closed. This table has been revised after every
review that found an uncovered path. A future review that finds a 24th path has found a spec
defect. Every row states which invocation path(s) — (i) build-time VCSDD gate, (ii) runtime
standalone loop — it protects.

| # | Path to a wrong verdict | Applies to | Status | Closed by |
|---|---|---|---|---|
| 1 | Zero-citation PASS | (i)+(ii) | CLOSED | `enforceVerdict`'s citation-presence check, run unconditionally (regardless of `automatedVerification`, FIND-M fix) for BOTH paths — yields `CANNOT_VERIFY`/`no_citation` (reclassified this iteration: absence of any capture is "could not verify," not itself proof of a lie — see REQ-004). PROP-022. |
| 2 | Citation from an authenticated-capture tool | (i)+(ii) | CLOSED | `tool` check, always runs, yields `FAIL`/`wrong_tool` (a genuine contradiction — citing an authenticated capture as public proof is itself dishonest). PROP-010/018. |
| 3 | Citation resolves to no real row | (i)+(ii) | CLOSED | Row-existence check, always runs, yields `FAIL`/`no_matching_row` (the LLM asserted evidence that provably does not exist — a contradiction, not an inconclusive read). PROP-011/018b. |
| 4 | Citation from a different/stale pass | (i)+(ii) | CLOSED | `passId`/`ts` check, always runs, yields `FAIL`/`stale_row`. PROP-012. |
| 5 | LLM self-declares `claimType` | (i)+(ii) | CLOSED | `claimType` sourced ONLY from committed `reality-claim.json`, threaded by the CALLER, never the verdict. |
| 6 | Cites 1 of N required URLs | (i)+(ii) | CLOSED | `requiredArtifactCount`, always runs, yields `FAIL`/`insufficient_count`. PROP-023. |
| 7 | Same row cited N times | (i)+(ii) | CLOSED | Distinctness dedup, always runs, yields `FAIL`/`duplicate_citation`. PROP-023. |
| 8 | Non-2xx status counted as sufficient | (i)+(ii) | CLOSED | Status check, always runs; a genuine, server-returned non-2xx/redirect-to-removal status yields `FAIL` (a real, structural contradiction); a network-level failure to even GET a status yields `CANNOT_VERIFY` (new distinction, FIND-O fix — see REQ-004/012). PROP-024. |
| 9 | Caller mispropagates the backstop's verdict | (i)+(ii) | CLOSED | `enforceVerdict`'s return value IS the accepted verdict, by construction. PROP-025/039. |
| 10 | `gates.reality` recorded but never checked before VCSDD convergence | (i) only | CLOSED | REQ-009: required `.githooks/pre-push` wiring. PROP-027. |
| 11 | `SKIP` treated as convergence-sufficient for a real claim | (i) only | CLOSED | `SKIP` legal only when `claimType === "none"`. PROP-026. |
| 14 | Citation resolves cleanly but for the WRONG (real, public) URL, or redirects off the artifact | (i)+(ii) | CLOSED | URL-identity + no-redirect checks, always run, yield `FAIL`/`url_mismatch` or `redirect_off_artifact` (a genuine, structural contradiction). PROP-028/029/030/041. |
| 15 | `gates.reality` not bound to a specific `reality-claim.json` version | (i) only | CLOSED | `hashRealityClaim` binding. PROP-031. |
| 16 | Local git hook bypass by an agent with shell access | (i) only | **OPEN — disclosed, structural limit** | See "Local-hook trust boundary" below. |
| 17 | Capture signal not proven diagnostic for the platform | (i)+(ii) | MITIGATED — checks ALWAYS run (FIND-M fix); `automatedVerification` now governs ONLY whether a clean, no-contradiction result may be recorded as `PASS` (else `CANNOT_VERIFY`, never suppressing the checks that would have caught a real contradiction) | REQ-012/013 `automatedVerification`, default `false`. See row 23 for the operational-consequence fix. PROP-034/038. |
| 18 | Backstop never invoked on the runtime path at all | (ii), was fully unprotected | CLOSED | `enforceVerdict` shared module, unconditionally invoked by the now-blocking `reality-verify-spawn.sh`. PROP-039/040. |
| 19 | Loop-supplied URL treated as sufficient ground truth | (i)+(ii) | CLOSED | Fixed public surface + pre-committed content fingerprint (REQ-015); loop-supplied URL demoted to locator only. PROP-035/036/037. |
| 20 | Query-string collision (`?v=A` vs `?v=B`) | (i)+(ii) | CLOSED | `canonicalizeUrl` preserves non-tracking query params. PROP-041. |
| 21 | `automatedVerification` fail-open default | (i)+(ii) | CLOSED | Default `false`. PROP-038. |
| **22** | **(FIND-N) The loop under test supplies `pass-id` itself, pre-selecting the namespace a pre-staged, forged `artifacts.jsonl` row must land in, before the verifier is even spawned — a materially easier, more deterministic variant of row 12's forgery risk, reachable by the accused rather than requiring an adversarial verifier** | **(i)+(ii)** | **CLOSED** | **REQ-005/012: `passId` is generated INTERNALLY by `reality-verify-spawn.sh` at spawn time (mirrors `gig_reality_verify.sh:100-105`'s own precedent exactly), never accepted as a caller argument, env var, or any other externally-suppliable channel. A caller attempting to supply one is rejected/ignored, not honored. PROP-042. **AND (FIND-Q fix, iteration 7 — internal generation alone was NOT sufficient): the value must be CSPRNG-derived (>=128 bits), never `date +%s`+PID (which the caller can derive in advance via `$!` + a 2-second timestamp search), and the artifact-trail directory must be created with an EXCLUSIVE create so that a pre-existing directory — which at a freshly-drawn 128-bit CSPRNG name is proof of observation/pre-staging, never a collision or stale leftover — yields `FAIL` / `artifact_trail_tampered` (REQ-017), NOT `CANNOT_VERIFY` (corrected iteration 9: the soft outcome is exactly what a watching loop wants), and is never reused. PROP-048.**** |
| **23** | **(FIND-M) `automatedVerification`'s correct, fail-closed default (row 17/21) had an undisclosed operational consequence: it gated the ENTIRE provenance backstop behind itself, so for Instagram — the one named production customer, in its own mandated default configuration — the gate could only ever emit `FAIL`, and REQ-010 routed every such `FAIL` to `self-fix.sh` unconditionally; a perfectly healthy, honestly-posting loop would self-fix forever. Same disease as the false-PASS bug, opposite sign** | **(i)+(ii)** | **CLOSED** | **Three-outcome verdict space (`PASS`/`FAIL`/`CANNOT_VERIFY`, REQ-004/014). `validateArtifactProvenance` ALWAYS runs, regardless of `automatedVerification` — it only ever DOWNGRADES an over-optimistic raw `PASS`, and does so to `FAIL` when it finds a genuine, structural CONTRADICTION (wrong URL, fingerprint mismatch, not-on-fixed-surface, real non-2xx, etc. — trustworthy even on an unproven platform), or to `CANNOT_VERIFY` when it finds no contradiction but also cannot vouch for the result (no citation, capture-tool network/empty-body failure, or `automatedVerification !== true` on an otherwise-clean capture). REQ-010 routes `CANNOT_VERIFY` to a human-review queue, NEVER `self-fix.sh` — a healthy loop pre-diagnosability-proof gets `CANNOT_VERIFY` forever, not `FAIL` forever, and is never flogged with unfixable self-fix escalations. PROP-043/044/045.** |
| 12 | **Same-uid artifact-trail forgery — WIDENED, iteration 7 (FIND-S).** Any process running as the same OS user can write to the artifact trail. This covers (a) an adversarial VERIFIER forging evidence during its own run (the original, inherited-from-`gig` scope) AND (b) **the loop under test winning a race**: it watches the trail's parent directory, sees the exclusive `mkdir` succeed, learns the `passId` the instant it exists, and writes a forged, structurally-valid row while the real verifier runs. Entropy (row 22) defeats *guessing* the passId in advance; it does not defeat *observing* it. | (i)+(ii) | **OPEN — disclosed architectural limit, NOT closable by spec text.** MITIGATED (not closed) by REQ-016's HMAC row signing: the capture tool signs each row with a per-run secret generated inside the verification wrapper and never placed in the loop's environment/arguments, and `enforceVerdict` rejects any unsigned/mis-signed row — a loop must now steal a secret from another process, not merely write a file. **The honest statement: a verifier and the loop it verifies inside the SAME trust domain (same uid, same host) admits no cryptographic closure. No amount of additional spec text changes this.** The real defenses, stated plainly: (1) the verifier is spawned from OUTSIDE the loop with fresh context; (2) recurring own-eyes/fresh-adversary review; (3) **the actual structural fix, recorded as future work, is to move the verifier out of the loop's trust domain — a separate OS user, or a different host (cloud routines) — so the loop cannot write what verifies it.** Pretending row 12 is "closed" would be the exact false assurance this whole feature exists to abolish. | REQ-016 (mitigation only) |
| 13 | TOCTOU: public at verification time, taken down immediately after | (i)+(ii) | NOT closed — inherent to any point-in-time check | REQ-006's trail makes it discoverable in hindsight, not prevented. |

Rows 12, 13, and 16 are OPEN by explicit, reasoned disclosure. A row is only ever removed from
"open" by a required proof obligation that forces it for the specific path/scope it names.

### Local-hook trust boundary (FIND-F disposition — orchestrator's reasoning, not paraphrased; unchanged this iteration)

> An agent with shell access can bypass ANY local git hook (`--no-verify`, `chmod -x`, unset
> `core.hooksPath`, stale checkout). Therefore a local hook is not a security boundary against
> an adversarial insider — it is a discipline boundary against accident and drift, and that is
> all we should claim for it. Pretending otherwise is exactly the kind of false assurance this
> feature exists to kill.

Adopted verbatim, unchanged. Row 16 only ever mattered for path (i); REQ-011's standalone
runtime customer never touches `.githooks/pre-push` at all.

## Purity boundary analysis (top-level, elaborated per-requirement below)

- **Pure / deterministic core**, all in `skills/self/lib/reality-verdict-schema.mjs`:
  - the finding-category catalog and its validators (`FINDING_CATEGORIES`, `isKnownCategory`,
    `validateVerdictShape` — the latter now also accepting `CANNOT_VERIFY` as a legal
    `overallVerdict` value alongside `PASS`/`FAIL`, REQ-004/014) — extended, not replaced;
  - path/line derivation for the durable verdict trail (REQ-006), the artifact trail
    (REQ-012), and (new, minimal, FIND-M's routing fix) the human-review queue (REQ-010);
  - `canonicalizeUrl(url)` (closure row 14/20) — unchanged this iteration: allowlist-only
    tracking-param stripping, everything else preserved, sorted, compared.
  - `computeContentFingerprint(content)` (closure row 19) — unchanged.
  - `hashRealityClaim(realityClaim)` (closure row 15) — unchanged.
  - `validateArtifactProvenance(verdict, capturedArtifacts, claimType, requiredArtifactCount,
    groundTruth, automatedVerification)` (REQ-004/023 — `automatedVerification` is now a
    parameter of THIS function, consulted only at its FINAL step, not a precondition to
    running it at all — the FIND-M fix) — returns one of `PASS`/`FAIL`/`CANNOT_VERIFY`, per a
    fixed, deterministic CONTRADICTION-vs-INCONCLUSIVE violation taxonomy (closure rows 1-4,
    6-9, 14, 19, 20, 22, 23).
  - `enforceVerdict(rawVerdict, capturedArtifacts, claimType, requiredArtifactCount,
    groundTruth, automatedVerification)` (closure rows 18, 22, 23 — REORDERED this iteration,
    the FIND-M fix) — composition: `validateVerdictShape` (malformed ⇒ `CANNOT_VERIFY`) → if
    `rawVerdict.overallVerdict !== "PASS"`, pass through unchanged (never second-guess a
    cautious/inconclusive raw verdict) → else, for a public-artifact `claimType`,
    `validateArtifactProvenance(...)` UNCONDITIONALLY (regardless of `automatedVerification`).
    The SOLE function either invocation path may treat a raw LLM verdict as accepted through.
  - `decideConvergenceGate(state, realityClaim)` (closure rows 11, 15) — unchanged; note
    (FIND-M consequence) it still only ever sees the schema-legal `PASS`/`FAIL`/`SKIP` mapping
    `recordGate` stores — `CANNOT_VERIFY` maps to a stored `verdict: "FAIL"` plus
    `details.enforcementOutcome: "CANNOT_VERIFY"` (REQ-008/010) so convergence stays correctly
    blocked while the distinction survives for a human reading the record.
- **Effectful shell**:
  - `.claude/agents/reality-verifier.md` — LLM judgment, out of unit-test scope.
  - `skills/self/reality-verify-spawn.sh` — unchanged this iteration except: `passId` is now
    generated INTERNALLY (closure row 22, FIND-N fix), never accepted as an argument; on
    `CANNOT_VERIFY`, appends to the human-review queue instead of triggering `self-fix.sh`
    (REQ-010).
  - `skills/self/scripts/public_artifact_snapshot.py` (REQ-012) — unchanged shape; edge cases
    for network error/timeout/empty body now explicitly specified (FIND-O fix, REQ-012).
  - `skills/self/reality-precommit.mjs` — unchanged.
  - the VCSDD gate script (REQ-008) — unchanged this iteration except the same `CANNOT_VERIFY`
    routing/recording rule.
  - `.claude/commands/vcsdd-reality.md` — unchanged.
  - `.githooks/pre-push`'s Reality Convergence Guard section — unchanged.
  - `.claude/settings.json`'s `hooks.PreToolUse` entry — unchanged.

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
spawn, SHALL enforce this as a default-closed rule that ALWAYS runs (REQ-014's reordering,
FIND-M fix) — never suppressed by `automatedVerification`, which governs only the final
`PASS`-vs-`CANNOT_VERIFY` recording decision, not whether the checks execute.
**Rejected designs (do not reintroduce)**:
1. (iter. 1) substring-matching free-text evidence fields.
2. (iter. 2) validating only citations that already carry a `filePath`.
3. (iter. 3) validating a citation resolves cleanly without checking it is FOR THE CLAIMED URL.
4. (iter. 4) wiring the check into only ONE of the two invocation paths.
5. (iter. 5, FIND-M) wiring the check into both paths correctly, but gating its EXECUTION
   behind a flag (`automatedVerification`) that is correctly `false` by default — making the
   check structurally unreachable for the feature's own production configuration. The fix is
   not "loosen the default" — it is "the check runs regardless; the flag only gates whether a
   clean result may be called `PASS`."
**Edge Cases**: unchanged from prior iterations (CDP:9222 for unrelated logged-in checks; no
URL ⇒ refuse to spawn; row 12/16 residual risk).
**Acceptance Criteria**: unchanged from prior iterations — `enforceVerdict` invoked
unconditionally by both `reality-verify-spawn.sh` and the gate script, plus (new): its
INTERNAL composition never conditions whether `validateArtifactProvenance` runs on
`automatedVerification`'s value — grep/read-checkable in REQ-014's own text.

### REQ-004: Provenance backstop — three-outcome (`PASS`/`FAIL`/`CANNOT_VERIFY`), contradiction-vs-inconclusive taxonomy, `automatedVerification` gates only the final PASS (closure rows 1, 6, 7, 8, 9, 14, 17, 19, 20, 22, 23 — REDESIGNED this iteration, FIND-M/N/O fix)
**EARS**: WHEN `enforceVerdict` runs `validateArtifactProvenance(verdict, capturedArtifacts,
claimType, requiredArtifactCount, groundTruth, automatedVerification)` for a public-artifact
claim whose raw `overallVerdict` is `"PASS"` THE SYSTEM SHALL check ALL of the following
(an open, growable set), classify any violation found as either **CONTRADICTION** (positive
evidence the claim is false) or **INCONCLUSIVE** (absence of a diagnostic capture — the
checking apparatus itself could not produce a trustworthy read), and return:
- `overallVerdict: "FAIL"` with a `post_not_publicly_visible` finding, if ANY CONTRADICTION
  violation is found — REGARDLESS of `automatedVerification`'s value (a structural
  contradiction is trustworthy evidence even on a platform whose PASS-signal is unproven);
- `overallVerdict: "CANNOT_VERIFY"` if NO contradiction is found but an INCONCLUSIVE
  condition applies (including `automatedVerification !== true` on an otherwise-clean
  capture — this is the LAST check performed, only after every contradiction check has
  already had the chance to fire);
- the input verdict UNCHANGED (`PASS`) only if every check resolves cleanly with no
  contradiction AND `automatedVerification === true` explicitly.

**Fixed violation taxonomy** (a deterministic lookup table, not a judgment call):

| Violation | Class | Outcome |
|---|---|---|
| Zero citations present at all | INCONCLUSIVE (`no_citation`) | `CANNOT_VERIFY` |
| Citation from `tool !== "public_artifact_snapshot"` | CONTRADICTION (`wrong_tool`) | `FAIL` |
| Citation resolves to no real row (fabricated) | CONTRADICTION (`no_matching_row`) | `FAIL` |
| Citation from a foreign/stale `passId`/`ts` | CONTRADICTION (`stale_row`) | `FAIL` |
| Citation's `requestedUrl` not in `groundTruth.claimedUrls` (post-`canonicalizeUrl`) | CONTRADICTION (`url_mismatch`) | `FAIL` |
| Citation's `finalUrl` differs from `requestedUrl` (redirect off the artifact) | CONTRADICTION (`redirect_off_artifact`) | `FAIL` |
| Fewer than `requiredArtifactCount` distinct resolved citations | CONTRADICTION (`insufficient_count`) | `FAIL` |
| Same row cited to pad the count | CONTRADICTION (`duplicate_citation`) | `FAIL` |
| Row's `httpStatus` is a genuine, server-returned non-2xx code (e.g. real `404`/`410`) | CONTRADICTION (`server_confirmed_absent`) | `FAIL` |
| Row records a NETWORK-level failure (timeout, connection refused, DNS failure — no real HTTP status was ever received) | INCONCLUSIVE (`capture_network_error`) | `CANNOT_VERIFY` |
| Row's response body is empty/near-empty (2xx status, nothing to read) | INCONCLUSIVE (`capture_empty_body`) | `CANNOT_VERIFY` |
| (`caller-per-invocation` only) locator not on `groundTruth.fixedPublicSurfaceUrl` | CONTRADICTION (`not_on_fixed_surface`) | `FAIL` |
| (`caller-per-invocation` only) `contentHash` ≠ `groundTruth.precommit.contentFingerprint` | CONTRADICTION (`fingerprint_mismatch`) | `FAIL` |
| (`caller-per-invocation` only) `groundTruth.precommit.ts` not before the capture pass's start | CONTRADICTION (`precommit_not_before_action`) | `FAIL` |
| **Row exists in the trail but its `rowHmac` is absent, mis-signed, or signed with another pass's secret (REQ-016/017)** | **CONTRADICTION (`artifact_trail_tampered`)** — a row that exists but does not verify is positive evidence that someone wrote/modified the trail; it is NOT an absence of information | **`FAIL`** |
| Everything else resolves cleanly, but `automatedVerification !== true` | INCONCLUSIVE (`automated_verification_unproven`) — checked LAST, only if no contradiction fired | `CANNOT_VERIFY` |

`validateArtifactProvenance` never mutates its inputs, never touches `fs` itself.
**Edge Cases**: `requiredArtifactCount` `0`/omitted ⇒ defaults `1`. A raw verdict whose
`overallVerdict` is already `FAIL` or `CANNOT_VERIFY` (the LLM's own honest judgment) passes
through UNCHANGED — this function only ever downgrades an over-optimistic raw `PASS`, never
upgrades or second-guesses a cautious one. A soft-404 (HTTP `200` with a generic
not-found-looking body) is NOT special-cased as its own violation — a genuinely-2xx response
with content the tool cannot structurally interpret falls through to the LAST check
(`automated_verification_unproven`), which is exactly correct: we do not yet have a
proven-diagnostic way to distinguish a soft-404 body from a real one, so it is INCONCLUSIVE,
never a silent PASS and never a false FAIL (per FIND-O's explicit instruction: "→ these
produce CANNOT_VERIFY (or FAIL where reality genuinely contradicts)" — a real 404 status is
the "genuinely contradicts" case; a 200-with-ambiguous-body is the CANNOT_VERIFY case).
**Acceptance Criteria** (each `required: true` — see verification-architecture.md
PROP-022..045): all CONTRADICTION rows above tested → `FAIL` (PROP-010/011/012/018/018b/023/
024/028/029/030/035/036/037/041, unchanged mechanism from prior iterations). **New**: zero
citations → `CANNOT_VERIFY`, not `FAIL` (PROP-022, reclassified). **New**: a fixture with
every OTHER check clean and `automatedVerification: false` → `CANNOT_VERIFY`/
`automated_verification_unproven`, and — critically — is proven to have actually EXECUTED
every other check first (a companion fixture proves that if a contradiction is ALSO present
alongside `automatedVerification: false`, the result is `FAIL`, not `CANNOT_VERIFY` — i.e.
contradictions are checked before, and take priority over, the automatedVerification gate)
(PROP-043). **New**: a fixture with a network-error-sentinel row and an empty-body row each →
`CANNOT_VERIFY` (PROP-044/045, FIND-O fix).

### REQ-005: Generalized, BLOCKING spawn wrapper — internally-generated `passId`, deterministic count/URLs/ground-truth, backward compatible with the real existing caller (closure row 22, FIND-N fix)
**EARS**: WHEN a caller needs to verify a real-world side-effect claim THE SYSTEM SHALL
provide `skills/self/reality-verify-spawn.sh` accepting `<loop-name>
<artifact-or-public-url> [claim-text] [claim-type] [required-artifact-count] [claimed-urls]
[fixed-public-surface-url] [content-fingerprint] [precommit-ts]` — **`pass-id` is NOT in this
list; it is NEVER accepted from the caller, by any channel (CLI argument, environment
variable, or otherwise)** — `reality-verify-spawn.sh` generates it INTERNALLY at spawn time
(mirrors `gig_reality_verify.sh:100-105`'s own precedent: `PASS_ID="realityverify-$(date
+%s)-$$"`, generated inside the script itself), embeds it in the task prompt, and uses it to
scope `artifacts.jsonl` — the caller never learns or chooses this value in advance. THE
SYSTEM SHALL run this call to COMPLETION (blocking, capped at 600s), and SHALL unconditionally
call `enforceVerdict` on the result before appending anything to REQ-006's trail. A loop
making a NEW post SHALL supply the real URL it received back from the platform (`claimed-urls`,
a LOCATOR only, REQ-015) and, for a `caller-per-invocation` claim, SHALL have already called
`reality-precommit.mjs` BEFORE attempting the post.
**Edge Cases**: unrecognized `claim-type` ⇒ generic handling. No URL for a public-artifact
`claim-type` ⇒ refuse to spawn. If a caller passes a value in the (now-removed) old `pass-id`
positional slot — e.g. an un-migrated old-style invocation — THE SYSTEM SHALL either reject
the call outright (argument-count mismatch) or, if positionally ambiguous with
`required-artifact-count`, treat it per the NEW argument order and never as a `passId`
override; there is no code path anywhere in this script that reads an externally-supplied
value into the internal `passId` variable. The blocking-vs-detached and other behavior changes
from iteration 5 are unchanged (NFR, disclosed).
**Acceptance Criteria**:
- `test-reality-verify-spawn.sh`'s existing 3 assertion groups (A/B/C) pass unchanged.
- Blocking `claude -p` invocation, grep-checkable (unchanged from iteration 5).
- **New, required (PROP-042)**: a fixture/unit test proves the script's internally-generated
  `passId` is used for the artifact-trail directory REGARDLESS of any caller-supplied value
  in any argument position or environment variable named `PASS_ID`/`passId`/similar — i.e. a
  test that attempts to inject a chosen passId via every plausible channel and asserts none of
  them are honored (the directory used is always the script's own freshly-generated value).
- **New (routing, REQ-010)**: on `overallVerdict: "CANNOT_VERIFY"`, the script's post-spawn
  logic appends to the human-review queue (REQ-010) and does NOT invoke `self-fix.sh` —
  grep-checkable, distinct code path from the `FAIL` branch.
- DRYRUN assertion (unchanged) confirms remaining arguments thread correctly with defaults.

### REQ-006: Durable per-loop verdict trail
**EARS**: WHEN an ENFORCED verdict (REQ-014's `enforceVerdict` output — now one of `PASS`/
`FAIL`/`CANNOT_VERIFY`) is produced for loop `<L>` THE SYSTEM SHALL append one JSON line to
`$HOME/.openclaw/state/reality-verdict-<L>.jsonl` with at minimum timestamp, `overallVerdict`
(one of the 3 legal values), `findings`, and the `RESULT` path.
**Edge Cases**: concurrent appends never overwrite; file created on first append;
`CANNOT_VERIFY` verdicts are recorded here identically to `PASS`/`FAIL` — the trail is a
complete, honest record of every outcome, never filtered to only "interesting" ones.
**Acceptance Criteria**: `buildVerdictTrailPath` deterministic, unit-tested; after a real/
fixture run, the trail's last line parses as JSON with `overallVerdict` one of the 3 legal
values.

### REQ-007: Negative test — fail-closed proof (a gate that cannot fail is not a gate)
**EARS**: WHEN `enforceVerdict` is given a FALSE or unprovable claim, on EITHER invocation
path, THE SYSTEM SHALL produce `overallVerdict: "FAIL"` (for a genuine contradiction) —
demonstrated by all of REQ-004's `FAIL`-class bypass fixtures, plus a real, live fresh spawn
via `reality-verify-spawn.sh` itself against a genuinely nonexistent public URL, and a second
live spawn where the located URL is a genuinely different real, public page.
**Edge Cases**: unambiguous random-UUID 404 for the nonexistent-URL proof; genuinely unrelated
real page for the wrong-URL proof; retry once on flaky network.
**Acceptance Criteria**: unchanged from iteration 5 — all REQ-004 `FAIL`-class bypass unit
tests pass; both live `FAIL` artifacts committed under `.vcsdd/features/reality-gate/evidence/`,
produced via the RUNTIME path.

### REQ-008: VCSDD Phase 4.5 REALITY GATE — `vcsdd-reality` command calls the SAME shared enforcement path, maps `CANNOT_VERIFY` to a distinguishable, still-blocking `gates.reality` record (closure rows 15, 18, 23)
**EARS**: WHEN a VCSDD feature has passed adversarial review THE SYSTEM SHALL provide a
`/vcsdd-reality` command that obtains an ALREADY-ENFORCED verdict (one of `PASS`/`FAIL`/
`CANNOT_VERIFY`) via `reality-verify-spawn.sh`/`enforceVerdict`, sources
`claimType`/`requiredArtifactCount`/`groundTruth`/`automatedVerification` EXCLUSIVELY from
`reality-claim.json`, and records into `state.json` via `recordGate(featureName, 'reality',
verdict, reviewedBy, details)` using ONLY schema-legal values
(`"verdict":{"enum":["PASS","FAIL","SKIP"]}`) — where `enforceVerdict`'s `PASS`/`FAIL` map
DIRECTLY to `recordGate`'s `verdict`, and `CANNOT_VERIFY` maps to `verdict: "FAIL"` (the only
schema-legal, convergence-blocking value available) PLUS `details.enforcementOutcome:
"CANNOT_VERIFY"` (distinct from a genuine-contradiction `FAIL`, which sets
`details.enforcementOutcome: "FAIL"`), so a human reading `gates.reality` later can tell
"code is wrong, self-fix already ran" from "nobody has determined this claim's truth yet."
**Edge Cases**: `claimType: "none"` ⇒ `SKIP` recording (unchanged). `CANNOT_VERIFY` NEVER maps
to `SKIP` — `SKIP` remains exclusively for the "no real claim exists" case (REQ-013), never for
"a real claim exists but couldn't be checked yet."
**Acceptance Criteria**: unchanged from iteration 5, plus: a fixture test proves a
`CANNOT_VERIFY` `enforceVerdict` result is recorded with `verdict: "FAIL"` +
`details.enforcementOutcome: "CANNOT_VERIFY"`, distinguishable from a contradiction-`FAIL`'s
`details.enforcementOutcome: "FAIL"`.

### REQ-009: Convergence requires the reality gate — hash-bound, enforced at a real, authoritative (not adversarial-insider-proof) point (closure rows 10, 11, 15, 16)
Unchanged from iteration 5. `decideConvergenceGate` still only ever sees the schema-mapped
`PASS`/`FAIL`/`SKIP` (REQ-008) — a `CANNOT_VERIFY` outcome blocks convergence exactly as a
genuine `FAIL` does (fail-closed for the convergence use case is preserved; only the SELF-FIX
ROUTING, REQ-010, path (ii)-specific, changes).

### REQ-010: reality-verifier stays read-only; escalation routing SEPARATES "the loop lied" from "we could not check" (closure row 23 — REDESIGNED this iteration, FIND-M fix)
**EARS**: WHEN `enforceVerdict` yields `overallVerdict: "FAIL"` (a genuine CONTRADICTION) THE
SYSTEM SHALL invoke `self-fix.sh <name> "<blocker+hint>"` — the loop's own code produced a
claim the evidence contradicts, which is a code/behavior bug self-fix can investigate. WHEN
`enforceVerdict` yields `overallVerdict: "CANNOT_VERIFY"` (an INCONCLUSIVE outcome) THE SYSTEM
SHALL NOT invoke `self-fix.sh` — there is no code bug to fix; the checking apparatus itself
could not produce a diagnostic read (an unproven platform, a network failure, an empty body).
Instead THE SYSTEM SHALL append `{ts, loopName, passId, reason, claimSummary}` to
`$HOME/.openclaw/state/reality-needs-human-review-<loopName>.jsonl` (a new, minimal,
append-only queue — mirrors REQ-006's own trail durability pattern, no new subsystem) — this
is the "own-eyes/human review" escalation path in place of code-fix escalation. In NEITHER
case (`FAIL` nor `CANNOT_VERIFY`) SHALL the gate script, spawn wrapper, or `reality-verifier`
itself edit any file; both escalation targets are separate, downstream processes.
**A `CANNOT_VERIFY` verdict SHALL NEVER**: (a) be treated as sufficient to satisfy a `PASS`
claim anywhere (REQ-004/008/009's existing fail-closed convergence/recording rules already
guarantee this — restated here as the routing-specific consequence); (b) be reported to a
loop's owner-facing success report (e.g. a daily summary) AS a verified post — REQ-018
requires it be surfaced explicitly AS `CANNOT_VERIFY`, distinct from both "posted and
verified" and "failed."

**AMENDED by REQ-018 (iteration 8 — FIND-V): the no-self-fix rule is per-pass, not permanent.**
A SINGLE `CANNOT_VERIFY` SHALL NOT invoke `self-fix.sh` (the loop's code is not implicated by one
unreadable pass). But **TWO CONSECUTIVE `CANNOT_VERIFY` verdicts for the same loop SHALL invoke
`self-fix.sh`**, because a verification apparatus that cannot read reality twice in a row is itself
a defect to repair, not a state to tolerate — and "unverifiable forever" is precisely how a loop
that does nothing stays silent. Any earlier phrasing in this requirement or in PROP-046 that reads
as an UNCONDITIONAL "CANNOT_VERIFY never calls self-fix" is superseded by this rule: PROP-046 MUST
be restated as "a single, first `CANNOT_VERIFY` does not call self-fix", and PROP-055 forces the
two-strike escalation. Both are required and must be jointly satisfiable by one implementation.
**Edge Cases**: `self-fix.sh`'s own dedupe/staleness logic is unaffected — it applies to EVERY
path that reaches `self-fix.sh`, which per REQ-018 is the `FAIL` branch AND the
second-consecutive-`CANNOT_VERIFY` branch (corrected iteration 9: an earlier draft said "the
`FAIL` branch only", which would have re-introduced the unconditional no-self-fix-on-
`CANNOT_VERIFY` rule REQ-018 explicitly abolishes). The human-review queue is append-only; multiple `CANNOT_VERIFY` results
for the same loop simply accumulate rows — THE SYSTEM SHALL NOT deduplicate or suppress
repeated appends (an unresolved diagnosability gap recurring daily is itself useful signal
that Phase 2a's experiment, REQ-012, has not yet run — silently deduping would hide that).
**Acceptance Criteria**: `reality-verifier.md`'s `tools` stays exactly
`["Read","Grep","Glob","Bash"]`; the gate script's AND `reality-verify-spawn.sh`'s `FAIL`
paths each contain a literal `self-fix.sh` call; their **FIRST-`CANNOT_VERIFY`** paths each
contain a literal append to the human-review queue and NO `self-fix.sh` call — grep-checkable,
two distinct code paths (PROP-046). **CORRECTED iteration 9 (FIND-AA): this is NOT an
unconditional rule. Per REQ-018, the SECOND consecutive `CANNOT_VERIFY` for the same loop MUST
invoke `self-fix.sh` (PROP-055) — a checker that cannot read reality twice in a row is itself a
defect. The implementation therefore branches on the consecutive-`CANNOT_VERIFY` counter:
first → human-review queue only; second → human-review queue AND `self-fix.sh`. PROP-046 and
PROP-055 are jointly satisfiable and both required; a Builder implementing an unconditional
"CANNOT_VERIFY never calls self-fix" would fail PROP-055.**

### REQ-011: First customer / acceptance vehicle — explicit, disclosed operational outputs for all three real scenarios (closure rows 18, 23 fixes make this claim honest)
**EARS**: WHEN the growth-engine marketing loop claims it posted a video to Instagram THE
SYSTEM's reality gate SHALL prove, disprove, OR honestly decline to determine that claim
(never silently collapsing "decline" into either "proved" or "disproved") via
`enforceVerdict`, invoked unconditionally by `reality-verify-spawn.sh` itself. This IS a
standalone loop-verification call (REQ-005): no `state.json`, no `gates.reality`, no `SKIP`.
**The three real operational outputs, stated explicitly (this is the requirement's own
completeness check, per the coordinator's direct request)**:
1. **A healthy, honestly-posted Instagram video, BEFORE REQ-012's Phase 2a diagnosability
   experiment has run for Instagram** (`automatedVerification: false`, the correct, mandated
   default): every structural check resolves cleanly (right URL, right pass, on the fixed
   surface, fingerprint matches, fresh, real 2xx) but the `automated_verification_unproven`
   check is the ONLY thing that fires ⇒ **`CANNOT_VERIFY`**. Routed to human-review (REQ-010),
   NEVER `self-fix.sh`, NEVER reported to the loop's owner as "verified."
2. **The same healthy post, AFTER Phase 2a's experiment records a proven-diagnostic signal
   for Instagram and `automatedVerification` is set `true`** (spec-time, Phase-1c-reviewed
   change to `reality-claim.json`, REQ-013): the identical structural checks resolve cleanly,
   the final gate now also passes ⇒ **`PASS`**.
3. **A loop that fabricates a post** (any CONTRADICTION-class violation — wrong URL,
   fingerprint mismatch, not on the fixed surface, a real non-2xx from the server, etc.) ⇒
   **`FAIL`**, REGARDLESS of `automatedVerification`'s value ⇒ routed to `self-fix.sh`
   (REQ-010).
**Edge Cases**: N/A beyond the above — this table IS the edge-case enumeration this
requirement previously left implicit (iteration 5's own finding: "the resulting operational
cost... named and accepted, not left implicit in a parenthetical edge case" — now explicit).
**Acceptance Criteria**: nothing platform-hardcoded; the loop-verification-vs-VCSDD-gate
distinction stated explicitly; the three scenarios above are each covered by a required proof
obligation (scenario 1 → PROP-043's `automated_verification_unproven`-only fixture; scenario 2
→ PROP-013's positive-control fixture with `automatedVerification: true`; scenario 3 →
PROP-028/029/035/036/037's contradiction fixtures, tested with `automatedVerification: false`
specifically, proving contradiction-detection does NOT depend on the flag).

### REQ-012: Deterministic logged-out capture tool — diagnosability experiment is a REQUIRED, scheduled Phase 2a task (not deferred/optional); network/empty-body/soft-404 handling explicit; `passId` namespace is caller-inaccessible (closure rows 17, 22, 23, FIND-G/M/N/O fix)
**EARS**: WHEN a public URL needs checking THE SYSTEM SHALL provide
`public_artifact_snapshot.py <passId> <seq> <label> <url>` — deterministic, never touches
CDP:9222, appends one row to `.../reality-artifacts/<passId>/artifacts.jsonl` (a directory
whose name is ALWAYS the internally-generated `passId` from REQ-005 — no caller-facing API
anywhere accepts this value, AND (FIND-Q fix, iteration 7) the value MUST be CSPRNG-derived
(>= 128 bits entropy), NOT time+PID-derived: a `$(date +%s)-$$` scheme is predictable by the
calling loop (`bash "$SPAWN" & pid=$!` reveals the child PID; the timestamp is a ~2-second
search space) and would leave closure row 22's pre-staging attack OPEN. The artifact-trail
directory MUST additionally be created with an EXCLUSIVE create that fails if it already
exists; **a pre-existing directory at a freshly-drawn 128-bit CSPRNG name cannot be a collision
or a stale leftover — it is proof that something observed or predicted the name and got there
first, so it yields `FAIL` / `artifact_trail_tampered` per REQ-017, NOT `CANNOT_VERIFY`**
(corrected iteration 9: an earlier draft of this line said `CANNOT_VERIFY`, which would have
handed a watching loop exactly the soft, non-escalating outcome it wants). Never reuse, never
PASS. Entropy makes guessing infeasible; exclusive-create turns a lucky guess into tamper
evidence. Forcing proof: PROP-048) with at minimum `{ts, passId, seq, label, tool,
requestedUrl, finalUrl, httpStatus, domExcerpt}`, plus `contentHash`/`referencedArtifactIds`
for `caller-per-invocation` claims — never raising.
**Network/empty-body/soft-404 handling (new, FIND-O, REQ-004's taxonomy)**: on a network-level
failure (timeout, connection refused, DNS failure, or any condition where no real HTTP
response was received) THE SYSTEM SHALL record a row with a reserved sentinel (e.g.
`httpStatus: null`, not a real code) so `validateArtifactProvenance`'s `capture_network_error`
check fires (`CANNOT_VERIFY`) — this MUST NOT be recorded as, or defaulted to, an in-range
`httpStatus` value. On an empty/near-empty response body (real 2xx status, no usable content)
THE SYSTEM SHALL record `httpStatus` accurately (real 2xx) but leave `domExcerpt` empty/marked,
triggering `capture_empty_body` (`CANNOT_VERIFY`). A soft-404 (real HTTP `200`, but a body that
LOOKS like a not-found page) is deliberately NOT special-cased by the tool — the tool records
the real, accurate `httpStatus`/`domExcerpt` it observed; whether that body constitutes proof
of absence is exactly what REQ-012's diagnosability experiment (below) determines, and until
proven, it falls through to `automated_verification_unproven` (`CANNOT_VERIFY`), never a
silent PASS and never an incorrect FAIL. A GENUINE non-2xx server response (real `404`/`410`)
IS recorded accurately and DOES trigger `server_confirmed_absent` (`FAIL`) — this is a
platform-agnostic, server-level signal, trustworthy independent of diagnosability proof.
**Diagnosability precondition — REQUIRED, scheduled Phase 2a task, not optional or deferred
(FIND-M part 4 fix)**: Phase 2a of this feature's own implementation MUST include, as a
REQUIRED task (not left to some later, unscheduled effort): fetch, logged-out, (a) a real,
known-public Instagram post URL and (b) a real, known-nonexistent/removed Instagram post URL,
and determine which structured, tool-recorded field (HTTP status difference, and/or a
structural field the tool writes — e.g. `referencedArtifactIds` presence/absence on the fixed
surface — never DOM prose interpretation) actually, materially differs between the two. This
evidence, and ONLY this evidence, may flip `reality-claim.json.automatedVerification` to
`true` for Instagram. **Fallback, explicitly named (not hand-waved)**: if a direct post-URL
fetch is not diagnostic (plausible — Instagram's SPA shell may return `200` regardless), THE
SYSTEM SHALL instead prove REQ-015's `fixedPublicSurfaceUrl` (the account's public
profile/feed) mechanism diagnostic: a removed/nonexistent post's identifier is structurally
ABSENT from the fixed surface's `referencedArtifactIds` while a real, live post's identifier
IS present — this is a naturally binary, list-membership signal (present-or-absent), likely
more robust than interpreting a single post URL's body, and REQ-015 already requires this
check to run for every `caller-per-invocation` claim regardless — Phase 2a's experiment MAY
therefore prove EITHER the direct-fetch signal OR the fixed-surface-membership signal
diagnostic (or both), and record which one(s) actually work.
**`automatedVerification` gate**: unchanged from iteration 5 — defaults `false`
(fail-closed), consulted ONLY as `validateArtifactProvenance`'s LAST check (REQ-004's
reordering, FIND-M fix), never suppressing any other check.
**Edge Cases**: JS-rendering platforms prefer headless-browser variant (unchanged). Anti-bot
403s: a real, server-returned `403` — this IS a genuine non-2xx status; whether it means
"the anti-bot layer blocked us" (inconclusive) or "genuinely forbidden/removed" (contradiction)
is itself a diagnosability question — until Phase 2a determines otherwise for a given
platform, `403` is treated the SAME as any other real non-2xx: `server_confirmed_absent`/
`FAIL` (the existing, unchanged, accepted false-negative-risk precedent from iteration 4 — not
loosened by this iteration's CANNOT_VERIFY introduction, since a definitive server response
code remains the platform-agnostic, trustworthy signal class).
**Acceptance Criteria**: no `9222` reference in the tool's source; distinct directory/`tool`
field from gig's; every row has an `httpStatus` field, whose value is EITHER a real HTTP status
code OR the reserved network-error sentinel, never conflated. **Required, new (FIND-O,
PROP-044/045)**: fixture rows for a network-error sentinel and an empty-body 2xx response each
route through `enforceVerdict` to `CANNOT_VERIFY`, not `FAIL` and not `PASS`. **Required
(unchanged from iteration 5, now genuinely scheduled not merely "pending")**: PROP-033, the
Phase 2a live diagnosability experiment (or its fixed-surface fallback variant), with
acceptance criterion "two captures, materially different on a named structured field" —
`required: true` as a Phase 2a deliverable of THIS feature's own implementation, not deferred
to an unrelated future effort.

### REQ-013: `reality-claim.json` — committed, spec-reviewed, deterministic claim declaration, fail-closed defaults, fixed-surface declaration
Unchanged from iteration 5 (closure rows 5, 11, 14, 15, 17, 19, 21). `automatedVerification`'s
role in `enforceVerdict`'s composition changed (REQ-004/014), but this requirement's own
schema, sourcing rules, and acceptance criteria are unaffected by that reordering.

### REQ-014: Shared enforcement module — ONE module, TWO callers, three-outcome verdict space, checks-always-run (closure rows 9, 18, 23 — REORDERED this iteration, FIND-M/P fix)
**EARS**: WHEN ANY `reality-verifier` verdict is produced, on ANY invocation path, THE SYSTEM
SHALL run it through exactly one shared, pure function —
`enforceVerdict(rawVerdict, capturedArtifacts, claimType, requiredArtifactCount, groundTruth,
automatedVerification)` — composed, in order: (1) `validateVerdictShape(rawVerdict)`
(malformed ⇒ synthesize `CANNOT_VERIFY`, reason `malformed_verdict_shape` — the checking
apparatus itself, i.e. the LLM's own output, failed to produce something processable, which is
an INCONCLUSIVE condition, not evidence of a lie); (2) if `rawVerdict.overallVerdict !==
"PASS"`, return it UNCHANGED (never second-guess a raw `FAIL`/`CANNOT_VERIFY` the LLM itself
already produced — the backstop's only job is catching an OVER-optimistic `PASS`); (3)
otherwise, for a public-artifact `claimType`, `validateArtifactProvenance(rawVerdict,
capturedArtifacts, claimType, requiredArtifactCount, groundTruth, automatedVerification)`
UNCONDITIONALLY — this step is REACHED regardless of `automatedVerification`'s value; that
flag is consulted ONLY inside `validateArtifactProvenance`, as its LAST check, after every
CONTRADICTION check has already had the chance to fire (REQ-004's taxonomy). A verdict that
has not passed through `enforceVerdict` SHALL be treated as `overallVerdict: "FAIL"` by
definition (unchanged from iteration 5).
**Rejected design (iteration 5, FIND-M — do not reintroduce)**: running the
`automatedVerification` refusal as its OWN step BEFORE `validateArtifactProvenance`, gating
whether the provenance checks execute at all. This was iteration 5's actual specification and
produced the inverse bug: for any claim whose platform is not yet proven diagnostic, the
provenance backstop — the entire mechanism 5 iterations were spent building — never ran, and
every such claim synthesized a bare `FAIL` (not even `CANNOT_VERIFY`, since that 3rd outcome
did not exist yet), triggering unconditional, indefinite `self-fix.sh` escalation for a
perfectly healthy loop. The fix moves `automatedVerification` from a PRECONDITION to a
POSTCONDITION of the provenance checks, and introduces the 3rd outcome so "could not verify"
is representable without being conflated with "verified false."
**Wiring**: unchanged from iteration 5 — `reality-verify-spawn.sh` is the runtime path's sole
call site; the VCSDD gate script calls the SAME module, never reimplementing it.
**Acceptance Criteria**:
- `enforceVerdict` exists, pure, composed of the steps above; unit-tested as a composition
  (PROP-039, updated fixtures: malformed→CANNOT_VERIFY; raw-FAIL passes through unchanged;
  raw-PASS-with-contradiction→FAIL regardless of automatedVerification; raw-PASS-clean-but-
  unproven→CANNOT_VERIFY; raw-PASS-clean-and-proven→PASS).
- `reality-verify-spawn.sh` contains no `tmux new-session -d` for the verifier call, DOES
  contain an unconditional `enforceVerdict` invocation, and its internally-generated `passId`
  is never caller-overridable (PROP-040, PROP-042).
- **NEW, required (FIND-P fix, closes the previously-unforced acceptance criterion)**: a
  grep-level, mechanical (not judgment-based — bookkeeping, per the coordinator's own framing)
  static check, run as part of this feature's own test suite, scans **BOTH callers' source
  files — (i) the build-time VCSDD gate script AND (ii) the runtime path
  `skills/self/reality-verify-spawn.sh`** (FIND-R/FIND-T fix, iteration 7: scoping this check
  to the gate script alone leaves REQ-011's named first customer, the runtime loop, with zero
  forcing check against shadow-reimplemented provenance logic — that is FIND-H reopening.
  "ONE module, TWO callers" is proven on both callers or on neither) — for definitions (not
  calls) of any of: `canonicalizeUrl`, `validateArtifactProvenance`,
  `enforceVerdict`, `computeContentFingerprint`, `hashRealityClaim`, `decideConvergenceGate`,
  or any function containing `httpStatus`/`referencedArtifactIds`/`contentHash` comparison
  logic OUTSIDE of `reality-verdict-schema.mjs`, and asserts ZERO such definitions exist in
  either caller (or anywhere outside `reality-verdict-schema.mjs`) — `required: true`
  (PROP-047).
- REQ-011's three-scenario table is now provably true: scenario 1 (healthy, unproven) reaches
  `CANNOT_VERIFY` via this exact composition, not `FAIL`.

### REQ-015: Ground-truth anchoring for `caller-per-invocation` claims — fixed public surface + pre-committed content fingerprint
Unchanged from iteration 5 (closure row 19). Note (REQ-012 fallback): the fixed-surface
membership check this requirement already mandates may ALSO serve as Phase 2a's chosen
diagnosability signal for Instagram, per REQ-012's explicit fallback ordering.

## Non-functional requirements

- **Performance bound**: unchanged from iteration 5 (600s cap, blocking runtime path).
- **Security constraint**: no signing/keypair/private-key library anywhere in this feature.
- **Security constraint**: all pure functions have no network/file access.
- **Security constraint**: `public_artifact_snapshot.py` structurally incapable of
  authenticated access.
- **Security constraint**: `reality-claim.json`, the precommit record, and (new) the
  artifact-trail `passId` namespace itself are never writable/choosable by any component that
  also produces the verdict checked against them — `passId` generation is now explicitly
  included in this sentence (it was conspicuously absent in iteration 5's version, per FIND-N).
- **Disclosed limit**: `.githooks/pre-push` is a discipline boundary, not a security boundary
  against an adversarial insider (row 16). Row 12 (adversarial-verifier-forges-during-its-
  own-run) remains open, narrowed this iteration to exclude the now-closed
  loop-pre-stages-under-a-chosen-passId variant (row 22).
- **New, disclosed limit**: `CANNOT_VERIFY` is an indefinitely-recurring, legitimate outcome
  for a platform Phase 2a has not yet proven diagnostic — this is NOT a bug to be silently
  suppressed or deduplicated (REQ-010 edge case); it is a visible signal that the required
  Phase 2a task (REQ-012) has not yet been completed, and completing it is the only way to
  resolve it into genuine `PASS` capability.

## Judgment vs determinism (anti-hardcoding discipline)

Per `~/.claude/rules/building-effective-ai-agents.md`: whether `domExcerpt` content at a
confirmed-2xx, confirmed-correct, confirmed-on-the-fixed-surface, confirmed-fingerprint-
matching URL actually LOOKS like the claim describes remains a JUDGMENT call, made by the LLM.
The CONTRADICTION-vs-INCONCLUSIVE taxonomy (REQ-004) is itself a fixed, deterministic lookup
table — which violation TYPE maps to which OUTCOME is decided once, in this spec, never by the
LLM at runtime and never by a heuristic guess about severity. `automatedVerification`'s role as
a final, boolean gate (not a judgment about whether a platform is "probably fine") is
unchanged in kind from iteration 5 — only its POSITION in the pipeline changed (a sequencing
fix, not a new judgment call). The rule, stated once, finally: **a public-artifact `PASS`
requires affirmative, counted, resolved, fresh, correctly-URLed, non-redirected,
correctly-tooled, 2xx-status, fixed-surface-corroborated, fingerprint-matched,
proven-diagnostic proof of the EXACT caller-declared claim; a public-artifact `FAIL` requires
POSITIVE, structural evidence of contradiction, never mere absence of proof; and everything in
between — no capture, a network failure, an empty body, or an unproven signal — is honestly
`CANNOT_VERIFY`, routed to a human, never silently folded into either PASS or FAIL, and never
flogged with an escalation mechanism (self-fix) that has nothing to fix.**

---

## REQ-016 (NEW, iteration 7 — FIND-S mitigation): HMAC-signed artifact rows + the trust-domain limit

**EARS**: WHEN the verification wrapper starts a pass THE SYSTEM SHALL generate a per-run HMAC
secret from a CSPRNG **inside the wrapper process**, pass it to `public_artifact_snapshot.py`
through a channel not observable to the loop under test (never a CLI argument, never an env var
exported into the loop's own environment, never written to the trail directory), and the capture
tool SHALL append `rowHmac = HMAC(secret, canonical_serialization_of_row)` to every row it writes.
`enforceVerdict` SHALL recompute the HMAC for every cited row. **A row that EXISTS but whose HMAC
does not verify (unsigned, mis-signed, or signed with a different pass's secret) is NOT "a missing
capture" — it is positive evidence of trail tampering and SHALL yield `FAIL` /
`artifact_trail_tampered` (REQ-017 governs; this supersedes any earlier "not a valid capture →
CANNOT_VERIFY" reading of this requirement).** `CANNOT_VERIFY` is reachable ONLY when the trail
contains NO row for the claim at all, or when the row records a network-level failure / empty body /
unproven diagnosability. A `PASS` is reachable only on a row that exists AND verifies AND does not
contradict the claim.

**What this buys**: a loop that observes the `passId` (row 12(b)'s race) can still *write* a file,
but it cannot produce a row that survives `enforceVerdict` without stealing a secret held in
another process's memory. That is a materially higher bar than "write a line to a jsonl".

**What this does NOT buy, stated without euphemism**: it is a bar, not a wall. A determined
same-uid adversary can still attack the secret. **A verifier cannot be made cryptographically
sound against a loop that shares its trust domain.** This spec therefore declares row 12 OPEN and
records the only real fix as future architectural work: run the reality-verifier under a different
OS user, or on a different host (cloud routines), so the code being judged cannot write the
evidence that judges it. Until then the operative defenses are (1) fresh-context spawn from
outside the loop, (2) recurring own-eyes review, (3) the fixed-public-surface + pre-committed
fingerprint anchors (REQ-015), which a forger would have to defeat *consistently* across
independent surfaces rather than by writing one line.

**Acceptance / proof obligations**
- **PROP-049** (required): a row with no `rowHmac` → never counted as a valid capture.
- **PROP-050** (required): a row with an `rowHmac` computed under a different secret (simulating a
  forger who observed the passId but not the secret) → never counted as a valid capture.
- **PROP-051** (required): the secret never appears in the wrapper's argv, in any env var visible
  to the spawned loop/verifier, or anywhere under the artifact-trail directory (mechanical check).
- **PROP-052** (required): a valid, correctly-signed row that CONTRADICTS the claim still yields
  `FAIL` (the signing layer must not become a new way to launder a contradiction into
  `CANNOT_VERIFY`).

---

## REQ-017 (NEW, iteration 8 — FIND-U fix): a TAMPERED row is positive evidence, not "cannot verify"

**The laundering channel FIND-U found**: with REQ-016's HMAC in place, a lying loop does not need
to steal the secret. It can let the capture tool honestly capture reality (e.g. a real 404 proving
the post does not exist — a `FAIL`), then **corrupt that row's bytes afterwards** using ordinary
same-uid file access. The signature no longer verifies, the row is discarded as "not a valid
capture", and the verdict falls back to `CANNOT_VERIFY` — which does not escalate to `self-fix` and
does not alarm. A `FAIL` has been laundered into a shrug.

**Ruling — absence and corruption are DIFFERENT facts and MUST NOT share an outcome:**

| Trail state | Meaning | Outcome |
|---|---|---|
| No row exists for the claim | The apparatus produced no read. Nothing is known. | `CANNOT_VERIFY` |
| A row exists and its HMAC verifies | A genuine capture. Judge the claim against it. | `PASS` or `FAIL` on the merits |
| **A row exists and its HMAC does NOT verify** | **Someone wrote or modified a row in this trail with a wrong/absent signature. That is positive evidence of tampering — a fact about the world, not an absence of facts.** | **`FAIL`**, category `artifact_trail_tampered`, escalated to `self-fix` and reported to the owner as tampering |

`CANNOT_VERIFY` is reserved for the apparatus producing NO read at all (no row, network error, empty
body, platform diagnosability unproven). It is NEVER reachable from a row that exists but fails
verification. REQ-004's taxonomy MUST carry `artifact_trail_tampered` as a first-class
CONTRADICTION category.

**Proof obligations**
- **PROP-053** (required): a trail containing a row whose bytes were modified after signing → verdict
  `FAIL`/`artifact_trail_tampered`. It MUST NOT be `CANNOT_VERIFY`. This is the exact FIND-U attack;
  it must be the fixture.
- **PROP-054** (required): a trail with NO row at all → `CANNOT_VERIFY`. (The two must be
  distinguishable, and this pair of PROPs proves they are.)

## REQ-018 (NEW, iteration 8 — FIND-V fix): a CANNOT_VERIFY streak is itself an alarm

**The hole**: nothing escalated a persistent `CANNOT_VERIFY`. A loop that never posts anything, or
that deliberately breaks its own capture apparatus, can sit in `CANNOT_VERIFY` forever and look
healthy to its owner — silence is indistinguishable from health. That reproduces the original sin
(the owner believes work is happening because nothing screamed).

**Ruling:**
1. **Every pass reports its verdict to the owner — including `CANNOT_VERIFY`.** Silence is never an
   outcome. A `CANNOT_VERIFY` pass is reported as "NOT verified — the checker could not get a
   diagnostic read", never as a post that happened.
2. **Two consecutive `CANNOT_VERIFY` verdicts for the same loop escalate exactly like `FAIL`** — to
   `self-fix.sh` — because a verification apparatus that cannot read reality twice in a row is
   itself broken and is a defect to be repaired, not a state to be tolerated.
3. The durable verdict trail MUST make a `CANNOT_VERIFY` streak mechanically visible (a counter the
   report reads), so "unverifiable forever" can never masquerade as "fine".

**Proof obligations**
- **PROP-055** (required): 2 consecutive `CANNOT_VERIFY` verdicts → `self-fix` escalation fires
  (fixture-level assertion on the escalation call, not on prose).
- **PROP-056** (required): a `CANNOT_VERIFY` pass's owner-facing report never contains a
  verified/success framing, and always names the reason the read failed.
