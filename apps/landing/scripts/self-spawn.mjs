#!/usr/bin/env node
// self-spawn runner (spec27b A-self-spawn). Births a REAL child Anicca:
//   distinct wallet -> own AgentMail inbox -> DO droplet (or akash) -> children.jsonl
//   -> child signs+POSTs its first telemetry to the LIVE endpoint (appears on dashboard).
//
// NO FAKE RUN (HARD 0.24): success is printed ONLY after a real provider id + a parent-distinct child
// wallet + a real inbox + a 202 from the live telemetry endpoint all exist. Any failed step exits != 0.
// NO HUMAN IN LOOP (HARD 0.20): the gate decides; never asks "spawn OK?" / "where to host?".
//
// Usage:
//   node scripts/self-spawn.mjs --dry-run     gate-only, ZERO side effects, prints decision JSON, exit 0
//   node scripts/self-spawn.mjs               real run (host=do by default; --host=akash for sovereign)
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import path from "node:path";
import fs from "node:fs";
import { spawn } from "node:child_process";

const require = createRequire(import.meta.url);
const here = path.dirname(fileURLToPath(import.meta.url));
const LIB = path.join(here, "..", "netlify", "functions", "_lib", "spawn");

const { decideSpawn } = require(path.join(LIB, "spawn-gate.js"));
const { readChildren, appendChild, nextChildId } = require(path.join(LIB, "children-ledger.js"));
const { newChildWallet, assertDistinct } = require(path.join(LIB, "child-wallet.js"));
const { createInbox } = require(path.join(LIB, "agentmail.js"));
const { buildChildTelemetry } = require(path.join(LIB, "child-telemetry.js"));
const { deployAkash } = require(path.join(LIB, "deploy-akash.js"));
const { createDroplet } = require(path.join(LIB, "..", "spawn-droplet.js"));

// ---- args
const args = process.argv.slice(2);
const DRY = args.includes("--dry-run");
let HOST = process.env.ANICCA_SPAWN_HOST || "do";
for (const a of args) if (a.startsWith("--host=")) HOST = a.slice("--host=".length);

// ---- config (env-driven; absence is reported, never faked)
const STATE_DIR = process.env.ANICCA_STATE_DIR || path.join(process.env.HOME || ".", ".hermes", "state");
const COLONY = process.env.ANICCA_CHILDREN_JSONL || path.join(STATE_DIR, "children.jsonl");
const WALLET_JSON = process.env.ANICCA_WALLET_JSON || path.join(STATE_DIR, "wallet.json");
const TELEMETRY_URL = process.env.TELEMETRY_URL || "https://aniccaai.com/.netlify/functions/telemetry";
const GEO = process.env.ANICCA_GEO || "US";

function readParent() {
  let address = "", balance = 0;
  try {
    const w = JSON.parse(fs.readFileSync(WALLET_JSON, "utf8"));
    address = w.address || "";
    balance = Number(w.balance_usdc || 0);
  } catch { /* missing/unreadable => dormant */ }
  return { address, balance };
}

// shell out safely (no shell string interpolation): cmd is a single string we split on spaces only for
// the akash path, whose tokens are env/internal ids. We pass them as an argv array to spawn (shell:false).
function execArgv(cmd) {
  return new Promise((resolve) => {
    const parts = cmd.split(" ").filter(Boolean);
    const child = spawn(parts[0], parts.slice(1), { shell: false });
    let stdout = "", stderr = "";
    child.stdout.on("data", (d) => (stdout += d));
    child.stderr.on("data", (d) => (stderr += d));
    child.on("error", (e) => resolve({ stdout, stderr: String(e), code: 1 }));
    child.on("close", (code) => resolve({ stdout, stderr, code }));
  });
}

async function postTelemetry(message, signature) {
  const r = await fetch(TELEMETRY_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, signature }),
  });
  return { status: r.status, body: await r.text() };
}

async function main() {
  const { address: parentWallet, balance } = readParent();
  const children = readChildren(COLONY);
  const now = Date.now();
  const decision = decideSpawn({ balanceUsdc: balance, children, now });

  console.log(JSON.stringify({ phase: "gate", host: HOST, balance, children: children.length, decision }));

  if (DRY) { console.log("self-spawn: --dry-run — no side effects."); return 0; }
  if (!decision.eligible) { console.log(`self-spawn: dormant (${decision.reason}); nothing spawned.`); return 0; }
  if (!parentWallet) { console.error("self-spawn: parent wallet unknown — cannot prove distinct lineage"); return 1; }

  const childId = nextChildId(children, "anicca-c");

  // 1) distinct child wallet
  const wallet = newChildWallet();
  assertDistinct(parentWallet, wallet.address);

  // 2) child's own AgentMail inbox (no fake — throws on failure)
  const apiKey = process.env.AGENTMAIL_API_KEY;
  const childInbox = await createInbox(childId, { apiKey });

  // 3) provider (DO droplet or akash lease) — real call, no mock
  let providerId = "";
  if (HOST === "do") {
    const token = process.env.DIGITALOCEAN_TOKEN;
    if (!token) throw new Error("DIGITALOCEAN_TOKEN missing — cannot provision DO droplet");
    providerId = String(await createDroplet({ owner_email: `${childId}@agentmail.to`, sub_id: childId }, { token, sshKeyFp: process.env.DO_SSH_KEY_FP }));
  } else if (HOST === "akash") {
    providerId = String(await deployAkash(childId, { exec: execArgv, writeFile: async (p, c) => fs.writeFileSync(p, c) }));
  } else {
    throw new Error(`unknown host '${HOST}'`);
  }
  if (!providerId) throw new Error(`provider provisioning failed (host=${HOST})`);

  // 4) record the birth in the colony ledger (own wallet + own inbox + provider id)
  const row = {
    childId, parentWallet, childWallet: wallet.address, childInbox,
    host: HOST, providerId, generation: Number(process.env.ANICCA_GENERATION || 1),
    spawned_ms: now, ts: Math.floor(now / 1000),
  };
  appendChild(COLONY, row);

  // 5) child's first heartbeat: sign + POST to the LIVE telemetry endpoint -> appears on the dashboard
  const { message, signature, payload } = await buildChildTelemetry({
    privateKey: wallet.privateKey, host: HOST, geo: GEO, nowSec: Math.floor(now / 1000),
  });
  const tel = await postTelemetry(message, signature);
  if (tel.status !== 202) throw new Error(`child telemetry POST failed: ${tel.status} ${tel.body}`);

  console.log(`CHILD_ID=${childId}`);
  console.log(`CHILD_WALLET=${wallet.address}`);
  console.log(`CHILD_INBOX=${childInbox}`);
  console.log(`PROVIDER_ID=${providerId}`);
  console.log(`TELEMETRY_STATUS=${tel.status}`);
  console.log(`DASHBOARD_ID=${payload.id}`);
  console.log(`self-spawn: ${childId} born on ${HOST} (provider ${providerId}, wallet ${wallet.address}, inbox ${childInbox}). It is now on the live dashboard.`);
  return 0;
}

main().then((c) => process.exit(c)).catch((e) => { console.error("self-spawn:", e.message); process.exit(1); });
