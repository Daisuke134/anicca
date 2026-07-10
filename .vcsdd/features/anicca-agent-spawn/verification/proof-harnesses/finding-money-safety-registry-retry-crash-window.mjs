// Sprint-2 Phase 5 money-safety re-confirmation harness (NOT a required PROP obligation -- an
// independently-discovered finding while re-confirming "durable registry-append retry does not
// double-append", one of the task's explicit hard-gate checks).
//
// Demonstrates: retryPendingRegistryAppends' own two-step sequence
//   (1) await append(citizens_registry_file, citizen_record)
//   (2) resolvePendingRegistryAppend(file, entry.child_id)
// is NOT atomic. If the process dies/crashes between step (1) succeeding and step (2) running (a
// real possibility: SIGKILL, OOM-kill, host reboot mid-wake), the pending-registry-appends queue
// entry is still "pending" state=child_id -- the NEXT wake's retryPendingRegistryAppends call will
// re-append the SAME citizen_record a second time into citizens.json, since appendCitizenRecord has
// no idempotency/existing-id guard.
//
// Consequence traced to a real money-safety effect: treasury-gate.mjs's computePerCitizenSurplusUsd/
// computeColonySurplusUsd iterate the raw citizens array with NO id-dedup (unlike ledger.js rows,
// which ARE deduped last-write-wins by groupLedgerRowsByChildId before use) -- a duplicated citizen
// record inflates colonySurplusUsd by that citizen's own surplus a second time, which feeds directly
// into decideColonySpawn's eligibility check (a REAL-money-spending decision).
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import assert from "node:assert/strict";

const REPO = "/Users/anicca/anicca";
const { appendCitizenRecord } = await (async () => {
  // appendCitizenRecord is NOT exported from spawn-orchestrator.mjs -- reimplement the exact
  // production logic here (byte-identical to lib/spawn-orchestrator.mjs lines 120-130) since this
  // harness must not modify production source to add a test-only export.
  const { promises: fsp } = await import("node:fs");
  return {
    appendCitizenRecord: async (citizensRegistryFile, record) => {
      let records = [];
      try {
        records = JSON.parse(await fsp.readFile(citizensRegistryFile, "utf8"));
      } catch (e) {
        if (e.code !== "ENOENT") throw e;
      }
      records.push(record);
      await fsp.mkdir(path.dirname(citizensRegistryFile), { recursive: true });
      await fsp.writeFile(citizensRegistryFile, JSON.stringify(records, null, 2));
    },
  };
})();

const { computeColonySurplusUsd } = await import(path.join(REPO, "skills/self/spawn/lib/treasury-gate.mjs"));

const dir = fs.mkdtempSync(path.join(os.tmpdir(), "anicca-money-safety-retry-crash-"));
const citizensRegistryFile = path.join(dir, "citizens.json");

const citizenRecord = {
  id: "anicca-c099",
  wallet: { evm: true },
  walletAddress: { evm: "0xChildFixtureRetryCrash00000000000001" },
  fuel: { provider: "free-model" },
  humanDependencies: [],
  homeDir: path.join(dir, "child-home"),
  coLocatedWithCoordinator: false,
  balanceUsd: 40, // fixture balance for the surplus-doubling demonstration below
};

// --- Simulate retryPendingRegistryAppends' step (1) succeeding on wake N ---
await appendCitizenRecord(citizensRegistryFile, citizenRecord);
// --- Simulate a crash BEFORE step (2) (resolvePendingRegistryAppend) ever runs: the pending queue
// entry for this child_id genuinely still reads status:"pending" on the next wake (not simulated
// here directly -- pending-registry-append.js's own deriveOutstandingRegistryAppends is already unit-
// tested elsewhere; this harness isolates the CONSEQUENCE of the queue entry surviving as "pending"
// across the crash, which is: the NEXT wake's retryPendingRegistryAppends calls appendCitizenRecord
// a SECOND time for the SAME entry). ---

// --- Simulate retryPendingRegistryAppends' step (1) on wake N+1, re-processing the SAME still-
// "pending" queue entry (this is the real, current production code path -- no guard prevents it) ---
await appendCitizenRecord(citizensRegistryFile, citizenRecord);

const records = JSON.parse(fs.readFileSync(citizensRegistryFile, "utf8"));
const dupes = records.filter((r) => r.id === citizenRecord.id);

console.log(`citizens.json record count for ${citizenRecord.id}: ${dupes.length}`);
assert.equal(dupes.length, 2, "FINDING CONFIRMED: appendCitizenRecord has no id-dedup guard -- a re-run of the same pending queue entry after a crash produces a genuine duplicate row");

// --- Trace the consequence into the actual money-safety-relevant aggregate ---
const perCitizenReserveUsd = 5.0;
const surplusWithDupe = computeColonySurplusUsd({ citizens: records, perCitizenReserveUsd });
const surplusWithoutDupe = computeColonySurplusUsd({ citizens: [records[0]], perCitizenReserveUsd });
console.log(`computeColonySurplusUsd with the duplicate record present: $${surplusWithDupe}`);
console.log(`computeColonySurplusUsd with only ONE (correct) record: $${surplusWithoutDupe}`);
assert.equal(surplusWithDupe, surplusWithoutDupe * 2, "FINDING CONFIRMED: the duplicate citizen record doubles that citizen's own surplus contribution to colonySurplusUsd -- decideColonySpawn's real-money eligibility check consumes this exact inflated value");

console.log("\n=== SUMMARY ===");
console.log("This is a genuine, narrow-window (process-crash-between-two-writes) gap in the FIND-003");
console.log("durable registry-append retry mechanism (lib/pending-registry-append.js +");
console.log("spawn-orchestrator.mjs::retryPendingRegistryAppends): appendCitizenRecord has no");
console.log("existing-id idempotency guard, so a crash between the append write and the resolve write");
console.log("(SIGKILL/OOM/host reboot mid-wake) causes the NEXT wake's retry to re-append the SAME");
console.log("citizen record, which computeColonySurplusUsd/computePerCitizenSurplusUsd (no id-dedup,");
console.log("unlike ledger.js rows) then double-counts -- inflating the real-money spawn-eligibility");
console.log("surplus decideColonySpawn consumes. NOT covered by any of PROP-115..121 (none of the 7");
console.log("target obligations name this idempotency property) and NOT one of sprint-2's contract");
console.log("obligations (FIND-003's own scope was the transient-failure-THEN-successful-retry happy");
console.log("path, never a crash-mid-retry scenario) -- reported here as a genuinely new Phase 5 finding,");
console.log("not a fake PROP discharge.");
