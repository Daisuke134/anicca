// VCSDD spawn-funding-swap Phase 2a/2b (sprint-2). PROP-041..PROP-051 — lib/real-clients/base-signer.mjs,
// the SOLE value-moving Base transaction in this repo. Every transport boundary (fetchImpl,
// walletClientFactory, publicClientFactory) is mocked; NO real network call, real signing, or real
// subprocess is ever made from this file (NFR-6). PROP-050 (FIND-001 CRITICAL fix, impl review iter1)
// added below: verifyEvmTxAgainstIntent's decode-and-bound-check gates. PROP-051 (FIND-003): the
// probe-vs-real spender mismatch fails closed.
//
// FIND-001 iter2 fix (CRITICAL, impl review iteration 2): getNextNonce() now takes a required `amount`
// param and ensureApprovalsSettled() grants EXACTLY that amount, never a standing higher cap -- every
// test below that calls getNextNonce()/signAndBroadcast() and reaches the allowance-settling/allowance-
// check code paths now uses allowance fixture values consistent with "exactly `amount`", not an
// arbitrarily-large placeholder (which the new iter2 gate now correctly REFUSES as a standing-excess
// allowance -- see the new PROP-050/FIND-001-iter2 tests below).
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { encodeFunctionData, decodeFunctionData } from "viem";
import { createRealBaseSigner } from "../base-signer.mjs";

// ERC20_APPROVE_ABI (test-local mirror of base-signer.mjs's own internal ABI) -- used ONLY to decode a
// captured approve() call's `data` field so tests can assert the ACTUAL approved (spender, amount) args,
// not merely that some tx was sent.
const ERC20_APPROVE_ABI = [{ type: "function", name: "approve", stateMutability: "nonpayable", inputs: [{ name: "spender", type: "address" }, { name: "amount", type: "uint256" }], outputs: [{ name: "", type: "bool" }] }];
function decodeApprove(sentTx) {
  return decodeFunctionData({ abi: ERC20_APPROVE_ABI, data: sentTx.data }).args;
}

// Known-answer fixture key -- the SAME vector used to independently derive the expected Base address and
// noble-1/osmosis-1 Cosmos addresses via viem/@noble during this sprint's design phase (cross-checked,
// not invented). Test-only; never a real-funds-holding key.
const FIXTURE_PRIVATE_KEY = "0x" + "11".repeat(32);
const EXPECTED_ADDRESS = "0x19E7E376E7C213B7E7e7e46cc70A5dD086DAff2A";
const EXPECTED_NOBLE_ADDRESS = "noble1l3e9pgs3mmwuwrh95fecme0s0qtn2880pf8n3h";
const EXPECTED_OSMO_ADDRESS = "osmo1l3e9pgs3mmwuwrh95fecme0s0qtn2880p3ptlt";
const DESTINATION_AKASH_ADDRESS = "akash1ms7gr5sxkv33ra353hg5lu8dm7akljdaamj523";
const BASE_USDC_DENOM = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";

function makeFixtureHome() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "spawn-funding-swap-basesigner-test-"));
  const automatonDir = path.join(dir, ".automaton");
  fs.mkdirSync(automatonDir, { recursive: true });
  fs.writeFileSync(path.join(automatonDir, "wallet.json"), JSON.stringify({ privateKey: FIXTURE_PRIVATE_KEY }));
  return dir;
}

const LIVE_SHAPED_ROUTE = {
  dest_asset_denom: "uakt",
  dest_asset_chain_id: "akashnet-2",
  amount_out: "24513647",
  txs_required: 2,
  source_asset_denom: BASE_USDC_DENOM,
  source_asset_chain_id: "8453",
  amount_in: "15000000",
  operations: [{ tx_index: 0 }],
  chain_ids: ["8453", "noble-1", "osmosis-1", "akashnet-2"],
};

// ROUTER_CONTRACT_ADDRESS -- PROP-050's gate 2 (base-signer.mjs) requires evm_tx.to to EXACTLY equal
// evm_tx.required_erc20_approvals[0].spender (self-consistency allowlist), so every fixture below that
// intends a LEGITIMATE, signable evm_tx now uses the SAME address for both `to` and `spender`. Must be a
// well-formed 20-byte hex address (viem's encodeFunctionData validates this when currentAllowance()
// encodes it as an ERC-20 `allowance(owner,spender)` argument) -- ASCII "skiprouter" hex-encoded, never a
// real/live contract address (opaque test placeholder).
const ROUTER_CONTRACT_ADDRESS = "0x736b6970726f7574657230303030303030303030";

function evmTxFixture({
  requiresApproval = true,
  signerAddress = EXPECTED_ADDRESS,
  to = ROUTER_CONTRACT_ADDRESS,
  approvalSpender = ROUTER_CONTRACT_ADDRESS,
  approvalAmount = "15000000",
  approvalTokenContract = BASE_USDC_DENOM,
  value = "0",
  data = "0xd77d6ec0deadbeef",
} = {}) {
  return {
    txs: [
      {
        evm_tx: {
          chain_id: "8453",
          to,
          value,
          data,
          required_erc20_approvals: requiresApproval ? [{ token_contract: approvalTokenContract, spender: approvalSpender, amount: approvalAmount }] : [],
          signer_address: signerAddress,
        },
      },
    ],
  };
}

/**
 * makeFetchMock — routes on URL substring (fungible/route, fungible/msgs, else Base JSON-RPC) and, for
 * eth_getTransactionCount calls specifically, returns the NEXT value from `nonceSequence` each call (so
 * a test can distinguish "approve tx's nonce" from "the final nonce getNextNonce() returns").
 */
function makeFetchMock({ allowanceHex = "0x0", nonceSequence = ["0x7"], evmTxOptions = {} } = {}) {
  let nonceCallIndex = 0;
  const calls = [];
  const fn = async (url, init) => {
    calls.push({ url, body: init && init.body ? JSON.parse(init.body) : null });
    if (typeof url === "string" && url.includes("fungible/route")) {
      return { ok: true, json: async () => LIVE_SHAPED_ROUTE };
    }
    if (typeof url === "string" && url.includes("fungible/msgs")) {
      return { ok: true, json: async () => evmTxFixture(evmTxOptions) };
    }
    const body = JSON.parse(init.body);
    if (body.method === "eth_call") {
      return { ok: true, json: async () => ({ jsonrpc: "2.0", id: 1, result: allowanceHex }) };
    }
    if (body.method === "eth_getTransactionCount") {
      const value = nonceSequence[Math.min(nonceCallIndex, nonceSequence.length - 1)];
      nonceCallIndex += 1;
      return { ok: true, json: async () => ({ jsonrpc: "2.0", id: 1, result: value }) };
    }
    throw new Error(`unexpected RPC method in test mock: ${body.method}`);
  };
  fn.calls = calls;
  return fn;
}

function makeWalletClientFactory() {
  const sent = [];
  const factory = () => ({
    async sendTransaction(args) {
      sent.push(args);
      return `0xhash${sent.length}`;
    },
  });
  factory.sent = sent;
  return factory;
}

function makePublicClientFactory() {
  return () => ({ async waitForTransactionReceipt() { return { status: "success" }; } });
}

// FIND-007 fix (impl review iter1): every createRealBaseSigner() call below now injects an explicit
// fetchImpl that THROWS if ever called -- even though getAddress() never reaches the network in this
// implementation (so a bare, transport-less construction was previously "safe by accident"), PROP-049's
// tightened scan (test-money-safety-scan.test.mjs) now REQUIRES every createRealXxx() call in this
// directory to inject fetchImpl/execFileImpl, closing the gap where a FUTURE test adding a bare
// createRealXxx() call on a code path that DOES reach the network would go undetected.
const NEVER_CALLED_FETCH = async () => { throw new Error("must not be called"); };

test("PROP-041: getAddress throws when ANICCA_HOME is unset", async () => {
  const signer = createRealBaseSigner({ env: {}, fetchImpl: NEVER_CALLED_FETCH });
  await assert.rejects(() => signer.getAddress(), /ANICCA_HOME/);
});

test("PROP-041: getNextNonce throws when ANICCA_HOME is unset", async () => {
  const signer = createRealBaseSigner({ env: {}, fetchImpl: NEVER_CALLED_FETCH });
  await assert.rejects(() => signer.getNextNonce(15_000_000n), /ANICCA_HOME/);
});

test("PROP-042: getAddress returns the address viem's privateKeyToAccount derives from the SAME resolved fixture key", async () => {
  const home = makeFixtureHome();
  const signer = createRealBaseSigner({ env: { ANICCA_HOME: home }, fetchImpl: NEVER_CALLED_FETCH });
  assert.equal(await signer.getAddress(), EXPECTED_ADDRESS);
});

test("PROP-043 (iter2): getNextNonce(amount) sends the approve tx at a nonce STRICTLY LESS than the nonce it returns, approving EXACTLY `amount` (not a standing higher cap), when the mocked allowance is 0", async () => {
  const home = makeFixtureHome();
  const fetchImpl = makeFetchMock({ allowanceHex: "0x0", nonceSequence: ["0x7", "0x8"] });
  const walletClientFactory = makeWalletClientFactory();
  const signer = createRealBaseSigner({ env: { ANICCA_HOME: home }, fetchImpl, walletClientFactory, publicClientFactory: makePublicClientFactory() });

  const returnedNonce = await signer.getNextNonce(15_000_000n);

  assert.equal(returnedNonce, 8n);
  assert.equal(walletClientFactory.sent.length, 1, "exactly one approve tx must have been sent (allowance was 0, no reset needed)");
  assert.equal(walletClientFactory.sent[0].nonce, 7, "the approve tx's nonce must be strictly less than the returned nonce");
  assert.equal(walletClientFactory.sent[0].to, BASE_USDC_DENOM);
  const approveArgs = decodeApprove(walletClientFactory.sent[0]);
  assert.equal(approveArgs[1], 15_000_000n, "FIND-001 iter2 fix: the approved amount must be EXACTLY the driver-supplied `amount`, never a flat $100 standing cap");
});

test("PROP-044 (iter2): getNextNonce(amount) sends NO approve tx when the mocked on-chain allowance ALREADY EXACTLY equals `amount`", async () => {
  const home = makeFixtureHome();
  const fetchImpl = makeFetchMock({ allowanceHex: "0x" + (15_000_000n).toString(16), nonceSequence: ["0x9"] });
  const walletClientFactory = makeWalletClientFactory();
  const signer = createRealBaseSigner({ env: { ANICCA_HOME: home }, fetchImpl, walletClientFactory, publicClientFactory: makePublicClientFactory() });

  const returnedNonce = await signer.getNextNonce(15_000_000n);

  assert.equal(returnedNonce, 9n);
  assert.equal(walletClientFactory.sent.length, 0, "no approve tx should be sent when the on-chain allowance already exactly equals the desired amount");
});

test("PROP-044b (iter2): getNextNonce(amount) approve-race guard -- a prior NON-ZERO allowance that does NOT already equal `amount` (e.g. a residual $50 from an earlier swap) is RESET TO 0 first, then set to the new `amount`, as two sequential approve txs at two sequential nonces", async () => {
  const home = makeFixtureHome();
  const fetchImpl = makeFetchMock({ allowanceHex: "0x" + (50_000_000n).toString(16), nonceSequence: ["0x10", "0x11", "0x12"] });
  const walletClientFactory = makeWalletClientFactory();
  const signer = createRealBaseSigner({ env: { ANICCA_HOME: home }, fetchImpl, walletClientFactory, publicClientFactory: makePublicClientFactory() });

  const returnedNonce = await signer.getNextNonce(15_000_000n);

  assert.equal(returnedNonce, 18n); // 0x12
  assert.equal(walletClientFactory.sent.length, 2, "a non-zero, non-matching prior allowance must be reset-to-0 THEN set-to-desired -- two txs");
  assert.equal(walletClientFactory.sent[0].nonce, 16, "reset-to-0 tx uses the first free nonce"); // 0x10
  assert.deepEqual(decodeApprove(walletClientFactory.sent[0])[1], 0n, "first tx must reset the allowance to exactly 0");
  assert.equal(walletClientFactory.sent[1].nonce, 17, "set-to-desired tx uses the NEXT nonce, strictly after the reset tx"); // 0x11
  assert.equal(decodeApprove(walletClientFactory.sent[1])[1], 15_000_000n, "second tx must set the allowance to EXACTLY the new swap's amount");
});

test("PROP-045: signAndBroadcast throws BEFORE any network call when sourceAddress does not match this signer's own address", async () => {
  const home = makeFixtureHome();
  const fetchImpl = makeFetchMock();
  const signer = createRealBaseSigner({ env: { ANICCA_HOME: home }, fetchImpl });
  await assert.rejects(() => signer.signAndBroadcast({ amount: 15_000_000n, nonce: 8n, sourceAddress: "0xWRONGADDRESS000000000000000000000000001", destinationAkashAddress: DESTINATION_AKASH_ADDRESS }));
  assert.equal(fetchImpl.calls.length, 0, "must fail closed before any network call");
});

test("PROP-045: signAndBroadcast throws BEFORE any network call when destinationAkashAddress does not match the fixed colony destination", async () => {
  const home = makeFixtureHome();
  const fetchImpl = makeFetchMock();
  const signer = createRealBaseSigner({ env: { ANICCA_HOME: home }, fetchImpl });
  await assert.rejects(() => signer.signAndBroadcast({ amount: 15_000_000n, nonce: 8n, sourceAddress: EXPECTED_ADDRESS, destinationAkashAddress: "akash1wrongdestination0000000000000000" }));
  assert.equal(fetchImpl.calls.length, 0);
});

test("PROP-046: signAndBroadcast throws when the re-fetched route's destination fields are wrong", async () => {
  const home = makeFixtureHome();
  const fetchImpl = async (url) => {
    if (String(url).includes("fungible/route")) return { ok: true, json: async () => ({ ...LIVE_SHAPED_ROUTE, dest_asset_denom: "not-uakt" }) };
    throw new Error("must not reach msgs/RPC after a bad route");
  };
  const signer = createRealBaseSigner({ env: { ANICCA_HOME: home }, fetchImpl });
  await assert.rejects(() => signer.signAndBroadcast({ amount: 15_000_000n, nonce: 8n, sourceAddress: EXPECTED_ADDRESS, destinationAkashAddress: DESTINATION_AKASH_ADDRESS }));
});

test("PROP-046: signAndBroadcast throws when the msgs response contains zero evm_tx entries", async () => {
  const home = makeFixtureHome();
  const fetchImpl = async (url) => {
    if (String(url).includes("fungible/route")) return { ok: true, json: async () => LIVE_SHAPED_ROUTE };
    if (String(url).includes("fungible/msgs")) return { ok: true, json: async () => ({ txs: [] }) };
    throw new Error("must not reach RPC");
  };
  const signer = createRealBaseSigner({ env: { ANICCA_HOME: home }, fetchImpl });
  await assert.rejects(() => signer.signAndBroadcast({ amount: 15_000_000n, nonce: 8n, sourceAddress: EXPECTED_ADDRESS, destinationAkashAddress: DESTINATION_AKASH_ADDRESS }));
});

test("PROP-046: signAndBroadcast throws when evm_tx.signer_address does not match this signer's own address", async () => {
  const home = makeFixtureHome();
  const fetchImpl = async (url) => {
    if (String(url).includes("fungible/route")) return { ok: true, json: async () => LIVE_SHAPED_ROUTE };
    if (String(url).includes("fungible/msgs")) return { ok: true, json: async () => evmTxFixture({ signerAddress: "0xSOMEONEELSE00000000000000000000000001" }) };
    throw new Error("must not reach RPC");
  };
  const signer = createRealBaseSigner({ env: { ANICCA_HOME: home }, fetchImpl });
  await assert.rejects(() => signer.signAndBroadcast({ amount: 15_000_000n, nonce: 8n, sourceAddress: EXPECTED_ADDRESS, destinationAkashAddress: DESTINATION_AKASH_ADDRESS }));
});

test("PROP-047: signAndBroadcast throws (never signs) when the allowance check at sign time is still insufficient", async () => {
  const home = makeFixtureHome();
  const fetchImpl = makeFetchMock({ allowanceHex: "0x0", evmTxOptions: { requiresApproval: true } });
  const walletClientFactory = makeWalletClientFactory();
  const signer = createRealBaseSigner({ env: { ANICCA_HOME: home }, fetchImpl, walletClientFactory });
  await assert.rejects(() => signer.signAndBroadcast({ amount: 15_000_000n, nonce: 8n, sourceAddress: EXPECTED_ADDRESS, destinationAkashAddress: DESTINATION_AKASH_ADDRESS }));
  assert.equal(walletClientFactory.sent.length, 0, "must never attempt a second, nonce-colliding approve inline");
});

test("PROP-048: signAndBroadcast's broadcast call uses `nonce` EXACTLY as passed in, and returns the resulting txHash", async () => {
  const home = makeFixtureHome();
  // requiresApproval defaults true (evmTxFixture) -- PROP-050's gate 2 now requires exactly one
  // required_erc20_approvals entry whose spender equals evm_tx.to on every legitimate/signable fixture.
  const fetchImpl = makeFetchMock({ allowanceHex: "0x" + (15_000_000n).toString(16) /* FIND-001 iter2: EXACTLY `amount`, never a standing-excess allowance */ });
  const walletClientFactory = makeWalletClientFactory();
  const signer = createRealBaseSigner({ env: { ANICCA_HOME: home }, fetchImpl, walletClientFactory });

  const result = await signer.signAndBroadcast({ amount: 15_000_000n, nonce: 8n, sourceAddress: EXPECTED_ADDRESS, destinationAkashAddress: DESTINATION_AKASH_ADDRESS });

  assert.equal(walletClientFactory.sent.length, 1);
  assert.equal(walletClientFactory.sent[0].nonce, 8);
  assert.equal(walletClientFactory.sent[0].to, ROUTER_CONTRACT_ADDRESS);
  assert.equal(result.txHash, "0xhash1");
});

test("REQ-013/PROP-042 (integration sanity): the noble-1/osmosis-1 addresses this signer would submit to Skip's address_list are the SAME known-answer values REQ-013's own cosmos-address tests independently verify", async () => {
  const home = makeFixtureHome();
  const fetchImpl = makeFetchMock({ allowanceHex: "0x" + (15_000_000n).toString(16) /* FIND-001 iter2: EXACTLY `amount`, never a standing-excess allowance */ });
  const walletClientFactory = makeWalletClientFactory();
  const signer = createRealBaseSigner({ env: { ANICCA_HOME: home }, fetchImpl, walletClientFactory });
  await signer.signAndBroadcast({ amount: 15_000_000n, nonce: 8n, sourceAddress: EXPECTED_ADDRESS, destinationAkashAddress: DESTINATION_AKASH_ADDRESS });

  const msgsCall = fetchImpl.calls.find((c) => typeof c.url === "string" && c.url.includes("fungible/msgs"));
  assert.deepEqual(msgsCall.body.address_list, [EXPECTED_ADDRESS, EXPECTED_NOBLE_ADDRESS, EXPECTED_OSMO_ADDRESS, DESTINATION_AKASH_ADDRESS]);
});

// ==== PROP-050 (Tier-2, money-safety-critical, FIND-001 CRITICAL fix, impl review iter1) ====
// verifyEvmTxAgainstIntent's four independent gates: (a) honest evm_tx from a well-formed Skip response
// signs successfully, (b) a tampered/inflated approval amount is refused, (c) a tampered/arbitrary `to`
// (a drain address unrelated to the approved spender) is refused, (d) an amount exceeding the absolute
// MAX_SWAP_BASE_UNITS ceiling is refused -- even if it were otherwise self-consistent.

test("PROP-050(a): signAndBroadcast SIGNS an honest evm_tx whose to/approval-spender/approval-amount are all self-consistent and within the ceiling", async () => {
  const home = makeFixtureHome();
  const fetchImpl = makeFetchMock({ allowanceHex: "0x" + (15_000_000n).toString(16) /* FIND-001 iter2: EXACTLY `amount`, never a standing-excess allowance */ });
  const walletClientFactory = makeWalletClientFactory();
  const signer = createRealBaseSigner({ env: { ANICCA_HOME: home }, fetchImpl, walletClientFactory });

  const result = await signer.signAndBroadcast({ amount: 15_000_000n, nonce: 8n, sourceAddress: EXPECTED_ADDRESS, destinationAkashAddress: DESTINATION_AKASH_ADDRESS });

  assert.equal(walletClientFactory.sent.length, 1, "the honest tx must actually be broadcast");
  assert.equal(result.txHash, "0xhash1");
});

test("PROP-050(b): signAndBroadcast REFUSES (never broadcasts) a tampered evm_tx whose required_erc20_approvals[0].amount is inflated above the driver-supplied intended amount", async () => {
  const home = makeFixtureHome();
  const fetchImpl = makeFetchMock({
    allowanceHex: "0x" + (15_000_000n).toString(16) /* FIND-001 iter2: EXACTLY `amount`, never a standing-excess allowance */,
    evmTxOptions: { approvalAmount: "99000000" }, // Skip/attacker claims a $99 pull, driver only asked for $15
  });
  const walletClientFactory = makeWalletClientFactory();
  const signer = createRealBaseSigner({ env: { ANICCA_HOME: home }, fetchImpl, walletClientFactory });

  await assert.rejects(
    () => signer.signAndBroadcast({ amount: 15_000_000n, nonce: 8n, sourceAddress: EXPECTED_ADDRESS, destinationAkashAddress: DESTINATION_AKASH_ADDRESS }),
    /does not exactly equal the driver-supplied swap amount/
  );
  assert.equal(walletClientFactory.sent.length, 0, "an inflated-amount tx must NEVER be broadcast");
});

test("PROP-050(b): signAndBroadcast REFUSES a bare ERC-20 transfer() call (evm_tx.data encodes transfer(evilRecipient, fullBalance), no approval at all) -- the exact FIND-001 attack shape", async () => {
  const home = makeFixtureHome();
  const evilRecipient = "0x6576696c726563697069656e7430303030303030"; // ASCII "evilrecipient" hex-encoded, opaque test placeholder
  const bareTransferData = encodeFunctionData({ abi: [{ type: "function", name: "transfer", stateMutability: "nonpayable", inputs: [{ name: "to", type: "address" }, { name: "amount", type: "uint256" }], outputs: [{ name: "", type: "bool" }] }], functionName: "transfer", args: [evilRecipient, 999_000_000n] });
  const fetchImpl = makeFetchMock({
    allowanceHex: "0x" + (15_000_000n).toString(16) /* FIND-001 iter2: EXACTLY `amount`, never a standing-excess allowance */,
    evmTxOptions: { to: BASE_USDC_DENOM, data: bareTransferData, requiresApproval: false },
  });
  const walletClientFactory = makeWalletClientFactory();
  const signer = createRealBaseSigner({ env: { ANICCA_HOME: home }, fetchImpl, walletClientFactory });

  await assert.rejects(
    () => signer.signAndBroadcast({ amount: 15_000_000n, nonce: 8n, sourceAddress: EXPECTED_ADDRESS, destinationAkashAddress: DESTINATION_AKASH_ADDRESS }),
    /bare ERC-20 transfer\/transferFrom/
  );
  assert.equal(walletClientFactory.sent.length, 0, "a bare-transfer drain tx must NEVER be broadcast, regardless of amount/no-approval-needed");
});

test("PROP-050(c): signAndBroadcast REFUSES a tampered evm_tx whose `to` is an arbitrary drain address unrelated to the approved spender", async () => {
  const home = makeFixtureHome();
  const drainAddress = "0x647261696e616464726573733030303030303030"; // ASCII "drainaddress" hex-encoded, opaque test placeholder, != approval spender
  const fetchImpl = makeFetchMock({ allowanceHex: "0x" + (15_000_000n).toString(16) /* FIND-001 iter2: EXACTLY `amount`, never a standing-excess allowance */, evmTxOptions: { to: drainAddress } });
  const walletClientFactory = makeWalletClientFactory();
  const signer = createRealBaseSigner({ env: { ANICCA_HOME: home }, fetchImpl, walletClientFactory });

  await assert.rejects(
    () => signer.signAndBroadcast({ amount: 15_000_000n, nonce: 8n, sourceAddress: EXPECTED_ADDRESS, destinationAkashAddress: DESTINATION_AKASH_ADDRESS }),
    /does not equal its own required_erc20_approvals\[0\]\.spender/
  );
  assert.equal(walletClientFactory.sent.length, 0, "a to-mismatched tx must NEVER be broadcast");
});

test("PROP-050(c): signAndBroadcast REFUSES an evm_tx whose `to` is the USDC contract itself (even with a matching, self-consistent approval)", async () => {
  const home = makeFixtureHome();
  const fetchImpl = makeFetchMock({ allowanceHex: "0x" + (15_000_000n).toString(16) /* FIND-001 iter2: EXACTLY `amount`, never a standing-excess allowance */, evmTxOptions: { to: BASE_USDC_DENOM, approvalSpender: BASE_USDC_DENOM } });
  const walletClientFactory = makeWalletClientFactory();
  const signer = createRealBaseSigner({ env: { ANICCA_HOME: home }, fetchImpl, walletClientFactory });

  await assert.rejects(
    () => signer.signAndBroadcast({ amount: 15_000_000n, nonce: 8n, sourceAddress: EXPECTED_ADDRESS, destinationAkashAddress: DESTINATION_AKASH_ADDRESS }),
    /evm_tx\.to is the USDC contract itself/
  );
  assert.equal(walletClientFactory.sent.length, 0);
});

test("PROP-050(d): signAndBroadcast REFUSES an evm_tx/amount whose approval amount exceeds MAX_SWAP_BASE_UNITS, even when self-consistent and matching the (attacker-supplied) intended amount", async () => {
  const home = makeFixtureHome();
  const overCeilingAmount = 150_000_000n; // > MAX_SWAP_BASE_UNITS (iter2 fix: 20_000_000n, SWAP_MAX_USD=$20's base-unit equivalent -- previously a looser 100_000_000n/$100)
  const fetchImpl = makeFetchMock({
    allowanceHex: "0x" + (300_000_000n).toString(16),
    evmTxOptions: { approvalAmount: overCeilingAmount.toString() },
  });
  const walletClientFactory = makeWalletClientFactory();
  const signer = createRealBaseSigner({ env: { ANICCA_HOME: home }, fetchImpl, walletClientFactory });

  await assert.rejects(
    () => signer.signAndBroadcast({ amount: overCeilingAmount, nonce: 8n, sourceAddress: EXPECTED_ADDRESS, destinationAkashAddress: DESTINATION_AKASH_ADDRESS }),
    /exceeds the absolute per-swap ceiling MAX_SWAP_BASE_UNITS/
  );
  assert.equal(walletClientFactory.sent.length, 0, "an over-ceiling tx must NEVER be broadcast even if internally self-consistent");
});

test("PROP-050: signAndBroadcast REFUSES an evm_tx carrying a non-zero native `value` (this feature's route is USDC-only)", async () => {
  const home = makeFixtureHome();
  const fetchImpl = makeFetchMock({ allowanceHex: "0x" + (15_000_000n).toString(16) /* FIND-001 iter2: EXACTLY `amount`, never a standing-excess allowance */, evmTxOptions: { value: "1000000000000000" } });
  const walletClientFactory = makeWalletClientFactory();
  const signer = createRealBaseSigner({ env: { ANICCA_HOME: home }, fetchImpl, walletClientFactory });

  await assert.rejects(
    () => signer.signAndBroadcast({ amount: 15_000_000n, nonce: 8n, sourceAddress: EXPECTED_ADDRESS, destinationAkashAddress: DESTINATION_AKASH_ADDRESS }),
    /evm_tx\.value.*is non-zero/
  );
  assert.equal(walletClientFactory.sent.length, 0);
});

test("PROP-050: signAndBroadcast REFUSES an evm_tx with zero required_erc20_approvals entries (the exact no-approval-needed bypass shape)", async () => {
  const home = makeFixtureHome();
  const fetchImpl = makeFetchMock({ allowanceHex: "0x" + (15_000_000n).toString(16) /* FIND-001 iter2: EXACTLY `amount`, never a standing-excess allowance */, evmTxOptions: { requiresApproval: false, to: ROUTER_CONTRACT_ADDRESS } });
  const walletClientFactory = makeWalletClientFactory();
  const signer = createRealBaseSigner({ env: { ANICCA_HOME: home }, fetchImpl, walletClientFactory });

  await assert.rejects(
    () => signer.signAndBroadcast({ amount: 15_000_000n, nonce: 8n, sourceAddress: EXPECTED_ADDRESS, destinationAkashAddress: DESTINATION_AKASH_ADDRESS }),
    /expected exactly ONE required_erc20_approvals entry/
  );
  assert.equal(walletClientFactory.sent.length, 0);
});

// ==== FIND-001 iter2 CRITICAL fix (impl review iteration 2) ====
// The iteration-2 adversary finding: base-signer kept a STANDING allowance (previously topped up to a
// flat $100 APPROVAL_CAP_BASE_UNITS across every swap) and verifyEvmTxAgainstIntent's gate 3 only checked
// Skip's SELF-REPORTED `required_erc20_approvals[0].amount` metadata field -- never the ACTUAL on-chain
// allowance. A fully-malicious/compromised Skip route could therefore name the already-approved spender,
// report a small/honest metadata amount (passing gate 3), and embed calldata pulling the FULL standing
// allowance -- a 5x loss-amplification over SWAP_MAX_USD ($20). The tests below reproduce that EXACT
// attack shape and prove it is now refused, plus prove the honest/regression path still works.

test("FIND-001 (iter2 CRITICAL): signAndBroadcast REFUSES to broadcast when a STANDING on-chain allowance for evm_tx.to EXCEEDS the driver-supplied intended amount, even though Skip's reported metadata amount matches `amount` EXACTLY -- the exact iter2 attack: pre-existing $100 allowance + honest-looking metadata + attacker-controlled calldata", async () => {
  const home = makeFixtureHome();
  // Simulates a STANDING allowance left over from the pre-fix ($100 APPROVAL_CAP_BASE_UNITS) design, or
  // any other stale/higher grant -- evmTxFixture's default approvalAmount ("15000000") matches the
  // driver's intended `amount` EXACTLY, so gate 3 (metadata-amount check) passes; only the NEW iter2
  // on-chain-allowance gate can catch this.
  const standingAllowance = 100_000_000n; // $100 -- the exact pre-fix APPROVAL_CAP_BASE_UNITS value
  const fetchImpl = makeFetchMock({ allowanceHex: "0x" + standingAllowance.toString(16) });
  const walletClientFactory = makeWalletClientFactory();
  const signer = createRealBaseSigner({ env: { ANICCA_HOME: home }, fetchImpl, walletClientFactory });

  await assert.rejects(
    () => signer.signAndBroadcast({ amount: 15_000_000n, nonce: 8n, sourceAddress: EXPECTED_ADDRESS, destinationAkashAddress: DESTINATION_AKASH_ADDRESS }),
    /EXCEEDS the intended swap amount/
  );
  assert.equal(walletClientFactory.sent.length, 0, "worst-case loss under this exact iter2 attack shape must now be ZERO -- the standing-excess allowance itself is refused before any broadcast, never merely bounded to the standing $100");
});

test("FIND-001 (iter2 regression): signAndBroadcast SIGNS the honest path when the on-chain allowance is EXACTLY `amount` (proves the new gate does not merely reject everything)", async () => {
  const home = makeFixtureHome();
  const fetchImpl = makeFetchMock({ allowanceHex: "0x" + (15_000_000n).toString(16) });
  const walletClientFactory = makeWalletClientFactory();
  const signer = createRealBaseSigner({ env: { ANICCA_HOME: home }, fetchImpl, walletClientFactory });

  const result = await signer.signAndBroadcast({ amount: 15_000_000n, nonce: 8n, sourceAddress: EXPECTED_ADDRESS, destinationAkashAddress: DESTINATION_AKASH_ADDRESS });

  assert.equal(walletClientFactory.sent.length, 1, "an exactly-matching allowance must still broadcast the honest swap");
  assert.equal(result.txHash, "0xhash1");
});

// ==== FIND-004 fix (route reconciliation) ====

test("FIND-004: signAndBroadcast REFUSES when its own re-fetched route's amount_out diverges from the driver-supplied expectedAmountOutUakt", async () => {
  const home = makeFixtureHome();
  const fetchImpl = makeFetchMock({ allowanceHex: "0x" + (15_000_000n).toString(16) /* FIND-001 iter2: EXACTLY `amount`, never a standing-excess allowance */ });
  const signer = createRealBaseSigner({ env: { ANICCA_HOME: home }, fetchImpl });

  await assert.rejects(
    () => signer.signAndBroadcast({ amount: 15_000_000n, nonce: 8n, sourceAddress: EXPECTED_ADDRESS, destinationAkashAddress: DESTINATION_AKASH_ADDRESS, expectedAmountOutUakt: 999999999n, expectedTxsRequired: 2 }),
    /re-fetched Skip route's amount_out.*diverges/
  );
});

test("FIND-004: signAndBroadcast REFUSES when its own re-fetched route's txs_required diverges from the driver-supplied expectedTxsRequired", async () => {
  const home = makeFixtureHome();
  const fetchImpl = makeFetchMock({ allowanceHex: "0x" + (15_000_000n).toString(16) /* FIND-001 iter2: EXACTLY `amount`, never a standing-excess allowance */ });
  const signer = createRealBaseSigner({ env: { ANICCA_HOME: home }, fetchImpl });

  await assert.rejects(
    () => signer.signAndBroadcast({ amount: 15_000_000n, nonce: 8n, sourceAddress: EXPECTED_ADDRESS, destinationAkashAddress: DESTINATION_AKASH_ADDRESS, expectedAmountOutUakt: BigInt(LIVE_SHAPED_ROUTE.amount_out), expectedTxsRequired: 999 }),
    /re-fetched Skip route's txs_required.*diverges/
  );
});

test("FIND-004: signAndBroadcast SIGNS when its own re-fetched route matches the driver-supplied expectedAmountOutUakt/expectedTxsRequired exactly", async () => {
  const home = makeFixtureHome();
  const fetchImpl = makeFetchMock({ allowanceHex: "0x" + (15_000_000n).toString(16) /* FIND-001 iter2: EXACTLY `amount`, never a standing-excess allowance */ });
  const walletClientFactory = makeWalletClientFactory();
  const signer = createRealBaseSigner({ env: { ANICCA_HOME: home }, fetchImpl, walletClientFactory });

  const result = await signer.signAndBroadcast({ amount: 15_000_000n, nonce: 8n, sourceAddress: EXPECTED_ADDRESS, destinationAkashAddress: DESTINATION_AKASH_ADDRESS, expectedAmountOutUakt: BigInt(LIVE_SHAPED_ROUTE.amount_out), expectedTxsRequired: LIVE_SHAPED_ROUTE.txs_required });

  assert.equal(result.txHash, "0xhash1");
  assert.equal(walletClientFactory.sent.length, 1);
});

// ==== FIND-003 (documented probe-vs-real spender assumption) ====

test("PROP-051 (FIND-003): a probe-route spender that diverges from the real route's spender fails CLOSED (refuses to sign), never signs against a mismatched/under-approved spender", async () => {
  const home = makeFixtureHome();
  // getNextNonce() settles an allowance for PROBE_SPENDER (via the probe route), but the REAL route
  // signAndBroadcast fetches back requires REAL_SPENDER instead -- simulating Skip choosing a different
  // bridge/venue contract at the real (larger) amount than it chose for the 1-USDC probe.
  const PROBE_SPENDER = "0x70726f62657370656e6465723030303030303030"; // ASCII "probespender" hex-encoded
  const REAL_SPENDER = "0x7265616c7370656e646572303030303030303030"; // ASCII "realspender" hex-encoded
  let sawApprove = false;
  const fetchImpl = async (url, init) => {
    const urlStr = String(url);
    if (urlStr.includes("fungible/route")) return { ok: true, json: async () => LIVE_SHAPED_ROUTE };
    if (urlStr.includes("fungible/msgs")) {
      // getNextNonce()'s probe uses APPROVAL_PROBE_AMOUNT_BASE_UNITS (1 USDC) as amount_in; the real
      // signAndBroadcast call uses the full 15 USDC. Route the spender by that distinguishing field.
      const body = JSON.parse(init.body);
      const isProbe = body.amount_in === "1000000";
      return { ok: true, json: async () => evmTxFixture({ approvalSpender: isProbe ? PROBE_SPENDER : REAL_SPENDER, to: isProbe ? PROBE_SPENDER : REAL_SPENDER }) };
    }
    const body = JSON.parse(init.body);
    if (body.method === "eth_call") return { ok: true, json: async () => ({ jsonrpc: "2.0", id: 1, result: "0x0" }) }; // no prior allowance for either spender
    if (body.method === "eth_getTransactionCount") return { ok: true, json: async () => ({ jsonrpc: "2.0", id: 1, result: "0x1" }) };
    throw new Error(`unexpected RPC method: ${body.method}`);
  };
  const walletClientFactory = makeWalletClientFactory();
  const publicClientFactory = makePublicClientFactory();
  const signer = createRealBaseSigner({ env: { ANICCA_HOME: home }, fetchImpl, walletClientFactory, publicClientFactory });

  const nonce = await signer.getNextNonce(15_000_000n); // settles a $15-exact allowance for PROBE_SPENDER only (FIND-001 iter2: never a standing $100 cap)
  sawApprove = walletClientFactory.sent.length === 1 && walletClientFactory.sent[0].to === BASE_USDC_DENOM;
  assert.ok(sawApprove, "getNextNonce() must have approved the PROBE route's spender");
  assert.equal(decodeApprove(walletClientFactory.sent[0])[1], 15_000_000n, "the approved amount must be exactly the real swap amount, not a flat cap");

  // The REAL route's evm_tx.to is REAL_SPENDER, which was NEVER approved (only PROBE_SPENDER was) -- the
  // allowance-check loop must refuse (fail closed), never attempt a second, nonce-colliding approve.
  const preRealSendCount = walletClientFactory.sent.length;
  await assert.rejects(() => signer.signAndBroadcast({ amount: 15_000_000n, nonce, sourceAddress: EXPECTED_ADDRESS, destinationAkashAddress: DESTINATION_AKASH_ADDRESS }));
  assert.equal(walletClientFactory.sent.length, preRealSendCount, "no additional tx (approve or swap) may ever be sent once the spender mismatch is detected");
});
