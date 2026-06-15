// Durable state-dir resolver (spec27 §2 WF-A self-spawn gap-fix #3). FAIL-CLOSED: the colony ledger
// (children.jsonl) and the parent wallet (wallet.json) MUST persist across reboots / tmp-cleans, or a
// spawned child silently vanishes from the colony. So a /tmp (or /private/tmp on macOS) state dir is a
// hard error, not a silent fallback — we'd rather refuse than lose lineage.
const path = require("node:path");

function isTmp(p) {
  const s = String(p || "");
  return /(^|\/)tmp(\/|$)/.test(s) || /\/private\/tmp(\/|$)/.test(s) || /^\/var\/tmp(\/|$)/.test(s);
}

// Throws if `p` resolves under any tmp-cleaned location.
function assertDurable(p) {
  if (isTmp(p)) {
    throw new Error(`state-path: refusing tmp (non-durable) location '${p}' — children.jsonl/wallet.json would be lost`);
  }
  return p;
}

// Resolve the durable state directory.
//   1. ANICCA_STATE_DIR if set (validated durable; tmp => throw)
//   2. else $HOME/.hermes/state (host default)
function resolveStateDir({ env = process.env } = {}) {
  const explicit = env.ANICCA_STATE_DIR;
  if (explicit) return assertDurable(explicit);
  const home = env.HOME || ".";
  return assertDurable(path.join(home, ".hermes", "state"));
}

module.exports = { resolveStateDir, assertDurable, isTmp };
