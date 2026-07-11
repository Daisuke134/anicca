// VCSDD spawn-funding-swap Phase 2a (sprint-2, RED). PROP-041..PROP-048 — lib/real-clients/base-signer.mjs,
// the SOLE value-moving Base transaction in this repo. Every transport boundary (fetchImpl,
// walletClientFactory, publicClientFactory) is mocked; NO real network call, real signing, or real
// subprocess is ever made from this file (NFR-6). Written against a file that does NOT exist yet as of
// this commit -- every test below MUST fail (module-not-found) until Phase 2b.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createRealBaseSigner } from "../base-signer.mjs";

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

function evmTxFixture({ requiresApproval = true, signerAddress = EXPECTED_ADDRESS } = {}) {
  return {
    txs: [
      {
        evm_tx: {
          chain_id: "8453",
          to: "0xSKIPRELAYCONTRACT00000000000000000001",
          value: "0",
          data: "0xd77d6ec0deadbeef",
          required_erc20_approvals: requiresApproval ? [{ token_contract: BASE_USDC_DENOM, spender: "0x1111111111111111111111111111111111111111", amount: "15000000" }] : [],
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

test("PROP-041: getAddress throws when ANICCA_HOME is unset", async () => {
  const signer = createRealBaseSigner({ env: {} });
  await assert.rejects(() => signer.getAddress(), /ANICCA_HOME/);
});

test("PROP-041: getNextNonce throws when ANICCA_HOME is unset", async () => {
  const signer = createRealBaseSigner({ env: {}, fetchImpl: async () => { throw new Error("must not be called"); } });
  await assert.rejects(() => signer.getNextNonce(), /ANICCA_HOME/);
});

test("PROP-042: getAddress returns the address viem's privateKeyToAccount derives from the SAME resolved fixture key", async () => {
  const home = makeFixtureHome();
  const signer = createRealBaseSigner({ env: { ANICCA_HOME: home } });
  assert.equal(await signer.getAddress(), EXPECTED_ADDRESS);
});

test("PROP-043: getNextNonce sends the approve tx at a nonce STRICTLY LESS than the nonce it returns, when the mocked allowance is insufficient", async () => {
  const home = makeFixtureHome();
  const fetchImpl = makeFetchMock({ allowanceHex: "0x0", nonceSequence: ["0x7", "0x8"] });
  const walletClientFactory = makeWalletClientFactory();
  const signer = createRealBaseSigner({ env: { ANICCA_HOME: home }, fetchImpl, walletClientFactory, publicClientFactory: makePublicClientFactory() });

  const returnedNonce = await signer.getNextNonce();

  assert.equal(returnedNonce, 8n);
  assert.equal(walletClientFactory.sent.length, 1, "exactly one approve tx must have been sent");
  assert.equal(walletClientFactory.sent[0].nonce, 7, "the approve tx's nonce must be strictly less than the returned nonce");
  assert.equal(walletClientFactory.sent[0].to, BASE_USDC_DENOM);
});

test("PROP-044: getNextNonce sends NO approve tx when the mocked allowance is already sufficient", async () => {
  const home = makeFixtureHome();
  // APPROVAL_CAP_BASE_UNITS = 100_000_000n ($100) -- 0xf4240 * ... use a hex well above that.
  const fetchImpl = makeFetchMock({ allowanceHex: "0x" + (200_000_000n).toString(16), nonceSequence: ["0x9"] });
  const walletClientFactory = makeWalletClientFactory();
  const signer = createRealBaseSigner({ env: { ANICCA_HOME: home }, fetchImpl, walletClientFactory, publicClientFactory: makePublicClientFactory() });

  const returnedNonce = await signer.getNextNonce();

  assert.equal(returnedNonce, 9n);
  assert.equal(walletClientFactory.sent.length, 0, "no approve tx should be sent when allowance is already sufficient");
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
  const fetchImpl = makeFetchMock({ allowanceHex: "0x" + (200_000_000n).toString(16), evmTxOptions: { requiresApproval: false } });
  const walletClientFactory = makeWalletClientFactory();
  const signer = createRealBaseSigner({ env: { ANICCA_HOME: home }, fetchImpl, walletClientFactory });

  const result = await signer.signAndBroadcast({ amount: 15_000_000n, nonce: 8n, sourceAddress: EXPECTED_ADDRESS, destinationAkashAddress: DESTINATION_AKASH_ADDRESS });

  assert.equal(walletClientFactory.sent.length, 1);
  assert.equal(walletClientFactory.sent[0].nonce, 8);
  assert.equal(walletClientFactory.sent[0].to, "0xSKIPRELAYCONTRACT00000000000000000001");
  assert.equal(result.txHash, "0xhash1");
});

test("REQ-013/PROP-042 (integration sanity): the noble-1/osmosis-1 addresses this signer would submit to Skip's address_list are the SAME known-answer values REQ-013's own cosmos-address tests independently verify", async () => {
  const home = makeFixtureHome();
  let capturedMsgsBody = null;
  const fetchImpl = async (url, init) => {
    if (String(url).includes("fungible/route")) return { ok: true, json: async () => LIVE_SHAPED_ROUTE };
    if (String(url).includes("fungible/msgs")) {
      capturedMsgsBody = JSON.parse(init.body);
      return { ok: true, json: async () => evmTxFixture({ requiresApproval: false }) };
    }
    throw new Error("must not reach RPC");
  };
  const walletClientFactory = makeWalletClientFactory();
  const signer = createRealBaseSigner({ env: { ANICCA_HOME: home }, fetchImpl, walletClientFactory });
  await signer.signAndBroadcast({ amount: 15_000_000n, nonce: 8n, sourceAddress: EXPECTED_ADDRESS, destinationAkashAddress: DESTINATION_AKASH_ADDRESS });

  assert.deepEqual(capturedMsgsBody.address_list, [EXPECTED_ADDRESS, EXPECTED_NOBLE_ADDRESS, EXPECTED_OSMO_ADDRESS, DESTINATION_AKASH_ADDRESS]);
});
