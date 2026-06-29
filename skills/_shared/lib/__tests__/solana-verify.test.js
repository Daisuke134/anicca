// node:test — solana-verify: confirm a Solana signature + compute the inbound SPL-USDC delta
// to OUR wallet's ATA. Pure transport (fetchImpl injected → never touches the network).
// Fixtures mirror the REAL mainnet RPC shapes verified 2026-06-29:
//   getSignatureStatuses → result.value[0] = {confirmationStatus, err, ...}
//   getTransaction jsonParsed → result.meta.{pre,post}TokenBalances[] =
//     {accountIndex, mint, owner, uiTokenAmount:{amount, decimals, uiAmount, uiAmountString}}
import { test } from "node:test";
import assert from "node:assert/strict";
import { sigStatus, usdcDeltaForSig, usdcBalance } from "../solana-verify.mjs";

const USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v";
const WALLET = "xxKC33TYJ2czjGQAADrvDCLjF6pRvtHX125fCwP5u9H";
const OTHER = "65ucDYoCymbLKjEx3HftN5UpCoF5N1V9TtniScf5bpiZ";
const SIG = "52RZBMCUqGWrWPZCJo82xDaYusUhGNFNCEzW51nyJNhFN9AECae9dWyp8TQQZMP731LpP2Xu8JDpJDRxp3xCRD7m";

// Build a fake fetch that returns a canned JSON-RPC result for the requested method.
function fakeFetch(byMethod) {
  return async (_rpc, init) => {
    const body = JSON.parse(init.body);
    const result = byMethod[body.method];
    if (result === undefined) throw new Error(`unexpected method ${body.method}`);
    return { ok: true, json: async () => ({ jsonrpc: "2.0", id: body.id, result }) };
  };
}
const tok = (accountIndex, owner, mint, uiAmount, amount, decimals = 6) => ({
  accountIndex, owner, mint,
  uiTokenAmount: { amount: String(amount), decimals, uiAmount, uiAmountString: String(uiAmount) },
});

test("sigStatus: finalized + err:null → confirmed:true", async () => {
  const f = fakeFetch({ getSignatureStatuses: { value: [{ confirmationStatus: "finalized", err: null }] } });
  assert.deepEqual(await sigStatus(SIG, { fetchImpl: f }), { confirmed: true, err: null });
});

test("sigStatus: confirmed + err:null → confirmed:true", async () => {
  const f = fakeFetch({ getSignatureStatuses: { value: [{ confirmationStatus: "confirmed", err: null }] } });
  assert.equal((await sigStatus(SIG, { fetchImpl: f })).confirmed, true);
});

test("sigStatus: processed (not yet confirmed) → confirmed:false", async () => {
  const f = fakeFetch({ getSignatureStatuses: { value: [{ confirmationStatus: "processed", err: null }] } });
  assert.equal((await sigStatus(SIG, { fetchImpl: f })).confirmed, false);
});

test("sigStatus: tx errored (err set) → confirmed:false even if finalized", async () => {
  const f = fakeFetch({ getSignatureStatuses: { value: [{ confirmationStatus: "finalized", err: { InstructionError: [0, "x"] } }] } });
  assert.equal((await sigStatus(SIG, { fetchImpl: f })).confirmed, false);
});

test("sigStatus: unknown signature (value[0]=null) → confirmed:false", async () => {
  const f = fakeFetch({ getSignatureStatuses: { value: [null] } });
  assert.equal((await sigStatus(SIG, { fetchImpl: f })).confirmed, false);
});

test("sigStatus: rejects a non-base58 / EVM-style hash", async () => {
  await assert.rejects(() => sigStatus("0xdeadbeef", { fetchImpl: fakeFetch({}) }), /base58|signature/i);
});

test("usdcDeltaForSig: normal inbound (pre 10 → post 60 = +50) to OUR ATA only", async () => {
  const meta = {
    err: null,
    preTokenBalances: [tok(3, WALLET, USDC, 10, 10_000000), tok(5, OTHER, USDC, 999, 999_000000)],
    postTokenBalances: [tok(3, WALLET, USDC, 60, 60_000000), tok(5, OTHER, USDC, 949, 949_000000)],
  };
  const f = fakeFetch({ getTransaction: { meta } });
  assert.equal(await usdcDeltaForSig(SIG, WALLET, { fetchImpl: f }), 50);
});

test("usdcDeltaForSig: FIRST-INBOUND (ATA created in this tx → NO pre entry) → full post amount", async () => {
  // This IS the acceptance scenario: wallet has no USDC ATA, the withdraw creates it.
  const meta = {
    err: null,
    preTokenBalances: [], // no pre entry for our index at all
    postTokenBalances: [tok(7, WALLET, USDC, 12.5, 12_500000)],
  };
  const f = fakeFetch({ getTransaction: { meta } });
  assert.equal(await usdcDeltaForSig(SIG, WALLET, { fetchImpl: f }), 12.5);
});

test("usdcDeltaForSig: ignores other owners and other mints in a batch tx", async () => {
  const meta = {
    err: null,
    preTokenBalances: [tok(3, WALLET, USDC, 0, 0)],
    postTokenBalances: [
      tok(3, WALLET, USDC, 5, 5_000000),                 // +5 ours
      tok(4, OTHER, USDC, 100, 100_000000),              // other owner — ignore
      tok(8, WALLET, "BDdzUjksj1J4bSnMveQ5tV9Up8A9c6YS1tHrxNw3pump", 999, 999_000000), // other mint — ignore
    ],
  };
  const f = fakeFetch({ getTransaction: { meta } });
  assert.equal(await usdcDeltaForSig(SIG, WALLET, { fetchImpl: f }), 5);
});

test("usdcDeltaForSig: uiAmount null → falls back to amount/10**decimals", async () => {
  const post = tok(3, WALLET, USDC, null, 7_250000);
  post.uiTokenAmount.uiAmount = null; // RPC sometimes returns null
  const meta = { err: null, preTokenBalances: [], postTokenBalances: [post] };
  const f = fakeFetch({ getTransaction: { meta } });
  assert.equal(await usdcDeltaForSig(SIG, WALLET, { fetchImpl: f }), 7.25);
});

test("usdcBalance: existing ATA returns uiAmount", async () => {
  const value = [{ account: { data: { parsed: { info: { tokenAmount: { amount: "42000000", decimals: 6, uiAmount: 42, uiAmountString: "42" } } } } } }];
  const f = fakeFetch({ getTokenAccountsByOwner: { value } });
  assert.equal(await usdcBalance(WALLET, { fetchImpl: f }), 42);
});

test("usdcBalance: NO ATA (empty value) → 0, does not throw", async () => {
  const f = fakeFetch({ getTokenAccountsByOwner: { value: [] } });
  assert.equal(await usdcBalance(WALLET, { fetchImpl: f }), 0);
});
