# Behavioral Spec — earn-slot-loop-integration (lean) — ITERATION 2 (grounded in index.mjs's REAL path)

## Goal (provable, E2E)
The ONE runtime loop picks a PER-METHOD earn slot (`earn/gig|clip|affiliate|video|audit`), spawns its
`skills/earn/<sub>/run.sh`, passes it the earn env (EARN_LEDGER/EARN_MODE/WAKE_ID), classifies its result as
an EARN outcome from the earn-ledger, and records it — proven end-to-end with a stub slot that writes an
earn-ledger line. Then a CC dropping a real `run.sh` makes that earner live on the one loop.

## GROUNDING — the REAL execution path (read 2026-06-29, fixes iter-1 FIND-001..007)
File `~/anicca/runtime/loop/index.mjs`:
- The loop runs the picked slot via **`runSkillWithKillRef(slot,args,wakeId,config,killRef)`** (index.mjs:301) —
  NOT the `runSkill` export of run-skill.mjs (that export is unused by the loop). iter-1's grounding was wrong.
- **Path resolution (index.mjs:373-380):** `EARN_SLOT_DIRS=['earn','yield','hl_trade','x402_sell','token_launch']`.
  `slot in EARN_SLOT_DIRS` → `skills/earn/run.sh` (the fat shared earn skill). **else → `skills/<slot.replace('/',sep)>/run.sh`**.
  ⇒ `earn/gig` is NOT in EARN_SLOT_DIRS, so it ALREADY resolves to `skills/earn/gig/run.sh`. ✅ (no change needed)
- **GAP-A — earn classification (index.mjs:318):** `['earn','yield','hl_trade','x402_sell','token_launch'].includes(slot)`
  gates `classifyEarnResult(wakeId, earnLedgerPath, isProfitable)`. `earn/gig` is excluded ⇒ kind stays 'wake',
  profit never computed from the earn-ledger. ← MUST fix.
- **GAP-B — earn env (index.mjs buildSkillEnv, EARN_SLOTS map):** only `{earn,yield,hl_trade,x402_sell,token_launch}`
  receive `EARN_MODE/EARN_STRATEGY/WAKE_ID/EARN_LEDGER`. `earn/gig` falls to the else → gets only `ANICCA_ARGS+WAKE_ID`,
  **no EARN_LEDGER** ⇒ the sub-skill cannot write the earn-ledger line that GAP-A's classify reads. ← MUST fix.
- **GAP-C — prompt.mjs (≈:69-101,121):** hardcodes the old 5 slots + the line "there is NO generic earn slot",
  steering the brain away from `earn/*`. The brain must be offered the live `earn/<sub>` slots. ← MUST fix.
- VERIFIED-OK (don't over-correct): enum carries `earn/gig` (prompt:121) → parseToolCall returns it (:41) →
  index.mjs:379 resolves the path; `liveSlotNames` handles slash keys; notFound→'skill_missing' (no crash).
- Two ledgers: WAKE ledger `state/ledger.jsonl` (every wake) vs EARN ledger (per-source, correlated by WAKE_ID,
  read by `classifyEarnResult`). They are DISTINCT; the sub-skill writes the EARN ledger via record-earn.

## Scope
IN: (1) one predicate `isEarnSlot(slot) = EARN_ACTION.includes(slot) || slot.startsWith('earn/')` used in BOTH
the classify gate (GAP-A) and buildSkillEnv (GAP-B); for `earn/<sub>`, `EARN_STRATEGY=<sub>`; pass EARN_LEDGER/
EARN_MODE/WAKE_ID. (2) prompt.mjs surfaces live `earn/<sub>` slots + drop the "no generic earn slot" steer (GAP-C).
(3) declare `earn/gig|clip|affiliate|video|audit` in registry.json (status declared→live when run.sh exists).
(4) a STUB `skills/earn/_probe/run.sh` that writes a real EARN-ledger line (WAKE_ID, earn_usdc) + exits 0,
used to E2E-prove pick→spawn→env→earn-classify→wake-ledger.
OUT: the 4 CCs' real earn logic (their run.sh + 5-gate + record-earn live in their slot, their own VCSDD).

## Requirements (EARS)
- **REQ-1 (isEarnSlot predicate, PURE):** `isEarnSlot(slot)` SHALL be true for the legacy action slots
  {earn,yield,hl_trade,x402_sell,token_launch} AND for any `slot.startsWith('earn/')`. Unit-tested.
- **REQ-2 (classify, GAP-A):** the index.mjs:318 gate SHALL use `isEarnSlot(slot)` so a successful `earn/<sub>`
  wake runs `classifyEarnResult` against the earn-ledger (profit only from the ledger line, never exit-0 alone).
- **REQ-3 (env, GAP-B):** buildSkillEnv SHALL give every `isEarnSlot` slot `EARN_MODE`, `WAKE_ID`, `EARN_LEDGER`
  (when configured), and `EARN_STRATEGY` = the legacy map value for action slots, else `<sub>` for `earn/<sub>`.
- **REQ-4 (path, unchanged):** `earn/<sub>` SHALL resolve to `skills/earn/<sub>/run.sh` (already true via the
  else branch); `earn` and the 4 action slots SHALL still map to the fat `skills/earn/run.sh`. Regression-tested.
- **REQ-5 (prompt, GAP-C):** the brain menu SHALL include every `status:live` slot whose name starts `earn/`
  (with its summary), and SHALL NOT contain copy that denies a generic/earn slot exists.
- **REQ-6 (registry):** registry.json SHALL declare `earn/gig`, `earn/clip`, `earn/affiliate`, `earn/video`,
  `earn/audit` (summaries; status declared until run.sh exists). A declared slot with no run.sh ⇒ 'skill_missing'
  (not crash) if forced.
- **REQ-7 (slot contract — CCs own):** each live `earn/<sub>/run.sh` is bounded, no-human-loop, prints a
  structured one-line result, exits 0, and writes its earn-ledger line via record-earn(INV-7, WAKE_ID-correlated).
  The harness RUNS + classifies + records; it does not implement the earner.

## Acceptance / E2E (objective)
- Unit: isEarnSlot (REQ-1, incl earn/gig true, cook false); EARN_STRATEGY mapping (yield→yield, earn/gig→gig);
  path resolution (earn/gig→skills/earn/gig/run.sh; yield→skills/earn/run.sh) (REQ-4).
- Integration: with a stub `earn/_probe/run.sh` that writes an earn-ledger line {wake_id, earn_usdc:0.01} +
  exit 0 → buildSkillEnv gave it EARN_LEDGER + EARN_STRATEGY=_probe; classifyEarnResult reads the line.
- **E2E (mine, NO-MOCK): run the REAL loop one wake with the brain stubbed to emit a tool-call for `earn/_probe`
  (status:live) in a tmp ANICCA_HOME; assert (a) skills/earn/_probe/run.sh was spawned, (b) it received EARN_LEDGER
  + WAKE_ID, (c) the wake ledger line has slot=earn/_probe and (because the earn-ledger line exists) the earn
  classification ran, (d) no crash.** This proves a per-method earn slot flows pick→spawn→env→classify→record.

## Done = isEarnSlot wired into classify+env (GAP-A/B), prompt surfaces earn/* (GAP-C), registry declares the 5,
## the stub flows end-to-end through the REAL loop (earn env + classify + ledger), adversary PASS + my no-mock run.
