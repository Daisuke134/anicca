#!/usr/bin/env node
// REQ-307's own "wake-cycle scheduler's real identity" correction (sprint-2, contract-review round 2,
// resolves FIND-004): the real body __REPO_ROOT__/skills/self/spawn/run.sh's production wrapper invokes on
// every wake. Reads real, freshly-computed colony state and calls decideColonySpawn() (REQ-102,
// ../lib/treasury-gate.mjs) then, only if eligible:true, calls executeSpawnAttempt() (REQ-307,
// ../lib/spawn-orchestrator.mjs) -- replacing run.sh's OLD lib/spawn-decision.js-based gate and
// DigitalOcean+AgentMail provisioning path entirely (PROP-307e). This module contains NO
// decision/judgment logic of its own beyond calling these two already-specified functions with their
// real inputs -- mirrors REQ-104/REQ-307's own bookkeeping-only discipline.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { privateKeyToAccount } from "viem/accounts";
import { createPublicClient, http } from "viem";
import { base } from "viem/chains";
import bs58 from "bs58";

import { resolveEvmPrivateKey, resolveSolanaSecret } from "../../../earn/lib/resolve-identity.mjs";
import {
  filterProductiveCitizens,
  computeColonySurplusUsd,
  deriveRecentSpawnAttempts,
  countChildrenProvisioning,
  deriveMeasuredShelterCostUsd,
  decideColonySpawn as decideColonySpawnPure,
  dedupCitizensById,
} from "../lib/treasury-gate.mjs";
import { readCitizenBalances } from "../lib/colony-balances.mjs";
import { ensureCitizensRegistry as ensureCitizensRegistryReal, CITIZENS_SEED_PATH } from "../lib/citizens-registry.mjs";
import { CITIZENS_REGISTRY_PATH } from "../lib/registry-path.mjs";
import { resolveStateDir } from "../lib/state-path.js";
import { readChildren } from "../lib/ledger.js";
import { readShelterCostEntries } from "../lib/shelter-cost-ledger.js";
import {
  executeSpawnAttempt as executeSpawnAttemptReal,
  retryPendingRegistryAppends as retryPendingRegistryAppendsReal,
} from "../lib/spawn-orchestrator.mjs";

// REQ-102's own stated defaults (behavioral-spec.md REQ-102): perCitizenReserveUsd=5.00,
// MIN_SHELTER_USD=5.00, SAFETY_MARGIN_MULTIPLIER=2 -- never independently re-invented here.
const PER_CITIZEN_RESERVE_USD_DEFAULT = 5.0;
const MIN_SHELTER_USD_DEFAULT = 5.0;
const SAFETY_MARGIN_MULTIPLIER_DEFAULT = 2;
const USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
const SOL_USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v";
const ERC20_BALANCE_OF_ABI = [
  { name: "balanceOf", type: "function", stateMutability: "view", inputs: [{ type: "address" }], outputs: [{ type: "uint256" }] },
];

function parseInitialSkills(argv, env) {
  const flag = argv.find((a) => a.startsWith("--skills="));
  const raw = flag ? flag.slice("--skills=".length) : env.ANICCA_CHILD_INITIAL_SKILLS || "";
  return raw.split(",").map((s) => s.trim()).filter(Boolean);
}

// REQ-307's own caller identity: whichever citizen's ANICCA_HOME this wake is running as, resolved via
// the SAME per-instance resolvers (resolveEvmPrivateKey/resolveSolanaSecret) telemetry-poster.mjs/
// telemetry-post-franklin.mjs already use for the identical "which citizen is this process" question --
// never a re-derived/independent identity mechanism. Returns null (fail-closed) if neither resolves.
async function defaultResolveDrivingCitizen(env) {
  const evmKey = resolveEvmPrivateKey({ env });
  if (evmKey) return { wallet: privateKeyToAccount(evmKey).address, chain: "evm" };
  const solKey = resolveSolanaSecret({ env });
  if (solKey) {
    const secretKey = bs58.decode(solKey);
    return { wallet: bs58.encode(Buffer.from(secretKey.slice(32))), chain: "solana" };
  }
  return null;
}

async function solanaRpc(method, params) {
  const r = await fetch("https://api.mainnet-beta.solana.com", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }),
  });
  return (await r.json()).result;
}

// Real Base USDC balance -- the SAME balanceOf mechanism telemetry-poster.mjs/usdc-balance.py already
// prove, generalized to any address rather than one hardcoded wallet (REQ-101's own colony-balances.mjs
// registry-driven design).
async function defaultFetchEvmBalanceUsd(address) {
  const pub = createPublicClient({ chain: base, transport: http("https://base-rpc.publicnode.com") });
  const bal = await pub.readContract({ address: USDC_BASE, abi: ERC20_BALANCE_OF_ABI, functionName: "balanceOf", args: [address] });
  return Number(bal) / 1e6;
}

// Real Solana SOL+USDC balance, priced in USD -- the SAME mechanism telemetry-post-franklin.mjs already
// proves (solBalance/usdcBalance/solPrice), generalized to any address.
async function defaultFetchSolanaBalanceUsd(address) {
  const [balResult, tokenResult, priceResult] = await Promise.all([
    solanaRpc("getBalance", [address]).catch(() => null),
    solanaRpc("getTokenAccountsByOwner", [address, { mint: SOL_USDC_MINT }, { encoding: "jsonParsed" }]).catch(() => null),
    fetch("https://api.coinbase.com/v2/prices/SOL-USD/spot").then((r) => r.json()).catch(() => null),
  ]);
  const sol = (balResult?.value || 0) / 1e9;
  const usdc = (tokenResult?.value || []).reduce(
    (s, a) => s + (Number(a.account?.data?.parsed?.info?.tokenAmount?.uiAmount) || 0),
    0
  );
  const price = Number(priceResult?.data?.amount) || 0;
  return usdc + sol * price;
}

/**
 * runWakeGate -- REQ-307's own caller. `deps` is a test/production wiring seam (mirrors
 * spawn-orchestrator.mjs's own executeSpawnAttempt `deps` convention): omitting any key wires the
 * real production implementation directly. Returns `{decision, result}` -- `result` is null whenever
 * no spawn attempt was ever started (dry-run, or genuinely not eligible this wake).
 */
export async function runWakeGate({ argv = [], env = process.env, deps = {} } = {}) {
  const dryRun = argv.includes("--dry-run");
  const initialSkills = parseInitialSkills(argv, env);
  const nowMs = deps.nowMs ?? Date.now();

  // --dry-run is genuinely zero-side-effect: it never bootstraps citizens.json (a real filesystem
  // write via ensureCitizensRegistry's own atomic exclusive-create) -- it reads the durable registry
  // if it already exists, else falls back to a READ-ONLY preview of citizens.seed.json. A real
  // (non-dry-run) invocation still bootstraps the durable registry exactly as before.
  const registryPath = deps.registryPath || CITIZENS_REGISTRY_PATH;
  let citizens;
  if (dryRun) {
    try {
      citizens = JSON.parse(fs.readFileSync(registryPath, "utf8"));
    } catch {
      const seedPath = deps.citizensSeedPath || CITIZENS_SEED_PATH;
      citizens = JSON.parse(fs.readFileSync(seedPath, "utf8"));
    }
  } else {
    const ensureCitizensRegistry = deps.ensureCitizensRegistry || ensureCitizensRegistryReal;
    await ensureCitizensRegistry({ registryPath });
    citizens = JSON.parse(fs.readFileSync(registryPath, "utf8"));
  }
  // Money-safety backstop (Phase-5 finding): citizens.json is the untrusted, durable file a crash-window
  // retry re-drive could have double-appended into (see appendCitizenRecord's own idempotency-by-id fix,
  // spawn-orchestrator.mjs) -- dedup by id here, BEFORE any surplus computation, so a duplicate entry (from
  // any cause) can never double-count into colonySurplusUsd, a real-money spawn-eligibility input.
  citizens = dedupCitizensById(citizens);

  const ledgerFile = deps.ledgerFile || path.join(resolveStateDir({}), "children.jsonl");
  const readLedgerRows = deps.readChildren || readChildren;
  const ledgerRows = readLedgerRows(ledgerFile);

  // REQ-305 edge case (FIND-003): retry any citizens.json append a PRIOR wake's executeSpawnAttempt
  // queued after a transient failure -- BEFORE any further spawn evaluation runs this wake. Skipped
  // under --dry-run, mirroring this same function's own "--dry-run is genuinely zero-side-effect" rule
  // above (a registry append is a real filesystem write, never performed during a dry-run preview).
  if (!dryRun) {
    const retryPendingRegistryAppends = deps.retryPendingRegistryAppends || retryPendingRegistryAppendsReal;
    await retryPendingRegistryAppends({ pendingRegistryAppendsFile: deps.pendingRegistryAppendsFile });
  }

  const perCitizenReserveUsd = Number(env.ANICCA_SPAWN_RESERVE_USD || PER_CITIZEN_RESERVE_USD_DEFAULT);
  const safetyMarginMultiplier = Number(env.ANICCA_SPAWN_SAFETY_MARGIN || SAFETY_MARGIN_MULTIPLIER_DEFAULT);

  const productiveCitizens = filterProductiveCitizens({ citizens, ledgerRows, nowMs });
  const fetchEvmBalanceUsd = deps.fetchEvmBalanceUsd || defaultFetchEvmBalanceUsd;
  const fetchSolanaBalanceUsd = deps.fetchSolanaBalanceUsd || defaultFetchSolanaBalanceUsd;
  const balances = await readCitizenBalances({ citizens: productiveCitizens, fetchEvmBalanceUsd, fetchSolanaBalanceUsd });
  const balancedCitizens = productiveCitizens.map((c) => {
    const match = balances.find((b) => b.citizenId === c.id);
    return { ...c, balanceUsd: match ? match.balanceUsd : 0 };
  });
  const colonySurplusUsd = computeColonySurplusUsd({ citizens: balancedCitizens, perCitizenReserveUsd });

  const shelterCostFile = deps.shelterCostFile || path.join(resolveStateDir({}), "shelter-cost.jsonl");
  const readShelterCosts = deps.readShelterCostEntries || readShelterCostEntries;
  const measuredShelterUsd = deriveMeasuredShelterCostUsd({ shelterCostLedgerRows: readShelterCosts(shelterCostFile) });
  const spawnThresholdUsd = (measuredShelterUsd ?? MIN_SHELTER_USD_DEFAULT) * safetyMarginMultiplier;

  const recentSpawnAttempts = deriveRecentSpawnAttempts({ ledgerRows });
  const childrenProvisioning = countChildrenProvisioning({ ledgerRows });

  const decideColonySpawn = deps.decideColonySpawn || decideColonySpawnPure;
  const decisionCore = decideColonySpawn({ colonySurplusUsd, spawnThresholdUsd, recentSpawnAttempts, nowMs, childrenProvisioning });
  const decision = { ...decisionCore, colonySurplusUsd, spawnThresholdUsd, childrenProvisioning };

  if (dryRun || !decisionCore.eligible) {
    return { decision, result: null };
  }

  const resolveDrivingCitizen = deps.resolveDrivingCitizen || defaultResolveDrivingCitizen;
  const driving = await resolveDrivingCitizen(env);
  if (!driving) {
    return {
      decision,
      result: { status: "failed", childId: null, error: "no resolvable per-instance identity (ANICCA_HOME/HOME) -- cannot determine drivingCitizenWallet" },
    };
  }

  const executeSpawnAttempt = deps.executeSpawnAttempt || executeSpawnAttemptReal;
  const result = await executeSpawnAttempt({ initialSkills, drivingCitizenWallet: driving.wallet, nowMs });
  return { decision: { ...decision, drivingCitizenWallet: driving.wallet }, result };
}

// CLI entrypoint: `node wake-gate.mjs [--dry-run] [--skills=a,b,c]`. Prints the decision JSON (and the
// spawn-attempt result JSON, if one ran) to stdout. exit 0 for dormant/dry-run, exit 1 only for a
// genuine spawn-attempt failure -- mirrors run.sh's own pre-existing exit-code convention.
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  runWakeGate({ argv: process.argv.slice(2), env: process.env })
    .then(({ decision, result }) => {
      console.log(JSON.stringify(decision));
      if (result) {
        console.log(JSON.stringify(result));
        if (result.status !== "active") process.exitCode = 1;
      }
    })
    .catch((e) => {
      console.error(`wake-gate: fatal: ${(e && e.message) || e}`);
      process.exitCode = 1;
    });
}
