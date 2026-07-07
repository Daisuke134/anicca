// REQ-307: the spawn attempt's single entry-point function. Pure sequencing and error propagation
// over the already-specified REQ-201-206/301-306 building blocks -- this module makes zero
// eligibility/threshold decisions of its own (that decision is made entirely by this function's own
// caller, before it is ever invoked).
import fs from "node:fs";
import { promises as fsp } from "node:fs";
import path from "node:path";
import os from "node:os";
import crypto from "node:crypto";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

import { withGigLock } from "../../../economy/gig/lib/lock.mjs";
import { ensureAgentId } from "../../../economy/gig/lib/ensure-agent-id.mjs";
import { isSelfFunded, selfFundedReasons } from "../../../_shared/lib/is-self-funded.mjs";
import { CITIZENS_REGISTRY_PATH } from "./registry-path.mjs";
import { resolveStateDir } from "./state-path.js";
import { readChildren, appendChild } from "./ledger.js";
import { nextChildId, buildChildSpec } from "./child-spec.js";
import { needsSolanaWallet } from "./needs-solana-wallet.mjs";
import { selectCloudTarget as selectCloudTargetPure } from "./cloud-target.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const GENESIS_PATH = path.join(__dirname, "..", "..", "..", "..", "identity", "genesis.md");
const GEN_WALLET_SCRIPT = path.join(__dirname, "..", "scripts", "gen-wallet.sh");
const GEN_SOLANA_WALLET_SCRIPT = path.join(__dirname, "..", "scripts", "gen-solana-wallet.sh");
const DEPLOY_AKASH_SCRIPT = path.join(__dirname, "..", "scripts", "deploy-akash.sh");

// REQ-206: fixed at 1 for every child this feature produces -- colony-treasury-funded spawns are,
// by design, top-level, non-lineage children (spawn chaining is out of scope this increment).
const GENERATION = 1;
// REQ-401: the exclusive $0-bootstrap fuel provider every child this feature produces carries.
const FUEL_PROVIDER = "free-model";

function constitutionHash() {
  return crypto.createHash("sha256").update(fs.readFileSync(GENESIS_PATH)).digest("hex");
}

// REQ-206: identical to REQ-204's actual gas-seed transfer amount, never a second, independently
// derived quantity -- reuses the SAME env-override convention this codebase's own existing
// gas-seed-transfer call site already uses.
function seedUsdcAmount() {
  return Number(process.env.ANICCA_SEED_USDC || 1);
}

function defaultLedgerFile() {
  return path.join(resolveStateDir({}), "children.jsonl");
}

function errorMessage(e) {
  return (e && e.message) || String(e);
}

function appendMinimalFailure(ledgerFile, { childId, attemptedMs, error }) {
  appendChild(ledgerFile, { child_id: childId, status: "failed", attempted_ms: attemptedMs, error: errorMessage(error) });
}

function appendSpecFailure(ledgerFile, spec, { attemptedMs, error }) {
  appendChild(ledgerFile, { ...spec, status: "failed", attempted_ms: attemptedMs, error: errorMessage(error) });
}

// Every REQ-201/202/203/204/205/306/302/303 call site below shares the exact same shape: run a
// deps-or-default effectful step, and on either a thrown error OR (for the "ok"-shaped results)
// result.ok === false, record a failure row and signal the caller to return early. This helper is
// the single place that shape lives; `onFailure` lets step 7 (REQ-205) redirect the failure row to
// appendSpecFailure's buildChildSpec-based shape instead of the default minimal one, without
// duplicating the try/catch/requireOk logic itself.
async function runStep({ ledgerFile, childId, nowMs, run, requireOk = false, defaultErrorMessage, onFailure }) {
  const recordFailure = onFailure || ((error) => appendMinimalFailure(ledgerFile, { childId, attemptedMs: nowMs, error }));
  let result;
  try {
    result = await run();
  } catch (e) {
    const error = errorMessage(e);
    recordFailure(error);
    return { failed: true, error };
  }
  if (requireOk && (!result || !result.ok)) {
    const error = (result && result.error) || defaultErrorMessage;
    recordFailure(error);
    return { failed: true, error };
  }
  return { failed: false, value: result };
}

async function appendCitizenRecord(citizensRegistryFile, record) {
  let records = [];
  try {
    records = JSON.parse(await fsp.readFile(citizensRegistryFile, "utf8"));
  } catch (e) {
    if (e.code !== "ENOENT") throw e;
  }
  records.push(record);
  await fsp.mkdir(path.dirname(citizensRegistryFile), { recursive: true });
  await fsp.writeFile(citizensRegistryFile, JSON.stringify(records, null, 2));
}

// --- Production default wiring (used only when a caller omits the corresponding `deps` override). ---

async function defaultCheckHomeDistinct({ childId, citizensRegistryFile }) {
  const homeDir = path.join(os.homedir(), ".anicca-children", childId);
  let citizens = [];
  try {
    citizens = JSON.parse(fs.readFileSync(citizensRegistryFile, "utf8"));
  } catch {
    // no registry yet -- nothing to collide with
  }
  const collides = citizens.some(
    (c) =>
      c &&
      typeof c.homeDir === "string" &&
      (c.homeDir === homeDir || homeDir.startsWith(c.homeDir + path.sep) || c.homeDir.startsWith(homeDir + path.sep))
  );
  if (collides) return { ok: false, error: `home collides with an existing citizen: ${homeDir}` };
  return { ok: true, homeDir };
}

function defaultGenerateEvmWallet() {
  const out = execFileSync("bash", [GEN_WALLET_SCRIPT], { encoding: "utf8" });
  const { address, private_key: privateKey } = JSON.parse(out);
  return { address, privateKey };
}

function defaultGenerateSolanaWallet() {
  const out = execFileSync("bash", [GEN_SOLANA_WALLET_SCRIPT], { encoding: "utf8" });
  const { address, private_key: privateKey } = JSON.parse(out);
  return { address, privateKey };
}

// Honest limitation (mirrors this spec's own established honesty precedent for genuinely-missing
// infra): no live NOS/AKT spot-price feed and no Nosana deploy path exist anywhere in this codebase
// yet -- deploy-akash.sh is the only proven cloud-deploy path today, so it is the only target this
// default ever selects, never a fabricated price comparison against a target this repo cannot
// actually deploy to. selectCloudTargetPure's own deterministic rule still governs the decision.
async function defaultSelectCloudTarget() {
  return selectCloudTargetPure({ nosanaAvailable: false, akashAvailable: true, akashPriceUsd: 0 });
}

function defaultDeploy({ target, childId }) {
  if (target !== "akash") {
    return { ok: false, error: `no deploy path implemented for cloud target "${target}"` };
  }
  let leaseId;
  try {
    leaseId = execFileSync("bash", [DEPLOY_AKASH_SCRIPT, childId], { encoding: "utf8" }).trim();
  } catch (e) {
    return { ok: false, error: `deploy-akash.sh failed: ${errorMessage(e)}` };
  }
  if (!leaseId) return { ok: false, error: "deploy-akash.sh produced no lease id" };
  return { ok: true, leaseId, shelterCostUsd: null };
}

async function defaultRegisterIdentity({ childPrivateKey, childHomeDir }) {
  const cacheFile = path.join(childHomeDir, ".automaton", "gig-agent-id.json");
  const result = await ensureAgentId({ privateKey: childPrivateKey, cacheFile });
  if (!result.ok) return { ok: false, error: result.reason };
  return { ok: true, agentId: result.agentId };
}

function defaultWriteMcpConfig({ childHomeDir }) {
  const gigStatePath = path.join(childHomeDir, ".anicca-signing", "gig-board", "state", "gigs.json");
  const mcpConfig = {
    mcpServers: {
      "anicca-gig": {
        transport: "stdio",
        command: process.execPath,
        args: [path.join(childHomeDir, "skills", "economy", "gig", "mcp-server.mjs")],
        env: {
          GIG_FACILITATOR_URL: process.env.GIG_FACILITATOR_URL || "http://127.0.0.1:8407",
          GIG_STATE_PATH: gigStatePath,
          GIG_CHAIN: process.env.GIG_CHAIN || "base",
        },
      },
    },
  };
  const mcpPath = path.join(childHomeDir, "mcp.json");
  fs.mkdirSync(path.dirname(mcpPath), { recursive: true });
  fs.writeFileSync(mcpPath, JSON.stringify(mcpConfig, null, 2));
  return { ok: true };
}

/**
 * executeSpawnAttempt -- the single call-graph root for a spawn attempt, run under the "colony-spawn"
 * lock for its entire duration. `deps` is a test/production wiring seam for the 7 genuinely effectful
 * steps this sprint newly wires; omitting it wires the real scripts/modules above directly.
 *
 * @returns {Promise<{status: "active"|"failed", childId: string|null, error?: string}>}
 */
export async function executeSpawnAttempt({ initialSkills = [], drivingCitizenWallet, nowMs = Date.now() } = {}, deps = {}) {
  const lockStatePath = deps.lockStatePath || CITIZENS_REGISTRY_PATH;
  const ledgerFile = deps.ledgerFile || defaultLedgerFile();
  const citizensRegistryFile = deps.citizensRegistryFile || CITIZENS_REGISTRY_PATH;

  const runAttempt = async () => {
    const childId = nextChildId(readChildren(ledgerFile), "anicca-c");

    // Step 1 (REQ-203): HOME/ANICCA_HOME distinctness, before any key generation.
    const homeStep = await runStep({
      ledgerFile,
      childId,
      nowMs,
      run: () =>
        deps.checkHomeDistinct
          ? deps.checkHomeDistinct({ childId, citizensRegistryFile })
          : defaultCheckHomeDistinct({ childId, citizensRegistryFile }),
      requireOk: true,
      defaultErrorMessage: "home distinctness check failed",
    });
    if (homeStep.failed) return { status: "failed", childId, error: homeStep.error };
    const homeDir = homeStep.value.homeDir;

    // Step 2 (REQ-201): child EVM wallet generation.
    const evmStep = await runStep({
      ledgerFile,
      childId,
      nowMs,
      run: () => (deps.generateEvmWallet ? deps.generateEvmWallet() : defaultGenerateEvmWallet()),
    });
    if (evmStep.failed) return { status: "failed", childId, error: evmStep.error };
    const evmWallet = evmStep.value;

    // Step 3 (REQ-306): a fresh cloud-target selection for THIS attempt.
    const cloudStep = await runStep({
      ledgerFile,
      childId,
      nowMs,
      run: () => (deps.selectCloudTarget ? deps.selectCloudTarget() : defaultSelectCloudTarget()),
    });
    if (cloudStep.failed) return { status: "failed", childId, error: cloudStep.error };
    const cloudTarget = cloudStep.value;
    if (cloudTarget === "none") {
      const error = "no cloud target available (neither nosana nor akash)";
      appendMinimalFailure(ledgerFile, { childId, attemptedMs: nowMs, error });
      return { status: "failed", childId, error };
    }

    // Step 4 (REQ-202): conditional Solana wallet generation, fed step 3's own return value directly.
    let solanaWallet = null;
    if (needsSolanaWallet({ initialSkills, deployTarget: cloudTarget })) {
      const solanaStep = await runStep({
        ledgerFile,
        childId,
        nowMs,
        run: () => (deps.generateSolanaWallet ? deps.generateSolanaWallet() : defaultGenerateSolanaWallet()),
      });
      if (solanaStep.failed) return { status: "failed", childId, error: solanaStep.error };
      solanaWallet = solanaStep.value;
    }

    // Step 5 (REQ-302/303): deploy, selected by step 3's own return value.
    const deployStep = await runStep({
      ledgerFile,
      childId,
      nowMs,
      run: () =>
        deps.deploy
          ? deps.deploy({ target: cloudTarget, childId, childWallet: evmWallet.address })
          : defaultDeploy({ target: cloudTarget, childId }),
      requireOk: true,
      defaultErrorMessage: "deploy failed",
    });
    if (deployStep.failed) return { status: "failed", childId, error: deployStep.error };

    // Step 6 (REQ-204): ERC-8004 registration -- the second half of the identity anchor.
    const identityStep = await runStep({
      ledgerFile,
      childId,
      nowMs,
      run: () =>
        deps.registerIdentity
          ? deps.registerIdentity({ childPrivateKey: evmWallet.privateKey })
          : defaultRegisterIdentity({ childPrivateKey: evmWallet.privateKey, childHomeDir: homeDir }),
      requireOk: true,
      defaultErrorMessage: "identity registration failed",
    });
    if (identityStep.failed) return { status: "failed", childId, error: identityStep.error };
    const identityResult = identityStep.value;

    // The identity anchor is now complete -- every failure from here on uses the buildChildSpec-based
    // recording path (REQ-305), never the minimal direct-append row above.
    let spec;
    try {
      spec = buildChildSpec({
        childId,
        parentWallet: drivingCitizenWallet,
        childWallet: evmWallet.address,
        generation: GENERATION,
        seedUsdc: seedUsdcAmount(),
        constitutionHash: constitutionHash(),
        agentEvmAddress: evmWallet.address,
        agentId: identityResult.agentId,
      });
    } catch (e) {
      // buildChildSpec's own real, untouched assertion fired -- the identity anchor is complete, so
      // this is recorded via a buildChildSpec-shaped row even though buildChildSpec itself never
      // returned one.
      appendChild(ledgerFile, {
        child_id: childId,
        wallet: evmWallet.address,
        parent_wallet: drivingCitizenWallet,
        generation: GENERATION,
        agent_evm_address: evmWallet.address,
        agent_id: identityResult.agentId,
        status: "failed",
        attempted_ms: nowMs,
        error: errorMessage(e),
      });
      return { status: "failed", childId, error: errorMessage(e) };
    }

    // Step 7 (REQ-205): mcp.json write. The identity anchor is already complete here, so a failure
    // is recorded via appendSpecFailure's buildChildSpec-shaped row, never the minimal one above.
    const mcpStep = await runStep({
      ledgerFile,
      childId,
      nowMs,
      run: () => (deps.writeMcpConfig ? deps.writeMcpConfig() : defaultWriteMcpConfig({ childHomeDir: homeDir, childId })),
      requireOk: true,
      defaultErrorMessage: "mcp.json write failed",
      onFailure: (error) => appendSpecFailure(ledgerFile, spec, { attemptedMs: nowMs, error }),
    });
    if (mcpStep.failed) return { status: "failed", childId, error: mcpStep.error };

    // Step 9 (REQ-305): ledger append (the "active" row) + citizen-registry append, gated on
    // isSelfFunded(). A failure here (e.g. the ledger file itself cannot be written) is allowed to
    // propagate -- there is no lower-tier ledger left to record it in.
    appendChild(ledgerFile, { ...spec, status: "active", attempted_ms: nowMs, active_since: nowMs });

    const citizenRecord = {
      id: childId,
      wallet: { evm: true, ...(solanaWallet ? { solana: true } : {}) },
      walletAddress: { evm: evmWallet.address, ...(solanaWallet ? { solana: solanaWallet.address } : {}) },
      fuel: { provider: FUEL_PROVIDER },
      humanDependencies: [],
      homeDir,
      coLocatedWithCoordinator: false,
    };
    if (isSelfFunded(citizenRecord)) {
      await appendCitizenRecord(citizensRegistryFile, citizenRecord);
    } else {
      console.error(
        `self/spawn: refusing citizens.json append for ${childId} -- fails isSelfFunded(): ${selfFundedReasons(citizenRecord).join(",")}`
      );
    }

    return { status: "active", childId };
  };

  const lockResult = await withGigLock(lockStatePath, "colony-spawn", runAttempt);
  if (lockResult && Object.prototype.hasOwnProperty.call(lockResult, "status")) {
    return lockResult;
  }
  // withGigLock's own lock-rejection shape ({ok:false, reason}) -- never itself a status:"active" claim.
  return { status: "failed", childId: null, error: (lockResult && lockResult.reason) || "lock not acquired" };
}
