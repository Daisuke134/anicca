"use strict";
// 11b PHY-b readback: run the real candidate selection against real provider
// pages. The living area is read from production lm_users.home_address and
// reduced to a ward before it is used; the exact address never leaves this
// process. The care category, the user's own visit history, and the three
// public providers are supplied in a local JSON file so private history is
// never committed to the repository.
//
// Usage:
//   SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... \
//   node scripts/care-candidate-readback.js <input.json>
//
// input.json = { careCategory, workArea, history: [{careType,startMs,providerName}],
//                candidates: [{providerId,publicName,officialUrl,publicArea}] }

const fs = require("node:fs");
const { livingAreaFromAddress, selectCareCandidates } = require("../lib/care-candidates.js");

const USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
  + "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36";

async function homeArea() {
  const base = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!base || !key) throw new Error("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required");
  const url = `${base}/rest/v1/lm_users?select=home_address&home_address=not.is.null&limit=1`;
  const response = await fetch(url, { headers: { apikey: key, authorization: `Bearer ${key}` } });
  if (!response.ok) throw new Error(`supabase read failed: ${response.status}`);
  const rows = await response.json();
  if (!rows.length) throw new Error("no stored home address: living area cannot be derived");
  return livingAreaFromAddress(rows[0].home_address);
}

async function main() {
  const input = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
  const derived = await homeArea();
  const receipt = await selectCareCandidates({
    careCategory: input.careCategory,
    livingArea: { homeArea: derived.area, workArea: input.workArea || null },
    history: input.history,
    candidates: input.candidates,
  }, (url) => fetch(url, {
    headers: { "user-agent": USER_AGENT, "accept-language": "ja" },
    redirect: "follow",
    signal: AbortSignal.timeout(20_000),
  }));
  console.log(JSON.stringify({
    living_area: derived,
    receipt,
  }, null, 2));
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
