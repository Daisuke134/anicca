#!/usr/bin/env node
// economy/lending/scripts/wake-gate.mjs — the autonomous daemon-wake entry point (REQ-117,
// anicca-agent-lending sprint-3). Makes REQ-115's executeLoanIssuanceAttempt and REQ-116's
// executeDefaultDetectionSweep genuinely REACHABLE from a real daemon wake, mirroring the self/spawn
// sibling skill's own already-proven run.sh + wake-gate pair shape (see behavioral-spec.md REQ-117 for
// the full canonical-order derivation). This module contains NO eligibility/sizing/default-detection
// arithmetic of its own — every decision is a plain, already-computed boolean/number combined via a
// single `&&`/`>`, delegated entirely to lending-gate.mjs's/lending-orchestrator.mjs's own
// already-hardened functions (mirrors REQ-103's bookkeeping-only discipline).
//
// export async function runWakeGate({argv, env, deps}) — the test/production wiring seam (mirrors the
// self/spawn sibling's own identical convention): omitting any `deps` key wires the real production
// implementation. See wake-gate.test.mjs's own header for the full `deps` seam list.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  computeLenderAvailableUsd,
  sumOutstandingPrincipalUsd,
  sumRecentGojoGiftsUsd,
  isBorrowerEligible,
} from "../lib/lending-gate.mjs";
import { executeLoanIssuanceAttempt, executeDefaultDetectionSweep } from "../lib/lending-orchestrator.mjs";
import { LOANS_LEDGER_PATH } from "../lib/lending-path.mjs";
import { readGojoLogRows } from "../lib/gojo-read.mjs";
import { isSelfFunded } from "../../../_shared/lib/is-self-funded.mjs";
import { usdcBalance } from "../../../_shared/lib/usdc.mjs";
import { readChildren } from "../../../self/spawn/lib/ledger.js";
import { CITIZENS_REGISTRY_PATH } from "../../../self/spawn/lib/registry-path.mjs";
import { ensureCitizensRegistry as ensureCitizensRegistryReal } from "../../../self/spawn/lib/citizens-registry.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// economy/ubi/run.sh's own already-established gojo-log.jsonl location (REQ-101, reused unmodified) —
// never a second, competing gojo-log path.
const DEFAULT_GOJO_LOG_PATH = path.join(__dirname, "..", "..", "ubi", "state", "gojo-log.jsonl");

function readCitizensRegistry(registryPath) {
  return JSON.parse(fs.readFileSync(registryPath, "utf8"));
}

// Step 4's own structural filter — isSelfFunded (REQ-111) AND wallet.evm===true (REQ-107) AND
// coLocatedWithCoordinator===true (REQ-112). No balance/arithmetic check belongs here.
function isCandidateCitizen(citizen) {
  if (!citizen || typeof citizen !== "object") return false;
  if (!isSelfFunded(citizen)) return false;
  if (!citizen.wallet || citizen.wallet.evm !== true) return false;
  return citizen.coLocatedWithCoordinator === true;
}

// The production getCitizen(id) closure (step 6's own "fresh read, never a snapshot" discipline,
// extended here to step 4/5's own balance gathering too): re-reads the registry fresh on EVERY call,
// merging a fresh balanceUsd on top of the REAL, full registry record — never a hand-enumerated shape
// (FIND-1004/1006's own defect class).
function buildDefaultGetCitizen({ citizensRegistryFile, fetchImpl }) {
  return async (id) => {
    const citizens = readCitizensRegistry(citizensRegistryFile);
    const citizen = citizens.find((c) => c && c.id === id);
    if (!citizen) return null;
    const balanceUsd = await usdcBalance(citizen.walletAddress.evm, { fetchImpl });
    return { ...citizen, balanceUsd };
  };
}

// Step 5's own deterministic pair enumeration — registry order, lender outer loop / borrower inner
// loop, lenderId!==borrowerId — selecting the FIRST pair where BOTH already-computed, independent
// outputs hold. Combines them via a single, plain `&&`; never re-derives either function's own
// arithmetic.
function findSelectedPair({ candidateIds, citizensById, loanRows, gojoLogRows, nowMs }) {
  for (const lenderId of candidateIds) {
    for (const borrowerId of candidateIds) {
      if (lenderId === borrowerId) continue;
      const lender = citizensById.get(lenderId);
      const borrower = citizensById.get(borrowerId);
      const lenderAvailableUsd = computeLenderAvailableUsd({
        lenderBalanceUsd: lender && lender.balanceUsd,
        outstandingPrincipalUsd: sumOutstandingPrincipalUsd(loanRows, lenderId),
        recentGojoGiftsUsd: sumRecentGojoGiftsUsd(gojoLogRows, nowMs, 24, lenderId),
      });
      const borrowerEligibility = isBorrowerEligible({
        borrowerAgent: borrower,
        loanRows,
        borrowerId,
        borrowerBalanceUsd: borrower && borrower.balanceUsd,
        lenderId,
      });
      if (lenderAvailableUsd > 0 && borrowerEligibility.eligible === true) {
        return { lenderId, borrowerId };
      }
    }
  }
  return null;
}

export async function runWakeGate({ argv = [], env = process.env, deps = {} } = {}) {
  const nowMs = deps.nowMs ?? Date.now();

  // Step 1.
  const citizensRegistryFile = deps.citizensRegistryFile || CITIZENS_REGISTRY_PATH;
  const ensureCitizensRegistry = deps.ensureCitizensRegistry || ensureCitizensRegistryReal;
  await ensureCitizensRegistry({ registryPath: citizensRegistryFile });
  const citizens = readCitizensRegistry(citizensRegistryFile);

  // Step 2. deps.ledgerFile is threaded through into BOTH this read AND executeLoanIssuanceAttempt's/
  // executeDefaultDetectionSweep's own internal ledgerFile/lockStatePath below (step 6/7) — never a
  // second, parallel ledger, never the real production LOANS_LEDGER_PATH substituted for a test's own
  // tmp ledger.
  const ledgerFile = deps.ledgerFile || LOANS_LEDGER_PATH;
  const loanRows = readChildren(ledgerFile);

  // Step 3.
  const gojoLogFile = deps.gojoLogFile || DEFAULT_GOJO_LOG_PATH;
  const gojoLogRows = readGojoLogRows(gojoLogFile);

  // Step 4. deps.getCitizen, when supplied, fully replaces the internal closure below — for both this
  // step's own candidate/balance gathering AND step 6's own executeLoanIssuanceAttempt wiring.
  const getCitizen =
    deps.getCitizen || buildDefaultGetCitizen({ citizensRegistryFile, fetchImpl: deps.fetchImpl });
  const candidateIds = citizens.filter(isCandidateCitizen).map((c) => c.id);
  const citizensById = new Map();
  for (const id of candidateIds) {
    citizensById.set(id, await getCitizen(id));
  }

  // Step 5.
  const selectedPair = findSelectedPair({ candidateIds, citizensById, loanRows, gojoLogRows, nowMs });

  // Step 6: at most one new issuance attempt per wake, never a second candidate pair retried within
  // the same invocation.
  let issuance = null;
  if (selectedPair) {
    issuance = await executeLoanIssuanceAttempt(
      { lenderId: selectedPair.lenderId, borrowerId: selectedPair.borrowerId, nowMs },
      {
        ledgerFile,
        lockStatePath: ledgerFile,
        getCitizen,
        gojoLogRows,
        reconcile: deps.reconcile,
        disburse: deps.disburse,
      }
    );
  }

  // Step 7 (unconditional, regardless of steps 5/6's own outcome). Step 8: executeRepaymentClaim is
  // deliberately never invoked from this entry point (REQ-117's own documented scope exclusion — no
  // external repayment-claim channel exists yet).
  const sweep = await executeDefaultDetectionSweep({ nowMs }, { ledgerFile, lockStatePath: ledgerFile });

  // Step 9.
  return { candidatesConsidered: candidateIds.length, selectedPair, issuance, sweep };
}

// CLI entrypoint: `node wake-gate.mjs`. Prints the decision object as JSON to stdout. Exit 0 for a
// clean no-op or a completed/refused issuance attempt plus a completed sweep; exit 1 only for a
// genuine, unexpected in-process error (an uncaught exception escaping this script's own top-level
// .catch) — a routine per-pair refusal from executeLoanIssuanceAttempt deliberately stays exit 0, a
// documented divergence from the self/spawn sibling's own CLI convention (see behavioral-spec.md
// REQ-117 step 9's own correction for the full reasoning: treating an ordinary "no eligible pair this
// wake" outcome as a failure would make it indistinguishable from a genuine daemon error to any
// exit-code-watching monitor).
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  runWakeGate({ argv: process.argv.slice(2), env: process.env })
    .then((result) => {
      console.log(JSON.stringify(result));
    })
    .catch((e) => {
      console.error(`wake-gate: fatal: ${(e && e.message) || e}`);
      process.exitCode = 1;
    });
}
