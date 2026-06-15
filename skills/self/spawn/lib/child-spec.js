// Pure child-spec derivation (no I/O).
// nextChildId: monotonic, gap-safe (max existing + 1), zero-padded to width 3.
// buildChildSpec: assembles the colony row; refuses if the child wallet is not distinct.

function nextChildId(children = [], prefix = "anicca-c", width = 3) {
  let max = 0;
  for (const c of children) {
    const id = c && c.child_id;
    if (typeof id !== "string" || !id.startsWith(prefix)) continue;
    const n = parseInt(id.slice(prefix.length), 10);
    if (Number.isInteger(n) && n > max) max = n;
  }
  return prefix + String(max + 1).padStart(width, "0");
}

function buildChildSpec({
  childId,
  parentWallet,
  childWallet,
  childInbox,
  generation,
  seedUsdc,
  constitutionHash,
} = {}) {
  const required = { childId, parentWallet, childWallet, childInbox, generation, seedUsdc, constitutionHash };
  for (const [k, v] of Object.entries(required)) {
    if (v === undefined || v === null || v === "") {
      throw new Error(`buildChildSpec: missing required field "${k}"`);
    }
  }
  // Lineage must be sovereign: a child wallet equal to the parent's is a bug (compare case-insensitive).
  if (String(childWallet).toLowerCase() === String(parentWallet).toLowerCase()) {
    throw new Error("buildChildSpec: child wallet must be distinct from parent wallet");
  }
  return {
    child_id: childId,
    wallet: childWallet,
    parent_wallet: parentWallet,
    inbox: childInbox,
    generation,
    seed_usdc: seedUsdc,
    constitution_hash: constitutionHash,
    identity: `Daughter of Anicca ${constitutionHash}`,
    status: "provisioning",
  };
}

module.exports = { nextChildId, buildChildSpec };
