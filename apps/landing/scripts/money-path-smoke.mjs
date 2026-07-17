// money-path-smoke.mjs — C5/C6 (VCSDD life-manager-cost-connect-reliability). Post-deploy smoke:
// assert the live site is up AND the /lm bundle's Stripe link == the registry known-good LM $20/mo link.
// Exit 0 = PASS, exit 1 = FAIL (caller rolls back). Deterministic, no LLM. Usage: node money-path-smoke.mjs [baseUrl]
// The link-assertion logic is the SINGLE tested source (apps/life-call/lib/money-path.js) — no reimplementation
// (adversary FIND-006 drift). registry.json is the single known-good SSOT.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { createRequire } from "node:module";

const here = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const { assertMoneyPath } = require(join(here, "../../life-call/lib/money-path.js"));
const registry = JSON.parse(readFileSync(join(here, "../monitors/registry.json"), "utf8"));

const BASE = process.argv[2] || "https://aniccaai.com";
const fail = (m) => { console.error("SMOKE FAIL:", m); process.exit(1); };

// 1. core routes 200
for (const p of ["/", "/life-manager", "/lm"]) {
  const r = await fetch(BASE + p);
  if (r.status !== 200) fail(`${p} returned ${r.status}`);
}
// 2. /lm chunk Stripe link == registry (content assertion via the shared, tested assertMoneyPath)
const html = await (await fetch(`${BASE}/lm?cb=${Date.now()}`)).text();
const chunkPath = (html.match(/\/_next\/static\/chunks\/app\/lm\/page-[A-Za-z0-9]+\.js/) || [])[0];
if (!chunkPath) fail("no /lm page chunk found in HTML");
const chunk = await (await fetch(BASE + chunkPath)).text();
const verdict = assertMoneyPath({ chunk }, registry);
if (!verdict.ok) fail(verdict.reason);
// 3. the known-good registry link is reachable (its $20/mo Life Manager identity is verified once at
// registry-set time via the Stripe API; a per-deploy raw fetch of Stripe's client-rendered page is unreliable)
const pay = await fetch(registry.stripe_lm_url);
if (pay.status !== 200) fail(`registry Stripe link not reachable (${pay.status})`);

console.log(`SMOKE PASS: ${BASE} up, /lm Stripe link == ${registry.stripe_lm_url} (registry known-good), reachable`);
process.exit(0);
