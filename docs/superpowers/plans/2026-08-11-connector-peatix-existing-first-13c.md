# Connector Peatix existing-first recovery Item 13C plan

## Goal

Stable-partition Peatix's already Calendar-covered same-event candidate before unprocessed Calendar-free candidates so the official wake can validate and reuse its exact bundle with Submit zero, then continue to the remaining candidates. Preserve every candidate and the original order inside both partitions.

## Live failure evidence

- Official schedule-unloaded wake `wake-9bb615ee5684f064d329e016` ran the pushed runner once and ended `circuit_open / effect_unknown`, failure count 2, bundle delta 0.
- Luma had one Calendar-free candidate, Connpass zero, and Peatix 18. The first unprocessed Peatix candidate reached cache/direct/Harness and became ambiguous before the accepted same-event Peatix bundle candidate was visited.
- The terminal wake report and delivery were durable; Telegram provider ID `11062` is positive. Process/lock/owned page cleaned up, four labels remained unloaded, Git stayed clean/upstream `0/0`.
- Peatix Calendar gating already recognizes the exact overlapping `connector_idempotency` SHA and excludes only that same event from conflict. Discovery currently discards that information and preserves raw search order.

## Ponytail full gate

- Reuse the existing strict canonical URL SHA and overlapping Calendar marker comparison. Add no applied-bundle index, runner dependency, database, cursor, ranking model, filter, provider action, browser action, schedule, or retry.
- Change only Peatix discovery production/test. Do not touch runner/evidence/Calendar inventory production.
- This is a stable partition, not a score or stop gate. Every Calendar-free candidate remains present. Exact-covered candidates preserve their mutual order; all others preserve theirs.
- Wrong, absent, non-overlapping, or another-event markers never gain priority.

## Implementation slice

Luna owns only:

1. `apps/mr-bot/lib/connector-peatix-workflow.test.js`
2. `apps/mr-bot/lib/connector-peatix-workflow.js`

Soft target: 2 files; production +10–25 LOC; tests +35–70 LOC.

Final size: production +25/-13 LOC and tests +69 LOC, both inside the soft target.

### RED

1. Search order `[unprocessed A, exact-covered B, unprocessed C]` returns `[B, A, C]` with count and candidate bytes otherwise unchanged.
2. Two exact-covered candidates preserve their original relative order and all remaining candidates preserve theirs.
3. Wrong hash, absent marker, another-event marker, and exact marker on a non-overlapping interval preserve original order.
4. Existing same-event conflict exemption remains exact; unrelated overlapping events still block.
5. Discovery audit counts remain identical and no candidate is added, removed, or duplicated.
6. Direct action/readback and all existing Peatix failure mappings remain unchanged.

### GREEN

- Extract or reuse one predicate that requires a timed interval overlap and exact canonical URL SHA equality.
- Use that predicate both for same-event conflict exemption and post-filter stable partition.
- Return exact-covered candidates first, then all other Calendar-free candidates; never sort within a partition.

## Verify

- Focused Peatix workflow; busy inventory; evidence, minimal runner/production, provider/Harness, native entrypoint; changed-file syntax; `git diff --check`.
- Fresh Sol review for stable ordering, no filtering/ranking drift, overlap/hash exactness, malformed-marker assumptions, audit counts, provider non-regression, and absence of external effects.
- Update SSOT, commit, push, then run the official foreground wake exactly once more while schedules stay unloaded. Do not mark Item 13 complete until live reuse/Submit-zero/later-candidate/positive-report/cleanup acceptance passes.

## Result

- Luna reproduced the ordering failure: exact-covered candidates remained behind unprocessed search-order candidates. The non-priority controls already preserved order.
- Production now reuses one predicate requiring timed overlap and exact canonical URL SHA equality for both same-event conflict exemption and a two-array stable partition.
- Single and multiple exact-covered candidates move first while mutual order, remaining order, candidate bytes, counts, and audit remain unchanged. Wrong, absent, other-event, non-overlapping, and malformed markers gain no priority.
- Luna focused and adjacent suites passed except the three unchanged baselines. Sol independently reran the relevant suite with all new tests passing; syntax and `git diff --check` passed. Fresh Sol review returned `ship`.
- Code capability is complete. Item 13 remains open until the second official 13C foreground wake passes live acceptance. Schedule remains unloaded.
