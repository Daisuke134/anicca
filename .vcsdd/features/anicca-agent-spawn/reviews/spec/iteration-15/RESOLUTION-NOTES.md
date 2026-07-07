# Resolution Notes — spec review iteration-15 (FIND-1401)

**Feature**: anicca-agent-spawn · **Result**: finding resolved; `behavioral-spec.md` and
`verification-architecture.md` bumped to **revision: iteration 15**.

---

## FIND-1401 (critical) — `recentSpawnAttempts` gains a real, cited derivation from `ledger.js`'s rows

**Problem**: REQ-102's Cooldown Check pinned `recentSpawnAttempts: Array<{ts, outcome}>` as its own
input, but no function anywhere in the spec derived this array from `ledger.js`'s real rows — unlike
REQ-101's exactly analogous need, which is satisfied by a named, fully-specified pure join function,
`filterProductiveCitizens`. Two concrete gaps made this unimplementable, both confirmed against the
real, current source:

1. **No timestamp field existed for a failed/in-flight row's `ts`.** `~/anicca/skills/self/spawn/lib/
   child-spec.js::buildChildSpec`'s real, current returned row (confirmed by direct read, lines 35-46)
   carries no generic timestamp field at all — only REQ-305's `active_since`, set only on the SUCCESS
   path. A `"failed"` or `"provisioning"` row had no cited data source for `ts` whatsoever.
2. **The status→outcome mapping was unspecified for a `"bootstrap_failed"` relabeling.** It was never
   stated whether a LATER `"bootstrap_failed"` row (REQ-402) for an already-`"active"` child flips that
   attempt's `recentSpawnAttempts` entry to `outcome:"failure"`, leaves it `outcome:"success"`, or could
   be double-counted as both by a naive per-row mapping.

**Resolution**: Following the EXACT precedent REQ-305 already establishes for `active_since` (an extra
field the effectful caller merges into `buildChildSpec`'s base returned object before calling
`appendChild`, `child-spec.js` itself never modified), REQ-305 now specifies a new field,
`attempted_ms`, set to `nowMs` on the very FIRST `ledger.js` row ever appended for a given `child_id`
and copied forward, unchanged, onto every later row for that SAME `child_id` (a `"failed"` row, an
`"active"` row, or REQ-402's `"bootstrap_failed"` row) — never a freshly-generated timestamp for a
follow-up row. A new sibling pure function, same file as `filterProductiveCitizens`,
`~/anicca/skills/self/spawn/lib/treasury-gate.mjs::deriveRecentSpawnAttempts({ledgerRows}) →
Array<{ts, outcome}>`, groups `ledgerRows` by `child_id` and maps each group to exactly ONE entry:
`outcome:"success"` PERMANENTLY if the group ever reached `"active"` (a later `"bootstrap_failed"` row
never retroactively flips this, per REQ-102's own existing "a successful attempt is ALWAYS
cooldown-triggering" rule), else `outcome:"failure"` if the group's last (last-write-wins) row is
`"failed"`, else EXCLUDED entirely if the group's last row is still `"provisioning"` (an in-flight
attempt, already tracked via `childrenProvisioning`/`MAX_CONCURRENT_SPAWNS`, never double-counted here)
— one entry per `child_id`, never per raw row. REQ-102's real orchestration now calls this function
directly over `readChildren`'s real output, never a hand-rolled reimplementation at the call site,
mirroring REQ-101's own `filterProductiveCitizens` integration discipline. Three new proof obligations
verify this: PROP-102f (Tier 1, the four-case unit fixture), PROP-102g (Tier 1/2, the real-derivation
integration discipline, mirroring PROP-101d/PROP-101e), and PROP-305h (Tier 0, the `attempted_ms`
field-lifecycle structural check).

### `specs/behavioral-spec.md` edits

| Location | Change |
|---|---|
| Revision header (lines 3-30, was lines 3-20) | Bumped `iteration 14` → `iteration 15`; new lead paragraph describing the FIND-1401 fix, prior iteration-13→14 content preserved as a subordinate `AND spec review iteration-13 finding FIND-1301 resolved ...` clause, following the exact chaining pattern every prior revision bump already uses. |
| New `## Changelog (iteration 14 spec review → iteration 15)` section (inserted immediately after the existing `## Changelog (iteration 13 spec review → iteration 14)` section, before `## Scope of this increment (read first)`) | Added, with a `\| Finding \| Severity \| Resolution \|` table row for FIND-1401, following the exact same pattern as every prior iteration's changelog table. |
| REQ-102's Cooldown Check, new paragraph inserted between "...never two different behaviors." and the `SPAWN_THRESHOLD_USD = ...` bullet block | New paragraph, **"Deriving `recentSpawnAttempts` from real ledger rows (new, resolves FIND-1401, critical)"**, fully defines `deriveRecentSpawnAttempts({ledgerRows})`'s 4-step derivation rule (group by `child_id` → read `ts` from `attempted_ms` → map `outcome` per the success-permanence/failure/in-flight-exclusion rule → exactly one entry per group). |
| REQ-102 Acceptance Criteria, new bullet inserted immediately after the `recentSpawnAttempts`/`cooldownDays`/`failureCooldownCap` shape bullet | "**(resolves FIND-1401)** `recentSpawnAttempts` is never hand-assembled by the calling orchestration — it is ALWAYS the direct return value of `deriveRecentSpawnAttempts({ledgerRows: readChildren(...)})` ..." |
| REQ-305, new paragraph inserted between the existing "no partial spawn" paragraph and the "WHEN, and only when, a spawn attempt completes..." (`active_since`) paragraph | New paragraph, **"A stable attempt-timestamp field, `attempted_ms` (new, resolves FIND-1401, critical)"**, specifies the first-row-sets/later-rows-copy-forward rule and explicitly states `child-spec.js`/`buildChildSpec` itself is NOT modified. |
| REQ-305 Acceptance Criteria, new bullet inserted immediately after the existing `active_since` bullet | "**(new, resolves FIND-1401)** A structural/Tier-0 check confirms `attempted_ms` is set ... (PROP-305h)." |
| REQ-402 EARS clause, extended mid-paragraph (the `ledger.js::appendChild`-ing a NEW row sentence) | Added: "— this new row ALSO copies forward, unchanged, the SAME `attempted_ms` value REQ-305 set on that child's very first ledger row (never a freshly-generated timestamp for this relabeling row, resolves FIND-1401's second gap) —". |
| REQ-402 Acceptance Criteria, new bullet appended after the existing `children_bootstrap_failed` observability-only bullet | "**(resolves FIND-1401)** REQ-102's `deriveRecentSpawnAttempts` treats a `child_id` that ever reached `"active"` as `outcome:"success"` PERMANENTLY ... (PROP-102f)." |
| Purity boundary overview table (`## Purity boundary analysis`), "Spawn eligibility gate" row | Extended to cite the new `deriveRecentSpawnAttempts({ledgerRows})` function and its file location (resolves FIND-1401). |
| Purity boundary overview table, "Spawn ledger append" row | Extended to cite the new `attempted_ms` field alongside the existing `active_since` field, and REQ-102's new `deriveRecentSpawnAttempts` as a reader of it (resolves FIND-1401). |

### `specs/verification-architecture.md` edits

| Location | Change |
|---|---|
| Revision header (lines 3-31, was lines 3-17) | Bumped `iteration 14` → `iteration 15`; new lead paragraph condensing the FIND-1401 fix (mirroring `behavioral-spec.md`'s own header, this file's established condensed-summary convention), prior FIND-1301 content preserved as a subordinate `AND spec review iteration-13 finding FIND-1301 resolved ...` clause. |
| Purity Boundary Map — new row **`deriveRecentSpawnAttempts`** (inserted directly after the `filterProductiveCitizens` row, directly before the `decideColonySpawn` row) | Added: `~/anicca/skills/self/spawn/lib/treasury-gate.mjs::deriveRecentSpawnAttempts({ledgerRows}) → Array<{ts, outcome}>`, PURE (new), full derivation-rule description, resolves FIND-1401. |
| Purity Boundary Map — `decideColonySpawn` row | Classification extended to `"input derivation corrected, resolves FIND-1401"`; note added that `recentSpawnAttempts` is never hand-assembled, always the direct return of the new function. |
| Purity Boundary Map — `ledger.js::appendChild`/`readChildren` row | Extended to cite the new `attempted_ms` field's lifecycle (set on first row, copied forward including onto REQ-402's `"bootstrap_failed"` row) and the "no `child-spec.js` modification" note, alongside the existing `active_since` citation (resolves FIND-201/FIND-1401). |
| Tier 0 narrative list | New clause: "REQ-305's structural check (PROP-305h, resolves FIND-1401) that `attempted_ms` is set on the FIRST `ledger.js` row ... never a freshly-generated timestamp on a follow-up row". |
| Tier 1 narrative list | Extended the REQ-102 mention to cite the new `deriveRecentSpawnAttempts` join and its four-case fixture (PROP-102f, resolves FIND-1401). |
| Tier 2 narrative list | New clause citing PROP-102g (real orchestration wiring over a real `ledger.js` file, mirroring PROP-101d/PROP-101e's discipline). |
| Proof Obligations table — new rows **PROP-102f**, **PROP-102g** (inserted directly after PROP-102e, before PROP-103a) | Added per the design above. |
| Proof Obligations table — new row **PROP-305h** (inserted directly after PROP-305g, before PROP-306a) | Added per the design above. |
| Gate — new sub-item **(1f)** (inserted directly after (1e), before item (2)) | Requires the adversary to confirm `deriveRecentSpawnAttempts` is the sole mechanism producing `recentSpawnAttempts` (PROP-102g), independently re-derive the four-case mapping (PROP-102f), and confirm the `attempted_ms` field-lifecycle including the `"bootstrap_failed"` row (PROP-305h). |

---

## Note on revision numbering

Confirmed by direct read of both spec files' revision headers at the start of this task: the on-disk
revision was **iteration 14** (produced by the prior task's resolution of FIND-1301, per
`reviews/spec/iteration-14/RESOLUTION-NOTES.md`'s own numbering note). This task's dispatch was for
`reviews/spec/iteration-15/`'s `verdict.json`, which reviewed that revision-14 spec and raised
FIND-1401. Following the SAME convention that note already established (review round directory
`iteration-N` reviews the spec at revision `N-1` and, once resolved, the spec is bumped to revision
`N`), this task resolves `reviews/spec/iteration-15/`'s finding against a spec that was at revision 14,
so the spec is bumped to revision **15** — consistent with the task list's own next item, "P3 spawn
spec iteration-16待ち", i.e. the NEXT review round (directory `iteration-16`) will review this
now-produced revision 15. No `state.json`/review-manifest files were touched by this task per its own
instructions, so the orchestrator can advance `state.json` and create the `iteration-16` review
directory separately.

---

## Verification of internal consistency (post-edit)

- Grep-confirmed `PROP-102f`, `PROP-102g`, and `PROP-305h` each appear exactly once as a table-row
  definition in `verification-architecture.md`'s Proof Obligations table (no ID collisions with any
  existing `PROP-102*`/`PROP-305*` row), plus narrative cross-references in the Tier 0/1/2 lists and
  the Gate section's new item (1f).
- `deriveRecentSpawnAttempts` and `attempted_ms` are each referenced consistently across both spec
  files (9-13 occurrences each), all pointing at the SAME file location
  (`~/anicca/skills/self/spawn/lib/treasury-gate.mjs`) and the SAME field name — no divergent spelling
  or competing definition introduced.
- Confirmed the fix does NOT modify `child-spec.js`/`buildChildSpec`'s own source, `ledger.js`'s own
  `{readChildren, appendChild}` shape, or REQ-101's `filterProductiveCitizens` — this is purely an
  additive extension (a new field on the caller-assembled row object, and a new sibling pure function),
  mirroring the exact precedent `active_since` already established.
- No edits were made to `state.json`, review manifest/verdict files, or the `iteration-16` review
  directory — those remain the orchestrator's responsibility per this task's own instructions. No
  commit/push was performed.
