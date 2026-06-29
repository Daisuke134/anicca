// earn-slot.mjs — PURE predicate + strategy mapping for earn slots. ONE source of truth so the classify
// gate (index.mjs:318) and buildSkillEnv (index.mjs EARN_SLOTS) agree on "what counts as an earn slot".
// Legacy action slots (one shared fat earn skill, strategy = the slot) PLUS per-method nested earn/<sub>.

// Legacy earn-action slots that all map to the fat skills/earn/run.sh, strategy named by the slot.
const EARN_ACTION = { earn: null, yield: 'yield', hl_trade: 'hl', x402_sell: 'x402', token_launch: 'token' };

// True for the legacy action slots AND any per-method nested earn slot (earn/gig, earn/clip, …).
export function isEarnSlot(slot) {
  if (typeof slot !== 'string' || slot === '') return false;
  return Object.prototype.hasOwnProperty.call(EARN_ACTION, slot) || slot.startsWith('earn/');
}

// The EARN_STRATEGY value for a slot, PRESERVING the fat-earn fallback contract (index.mjs:446):
//   - legacy action slots → their map value (yield→yield, hl_trade→hl, x402_sell→x402, token_launch→token)
//   - fat `earn` → null  (so buildSkillEnv keeps `|| args.strategy || 'yield'`)
//   - earn/<sub> → '<sub>' (one level only; the registry declares only single-level earn slots)
//   - non-earn → null
export function earnStrategyFor(slot) {
  if (typeof slot !== 'string') return null;
  if (Object.prototype.hasOwnProperty.call(EARN_ACTION, slot)) return EARN_ACTION[slot]; // incl earn→null
  if (slot.startsWith('earn/')) return slot.slice('earn/'.length) || null;
  return null;
}

// The skill entrypoint path (relative to skills/) for a slot — single source so the loop's inline resolver
// and tests agree (REQ-4). Legacy action slots {earn,yield,hl_trade,x402_sell,token_launch} all run the fat
// `earn/run.sh`; everything else (incl per-method earn/<sub> and non-earn slots) runs `<slot>/run.sh`.
// Single-level only (FIND-007): `slot` carries at most one slash (earn/<sub>); deeper is not declared.
export function earnSkillRelPath(slot) {
  if (Object.prototype.hasOwnProperty.call(EARN_ACTION, slot)) return 'earn/run.sh';
  return `${slot}/run.sh`;
}

export { EARN_ACTION };
