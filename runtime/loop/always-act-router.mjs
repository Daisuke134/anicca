/**
 * always-act-router.mjs — Pure Core: franklin-alwaysact-skill-router (REQ-501..513).
 *
 * "Franklin never waits — every wake surveys the full earn-menu and picks exactly one positive-EV
 * earning action" (memory `feedback_franklin_never_waits_always_acts_to_earn`). This module is the
 * deterministic, side-effect-free core of that router: menu assembly, earn-action classification,
 * no-realized-action detection, the bounded reprompt/reroute attempt-state machine, and MUST-ACT
 * prompt/ledger record shaping. It mirrors the existing purity split of context.mjs/prompt.mjs/
 * tier.mjs/catalog-gate.mjs/earn-slot.mjs — no I/O, every input pre-loaded and passed in, every
 * classifier (riskTagOf/alwaysAvailableOf/hasOpenRiskPositionOf/catalogFilterFn) injected exactly
 * like catalog-gate.mjs's own contract.
 *
 * REQ-507 (skill choice stays 100% model judgment): this module never ranks, scores, or filters by
 * a model's chosen slot/args CONTENT — every branch below reads only registry BOOKKEEPING fields
 * (status, the doctrine-named set, risk tags, open-position facts) or the harness's own attempt-state
 * counter, never the model's args or free-text output.
 *
 * See .vcsdd/features/franklin-alwaysact-skill-router/specs/verification-architecture.md's Purity
 * Boundary Map for the authoritative, adversary-reviewed design this module implements.
 */

import { isEarnSlot } from './earn-slot.mjs';
import { getToolDefinitions } from './prompt.mjs';

// REQ-502: doctrine-named earn actions NOT already covered by isEarnSlot (a fixed, doctrine-derived
// bookkeeping set — never inferred, never regex/keyword-matched over model output).
const DOCTRINE_EARN_ACTIONS = new Set(['economy/gig', 'economy/lending']);

/**
 * isEarnActionSlot — REQ-502: the union of isEarnSlot and the doctrine-named set. Purely additive
 * over isEarnSlot (which is never modified/forked — see behavioral-spec.md sec1).
 *
 * @param {string} name
 * @param {{isEarnSlotFn?: (name: string) => boolean}} [opts] - injection point for tests; defaults
 *   to the real isEarnSlot.
 * @returns {boolean}
 */
export function isEarnActionSlot(name, { isEarnSlotFn = isEarnSlot } = {}) {
  return isEarnSlotFn(name) || DOCTRINE_EARN_ACTIONS.has(name);
}

/**
 * assembleAlwaysActMenu — REQ-502/503: every registry slot with status "live" that is
 * isEarnActionSlot(name), further filtered through the injected catalogFilterFn (catalog-gate.mjs's
 * filterCatalog, never re-implemented here) so the existing bootstrap-reserve gate applies unchanged.
 *
 * @param {object} opts
 * @param {object} opts.registry - parsed skills/registry.json
 * @param {Function} opts.catalogFilterFn - catalog-gate.mjs::filterCatalog (injected)
 * @param {number} opts.balanceUsdc
 * @param {number} opts.reserveThresholdUsdc
 * @param {(slotName: string) => (string|undefined)} opts.riskTagOf
 * @param {(slotName: string) => boolean} opts.alwaysAvailableOf
 * @param {(slotName: string) => boolean} opts.hasOpenRiskPositionOf
 * @returns {string[]}
 */
export function assembleAlwaysActMenu({
  registry,
  catalogFilterFn,
  balanceUsdc,
  reserveThresholdUsdc,
  riskTagOf,
  alwaysAvailableOf,
  hasOpenRiskPositionOf,
}) {
  const slots = registry && registry.slots;
  const liveSlots = slots && typeof slots === 'object'
    ? Object.keys(slots).filter((name) => slots[name] && slots[name].status === 'live')
    : [];
  const liveEarnActionSlots = liveSlots.filter((name) => isEarnActionSlot(name));

  if (typeof catalogFilterFn !== 'function') return liveEarnActionSlots;

  return catalogFilterFn({
    balanceUsdc,
    allSlotNames: liveEarnActionSlots,
    riskTagOf,
    alwaysAvailableOf,
    hasOpenRiskPositionOf,
    reserveThresholdUsdc,
  });
}

/**
 * buildAlwaysActToolDefinitions — REQ-504: a thin wrapper over prompt.mjs::getToolDefinitions's
 * additive `omitSleep` opt — not a parallel reimplementation, so the SAME function brain.mjs's own
 * `tools:` line calls is what this pure helper is verified against (PROP-504a necessary,
 * always-act-wire-seam.test.mjs::PROP-504b sufficient).
 *
 * @param {string[]} menuSlots
 * @returns {object[]}
 */
export function buildAlwaysActToolDefinitions(menuSlots) {
  return getToolDefinitions(menuSlots, { omitSleep: true });
}

/**
 * isMarketRiskFree — REQ-506: reads registry risk tags via the injected riskTagOf classifier (the
 * SAME injection assembleAlwaysActMenu already threads from skills/registry.json's per-slot `risk`
 * field — not a new classification source). A slot missing the risk field entirely evaluates
 * `undefined === 'safe'` -> false: fail-closed, mirroring catalog-gate.mjs's own untagged-slot default.
 *
 * @param {string} slot
 * @param {(slotName: string) => (string|undefined)} riskTagOf
 * @returns {boolean}
 */
export function isMarketRiskFree(slot, riskTagOf) {
  return typeof riskTagOf === 'function' && riskTagOf(slot) === 'safe';
}

/**
 * noRealizedAction — REQ-506: true iff earnLine is STRICTLY null (classifyEarnResult's own
 * "no realized action" signal) — never merely falsy; a real `{profitable:false}` line is still a
 * realized economic action, not a no-op.
 *
 * @param {object|null} earnLine
 * @returns {boolean}
 */
export function noRealizedAction(earnLine) {
  return earnLine === null;
}

/**
 * isRejectableSleepOrOffMenu — REQ-513 (spec-review FIND-103/FIND-201 fix): true iff `slot` is the
 * fabricated string "sleep" OR is not a member of `currentOfferedSlots` — the exact per-attempt array
 * that was actually offered to the model for THIS attempt (never the static full-wake menu once a
 * reroute has narrowed it). This predicate answers ONLY "is slot valid for this attempt" — it has NO
 * branch-selection role (spec-review FIND-301: that decision belongs exclusively to
 * nextRerouteState's attemptsUsed output, below).
 *
 * @param {string} slot
 * @param {string[]} currentOfferedSlots
 * @returns {boolean}
 */
export function isRejectableSleepOrOffMenu(slot, currentOfferedSlots) {
  const offered = Array.isArray(currentOfferedSlots) ? currentOfferedSlots : [];
  return slot === 'sleep' || !offered.includes(slot);
}

/**
 * nextRerouteState — REQ-505/506/511/513 (spec-review iteration-4 FIND-301, the class-killing fix):
 * the pure bounded-retry state machine whose `attemptsUsed` domain, {0, 1}, is the SOLE arbiter of
 * every retry/reroute/escalation branch decision — never `currentOfferedSlots`/menu array identity.
 *
 * @param {{attemptsUsed: number, maxAttempts: number}} opts
 * @returns {{shouldRetry: boolean, attemptsUsedNext: number, exhausted: boolean}}
 */
export function nextRerouteState({ attemptsUsed, maxAttempts }) {
  if (attemptsUsed < maxAttempts) {
    return { shouldRetry: true, attemptsUsedNext: attemptsUsed + 1, exhausted: false };
  }
  return { shouldRetry: false, attemptsUsedNext: attemptsUsed, exhausted: true };
}

/**
 * buildMustActReinforcement — REQ-505: a pure, deterministic MUST-ACT directive string, additive to
 * buildUserMessage's existing steer-composition pattern (prompt.mjs appends this verbatim as one more
 * line when present on ctx — see the wiring in index.mjs's reprompt call site).
 *
 * @param {object} ctx - WakeContext (reads ctx.alwaysActMenu only)
 * @param {{outcome?: string}} priorAttempt
 * @returns {string}
 */
export function buildMustActReinforcement(ctx, priorAttempt) {
  const menu = ctx && Array.isArray(ctx.alwaysActMenu) ? ctx.alwaysActMenu.join(', ') : '';
  const outcome = priorAttempt && typeof priorAttempt.outcome === 'string' ? priorAttempt.outcome : 'unknown';
  return `MUST-ACT (always-act mode, previous attempt: ${outcome}): you did NOT select a valid earn action. ` +
    `Sleep/no-op is not offered this wake. You MUST call run_skill with slot set to exactly one member of ` +
    `[${menu}] and your real args. Pick one now and act.`;
}

/**
 * buildAlwaysActLedgerFields — REQ-508/510: pure record-shaping for the router's own ledger fields.
 * `attemptsUsed` is passed through VERBATIM in its {0,1} domain (spec-review iteration-5 notes.md
 * non-blocking observation #2 fix) — never re-derived as a think()-call count. `slot: null` +
 * `realized: false` is REQ-508's truthful "never a fabricated success" escalation shape.
 *
 * @param {{wakeId: string, slot: string|null, args: object, attemptsUsed: number, realized: boolean}} opts
 * @returns {object}
 */
export function buildAlwaysActLedgerFields({ wakeId, slot, args, attemptsUsed, realized }) {
  return {
    wake_id: wakeId,
    slot: slot === undefined ? null : slot,
    args: args && typeof args === 'object' ? args : {},
    attemptsUsed,
    realized: realized === true,
  };
}

/**
 * isPostGoLiveRegression — REQ-512 (spec-review FIND-004 fix): mirrors
 * skills/self/earning-health.py::is_fresh_but_barren's exact contract (pure, no I/O, takes a
 * pre-gathered ledger tail). Returns true iff the tail contains an `always_act_go_live` line followed
 * by at least `minRun` CONSECUTIVE `always_act_not_engaged` lines with no intervening go-live/engaged
 * line — the "silently regressed back to idle-permitted after go-live" doctrine-'malware' condition.
 * Any `always_act_not_engaged` run BEFORE the first go-live line is the benign "not yet enabled"
 * pre-rollout state and never triggers a regression.
 *
 * @param {object[]} ledgerTail - pre-gathered, chronologically-ordered ledger lines
 * @param {{minRun: number}} opts
 * @returns {boolean}
 */
export function isPostGoLiveRegression(ledgerTail, { minRun } = {}) {
  const tail = Array.isArray(ledgerTail) ? ledgerTail : [];
  const threshold = typeof minRun === 'number' ? minRun : 20;
  let sinceGoLive = false;
  let run = 0;
  for (const line of tail) {
    const kind = line && line.kind;
    if (kind === 'always_act_go_live') {
      sinceGoLive = true;
      run = 0;
      continue;
    }
    if (!sinceGoLive) continue; // benign pre-rollout state — no go-live line seen yet
    if (kind === 'always_act_not_engaged') {
      run += 1;
      if (run >= threshold) return true;
    } else {
      run = 0; // any other kind after go-live is a successfully-engaged wake — resets the run
    }
  }
  return false;
}
