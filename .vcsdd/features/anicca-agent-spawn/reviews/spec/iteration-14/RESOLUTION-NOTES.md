# Resolution Notes — spec review iteration-14 (FIND-1301)

**Feature**: anicca-agent-spawn · **Result**: finding resolved; `behavioral-spec.md` and
`verification-architecture.md` bumped to **revision: iteration 14**.

---

## FIND-1301 (major) — REQ-102's `SPAWN_COOLDOWN_DAYS` constant gains an explicit default value

**Problem**: `SPAWN_COOLDOWN_DAYS` was used repeatedly throughout REQ-102's own Cooldown Check and
REQ-305's failure-cap reconciliation (5 uses in `behavioral-spec.md`, plus REQ-102's own Acceptance
Criteria `cooldownDays` parameter) but its own default numeric value was never stated anywhere in the
document — unlike every sibling constant in the SAME requirement (`MIN_SHELTER_USD` defaults to `5.00`,
`SAFETY_MARGIN_MULTIPLIER` defaults to `2`, `FAILURE_COOLDOWN_CAP` defaults to `3`,
`MAX_CONCURRENT_SPAWNS` defaults to `1`). The only place a numeric value (`14`) appeared was REQ-402's
`BOOTSTRAP_WINDOW_DAYS`, which claimed to be "reusing REQ-102's own `SPAWN_COOLDOWN_DAYS` constant for
internal consistency" — a backward citation to a definition that did not actually exist at REQ-102's own
location. The real, existing `~/anicca/skills/self/spawn/lib/spawn-decision.js::decideSpawn`'s own
`rateLimitDays` parameter defaults to `14` (confirmed by direct read, line 11) — the plausible intended
source, but never cited by REQ-102 for this purpose. No proof obligation anywhere verified
`SPAWN_COOLDOWN_DAYS`'s value or its identity with `BOOTSTRAP_WINDOW_DAYS`.

**Resolution**: REQ-102 now explicitly states `SPAWN_COOLDOWN_DAYS` defaults to `14`, citing
`spawn-decision.js::decideSpawn`'s own `rateLimitDays` default (line 11) — the same citation-discipline
pattern this spec already uses for `SAFETY_MARGIN_MULTIPLIER`'s citation to `akt-treasury.sh`'s "2×"
convention. REQ-402's existing citation to "REQ-102's own `SPAWN_COOLDOWN_DAYS` constant" now correctly
resolves to a value REQ-102 actually states, rather than an implied one. A new proof obligation,
PROP-402e, verifies `BOOTSTRAP_WINDOW_DAYS` and `SPAWN_COOLDOWN_DAYS` are configured to the IDENTICAL
value by construction, never merely coincidentally equal — mirroring this spec's own established
"identical by construction, never merely close" discipline already used for REQ-206's
`seedUsdc`/REQ-204 gas-seed-transfer-amount pair.

### `specs/behavioral-spec.md` edits

| Location | Change |
|---|---|
| Revision header (lines 3-77) | Bumped `iteration 13` → `iteration 14`; `日付` bumped `2026-07-07` → `2026-07-08`; new lead paragraph (lines 4-20) describing the FIND-1301 fix, prior iteration-12 content preserved as a subordinate `AND spec review iteration-12 findings FIND-1201/1202 resolved ...` clause. |
| New `## Changelog (iteration 13 spec review → iteration 14)` section (lines 279-286, immediately before `## Scope of this increment (read first)`) | Added, following the exact same pattern as every prior iteration's changelog table (FIND-1301 row). |
| REQ-102 Cooldown Check paragraph (originally lines 594-596, now lines 594-601) | Inserted a new sentence immediately before the `windowStart = ...` formula sentence: "`SPAWN_COOLDOWN_DAYS` defaults to `14` (resolves FIND-1301) — reusing `~/anicca/skills/self/spawn/lib/spawn-decision.js::decideSpawn`'s own existing `rateLimitDays` parameter default (line 11) for consistency with prior art, rather than inventing an unrelated value — the SAME precedent this Cooldown Check's own array-scan discipline (above) already reuses from that module." |
| REQ-102 Acceptance Criteria, pure-function-signature bullet (originally line 660-661, now ~665-667) | Inserted "`cooldownDays` defaults to `14`, identical to `SPAWN_COOLDOWN_DAYS`'s own default above (resolves FIND-1301) — never independently configurable to a different value;" immediately before the existing `failureCooldownCap defaults to 3` sentence. |
| REQ-402 EARS clause (originally lines 2157-2160, now ~2179-2183) | Extended "(default `14`, reusing REQ-102's own `SPAWN_COOLDOWN_DAYS` constant for internal consistency rather than inventing an unrelated window)" to "(default `14`, reusing REQ-102's own `SPAWN_COOLDOWN_DAYS` constant — which REQ-102 itself now states defaults to `14` (resolves FIND-1301) — for internal consistency rather than inventing an unrelated window)" — confirming the citation now resolves to a real, stated REQ-102 default, non-circular (REQ-102 appears earlier in the document and is the sole source of the value; REQ-402 only consumes it). |

### `specs/verification-architecture.md` edits

| Location | Change |
|---|---|
| Revision header (lines 3-20) | Bumped `iteration 13` → `iteration 14`; `日付` bumped `2026-07-07` → `2026-07-08`; same restructuring pattern as the behavioral-spec header (no separate `## Changelog` section exists in this file — the revision header paragraph is this file's sole changelog mechanism, consistent with prior iterations). |
| Proof Obligations table — new row **PROP-402e** (inserted directly after PROP-402d, before PROP-403a) | Added: verifies `BOOTSTRAP_WINDOW_DAYS`'s configured value is IDENTICAL to `SPAWN_COOLDOWN_DAYS`'s configured value, never merely coincidentally equal. Tier 0/1, required. Filed under REQ-402 (the "downstream" requirement that borrows the value), mirroring the exact precedent of PROP-206g (filed under REQ-206, the downstream consumer of REQ-204's gas-seed-transfer amount) rather than under REQ-102 (the "upstream" source). |
| Tier 0 narrative list (REQ-402 mention) | Extended to cite PROP-402e's structural half alongside PROP-402d. |
| Tier 1 narrative list (REQ-402 mention) | Extended to cite PROP-402e's unit half alongside PROP-402a/c. |
| Gate item (10) | Extended with a new clause requiring the adversary to confirm `BOOTSTRAP_WINDOW_DAYS` is read as/derived from REQ-102's own `SPAWN_COOLDOWN_DAYS` constant (PROP-402e), citing the same "identical by construction" discipline already established for REQ-206's `seedUsdc`/gas-seed pair (item (4a)). |

---

## Note on revision numbering

The team-lead dispatch instructions for this task described the target revision as "iteration 15" (i.e.
"bump the revision header ... from 'iteration 14' to 'iteration 15'"). The actual on-disk revision at the
start of this task was **iteration 13** (confirmed by direct read of both spec files' revision headers),
and the established numbering convention throughout this document's own changelog history is: review
round directory `reviews/spec/iteration-N/` reviews the spec at revision `N-1` and, once its findings are
resolved, the spec is bumped to revision `N` (e.g. `reviews/spec/iteration-13/` reviewed revision 12 and
its fix bumped the spec to revision 13, per that iteration's own `RESOLUTION-NOTES.md`). Since this task
resolves `reviews/spec/iteration-14/`'s FIND-1301 finding against a spec that was at revision 13, the
spec is bumped to revision **14** (not 15), consistent with that convention and with task-list item #44
("P3 spawn spec iteration-15待ち" — i.e. the NEXT review round, which will be directory `iteration-15`
reviewing this now-produced revision 14). This is flagged here explicitly in case the "iteration 15"
figure in the dispatch instructions was intended to mean something else; no state.json/review-manifest
files were touched by this task per its own instructions, so the orchestrator can reconcile this
numbering when it advances `state.json` and creates the iteration-15 review directory.

---

## Verification of internal consistency (post-edit)

- Grep-confirmed `SPAWN_COOLDOWN_DAYS` now has exactly one explicit default statement in REQ-102's
  Cooldown Check prose, plus one matching restatement in REQ-102's own Acceptance Criteria — both
  reading `14`, both citing `spawn-decision.js::decideSpawn`'s own `rateLimitDays` default (line 11).
- REQ-402's `BOOTSTRAP_WINDOW_DAYS` citation to "REQ-102's own `SPAWN_COOLDOWN_DAYS` constant" now points
  at a REQ-102 that actually states the value — confirmed non-circular (REQ-102 precedes REQ-402 in the
  document; REQ-402 is a pure downstream consumer of the value, never redefining it).
  `PROP-402e` appears exactly once as a table-row definition in `verification-architecture.md`'s Proof
  Obligations table (no ID collisions with any existing `PROP-402*`/`PROP-102*` row), plus narrative
  cross-references in the Tier 0/Tier 1 lists and the Gate section's item (10).
- No edits were made to `state.json`, review manifest/verdict files, or the `iteration-15` review
  directory — those remain the orchestrator's responsibility per this task's own instructions. No
  commit/push was performed.
