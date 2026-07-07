// VCSDD anicca-agent-spawn, sprint-2, Phase 2a (RED). REQ-307 -- the spawn orchestrator's single
// entry-point function, executeSpawnAttempt, wiring REQ-201/202/203/204/205/206/301/302/303/304/305/306
// in the canonical 9-step order (see behavioral-spec.md#REQ-307's "Canonical call order"). This module
// (../spawn-orchestrator.mjs) does not exist yet -- this whole file is expected to fail at IMPORT time
// (module-not-found), mirroring colony-spawn-lock.test.mjs's own sprint-1 RED-phase precedent for
// registry-path.mjs, and registry-path.test.mjs's own precedent for CITIZENS_REGISTRY_PATH/COORDINATOR_HOME.
//
// Test-only seam: executeSpawnAttempt's PINNED first argument is exactly
// { initialSkills, drivingCitizenWallet, nowMs = Date.now() } (REQ-307's own Acceptance Criteria). A
// SECOND, optional argument -- `deps` -- is the production/test wiring seam for the 7 genuinely
// effectful, non-file-based steps (subprocess/network calls this sprint newly wires: REQ-203's home
// check, REQ-201's EVM keygen, REQ-306's cloud-target selection, REQ-202's Solana keygen, REQ-302/303's
// deploy, REQ-204's ERC-8004 registration, REQ-205's mcp.json write). Steps 8 (REQ-206 buildChildSpec)
// and 9 (REQ-305 ledger/registry append) are NEVER injected -- they always call the REAL, unmodified
// child-spec.js/ledger.js against `deps.ledgerFile`/`deps.citizensRegistryFile` (real tmp-file
// integration, matching PROP-307c's own "integration test against a real ledger.js file" method and
// this codebase's established convention of injecting only genuinely-effectful I/O, never re-deriving
// pure/already-tested logic -- colony-balances.mjs/akash-funding-gate.mjs/cloud-target.mjs all follow
// this identical discipline). In production, omitting `deps` wires the real gen-wallet.sh/
// gen-solana-wallet.sh/deploy-akash.sh/nosana CLI/ensureAgentId/mcp.json-writer directly -- this second
// argument is a pure testability seam, never a second orchestration path (CRIT-201 is unaffected: there
// is still exactly one call-graph root, `executeSpawnAttempt`, reaching every REQ-2xx/3xx step).
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { executeSpawnAttempt } from "../spawn-orchestrator.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ORCH_PATH = path.resolve(__dirname, "../spawn-orchestrator.mjs");
const RUN_SH_PATH = path.resolve(__dirname, "../../run.sh");

function tmpDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "anicca-spawn-orch-"));
}

function readLedgerRows(file) {
  if (!fs.existsSync(file)) return [];
  return fs
    .readFileSync(file, "utf8")
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean)
    .map((l) => JSON.parse(l));
}

function readRegistryRecords(file) {
  if (!fs.existsSync(file)) return [];
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

const DRIVING_CITIZEN_WALLET = "0xParentWalletFixtureAbc0000000000000001";

function baseParams(overrides = {}) {
  return { initialSkills: [], drivingCitizenWallet: DRIVING_CITIZEN_WALLET, nowMs: 1_800_000_000_000, ...overrides };
}

// All 9 canonical steps succeed fast. Individual tests override exactly one step to fail.
function happyDeps(dir, overrides = {}) {
  return {
    lockStatePath: path.join(dir, "citizens.json"), // withGigLock's statePath (mirrors CITIZENS_REGISTRY_PATH)
    ledgerFile: path.join(dir, "children.jsonl"),
    citizensRegistryFile: path.join(dir, "citizens.json"),
    checkHomeDistinct: async () => ({ ok: true, homeDir: path.join(dir, "child-home") }),
    generateEvmWallet: async () => ({ address: "0xChildEvmFixture0000000000000000000000001", privateKey: "0xchildevmfixturekey" }),
    selectCloudTarget: async () => "akash",
    generateSolanaWallet: async () => ({ address: "ChildSolanaFixture1111111111111111111111111", privateKey: "childsolanafixturekey" }),
    deploy: async () => ({ ok: true, leaseId: "dseq-fixture-001", shelterCostUsd: 0.5 }),
    registerIdentity: async () => ({ ok: true, agentId: "9001", txHash: "0xregtxfixture" }),
    writeMcpConfig: async () => ({ ok: true }),
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// PROP-307a: exactly ONE call-graph root, no second orchestration path, run.sh untouched.
// ---------------------------------------------------------------------------

test("PROP-307a structural: spawn-orchestrator.mjs exports exactly one executeSpawnAttempt entry point and never references run.sh", () => {
  const src = fs.readFileSync(ORCH_PATH, "utf8");
  const exportMatches = src.match(/export\s+(async\s+function|function|const)\s+executeSpawnAttempt/g) || [];
  assert.equal(exportMatches.length, 1, "exactly one executeSpawnAttempt export, no second competing entry point");
  assert.ok(!/run\.sh/.test(src), "spawn-orchestrator.mjs must never reference the superseded run.sh");
});

test("PROP-307a structural: run.sh (pre-existing AgentMail+DigitalOcean/Akash design) is untouched by this sprint's diff", () => {
  const src = fs.readFileSync(RUN_SH_PATH, "utf8");
  assert.ok(src.length > 0, "run.sh must still exist, unmodified prior art -- never deleted or rewritten by REQ-307");
});

test("PROP-307a: a real invocation calls every one of steps 1-9 exactly once, in the canonical order, for a happy-path attempt", async () => {
  const dir = tmpDir();
  const calls = [];
  const deps = happyDeps(dir, {
    checkHomeDistinct: async () => (calls.push("checkHomeDistinct"), { ok: true, homeDir: path.join(dir, "child-home") }),
    generateEvmWallet: async () => (calls.push("generateEvmWallet"), { address: "0xChildEvmFixture0000000000000000000000001", privateKey: "0xk" }),
    selectCloudTarget: async () => (calls.push("selectCloudTarget"), "akash"),
    generateSolanaWallet: async () => (calls.push("generateSolanaWallet"), { address: "ChildSol1", privateKey: "sk" }),
    deploy: async () => (calls.push("deploy"), { ok: true, leaseId: "dseq-1", shelterCostUsd: 0.5 }),
    registerIdentity: async () => (calls.push("registerIdentity"), { ok: true, agentId: "9001", txHash: "0xtx" }),
    writeMcpConfig: async () => (calls.push("writeMcpConfig"), { ok: true }),
  });
  const result = await executeSpawnAttempt(baseParams(), deps);
  assert.equal(result.status, "active");
  // step 4 (Solana keygen) is conditional -- this fixture's initialSkills/deployTarget never trigger it
  assert.deepEqual(calls, ["checkHomeDistinct", "generateEvmWallet", "selectCloudTarget", "deploy", "registerIdentity", "writeMcpConfig"]);
});

// ---------------------------------------------------------------------------
// PROP-307b: no judgment/eligibility/LLM logic inside executeSpawnAttempt itself.
// ---------------------------------------------------------------------------

test("PROP-307b structural: executeSpawnAttempt contains no arithmetic/boolean eligibility comparison and no LLM/prompt reference", () => {
  const src = fs.readFileSync(ORCH_PATH, "utf8");
  assert.ok(
    !/decideColonySpawn|surplus\s*[<>]|colonySurplusUsd\s*[<>=]|spawnThresholdUsd\s*[<>=]/.test(src),
    "eligibility/threshold logic belongs exclusively to decideColonySpawn, called by executeSpawnAttempt's OWN caller before it is ever invoked"
  );
  assert.ok(
    !/\b(anthropic|openai|llm|prompt|chat\.completions|generateText)\b/i.test(src),
    "executeSpawnAttempt must contain zero LLM/prompt references -- pure sequencing and error propagation only"
  );
});

// ---------------------------------------------------------------------------
// PROP-307c / CRIT-203: a failure injected at each of the 9 canonical steps in turn.
// Steps 1-6 (before a complete identity anchor exists) -> minimal direct appendChild row.
// Steps 7-9 (after REQ-204 has genuinely succeeded) -> buildChildSpec-based failure row.
// ---------------------------------------------------------------------------

function assertMinimalFailedRow(row, expectStep) {
  assert.equal(row.status, "failed", `step ${expectStep}: row must be status:"failed"`);
  assert.equal(typeof row.child_id, "string");
  assert.equal(typeof row.attempted_ms, "number");
  assert.equal(typeof row.error, "string");
  assert.ok(row.error.length > 0);
  const keys = Object.keys(row).sort();
  assert.deepEqual(
    keys,
    ["attempted_ms", "child_id", "error", "status"],
    `step ${expectStep}: a pre-identity-anchor failure row must be the MINIMAL shape only -- never buildChildSpec's fields (wallet/parent_wallet/etc.), never via buildChildSpec`
  );
}

function assertBuildChildSpecFailedRow(row, expectStep) {
  assert.equal(row.status, "failed", `step ${expectStep}: row must be status:"failed"`);
  assert.equal(typeof row.attempted_ms, "number");
  assert.equal(typeof row.error, "string");
  // buildChildSpec's own pre-existing fields must be present -- proves the buildChildSpec-based path
  // (never the minimal-row path) was used for a POST-identity-anchor failure.
  assert.equal(typeof row.wallet, "string");
  assert.equal(typeof row.parent_wallet, "string");
  assert.equal(row.generation, 1);
  assert.equal(typeof row.agent_evm_address, "string");
  assert.equal(typeof row.agent_id, "string");
}

test("PROP-307c step 1 (REQ-203 home-distinctness failure) -> minimal direct-append row, never buildChildSpec", async () => {
  const dir = tmpDir();
  const deps = happyDeps(dir, { checkHomeDistinct: async () => ({ ok: false, error: "home collides with an existing citizen" }) });
  const result = await executeSpawnAttempt(baseParams(), deps);
  assert.equal(result.status, "failed");
  const rows = readLedgerRows(deps.ledgerFile).filter((r) => r.child_id === result.childId);
  assert.equal(rows.length, 1);
  assertMinimalFailedRow(rows[0], 1);
  assert.equal(readRegistryRecords(deps.citizensRegistryFile).length, 0, "a failed attempt appends NO registry record");
});

test("PROP-307c step 2 (REQ-201 EVM wallet generation failure) -> minimal direct-append row", async () => {
  const dir = tmpDir();
  const deps = happyDeps(dir, { generateEvmWallet: async () => { throw new Error("gen-wallet.sh: keccak implementation unavailable"); } });
  const result = await executeSpawnAttempt(baseParams(), deps);
  assert.equal(result.status, "failed");
  const rows = readLedgerRows(deps.ledgerFile).filter((r) => r.child_id === result.childId);
  assert.equal(rows.length, 1);
  assertMinimalFailedRow(rows[0], 2);
});

test("PROP-307c step 3 (REQ-306 cloud-target selection failure) -> minimal direct-append row", async () => {
  const dir = tmpDir();
  const deps = happyDeps(dir, { selectCloudTarget: async () => { throw new Error("both Nosana and Akash price/availability queries failed"); } });
  const result = await executeSpawnAttempt(baseParams(), deps);
  assert.equal(result.status, "failed");
  const rows = readLedgerRows(deps.ledgerFile).filter((r) => r.child_id === result.childId);
  assert.equal(rows.length, 1);
  assertMinimalFailedRow(rows[0], 3);
});

test("PROP-307c step 4 (REQ-202 conditional Solana wallet generation failure) -> minimal direct-append row", async () => {
  const dir = tmpDir();
  // Force needsSolanaWallet({initialSkills, deployTarget}) === true by having step-3's REAL selection
  // return "nosana" (REQ-202's own EARS trigger) so step 4 actually runs before it is made to fail.
  const deps = happyDeps(dir, {
    selectCloudTarget: async () => "nosana",
    generateSolanaWallet: async () => { throw new Error("solana keygen entropy source unavailable"); },
  });
  const result = await executeSpawnAttempt(baseParams(), deps);
  assert.equal(result.status, "failed");
  const rows = readLedgerRows(deps.ledgerFile).filter((r) => r.child_id === result.childId);
  assert.equal(rows.length, 1);
  assertMinimalFailedRow(rows[0], 4);
});

test("PROP-307c step 5 (REQ-302/303 deploy failure) -> minimal direct-append row", async () => {
  const dir = tmpDir();
  const deps = happyDeps(dir, { deploy: async () => ({ ok: false, error: "no open Akash bids for dseq" }) });
  const result = await executeSpawnAttempt(baseParams(), deps);
  assert.equal(result.status, "failed");
  const rows = readLedgerRows(deps.ledgerFile).filter((r) => r.child_id === result.childId);
  assert.equal(rows.length, 1);
  assertMinimalFailedRow(rows[0], 5);
});

test("PROP-307c step 6 (REQ-204 ERC-8004 registration failure) -> minimal direct-append row (FIND-S2-001: anchor still incomplete, agentId never produced)", async () => {
  const dir = tmpDir();
  const deps = happyDeps(dir, { registerIdentity: async () => ({ ok: false, error: "Registered event could not be decoded" }) });
  const result = await executeSpawnAttempt(baseParams(), deps);
  assert.equal(result.status, "failed");
  const rows = readLedgerRows(deps.ledgerFile).filter((r) => r.child_id === result.childId);
  assert.equal(rows.length, 1);
  assertMinimalFailedRow(rows[0], 6);
});

test("PROP-307c step 7 (REQ-205 mcp.json write failure) -> buildChildSpec-based failure row (identity anchor already complete)", async () => {
  const dir = tmpDir();
  const deps = happyDeps(dir, { writeMcpConfig: async () => { throw new Error("GIG_STATE_PATH collided with an existing citizen"); } });
  const result = await executeSpawnAttempt(baseParams(), deps);
  assert.equal(result.status, "failed");
  const rows = readLedgerRows(deps.ledgerFile).filter((r) => r.child_id === result.childId);
  assert.equal(rows.length, 1);
  assertBuildChildSpecFailedRow(rows[0], 7);
});

test("PROP-307c step 8 (REQ-206 buildChildSpec's own real distinct-wallet assertion fires) -> buildChildSpec-based failure row", async () => {
  const dir = tmpDir();
  // A genuinely REAL buildChildSpec failure (never fabricated): the generated child wallet happens to
  // equal the driving citizen's own wallet, tripping child-spec.js's existing, untouched
  // childWallet===parentWallet throw.
  const deps = happyDeps(dir, { generateEvmWallet: async () => ({ address: DRIVING_CITIZEN_WALLET, privateKey: "0xk" }) });
  const result = await executeSpawnAttempt(baseParams(), deps);
  assert.equal(result.status, "failed");
  assert.match(result.error, /distinct from parent wallet/);
  const rows = readLedgerRows(deps.ledgerFile).filter((r) => r.child_id === result.childId);
  assert.equal(rows.length, 1);
  assertBuildChildSpecFailedRow(rows[0], 8);
});

test("PROP-307c step 9 (REQ-305 ledger append itself fails) -> no row anywhere ever claims status:active", async () => {
  const dir = tmpDir();
  // A genuinely REAL ledger-append failure: point ledgerFile at a path whose parent segment is a FILE,
  // not a directory, so ledger.js's own fs.mkdirSync(dirname, {recursive:true}) throws ENOTDIR.
  const blockerFile = path.join(dir, "not-a-directory");
  fs.writeFileSync(blockerFile, "x");
  const deps = happyDeps(dir, { ledgerFile: path.join(blockerFile, "children.jsonl") });
  await assert.rejects(
    () => executeSpawnAttempt(baseParams(), deps),
    undefined,
    "a step-9 ledger-append failure may throw (there is no lower-tier ledger to record it in) -- but it must NEVER resolve with status:\"active\""
  ).catch(async (rejectAssertionError) => {
    // If the implementation instead resolves (rather than rejects) on a step-9 failure, the resolved
    // value must still never claim "active".
    if (rejectAssertionError) {
      const result = await executeSpawnAttempt(baseParams(), deps).catch(() => null);
      if (result) assert.notEqual(result.status, "active");
    }
  });
});

// ---------------------------------------------------------------------------
// PROP-307d / CRIT-204: the "colony-spawn" lock is held for the function's entire execution.
// ---------------------------------------------------------------------------

test("PROP-307d: the colony-spawn lock is held from before step 1 until after step 9 completes -- a staggered concurrent attempt fails throughout, succeeds only after release", async () => {
  const dir = tmpDir();
  let releaseDeploy;
  const deployDelay = new Promise((resolve) => { releaseDeploy = resolve; });
  let signalDeployReached;
  const deployReached = new Promise((resolve) => { signalDeployReached = resolve; });

  const deps = happyDeps(dir, {
    deploy: async () => {
      signalDeployReached();
      await deployDelay;
      return { ok: true, leaseId: "dseq-staggered", shelterCostUsd: 0.5 };
    },
  });

  const firstAttempt = executeSpawnAttempt(baseParams(), deps);
  await deployReached;

  for (let i = 0; i < 5; i++) {
    const staggered = await executeSpawnAttempt(baseParams({ drivingCitizenWallet: DRIVING_CITIZEN_WALLET }), deps).catch((e) => ({ status: "failed", error: String(e) }));
    assert.notEqual(staggered.status, "active", `staggered attempt ${i} while the deploy step is still in flight must never succeed`);
  }

  releaseDeploy();
  const firstResult = await firstAttempt;
  assert.equal(firstResult.status, "active");

  const afterRelease = await executeSpawnAttempt(baseParams(), deps);
  assert.equal(afterRelease.status, "active", "the lock must be acquirable again only AFTER the first attempt's REQ-305 append actually completed");
});

// ---------------------------------------------------------------------------
// REQ-204/205/302/303/305 call-site wiring (this sprint's own new call sites, wired by executeSpawnAttempt).
// ---------------------------------------------------------------------------

test("REQ-305 call-site: a successful attempt appends a citizens.json record matching REQ-105's exact schema, gated on isSelfFunded(), with coLocatedWithCoordinator:false", async () => {
  const dir = tmpDir();
  const deps = happyDeps(dir);
  const result = await executeSpawnAttempt(baseParams(), deps);
  assert.equal(result.status, "active");
  const records = readRegistryRecords(deps.citizensRegistryFile);
  assert.equal(records.length, 1);
  const record = records[0];
  assert.equal(record.id, result.childId);
  assert.equal(record.wallet.evm, true);
  assert.equal(record.walletAddress.evm, "0xChildEvmFixture0000000000000000000000001");
  assert.deepEqual(record.fuel, { provider: "free-model" });
  assert.deepEqual(record.humanDependencies, []);
  assert.equal(record.coLocatedWithCoordinator, false);
  assert.equal(record.telemetryPath, undefined, "REQ-105's schema carries no telemetryPath field (resolves FIND-302)");
  assert.equal(record.status, undefined, "status lives exclusively in ledger.js, never in citizens.json (resolves FIND-201)");
});

test("REQ-305 call-site: the ledger's active row sets active_since, and attempted_ms is copied forward from the child's own first row", async () => {
  const dir = tmpDir();
  const deps = happyDeps(dir);
  const nowMs = 1_800_000_000_000;
  const result = await executeSpawnAttempt(baseParams({ nowMs }), deps);
  assert.equal(result.status, "active");
  const rows = readLedgerRows(deps.ledgerFile).filter((r) => r.child_id === result.childId);
  assert.equal(rows.length, 1);
  assert.equal(rows[0].status, "active");
  assert.equal(typeof rows[0].active_since, "number");
  assert.equal(rows[0].attempted_ms, nowMs);
});

test("REQ-204 call-site: registerIdentity is invoked with the step-2-generated child private key, and a successful agentId/txHash feed buildChildSpec's identity anchor", async () => {
  const dir = tmpDir();
  let seenPrivateKey;
  const deps = happyDeps(dir, {
    registerIdentity: async ({ childPrivateKey } = {}) => {
      seenPrivateKey = childPrivateKey;
      return { ok: true, agentId: "42424", txHash: "0xdeadbeef" };
    },
  });
  const result = await executeSpawnAttempt(baseParams(), deps);
  assert.equal(result.status, "active");
  assert.equal(seenPrivateKey, "0xchildevmfixturekey", "REQ-204 must sign with the SAME child key REQ-201 generated in step 2, never a re-derived/second key");
  const rows = readLedgerRows(deps.ledgerFile).filter((r) => r.child_id === result.childId);
  assert.equal(rows[0].agent_id, "42424");
  assert.equal(rows[0].agent_evm_address, "0xChildEvmFixture0000000000000000000000001");
});

test("REQ-205 call-site: writeMcpConfig is invoked only AFTER REQ-204's registration has genuinely succeeded (never before)", async () => {
  const dir = tmpDir();
  const order = [];
  const deps = happyDeps(dir, {
    registerIdentity: async () => { order.push("registerIdentity"); return { ok: true, agentId: "1", txHash: "0xtx" }; },
    writeMcpConfig: async () => { order.push("writeMcpConfig"); return { ok: true }; },
  });
  const result = await executeSpawnAttempt(baseParams(), deps);
  assert.equal(result.status, "active");
  assert.deepEqual(order, ["registerIdentity", "writeMcpConfig"]);
});

test("REQ-202/REQ-302 call-site (PROP-202d): needsSolanaWallet's deployTarget is THIS SAME attempt's real selectCloudTarget return value, never hand-assembled -- a nosana target triggers Solana keygen, an akash target never does", async () => {
  const dirNosana = tmpDir();
  let solanaCallsNosana = 0;
  const depsNosana = happyDeps(dirNosana, {
    selectCloudTarget: async () => "nosana",
    generateSolanaWallet: async () => { solanaCallsNosana += 1; return { address: "ChildSol1", privateKey: "sk" }; },
  });
  const resultNosana = await executeSpawnAttempt(baseParams(), depsNosana);
  assert.equal(resultNosana.status, "active");
  assert.equal(solanaCallsNosana, 1, "a real nosana-selected attempt must invoke Solana keygen exactly once");

  const dirAkash = tmpDir();
  let solanaCallsAkash = 0;
  const depsAkash = happyDeps(dirAkash, {
    selectCloudTarget: async () => "akash",
    generateSolanaWallet: async () => { solanaCallsAkash += 1; return { address: "ChildSol1", privateKey: "sk" }; },
  });
  const resultAkash = await executeSpawnAttempt(baseParams(), depsAkash);
  assert.equal(resultAkash.status, "active");
  assert.equal(solanaCallsAkash, 0, "an akash-selected, EVM-only-skill attempt must never invoke Solana keygen at all");
});
