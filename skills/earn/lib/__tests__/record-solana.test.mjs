// node:test — FIND-201 round-trip: a Solana promote.fun payout recorded via the canonical write
// path (record.mjs → deriveLine → assertOwnIdentityOnly → appendLedger) MUST persist sig/confirmed
// so that isProfitable(persistedLine) === true. If deriveLine dropped sig/confirmed, DONE could
// never fire — this test is the guard against that regression.
import { test } from "node:test";
import assert from "node:assert/strict";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { record } from "../record.mjs";
import { readLedger, isProfitable } from "../../../_shared/lib/ledger.mjs";

async function tmpFile() {
  const d = await fs.mkdtemp(path.join(os.tmpdir(), "clip-earn-ledger-"));
  return path.join(d, "earn-ledger.jsonl");
}

test("record.mjs persists a Solana promote.fun payout that isProfitable accepts (DONE can fire)", async () => {
  const f = await tmpFile();
  const json = JSON.stringify({
    wallet: "xxKC33TYJ2czjGQAADrvDCLjF6pRvtHX125fCwP5u9H",
    source: "promote.fun",
    task: "clip payout withdraw",
    earn_usdc: 0.5,
    cost_usdc: 0.0,
    sig: "52RZBMCUqGWrWPZCJo82xDaYusUhGNFNCEzW51nyJNhFN9AECae9dWyp8TQQZMP731LpP2Xu8JDpJDRxp3xCRD7m",
    confirmed: true,
    chain: "solana",
    external: true,
    wake: "w-record",
  });
  const { line, profitable } = await record(json, f);
  assert.equal(profitable, true, "the Solana line must classify as profitable (DONE)");
  assert.equal(line.sig.length > 80, true, "sig persisted");
  assert.equal(line.confirmed, true, "confirmed persisted");

  // and it survives a round-trip through the ledger file (the real persisted shape).
  const rows = await readLedger(f);
  assert.equal(rows.length, 1);
  assert.equal(isProfitable(rows[0]), true, "persisted line on disk still passes the gate");
});

test("record.mjs: same Solana line without external:true is NOT profitable (false-green guard)", async () => {
  const f = await tmpFile();
  const json = JSON.stringify({
    wallet: "xxKC33TYJ2czjGQAADrvDCLjF6pRvtHX125fCwP5u9H", source: "promote.fun", task: "t",
    earn_usdc: 0.5, cost_usdc: 0, sig: "sigNoExternal", confirmed: true, chain: "solana", wake: "w",
  });
  const { profitable } = await record(json, f);
  assert.equal(profitable, false);
});
