#!/usr/bin/env node
// store-review.mjs — SELF-STORE-1 `review` action for the x402_sell loop slot. Answers the model's
// real question in one shot: what actually sold, and was any of it a REAL (external) buyer, or is
// this a demand problem? Reads the seller's own sales/attempts logs (serve-v2.mjs writes them) and
// aggregates them with the SAME self-wallet judgment verify-inflow.mjs uses (INV-7).
//
// Env:
//   X402_PAYTO   this instance's own receiving wallet (default: derived from the per-instance key)
//
// Loop child-script contract: prints exactly ONE JSON line on stdout, never throws.
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { privateKeyToAccount } from "viem/accounts";
import { loadEvmKey } from "../lib/resolve-identity.mjs";
import { SELF_WALLETS } from "./lib/self-wallets.mjs";
import { aggregateStore } from "./lib/store-metrics.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));

// Mirrors serve-v2.mjs's payTo() (#28: this instance's OWN gated key, never a borrowed one).
export function resolvePayTo(env = process.env) {
  if (env.X402_PAYTO) return env.X402_PAYTO;
  const pk = loadEvmKey({ env });
  if (pk) return privateKeyToAccount(pk).address;
  return null;
}

function readJsonl(path) {
  let raw;
  try { raw = readFileSync(path, "utf8"); } catch { return []; }
  return raw.split("\n").filter(Boolean).map((line) => {
    try { return JSON.parse(line); } catch { return null; }
  }).filter(Boolean);
}

export function review(env = process.env, now = Date.now()) {
  const payTo = resolvePayTo(env);
  if (!payTo) {
    return { error: "no payTo resolvable (no X402_PAYTO, no per-instance key)" };
  }
  const lower = payTo.toLowerCase();
  // The serve daemon writes state/ next to ITS OWN serve-v2.mjs. On colony instances the skill
  // copy under ANICCA_HOME is synced from the repo checkout while the seller runs FROM the repo
  // checkout — so this script's own state/ can be empty while the real logs sit in the checkout
  // (measured 2026-07-18: franklin1 review returned zeros against 5 real settled rows). Resolve:
  // explicit X402_STATE_DIR wins; else prefer whichever candidate actually has this payTo's file.
  const candidates = [
    env.X402_STATE_DIR,
    join(HERE, "state"),
    env.HOME ? join(env.HOME, "anicca", "skills", "earn", "x402-sell", "state") : null,
  ].filter(Boolean);
  const stateDir = candidates.find((d) => existsSync(join(d, `sales-${lower}.jsonl`))) || candidates[0];
  const sales = readJsonl(join(stateDir, `sales-${lower}.jsonl`));
  const attempts = readJsonl(join(stateDir, `attempts-${lower}.jsonl`));
  return aggregateStore(sales, attempts, new Set(SELF_WALLETS), now);
}

const isMain = process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1];
if (isMain) {
  console.log(JSON.stringify(review()));
}
