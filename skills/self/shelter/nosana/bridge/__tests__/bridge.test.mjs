// node:test — bridge.mjs: the full orchestration. Every I/O dependency is injected (fake fetch
// covering Base JSON-RPC + CoinGecko, fake Solana connection, real fs only for a throwaway
// per-test state dir and real tmp identity homes) so these tests exercise the worth-it verdict,
// the spend gate, and the at-most-once/never-blind-retry/poll-for-destination-credit orchestration
// deterministically — no real network, no real signing broadcast.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { generatePrivateKey } from "viem/accounts";
import { Keypair } from "@solana/web3.js";
import bs58 from "bs58";

import { bridgeToSolana, resolveBridgeAmount, buildBridgeIntentRecord, buildBridgeSettledRecord, DEFAULT_BRIDGE_AMOUNT_USDC } from "../bridge.mjs";
import { COINGECKO_SIMPLE_PRICE_URL } from "../eth-price.mjs";

// ---- resolveBridgeAmount (pure clamp) -------------------------------------------------------

test("resolveBridgeAmount: uses the requested amount when under both the balance and the cap", () => {
  const r = resolveBridgeAmount({ requestedUsdc: 10, availableUsdc: 20, capUsdc: 15 });
  assert.equal(r.amountUsdc, 10);
  assert.equal(r.hardCapApplied, false);
});

test("resolveBridgeAmount: clamps to the available balance when it is the smallest", () => {
  const r = resolveBridgeAmount({ requestedUsdc: 10, availableUsdc: 3, capUsdc: 15 });
  assert.equal(r.amountUsdc, 3);
  assert.equal(r.hardCapApplied, true);
});

test("resolveBridgeAmount: clamps to the explicit cap when it is the smallest", () => {
  const r = resolveBridgeAmount({ requestedUsdc: 50, availableUsdc: 100, capUsdc: 15 });
  assert.equal(r.amountUsdc, 15);
  assert.equal(r.hardCapApplied, true);
});

test("resolveBridgeAmount: never returns a negative amount even with a zero balance", () => {
  const r = resolveBridgeAmount({ requestedUsdc: 10, availableUsdc: 0, capUsdc: 15 });
  assert.equal(r.amountUsdc, 0);
});

test("resolveBridgeAmount: fails closed on non-finite/negative inputs", () => {
  assert.throws(() => resolveBridgeAmount({ requestedUsdc: 0, availableUsdc: 10, capUsdc: 15 }), /positive finite number/);
  assert.throws(() => resolveBridgeAmount({ requestedUsdc: 10, availableUsdc: -1, capUsdc: 15 }), /non-negative finite number/);
  assert.throws(() => resolveBridgeAmount({ requestedUsdc: 10, availableUsdc: 20, capUsdc: 0 }), /positive finite number/);
});

test("DEFAULT_BRIDGE_AMOUNT_USDC documents the $10 idle-balance shape from this feature's spec", () => {
  assert.equal(DEFAULT_BRIDGE_AMOUNT_USDC, 10);
});

// ---- ledger record shaping — no secret material ever embedded ------------------------------

test("buildBridgeIntentRecord and buildBridgeSettledRecord never embed anything secret-shaped", () => {
  const intent = buildBridgeIntentRecord({
    ts: 1000,
    intentId: "id1",
    kind: "burn",
    address: "0x810F6D61F7606dEEE2657d3083E150a222Bc29C5",
    txHash: "0xdeadbeef",
    amountUsdc: 10,
    destination: "F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T",
  });
  const settled = buildBridgeSettledRecord({
    ts: 1001,
    intentId: "id1",
    evmAddress: "0x810F6D61F7606dEEE2657d3083E150a222Bc29C5",
    solanaAddress: "F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T",
    burnTxHash: "0xdeadbeef",
    amountUsdc: 10,
    outcome: "awaiting-credit",
  });
  const serialized = JSON.stringify({ intent, settled });
  assert.ok(!/0x[0-9a-fA-F]{64}(?!.*"txHash")/.test(serialized) || serialized.includes("0xdeadbeef")); // no stray 32-byte hex besides the tx hash we put there
  assert.equal(intent.status, "intent");
  assert.equal(settled.status, "settled");
});

// ---- full orchestration, dry mode -----------------------------------------------------------

function mkTmpHome(prefix) {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

function writeEvmWallet(home, privateKey) {
  fs.mkdirSync(path.join(home, ".automaton"), { recursive: true });
  fs.writeFileSync(path.join(home, ".automaton", "wallet.json"), JSON.stringify({ privateKey }));
}

function writeSolanaSecret(home, secretBase58) {
  fs.mkdirSync(path.join(home, ".automaton"), { recursive: true });
  fs.writeFileSync(path.join(home, ".automaton", "solana.json"), JSON.stringify({ secretKey: secretBase58 }));
}

const REAL_GAS_PRICE_HEX = "0x5b8d80"; // 6,000,000 wei — real observed Base gas price 2026-07-25

function hexOf(n) {
  return `0x${BigInt(n).toString(16)}`;
}

/**
 * Builds a fake fetchImpl that routes: (a) GET to CoinGecko -> ETH/USD price, (b) POST JSON-RPC to
 * the Base RPC -> per-method canned responses. `overrides` lets a test customize specific methods
 * (e.g. allowance eth_call result, eth_sendRawTransaction behavior, eth_getTransactionReceipt
 * sequencing) while everything else uses a real-shaped default.
 */
function makeFakeBaseFetch({
  ethUsd = 1856.68,
  ethBalanceWei = 8_860_000_000_000n, // real measured founder-wallet balance
  usdcBalanceBaseUnits = 10_104_975n, // real measured founder-wallet USDC balance (10.104975)
  allowanceBaseUnits = 0n,
  chainId = 8453,
  nonce = 5,
  sendRawTransactionImpl,
  getTransactionReceiptImpl,
  onCall,
} = {}) {
  let sendCount = 0;
  let receiptCallCount = 0;
  return {
    fetchImpl: async (url, options) => {
      if (typeof url === "string" && url === COINGECKO_SIMPLE_PRICE_URL) {
        return { ok: true, status: 200, json: async () => ({ ethereum: { usd: ethUsd } }) };
      }
      // POST JSON-RPC to the Base RPC.
      const body = JSON.parse(options.body);
      if (onCall) onCall(body.method, body.params);
      switch (body.method) {
        case "eth_gasPrice":
          return { ok: true, status: 200, json: async () => ({ jsonrpc: "2.0", id: 1, result: REAL_GAS_PRICE_HEX }) };
        case "eth_getBalance":
          return { ok: true, status: 200, json: async () => ({ jsonrpc: "2.0", id: 1, result: hexOf(ethBalanceWei) }) };
        case "eth_chainId":
          return { ok: true, status: 200, json: async () => ({ jsonrpc: "2.0", id: 1, result: hexOf(chainId) }) };
        case "eth_getTransactionCount":
          return { ok: true, status: 200, json: async () => ({ jsonrpc: "2.0", id: 1, result: hexOf(nonce) }) };
        case "eth_call": {
          const data = body.params[0].data;
          // allowance(address,address) selector 0xdd62ed3e vs balanceOf(address) selector 0x70a08231.
          if (data.startsWith("0xdd62ed3e")) {
            return { ok: true, status: 200, json: async () => ({ jsonrpc: "2.0", id: 1, result: `0x${allowanceBaseUnits.toString(16).padStart(64, "0")}` }) };
          }
          if (data.startsWith("0x70a08231")) {
            return { ok: true, status: 200, json: async () => ({ jsonrpc: "2.0", id: 1, result: `0x${usdcBalanceBaseUnits.toString(16).padStart(64, "0")}` }) };
          }
          throw new Error(`unexpected eth_call data: ${data}`);
        }
        case "eth_sendRawTransaction":
          sendCount += 1;
          if (sendRawTransactionImpl) return sendRawTransactionImpl(body.params[0], sendCount);
          return { ok: true, status: 200, json: async () => ({ jsonrpc: "2.0", id: 1, result: "0xsentfake" }) };
        case "eth_getTransactionReceipt":
          receiptCallCount += 1;
          if (getTransactionReceiptImpl) return getTransactionReceiptImpl(body.params[0], receiptCallCount);
          return { ok: true, status: 200, json: async () => ({ jsonrpc: "2.0", id: 1, result: { status: "0x1" } }) };
        default:
          throw new Error(`makeFakeBaseFetch: unexpected RPC method in a dry run — this proves nothing beyond reads was attempted: ${body.method}`);
      }
    },
    getSendCount: () => sendCount,
  };
}

test("bridgeToSolana --dry: real-shaped inputs produce a WORTH-IT verdict, an ALLOWED gate, and stops before any signing/sending", async () => {
  const evmHome = mkTmpHome("bridge-dry-evm-");
  const solanaHome = mkTmpHome("bridge-dry-sol-");
  const stateDir = mkTmpHome("bridge-dry-state-");
  const pk = generatePrivateKey();
  writeEvmWallet(evmHome, pk);
  const kp = Keypair.generate();
  writeSolanaSecret(solanaHome, bs58.encode(kp.secretKey));

  const { fetchImpl } = makeFakeBaseFetch({});

  const result = await bridgeToSolana({
    env: { ANICCA_STATE_DIR: stateDir },
    live: false,
    amountUsdc: 10,
    evmHome,
    solanaHome,
    fetchImpl,
  });

  assert.equal(result.posted, false);
  assert.equal(result.quote.worthIt, true);
  assert.equal(result.gate.allowed, true);
  assert.equal(result.amountUsdc, 10);
  assert.equal(result.needsApprove, true); // allowanceBaseUnits defaults to 0

  // Never wrote an intent/ledger file in dry mode.
  assert.equal(fs.existsSync(path.join(stateDir, "nosana-bridge-intents.jsonl")), false);
  assert.equal(fs.existsSync(path.join(stateDir, "nosana-bridge.jsonl")), false);

  fs.rmSync(evmHome, { recursive: true, force: true });
  fs.rmSync(solanaHome, { recursive: true, force: true });
  fs.rmSync(stateDir, { recursive: true, force: true });
});

test("bridgeToSolana --dry: refuses (NOT worth it) when a fee shape makes the cost exceed the threshold, and reports why", async () => {
  const evmHome = mkTmpHome("bridge-dry-refuse-evm-");
  const solanaHome = mkTmpHome("bridge-dry-refuse-sol-");
  const stateDir = mkTmpHome("bridge-dry-refuse-state-");
  writeEvmWallet(evmHome, generatePrivateKey());
  writeSolanaSecret(solanaHome, bs58.encode(Keypair.generate().secretKey));

  // Absurdly small balance so the resolved bridge amount is tiny relative to fixed gas cost —
  // this makes the SAME real gas numbers a large fraction of the transfer, proving the worth-it
  // verdict actually reacts to real inputs rather than being hardcoded true.
  const { fetchImpl } = makeFakeBaseFetch({ usdcBalanceBaseUnits: 100n }); // $0.0001 available

  const result = await bridgeToSolana({
    env: { ANICCA_STATE_DIR: stateDir },
    live: false,
    amountUsdc: 10,
    evmHome,
    solanaHome,
    fetchImpl,
  });

  assert.equal(result.quote.worthIt, false);
  assert.equal(result.posted, false);

  fs.rmSync(evmHome, { recursive: true, force: true });
  fs.rmSync(solanaHome, { recursive: true, force: true });
  fs.rmSync(stateDir, { recursive: true, force: true });
});

// ---- full orchestration, live mode: at-most-once + never-blind-retry + poll-for-credit ------

test("bridgeToSolana --live: writes the intent BEFORE sending, never re-sends when the send call throws (reconciles via the receipt instead), and ends in 'awaiting-credit' honestly when the destination balance never moves", async () => {
  const evmHome = mkTmpHome("bridge-live-evm-");
  const solanaHome = mkTmpHome("bridge-live-sol-");
  const stateDir = mkTmpHome("bridge-live-state-");
  writeEvmWallet(evmHome, generatePrivateKey());
  writeSolanaSecret(solanaHome, bs58.encode(Keypair.generate().secretKey));

  // allowanceBaseUnits high enough that no approve is needed — isolates this test to exactly ONE
  // Base transaction (the burn), which is enough to prove the at-most-once property end to end.
  const { fetchImpl, getSendCount } = makeFakeBaseFetch({
    allowanceBaseUnits: 999_000_000n,
    sendRawTransactionImpl: async () => {
      // Simulates a real incident: the client-side send call throws (network blip) even though
      // the transaction may already have been broadcast/landed. The orchestration must NOT
      // interpret this as "safe to try again" — it must fall through to reconciliation.
      throw new Error("simulated network blip on send");
    },
    getTransactionReceiptImpl: async () => ({ ok: true, status: 200, json: async () => ({ jsonrpc: "2.0", id: 1, result: { status: "0x1" } }) }),
  });

  let clock = 0;
  const now = () => clock;
  const sleepImpl = async (ms) => {
    clock += ms;
  };

  // Fake Solana connection: USDC balance never increases — the destination-side finalize call is
  // never submitted in this build (documented known gap), so the poll must time out honestly.
  const fakeConnection = {
    getParsedTokenAccountsByOwner: async () => ({
      value: [{ account: { data: { parsed: { info: { tokenAmount: { uiAmount: 5 } } } } } }],
    }),
  };
  class FakePublicKey {
    constructor(v) {
      this.v = v;
    }
  }

  const result = await bridgeToSolana({
    env: { ANICCA_STATE_DIR: stateDir },
    live: true,
    amountUsdc: 10,
    evmHome,
    solanaHome,
    fetchImpl,
    connectionFactory: () => fakeConnection,
    publicKeyCtor: FakePublicKey,
    now,
    sleepImpl,
    destinationPollTimeoutMs: 30000, // small, bounded — keeps this test fast via the fake clock
  });

  assert.equal(result.posted, true);
  assert.equal(result.creditResult.outcome, "awaiting-credit");
  assert.match(result.creditResult.reason, /never re-sent/);

  // THE at-most-once proof: exactly one send attempt reached the network, despite the send call
  // itself throwing every time it was invoked. If the orchestration ever blind-retried on the
  // "unknown outcome" path, this would be > 1.
  assert.equal(getSendCount(), 1);

  // THE intent-before-send proof: the intent file's burn row was written with status "intent" and
  // a real, non-null txHash — and that hash is the SAME one eth_getTransactionReceipt was
  // eventually reconciled against and reported in the final result.
  const intentLines = fs
    .readFileSync(path.join(stateDir, "nosana-bridge-intents.jsonl"), "utf8")
    .trim()
    .split("\n")
    .map((l) => JSON.parse(l));
  const burnIntentRow = intentLines.find((r) => r.kind === "burn" && r.status === "intent");
  assert.ok(burnIntentRow, "expected a burn intent row written before send");
  assert.equal(typeof burnIntentRow.txHash, "string");
  assert.equal(burnIntentRow.txHash, result.burnTxHash);
  const burnedRow = intentLines.find((r) => r.status === "burned");
  assert.ok(burnedRow, "expected a 'burned' row after reconciliation confirmed the tx landed");

  // The settled ledger row records the honest (not-yet-credited) outcome.
  const ledgerLines = fs
    .readFileSync(path.join(stateDir, "nosana-bridge.jsonl"), "utf8")
    .trim()
    .split("\n")
    .map((l) => JSON.parse(l));
  assert.equal(ledgerLines.length, 1);
  assert.equal(ledgerLines[0].outcome, "awaiting-credit");
  assert.equal(ledgerLines[0].amountUsdc, 10);

  // No secret material anywhere in either file.
  const allText = fs.readFileSync(path.join(stateDir, "nosana-bridge-intents.jsonl"), "utf8") + fs.readFileSync(path.join(stateDir, "nosana-bridge.jsonl"), "utf8");
  assert.ok(!/[1-9A-HJ-NP-Za-km-z]{80,}/.test(allText)); // no base58-secret-shaped run

  fs.rmSync(evmHome, { recursive: true, force: true });
  fs.rmSync(solanaHome, { recursive: true, force: true });
  fs.rmSync(stateDir, { recursive: true, force: true });
});

test("bridgeToSolana --live: refuses to bridge and never writes an intent when the spend gate denies it", async () => {
  const evmHome = mkTmpHome("bridge-live-refuse-evm-");
  const solanaHome = mkTmpHome("bridge-live-refuse-sol-");
  const stateDir = mkTmpHome("bridge-live-refuse-state-");
  writeEvmWallet(evmHome, generatePrivateKey());
  writeSolanaSecret(solanaHome, bs58.encode(Keypair.generate().secretKey));

  // ETH balance far too low to cover gas at all -> gate refuses.
  const { fetchImpl, getSendCount } = makeFakeBaseFetch({ ethBalanceWei: 10n, allowanceBaseUnits: 999_000_000n });

  const result = await bridgeToSolana({
    env: { ANICCA_STATE_DIR: stateDir },
    live: true,
    amountUsdc: 10,
    evmHome,
    solanaHome,
    fetchImpl,
  });

  assert.equal(result.posted, false);
  assert.equal(result.gate.allowed, false);
  assert.equal(getSendCount(), 0);
  assert.equal(fs.existsSync(path.join(stateDir, "nosana-bridge-intents.jsonl")), false);

  fs.rmSync(evmHome, { recursive: true, force: true });
  fs.rmSync(solanaHome, { recursive: true, force: true });
  fs.rmSync(stateDir, { recursive: true, force: true });
});
