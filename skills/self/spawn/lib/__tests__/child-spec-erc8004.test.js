// VCSDD anicca-agent-spawn, Phase 2a (RED). REQ-206 — buildChildSpec's identity-anchor validation,
// backward-compatible extension: accept EITHER childInbox OR {agentEvmAddress, agentId}, "at least
// one" (never an XOR). This EXTENDS the existing, unmodified `../child-spec` — buildChildSpec today
// unconditionally throws on a missing childInbox, so the new-feature cases below (PROP-206b/c/e) are
// expected to fail against TODAY's implementation. PROP-206a below is a regression/coverage-retrofit
// case (already passes today) — see sprint-1 report for which cases are new-failing vs retrofit.
const { test } = require("node:test");
const assert = require("node:assert/strict");
const { buildChildSpec } = require("../child-spec");

const REQUIRED_NON_ANCHOR_FIELDS = {
  parentWallet: "0xPARENT0000000000000000000000000000000A",
  childWallet: "0xCHILD00000000000000000000000000000000B",
  generation: 1,
  seedUsdc: 1,
  constitutionHash: "deadbeef",
};

test("PROP-206a (coverage-retrofit, expected to already pass): existing childInbox-only fixture is unaffected", () => {
  const spec = buildChildSpec({
    childId: "anicca-c001",
    ...REQUIRED_NON_ANCHOR_FIELDS,
    childInbox: "anicca-c001@agentmail.to",
  });
  assert.equal(spec.inbox, "anicca-c001@agentmail.to");
  assert.equal(spec.status, "provisioning");
});

test("PROP-206b (new-feature, expected to fail today): agentEvmAddress+agentId without childInbox succeeds and returns agent_evm_address/agent_id", () => {
  const spec = buildChildSpec({
    childId: "anicca-c001",
    ...REQUIRED_NON_ANCHOR_FIELDS,
    agentEvmAddress: "0xCHILD00000000000000000000000000000000B",
    agentId: 42,
  });
  assert.equal(spec.agent_evm_address, "0xCHILD00000000000000000000000000000000B");
  assert.equal(spec.agent_id, 42);
});

test("PROP-206c (new-feature, expected to fail today): neither anchor present throws 'missing identity anchor'", () => {
  assert.throws(() => buildChildSpec({ childId: "anicca-c001", ...REQUIRED_NON_ANCHOR_FIELDS }), /missing identity anchor/i);
});

test("PROP-206c (new-feature, expected to fail today): only HALF the ERC-8004 pair (agentEvmAddress without agentId) throws 'missing identity anchor'", () => {
  assert.throws(
    () =>
      buildChildSpec({
        childId: "anicca-c001",
        ...REQUIRED_NON_ANCHOR_FIELDS,
        agentEvmAddress: "0xCHILD00000000000000000000000000000000B",
      }),
    /missing identity anchor/i
  );
});

test("PROP-206e (new-feature, expected to fail today): BOTH childInbox AND the ERC-8004 pair present succeeds — 'at least one', never an XOR", () => {
  const spec = buildChildSpec({
    childId: "anicca-c001",
    ...REQUIRED_NON_ANCHOR_FIELDS,
    childInbox: "anicca-c001@agentmail.to",
    agentEvmAddress: "0xCHILD00000000000000000000000000000000B",
    agentId: 42,
  });
  assert.equal(spec.inbox, "anicca-c001@agentmail.to");
  assert.equal(spec.agent_evm_address, "0xCHILD00000000000000000000000000000000B");
  assert.equal(spec.agent_id, 42);
});

test("PROP-206f (new-feature, expected to fail today): a real, full seven-field call (REQ-206 derivation rules) succeeds with every field present", () => {
  const spec = buildChildSpec({
    childId: "anicca-c001",
    parentWallet: "0xCOORDINATOR000000000000000000000000000C",
    childWallet: "0xCHILD00000000000000000000000000000000B",
    generation: 1,
    seedUsdc: 2.5,
    constitutionHash: "realsha256hexdigest",
    agentEvmAddress: "0xCHILD00000000000000000000000000000000B",
    agentId: 7,
  });
  assert.equal(spec.parent_wallet, "0xCOORDINATOR000000000000000000000000000C");
  assert.equal(spec.generation, 1);
  assert.equal(spec.seed_usdc, 2.5);
  assert.equal(spec.constitution_hash, "realsha256hexdigest");
  assert.equal(spec.agent_evm_address, "0xCHILD00000000000000000000000000000000B");
  assert.equal(spec.agent_id, 7);
});

test("PROP-206d structural (expected to fail until implemented): nextChildId and the distinct-wallet assertion remain byte-identical — child wallet === parent wallet still throws", () => {
  assert.throws(
    () =>
      buildChildSpec({
        childId: "anicca-c001",
        parentWallet: "0xSAME",
        childWallet: "0xsame",
        generation: 1,
        seedUsdc: 1,
        constitutionHash: "h",
        agentEvmAddress: "0xsame",
        agentId: 1,
      }),
    /distinct/i
  );
});
