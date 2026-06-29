// node:test — the RECORD executor (DONE gate). Injected fetch → no network. Covers the four outcomes:
// recorded (confirmed + inbound>0), unconfirmed, zero-delta, duplicate (sig-keyed idempotency).
import { test } from "node:test";
import assert from "node:assert/strict";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { recordPayout } from "../record-payout.mjs";
import { readLedger, isProfitable } from "../../../_shared/lib/ledger.mjs";

const WALLET = "xxKC33TYJ2czjGQAADrvDCLjF6pRvtHX125fCwP5u9H";
const USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v";
const SIG = "52RZBMCUqGWrWPZCJo82xDaYusUhGNFNCEzW51nyJNhFN9AECae9dWyp8TQQZMP731LpP2Xu8JDpJDRxp3xCRD7m";

async function tmpFile() {
  const d = await fs.mkdtemp(path.join(os.tmpdir(), "clip-promote-"));
  return path.join(d, "earn-ledger.jsonl");
}
function fetchFor({ status = "finalized", err = null, delta = 0 }) {
  return async (_rpc, init) => {
    const body = JSON.parse(init.body);
    if (body.method === "getSignatureStatuses") {
      return { ok: true, json: async () => ({ result: { value: [{ confirmationStatus: status, err }] } }) };
    }
    if (body.method === "getTransaction") {
      const meta = { err: null, preTokenBalances: [],
        postTokenBalances: delta > 0 ? [{ accountIndex: 3, owner: WALLET, mint: USDC,
          uiTokenAmount: { amount: String(delta * 1e6), decimals: 6, uiAmount: delta, uiAmountString: String(delta) } }] : [] };
      return { ok: true, json: async () => ({ result: { meta } }) };
    }
    throw new Error("unexpected method " + body.method);
  };
}

test("recordPayout: confirmed + inbound>0 → recorded, persisted line isProfitable (DONE)", async () => {
  const ledger = await tmpFile();
  const r = await recordPayout({ sig: SIG, wallet: WALLET, ledger, wake: "w1" }, { fetchImpl: fetchFor({ delta: 0.5 }) });
  assert.equal(r.status, "recorded");
  assert.equal(r.earn_usdc, 0.5);
  const rows = await readLedger(ledger);
  assert.equal(rows.length, 1);
  assert.equal(isProfitable(rows[0]), true);
});

test("recordPayout: unconfirmed signature → NOT recorded", async () => {
  const ledger = await tmpFile();
  const r = await recordPayout({ sig: SIG, wallet: WALLET, ledger, wake: "w1" }, { fetchImpl: fetchFor({ status: "processed", delta: 0.5 }) });
  assert.equal(r.status, "unconfirmed");
  assert.deepEqual(await readLedger(ledger), []);
});

test("recordPayout: confirmed but zero inbound delta → NOT recorded (no false earn)", async () => {
  const ledger = await tmpFile();
  const r = await recordPayout({ sig: SIG, wallet: WALLET, ledger, wake: "w1" }, { fetchImpl: fetchFor({ delta: 0 }) });
  assert.equal(r.status, "zero-delta");
  assert.deepEqual(await readLedger(ledger), []);
});

test("recordPayout: same sig twice → second is a duplicate, ledger has ONE line (idempotent)", async () => {
  const ledger = await tmpFile();
  await recordPayout({ sig: SIG, wallet: WALLET, ledger, wake: "w1" }, { fetchImpl: fetchFor({ delta: 0.5 }) });
  const r2 = await recordPayout({ sig: SIG, wallet: WALLET, ledger, wake: "w2" }, { fetchImpl: fetchFor({ delta: 0.5 }) });
  assert.equal(r2.status, "duplicate");
  assert.equal((await readLedger(ledger)).length, 1);
});
