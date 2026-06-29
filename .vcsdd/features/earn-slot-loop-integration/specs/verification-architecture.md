# Verification Architecture — earn-slot-loop-integration — ITERATION 2 (grounded in index.mjs)

## Purity boundary
### PURE (unit-tested, no spawn/network/clock)
- `isEarnSlot(slot)` (NEW, the single predicate) — true for {earn,yield,hl_trade,x402_sell,token_launch} ∪ startsWith('earn/').
- `earnStrategyFor(slot)` — legacy map for action slots; `<sub>` for `earn/<sub>` — pure.
- path-resolution rule (the if/else in runSkillWithKillRef) — extract/test the mapping: earn+actions→skills/earn/run.sh; earn/<sub>→skills/earn/<sub>/run.sh.
- `liveSlotNames(registry)` + prompt menu builders (already pure + tested in prompt.test.mjs) — add earn/* live cases.

### EFFECTFUL (integration / NO-MOCK E2E)
- `buildSkillEnv` — gives isEarnSlot slots EARN_MODE/EARN_STRATEGY/WAKE_ID/EARN_LEDGER (integration assert on the env object).
- `runSkillWithKillRef` — spawns the stub; `classifyEarnResult` reads the earn-ledger.
- the REAL loop wake (index.mjs) with a stubbed brain → spawns earn/_probe → earn env + classify + wake-ledger line.

## Test plan
| Layer | What | How |
|---|---|---|
| Unit | isEarnSlot (earn/gig=true, cook=false, yield=true); earnStrategyFor(earn/gig)=gig, (yield)=yield; path map | node:test, RED first |
| Unit | prompt: liveSlotNames + system prompt include a live earn/* slot; no "no generic earn slot" string | node:test against prompt.mjs |
| Integration | buildSkillEnv('earn/_probe') has EARN_LEDGER+EARN_STRATEGY=_probe+WAKE_ID; ('cook') does not | node:test |
| Integration | stub earn/_probe/run.sh writes earn-ledger {wake_id,earn_usdc} + exit0 → classifyEarnResult finds it | node:test |
| E2E (mine, NO-MOCK) | real loop, brain-stub emits earn/_probe tool-call, tmp ANICCA_HOME → spawned + got EARN_LEDGER + wake-ledger slot=earn/_probe + no crash | run index.mjs with stub brain + assert ledger files |

## Anti-tautology (iter-1 FIND-006)
The E2E asserts the EARN path specifically: (a) the spawned child received EARN_LEDGER (proves GAP-B fixed),
(b) the earn-ledger line written by the stub is what classify reads (not just any exit-0 wake line). A non-earn
slot would NOT receive EARN_LEDGER, so the assertion fails closed if GAP-A/B regress.

## Done (4-D)
spec ✓ + tests ✓ (unit isEarnSlot/strategy/path/prompt + integration env+classify + no-mock loop E2E) +
impl ✓ (isEarnSlot in classify+env, prompt surfaces earn/*, registry 5 slots, stub) + verification ✓
(adversary PASS on disk + my real-loop run showing earn/_probe flowed end-to-end).
