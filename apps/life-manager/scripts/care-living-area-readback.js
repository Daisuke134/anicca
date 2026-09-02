"use strict";
// 11b PHY-b readback: derive the coarse living area from the production
// lm_users.home_address without ever emitting the address itself.
// Usage: SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... node scripts/care-living-area-readback.js

const { livingAreaFromAddress } = require("../lib/care-candidates.js");

async function main() {
  const base = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!base || !key) throw new Error("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required");
  const url = `${base}/rest/v1/lm_users?select=uid,home_address&home_address=not.is.null`;
  const response = await fetch(url, { headers: { apikey: key, authorization: `Bearer ${key}` } });
  if (!response.ok) throw new Error(`supabase read failed: ${response.status}`);
  const rows = await response.json();
  for (const row of rows) {
    let derived = null;
    try {
      derived = livingAreaFromAddress(row.home_address);
    } catch (error) {
      derived = { area: null, granularity: null, refused: error.message };
    }
    // Only the derived coarse area is printed; the stored address never is.
    console.log(JSON.stringify({
      uid_tail: String(row.uid).slice(-4),
      address_chars: String(row.home_address).length,
      living_area: derived,
    }));
  }
  console.log(JSON.stringify({ rows_with_address: rows.length }));
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
