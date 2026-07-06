// is-self-funded.mjs — the P0 join gate for the Anicca agent economy
// (.vcsdd/features/anicca-agent-economy/specs/SPEC.md §1.2 point 2 / §3 P0).
//
// Anicca = a marketplace of SELF-FUNDED agents (own crypto wallet, human-zero). An agent is a
// CITIZEN only if ALL THREE hold:
//   (a) own wallet     — it holds its own EVM and/or Solana signing key (see resolve-identity.mjs
//                        for how a real instance resolves that key; this module takes the
//                        already-resolved presence as booleans, never the raw key material).
//   (b) own-funded fuel — its inference/compute is paid FROM ITS OWN WALLET: ClawRouter
//                        own-wallet balance, x402 (self-facilitated), or a genuinely free model.
//                        Anthropic-subscription billing and any human-card-billed provider are
//                        FUEL, but not OWN fuel — they fail this leg.
//   (c) human-zero      — no step in its earn or fuel path depends on a human OAuth grant, a
//                        KYC'd account, or any other human-owned credential.
//
// claude-p (this Claude Code session; fuel = Dais's Anthropic subscription) fails (b) by
// design: it is environment-building/oversight, not a citizen of the economy it builds.
//
// Fail-closed (money-safety, matches resolve-identity.mjs's R5 discipline): any missing/
// malformed/unrecognized field DENIES the gate. This module never throws.

// Fuel providers that pay for their OWN inference/compute out of the agent's OWN wallet.
// Unlisted / unrecognized providers are NOT own-funded — deny, don't guess (fail-closed).
export const OWN_FUNDED_FUEL_PROVIDERS = new Set([
  "clawrouter-own-wallet", // e.g. automaton (anicca-a3cdd4, Base) — ClawRouter billed to its own wallet
  "x402", // e.g. Franklin — self-facilitated x402 settlement from its own wallet
  "free-model", // genuinely free inference (no billing party at all)
]);

function hasOwnWallet(agent) {
  const wallet = agent && agent.wallet;
  if (!wallet || typeof wallet !== "object") return false;
  return Boolean(wallet.evm) || Boolean(wallet.solana);
}

function fuelProvider(agent) {
  const provider = agent && agent.fuel && agent.fuel.provider;
  return typeof provider === "string" && provider.length > 0 ? provider : null;
}

function fuelIsOwnFunded(agent) {
  const provider = fuelProvider(agent);
  return provider !== null && OWN_FUNDED_FUEL_PROVIDERS.has(provider);
}

// Returns the declared human-dependency array, or null if the field is missing/malformed
// (not an array at all). Mirrors hasOwnWallet/fuelProvider: missing and malformed both
// collapse to the same "can't confirm zero dependencies" signal, which hasNoHumanDependency
// then denies — a non-array humanDependencies (string/number/object/null) must NOT be
// silently coerced to [] (that coercion was FIND-P0-1: a typo'd humanDependencies wrongly
// read as "none declared" and passed the gate).
function declaredHumanDependencies(agent) {
  const deps = agent && agent.humanDependencies;
  return Array.isArray(deps) ? deps : null;
}

function hasNoHumanDependency(agent) {
  const deps = declaredHumanDependencies(agent);
  return deps !== null && deps.length === 0;
}

/**
 * The join/spawn gate. Pure, fail-closed, never throws.
 *
 * @param {{wallet?: {evm?: boolean, solana?: boolean}, fuel?: {provider?: string}, humanDependencies?: string[]}} agent
 * @returns {boolean} true only if (a) own wallet AND (b) own-funded fuel AND (c) zero human deps.
 */
export function isSelfFunded(agent) {
  if (!agent || typeof agent !== "object") return false;
  return hasOwnWallet(agent) && fuelIsOwnFunded(agent) && hasNoHumanDependency(agent);
}

/**
 * Explains WHY an agent failed the gate (for logs/audit trails). Empty array = gate passed.
 * Never throws; safe to call on the same malformed input isSelfFunded() would deny.
 *
 * @param {*} agent
 * @returns {string[]}
 */
export function selfFundedReasons(agent) {
  if (!agent || typeof agent !== "object") return ["no-agent"];
  const reasons = [];
  if (!hasOwnWallet(agent)) reasons.push("no-own-wallet");
  if (!fuelIsOwnFunded(agent)) reasons.push(`fuel-not-own-funded:${fuelProvider(agent) ?? "missing"}`);
  if (!hasNoHumanDependency(agent)) {
    const deps = declaredHumanDependencies(agent);
    const detail = deps === null ? `not-an-array:${typeof (agent && agent.humanDependencies)}` : deps.join(",");
    reasons.push(`human-dependency:${detail}`);
  }
  return reasons;
}
