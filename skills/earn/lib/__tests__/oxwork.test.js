// node:test — 0xwork external-revenue helpers + GATE-0 classifier (swap-guard + external proof).
import { test } from "node:test";
import assert from "node:assert/strict";
import { isProfitable } from "../ledger.mjs";
import { pickTask, isExternalPayout } from "../oxwork.mjs";

const TASKPOOL = "0xF404aFdbA46e05Af7B395FB45c43e66dB549C6D2";
const USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
const TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef";
const WALLET = "0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21";
const pad = (a) => "0x" + a.toLowerCase().replace(/^0x/, "").padStart(64, "0");

// ---- isProfitable: swap can NEVER be GATE-0; external proof is mandatory --------------------
test("isProfitable rejects a swap line even with status 0x1 + net>0 (asset rotation)", () => {
  assert.equal(
    isProfitable({ source: "swap-eth-usdc", tx: "0xabc", status: "0x1", net_usdc: 0.5 }),
    false
  );
  assert.equal(isProfitable({ source: "swap", tx: "0xabc", status: "0x1", net_usdc: 0.5 }), false);
});

test("isProfitable rejects a 0xwork line WITHOUT external:true (needs proven external inbound)", () => {
  assert.equal(
    isProfitable({ source: "0xwork", tx: "0xabc", status: "0x1", net_usdc: 0.5 }),
    false
  );
  assert.equal(
    isProfitable({ source: "0xwork", tx: "0xabc", status: "0x1", net_usdc: 0.5, external: false }),
    false
  );
});

test("isProfitable TRUE only for source:0xwork + status 0x1 + net>0 + external:true", () => {
  assert.equal(
    isProfitable({ source: "0xwork", tx: "0xabc", status: "0x1", net_usdc: 0.5, external: true }),
    true
  );
});

test("isProfitable still requires tx + status 0x1 + net>0 even with external:true", () => {
  assert.equal(isProfitable({ source: "0xwork", status: "0x1", net_usdc: 0.5, external: true }), false); // no tx
  assert.equal(isProfitable({ source: "0xwork", tx: "0xabc", status: "0x0", net_usdc: 0.5, external: true }), false); // reverted
  assert.equal(isProfitable({ source: "0xwork", tx: "0xabc", status: "0x1", net_usdc: 0, external: true }), false); // no net
});

// ---- isExternalPayout: only a USDC Transfer from taskPool -> wallet is external -------------
test("isExternalPayout TRUE for USDC Transfer from taskPool to our wallet", async () => {
  const receipt = {
    logs: [
      { address: USDC, topics: [TRANSFER, pad(TASKPOOL), pad(WALLET)], data: "0x" },
    ],
  };
  assert.equal(await isExternalPayout(receipt, WALLET), true);
});

test("isExternalPayout FALSE for a swap receipt (no taskPool->wallet USDC transfer)", async () => {
  const router = "0x2626664c2603336E57B271c5C0b26F421741e481";
  const receipt = {
    logs: [
      { address: USDC, topics: [TRANSFER, pad(router), pad(WALLET)], data: "0x" }, // from a DEX router, not taskPool
    ],
  };
  assert.equal(await isExternalPayout(receipt, WALLET), false);
});

test("isExternalPayout FALSE for an empty/missing receipt", async () => {
  assert.equal(await isExternalPayout(null, WALLET), false);
  assert.equal(await isExternalPayout({ logs: [] }, WALLET), false);
});

// ---- pickTask: case-insensitive status, stake filter, ANY_CATEGORY ---------------------------
const fakeFetch = (tasks) => async () => ({ ok: true, json: async () => ({ tasks }) });

test("pickTask skips stake>0 and non-open status, returns a doable open task", async () => {
  const tasks = [
    { id: 1, status: "Closed", category: "Code", stake_amount: null, bounty_amount: 50 },
    { id: 2, status: "Open", category: "Code", stake_amount: 40000, bounty_amount: 50 }, // stake required
    { id: 3, status: "Open", category: "Code", stake_amount: null, bounty_amount: 50 }, // doable
  ];
  const t = await pickTask(["Code"], { fetchImpl: fakeFetch(tasks) });
  assert.equal(t.id, 3);
});

test("pickTask with OXWORK_ANY_CATEGORY=1 claims a 'Social'/'Open' task", async () => {
  process.env.OXWORK_ANY_CATEGORY = "1";
  const tasks = [{ id: 390, status: "Open", category: "Social", stake_amount: null, bounty_amount: 50 }];
  const t = await pickTask(["Writing", "Research", "Code", "Data"], { fetchImpl: fakeFetch(tasks) });
  delete process.env.OXWORK_ANY_CATEGORY;
  assert.equal(t.id, 390);
});

test("pickTask returns null when no task matches capabilities (no ANY_CATEGORY)", async () => {
  delete process.env.OXWORK_ANY_CATEGORY;
  const tasks = [{ id: 390, status: "Open", category: "Social", stake_amount: null, bounty_amount: 50 }];
  const t = await pickTask(["Writing"], { fetchImpl: fakeFetch(tasks) });
  assert.equal(t, null);
});
