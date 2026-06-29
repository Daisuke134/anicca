# Verification Architecture — earn-slot-loop-integration

## Purity boundary
### PURE (unit-tested, no network/spawn)
- `resolveSkillPath(slot, config)` (already in run-skill.mjs) — pure path join; test earn/<sub> resolution + sep.
- `liveSlotNames(registry)` + the slot-menu builders (already in prompt.mjs, tested) — reuse; add nested-earn cases.
- registry shape check (the 5 earn slots present, valid status enum).

### EFFECTFUL (integration/E2E)
- `runSkill(slot,args,wakeId,config)` — spawns run.sh; tested via the `earn/_probe` stub (no real earner needed).
- the loop wake (index.mjs) — E2E with the brain stubbed to pick earn/_probe → ledger line.

## Test plan
| Layer | What | How |
|---|---|---|
| Unit | resolveSkillPath('earn/gig')→path; liveSlotNames includes live nested earn, excludes declared | node:test, RED first |
| Integration | runSkill('earn/_probe') with stub → exit0+output; runSkill('earn/gig') with no run.sh → notFound (no crash) | node:test spawning the stub |
| E2E (mine) | loop wake, brain stub emits tool-call earn/_probe → ledger.jsonl gains the line | run index.mjs with a stub brain + tmp ANICCA_HOME |

## Slot-contract assertion (REQ-5, structural)
A live earn slot MUST have an executable run.sh; the harness asserts notFound-not-crash when missing, and
runs+records when present. The 5-gate + record-earn(INV-7) live INSIDE each CC's run.sh (their VCSDD), not here.

## Done (4-D)
spec ✓ + tests ✓ (unit + integration + stub E2E) + impl ✓ (registry slots + any resolveSkillPath fix) +
verification ✓ (adversary PASS on disk + my E2E run: ledger line from earn/_probe through the real loop).
