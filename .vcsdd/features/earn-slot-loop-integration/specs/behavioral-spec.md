# Behavioral Spec — earn-slot-loop-integration (lean) — the loop picks per-method earn slots

## Goal (provable)
The ONE runtime loop (brain=claude-p|proxy) can pick among PER-METHOD earn slots (earn/gig, earn/clip,
earn/affiliate, earn/video, earn/audit) each wake, spawn the picked slot, and record the result — proven
end-to-end with a stub slot, so the 4 CCs just drop their real `run.sh` into their slot dir to go live.

## Grounding (real code, ~/anicca/runtime/loop + ~/anicca/skills)
- `run-skill.mjs resolveSkillPath(slot,config)` = `path.join(home,'skills',slot.replace('/',sep),'run.sh')`
  → ALREADY resolves nested slots: `earn/gig` → `skills/earn/gig/run.sh`. (verify with a unit test)
- `prompt.mjs liveSlotNames(registry)` returns slots with status==='live'; `getToolDefinitions`/`buildSystemPrompt`/
  `buildUserMessage` surface them to the brain (tested in prompt.test.mjs). The brain PICKS among live slots.
- `index.mjs` loads registry → activeSkillSlots + skillCatalog → brain → parseToolCall → runSkill → ledger.
- Established pattern: the monolithic `earn` slot was RETIRED → split into per-method live slots (yield/hl_trade/
  x402_sell/token_launch). The 4 new methods follow the SAME pattern.

## Scope
IN: (1) declare earn/gig, earn/clip, earn/affiliate, earn/video, earn/audit in `skills/registry.json` (status
`declared` with one-line summaries; flip to `live` when a real run.sh exists); (2) a unit test proving
resolveSkillPath('earn/<sub>') → skills/earn/<sub>/run.sh; (3) a STUB slot `earn/_probe` (trivial run.sh that
prints a structured result + exit 0) used to E2E-prove the loop picks→spawns→records a nested earn slot;
(4) confirm liveSlotNames surfaces a live earn sub-slot to the brain menu.
OUT: the 4 CCs' real skill logic (they own run.sh + the 5-gate verification + record-earn inside each slot);
the brain's actual selection quality; cloud spawn.

## Requirements (EARS)
- **REQ-1 (declare slots):** `skills/registry.json.slots` SHALL contain `earn/gig`, `earn/clip`, `earn/affiliate`,
  `earn/video`, `earn/audit`, each with a non-empty `summary` (one line the brain reads) and `status` in
  {declared, live}. New methods default `declared` until their `run.sh` exists.
- **REQ-2 (nested resolution, PURE):** `resolveSkillPath('earn/<sub>', config)` SHALL equal
  `join(ANICCA_HOME,'skills','earn','<sub>','run.sh')` (cross-platform sep). Verified by unit test.
- **REQ-3 (brain menu):** `liveSlotNames(registry)` SHALL include every earn sub-slot whose status==='live',
  and `buildSystemPrompt`/tool-defs SHALL surface them so the brain can pick `earn/<sub>`.
- **REQ-4 (pick→run→record):** WHEN the brain picks a live earn slot, the loop SHALL spawn its run.sh with
  private keys scrubbed (env-filter), capture stdout+exitcode, and append one ledger line (slot, result).
- **REQ-5 (slot contract — enforced on the CCs, asserted structurally):** each live earn slot's run.sh SHALL
  be bounded, no-human-loop, print a structured one-line result, exit 0, and call record-earn(INV-7) internally.
  The harness does NOT implement the earn logic; it RUNS the slot + records. A `declared` slot with no run.sh
  SHALL NOT be offered as live (REQ-3) and SHALL return notFound (not crash) if forced.
- **REQ-6 (stub E2E):** a stub `skills/earn/_probe/run.sh` (echo a structured result, exit 0) SHALL, when set
  live, be picked-or-forced through runSkill and produce a ledger line — proving the nested-earn-slot path
  end-to-end with zero dependency on the CCs.

## Acceptance / E2E
- Unit: resolveSkillPath('earn/gig') path (REQ-2); liveSlotNames filters declared vs live incl nested (REQ-3).
- Integration: runSkill('earn/_probe', …) with the stub run.sh → {output, exitCode:0, notFound:false}; runSkill
  on a declared-but-missing slot → notFound:true (no crash).
- E2E (mine): a real loop wake (brain stubbed to emit a tool-call for earn/_probe) → ledger.jsonl gains a line
  recording earn/_probe ran. Confirms the ONE loop picks+runs+records a per-method earn slot.

## Done = registry declares the 5 earn slots; resolveSkillPath + liveSlotNames handle nested earn slots (unit);
## the stub earn/_probe runs through the real loop end-to-end (ledger line); adversary PASS + my run evidence.
## Then each CC dropping skills/earn/<slot>/run.sh + flipping status:live makes that earner go live on the one loop.
