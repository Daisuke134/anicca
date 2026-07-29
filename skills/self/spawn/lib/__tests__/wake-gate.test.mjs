// VCSDD anicca-agent-spawn, sprint-2, contract-review round 2 (resolves FIND-004, PROP-307e).
// scripts/wake-gate.mjs is run.sh's own real production body: decideColonySpawn() (REQ-102) then,
// only if eligible:true, executeSpawnAttempt() (REQ-307) -- replacing the OLD lib/spawn-decision.js
// gate + DigitalOcean/AgentMail provisioning path this file used to name. `deps` mirrors
// spawn-orchestrator.mjs's own executeSpawnAttempt test-wiring convention: every genuinely effectful
// piece is injectable, decideColonySpawn/executeSpawnAttempt themselves are the REAL, unmodified
// functions unless a test explicitly overrides them.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { runWakeGate } from "../../scripts/wake-gate.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const RUN_SH_PATH = path.resolve(__dirname, "../../run.sh");
const WAKE_GATE_PATH = path.resolve(__dirname, "../../scripts/wake-gate.mjs");

function tmpDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "anicca-wake-gate-"));
}

function seedCitizens(dir, citizens) {
  const registryPath = path.join(dir, "citizens.json");
  fs.writeFileSync(registryPath, JSON.stringify(citizens, null, 2));
  return registryPath;
}

const ONE_CITIZEN = [
  {
    id: "automaton",
    wallet: { evm: true },
    walletAddress: { evm: "0xB9dd3B67921B354c656523d6851537988F31DD56" },
    fuel: { provider: "clawrouter-own-wallet" },
    humanDependencies: [],
    homeDir: "/home/life-manager/.anicca",
    coLocatedWithCoordinator: true,
  },
];

function baseDeps(dir, overrides = {}) {
  return {
    registryPath: path.join(dir, "citizens.json"),
    ledgerFile: path.join(dir, "children.jsonl"),
    shelterCostFile: path.join(dir, "shelter-cost.jsonl"),
    // FIND-003: scoped into the tmp dir, exactly like ledgerFile/shelterCostFile above -- without this
    // override, a real (non-dry-run) invocation would call the REAL retryPendingRegistryAppends against
    // the actual production state dir.
    pendingRegistryAppendsFile: path.join(dir, "pending-registry-appends.jsonl"),
    ensureCitizensRegistry: async () => ({ created: false }), // citizens.json already seeded by the test
    readChildren: () => [],
    readShelterCostEntries: () => [],
    fetchEvmBalanceUsd: async () => 0,
    fetchSolanaBalanceUsd: async () => 0,
    nowMs: 1_800_000_000_000,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Structural: run.sh no longer references the OLD gate/provisioning path, and genuinely hands off to
// wake-gate.mjs, which itself genuinely calls decideColonySpawn/executeSpawnAttempt (PROP-307e).
// ---------------------------------------------------------------------------

// Strips `#`/`//` line comments before grepping (mirrors test-akt-treasury.sh/test-deploy-akash.sh's
// own `sed 's/#.*//'` convention) -- the header docs legitimately NAME the retired OLD gate/path in
// prose ("the OLD lib/spawn-decision.js gate ... is RETIRED"); what must be absent is a live
// reference/call, not the documentation of what was removed.
function stripLineComments(src, marker) {
  return src
    .split("\n")
    .map((line) => {
      const i = line.indexOf(marker);
      return i === -1 ? line : line.slice(0, i);
    })
    .join("\n");
}

test("PROP-307e structural: run.sh no longer CALLS the OLD lib/spawn-decision.js gate or provisions DigitalOcean/AgentMail directly (outside its own retirement-note comments)", () => {
  const code = stripLineComments(fs.readFileSync(RUN_SH_PATH, "utf8"), "#");
  assert.ok(!/spawn-decision/.test(code), "run.sh must never call the OLD lib/spawn-decision.js gate");
  assert.ok(!/DIGITALOCEAN_TOKEN/.test(code), "run.sh must never provision a DigitalOcean droplet directly");
  assert.ok(!/AGENTMAIL_API_KEY/.test(code), "run.sh must never provision an AgentMail inbox directly");
  assert.ok(/wake-gate\.mjs/.test(code), "run.sh must hand off to scripts/wake-gate.mjs");
});

test("PROP-307e structural: wake-gate.mjs (run.sh's real production body) genuinely calls decideColonySpawn then, if eligible, executeSpawnAttempt", () => {
  const code = stripLineComments(fs.readFileSync(WAKE_GATE_PATH, "utf8"), "//");
  assert.ok(/decideColonySpawn/.test(code));
  assert.ok(/executeSpawnAttempt/.test(code));
  assert.ok(!/spawn-decision/.test(code), "wake-gate.mjs must never CALL the OLD gate (outside its own header-comment documentation of what was replaced)");
});

// ---------------------------------------------------------------------------
// Behavioral: eligible:false -> executeSpawnAttempt is NEVER called, regardless of --dry-run.
// ---------------------------------------------------------------------------

test("not eligible (insufficient colony surplus): executeSpawnAttempt is never invoked, dry-run or not", async () => {
  const dir = tmpDir();
  seedCitizens(dir, ONE_CITIZEN);
  let spawnCalls = 0;
  const deps = baseDeps(dir, {
    fetchEvmBalanceUsd: async () => 0.5, // below perCitizenReserveUsd(5.00) -> zero surplus
    executeSpawnAttempt: async () => { spawnCalls += 1; return { status: "active", childId: "should-never-happen" }; },
  });

  const dry = await runWakeGate({ argv: ["--dry-run"], env: {}, deps });
  assert.equal(dry.decision.eligible, false);
  assert.equal(dry.result, null);

  const real = await runWakeGate({ argv: [], env: {}, deps });
  assert.equal(real.decision.eligible, false);
  assert.equal(real.result, null);
  assert.equal(spawnCalls, 0, "an ineligible wake must never invoke executeSpawnAttempt");
});

// ---------------------------------------------------------------------------
// Behavioral: eligible:true + --dry-run -> STILL never invokes executeSpawnAttempt (zero side effects).
// ---------------------------------------------------------------------------

test("eligible:true but --dry-run: executeSpawnAttempt is never invoked (gate-only, zero side effects)", async () => {
  const dir = tmpDir();
  seedCitizens(dir, ONE_CITIZEN);
  let spawnCalls = 0;
  const deps = baseDeps(dir, {
    fetchEvmBalanceUsd: async () => 100, // well above perCitizenReserveUsd + spawnThresholdUsd
    executeSpawnAttempt: async () => { spawnCalls += 1; return { status: "active", childId: "should-never-happen" }; },
  });

  const dry = await runWakeGate({ argv: ["--dry-run"], env: {}, deps });
  assert.equal(dry.decision.eligible, true);
  assert.equal(dry.result, null);
  assert.equal(spawnCalls, 0, "--dry-run must never invoke executeSpawnAttempt even when eligible");
});

// ---------------------------------------------------------------------------
// Behavioral: eligible:true, real run -> executeSpawnAttempt IS invoked with the resolved driving
// citizen wallet and the --skills=-parsed initial skill set.
// ---------------------------------------------------------------------------

test("eligible:true, real run: executeSpawnAttempt is invoked with the resolved drivingCitizenWallet and --skills=-parsed initialSkills", async () => {
  const dir = tmpDir();
  seedCitizens(dir, ONE_CITIZEN);
  let seenArgs = null;
  const deps = baseDeps(dir, {
    fetchEvmBalanceUsd: async () => 100,
    resolveDrivingCitizen: async () => ({ wallet: "0xDrivingCitizenFixture000000000000000001", chain: "evm" }),
    executeSpawnAttempt: async (args) => { seenArgs = args; return { status: "active", childId: "anicca-c001" }; },
  });

  const result = await runWakeGate({ argv: ["--skills=sol-trade,pm-trade"], env: {}, deps });
  assert.equal(result.decision.eligible, true);
  assert.equal(result.result.status, "active");
  assert.equal(result.decision.drivingCitizenWallet, "0xDrivingCitizenFixture000000000000000001");
  assert.deepEqual(seenArgs.initialSkills, ["sol-trade", "pm-trade"]);
  assert.equal(seenArgs.drivingCitizenWallet, "0xDrivingCitizenFixture000000000000000001");
});

test("initialSkills falls back to ANICCA_CHILD_INITIAL_SKILLS env when --skills= is not passed", async () => {
  const dir = tmpDir();
  seedCitizens(dir, ONE_CITIZEN);
  let seenArgs = null;
  const deps = baseDeps(dir, {
    fetchEvmBalanceUsd: async () => 100,
    resolveDrivingCitizen: async () => ({ wallet: "0xDrivingCitizenFixture000000000000000001", chain: "evm" }),
    executeSpawnAttempt: async (args) => { seenArgs = args; return { status: "active", childId: "anicca-c001" }; },
  });

  await runWakeGate({ argv: [], env: { ANICCA_CHILD_INITIAL_SKILLS: "sol-trade" }, deps });
  assert.deepEqual(seenArgs.initialSkills, ["sol-trade"]);
});

test("initialSkills defaults to an empty array when neither --skills= nor the env var is set", async () => {
  const dir = tmpDir();
  seedCitizens(dir, ONE_CITIZEN);
  let seenArgs = null;
  const deps = baseDeps(dir, {
    fetchEvmBalanceUsd: async () => 100,
    resolveDrivingCitizen: async () => ({ wallet: "0xDrivingCitizenFixture000000000000000001", chain: "evm" }),
    executeSpawnAttempt: async (args) => { seenArgs = args; return { status: "active", childId: "anicca-c001" }; },
  });

  await runWakeGate({ argv: [], env: {}, deps });
  assert.deepEqual(seenArgs.initialSkills, []);
});

// ---------------------------------------------------------------------------
// Edge case: eligible:true but the driving citizen's own identity cannot be resolved -> a genuine,
// honest failure result -- never a fabricated "active" claim, never a silent skip.
// ---------------------------------------------------------------------------

test("eligible:true but no resolvable driving-citizen identity: a genuine failed result, executeSpawnAttempt never invoked", async () => {
  const dir = tmpDir();
  seedCitizens(dir, ONE_CITIZEN);
  let spawnCalls = 0;
  const deps = baseDeps(dir, {
    fetchEvmBalanceUsd: async () => 100,
    resolveDrivingCitizen: async () => null,
    executeSpawnAttempt: async () => { spawnCalls += 1; return { status: "active", childId: "should-never-happen" }; },
  });

  const result = await runWakeGate({ argv: [], env: {}, deps });
  assert.equal(result.decision.eligible, true, "the colony-wide gate itself was genuinely eligible");
  assert.equal(spawnCalls, 0);
  assert.equal(result.result.status, "failed");
  assert.equal(result.result.childId, null);
  assert.match(result.result.error, /no resolvable per-instance identity/);
});

// ---------------------------------------------------------------------------
// FIND-003 (REQ-305 edge case): a real wake retries any PRIOR wake's queued citizens.json append BEFORE
// any further spawn evaluation runs -- never during --dry-run (a registry append is a real side effect).
// ---------------------------------------------------------------------------

test("FIND-003: a real (non-dry-run) wake calls retryPendingRegistryAppends BEFORE decideColonySpawn's own evaluation runs", async () => {
  const dir = tmpDir();
  seedCitizens(dir, ONE_CITIZEN);
  const calls = [];
  const deps = baseDeps(dir, {
    fetchEvmBalanceUsd: async () => { calls.push("evaluate"); return 0.5; }, // insufficient surplus -> not eligible
    retryPendingRegistryAppends: async () => { calls.push("retry"); return []; },
  });

  const result = await runWakeGate({ argv: [], env: {}, deps });
  assert.equal(result.decision.eligible, false);
  assert.deepEqual(calls, ["retry", "evaluate"], "the pending-registry-append retry must run before the colony-surplus evaluation it precedes, every wake, regardless of the resulting eligibility");
});

test("FIND-003: --dry-run never calls retryPendingRegistryAppends (a registry append is a real side effect, excluded from dry-run's own zero-side-effect contract)", async () => {
  const dir = tmpDir();
  seedCitizens(dir, ONE_CITIZEN);
  let retryCalls = 0;
  const deps = baseDeps(dir, {
    retryPendingRegistryAppends: async () => { retryCalls += 1; return []; },
  });

  await runWakeGate({ argv: ["--dry-run"], env: {}, deps });
  assert.equal(retryCalls, 0);
});

// ---------------------------------------------------------------------------
// Money-safety regression, defense-in-depth backstop (Phase-5 finding,
// verification/proof-harnesses/finding-money-safety-registry-retry-crash-window.mjs): a duplicate-id
// citizen record in citizens.json -- exactly what a crash-window pending-registry-append re-drive would
// have produced BEFORE appendCitizenRecord's own idempotency-by-id fix -- must never double-count that
// citizen's surplus into colonySurplusUsd, the real-money spawn-eligibility input decideColonySpawn
// consumes. Tests dedupCitizensById's wiring into runWakeGate directly (independent of the
// spawn-orchestrator-level fix, which spawn-orchestrator.test.mjs's own money-safety regression covers).
// ---------------------------------------------------------------------------

const DUPLICATED_CITIZEN = [
  {
    id: "automaton",
    wallet: { evm: true },
    walletAddress: { evm: "0xB9dd3B67921B354c656523d6851537988F31DD56" },
    fuel: { provider: "clawrouter-own-wallet" },
    humanDependencies: [],
    homeDir: "/home/life-manager/.anicca",
    coLocatedWithCoordinator: true,
  },
  // The SAME citizen, id-duplicated -- the exact on-disk shape a crash-window re-drive produces.
  {
    id: "automaton",
    wallet: { evm: true },
    walletAddress: { evm: "0xB9dd3B67921B354c656523d6851537988F31DD56" },
    fuel: { provider: "clawrouter-own-wallet" },
    humanDependencies: [],
    homeDir: "/home/life-manager/.anicca",
    coLocatedWithCoordinator: true,
  },
];

test("money-safety: a duplicate-id citizens.json entry never doubles colonySurplusUsd (dedupCitizensById backstop)", async () => {
  const dir = tmpDir();
  seedCitizens(dir, DUPLICATED_CITIZEN);
  const deps = baseDeps(dir, {
    fetchEvmBalanceUsd: async () => 40, // surplus per citizen = 40 - 5 (PER_CITIZEN_RESERVE_USD_DEFAULT) = 35
  });

  const result = await runWakeGate({ argv: ["--dry-run"], env: {}, deps });
  assert.equal(
    result.decision.colonySurplusUsd,
    35,
    "FIX VERIFIED: a duplicate-id citizen entry must contribute its surplus exactly ONCE, never doubled to 70"
  );
});
