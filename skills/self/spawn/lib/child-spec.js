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
  agentEvmAddress,
  agentId,
} = {}) {
  const required = { childId, parentWallet, childWallet, generation, seedUsdc, constitutionHash };
  for (const [k, v] of Object.entries(required)) {
    if (v === undefined || v === null || v === "") {
      throw new Error(`buildChildSpec: missing required field "${k}"`);
    }
  }
  // REQ-206: identity anchor is "at least one," never an XOR — the old AgentMail inbox and the new
  // ERC-8004 (agentEvmAddress+agentId) pair may both be present.
  const hasInbox = childInbox !== undefined && childInbox !== null && childInbox !== "";
  const hasErc8004 =
    agentEvmAddress !== undefined &&
    agentEvmAddress !== null &&
    agentEvmAddress !== "" &&
    agentId !== undefined &&
    agentId !== null &&
    agentId !== "";
  if (!hasInbox && !hasErc8004) {
    throw new Error(
      "buildChildSpec: missing identity anchor — supply childInbox or both agentEvmAddress and agentId"
    );
  }
  // Lineage must be sovereign: a child wallet equal to the parent's is a bug (compare case-insensitive).
  if (String(childWallet).toLowerCase() === String(parentWallet).toLowerCase()) {
    throw new Error("buildChildSpec: child wallet must be distinct from parent wallet");
  }
  const spec = {
    child_id: childId,
    wallet: childWallet,
    parent_wallet: parentWallet,
    generation,
    seed_usdc: seedUsdc,
    constitution_hash: constitutionHash,
    identity: `Daughter of Anicca ${constitutionHash}`,
    status: "provisioning",
  };
  if (hasInbox) spec.inbox = childInbox;
  if (hasErc8004) {
    spec.agent_evm_address = agentEvmAddress;
    spec.agent_id = agentId;
  }
  return spec;
}

module.exports = { nextChildId, buildChildSpec };
