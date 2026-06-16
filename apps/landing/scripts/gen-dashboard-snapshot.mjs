// Build-time: fetch the live dashboard data and write it into the app so the
// static export ships REAL numbers (not a permanent "Loading…").
// Runs in `prebuild`. Never throws — on failure writes an empty snapshot so the
// build still succeeds and the client useEffect refreshes live at runtime.
import { writeFile, mkdir } from "node:fs/promises";
import { dirname } from "node:path";

const OUT = new URL("../app/dashboard/_snapshot.json", import.meta.url);
// Prefer the deployed function; allow override for preview builds.
const SRC =
  process.env.DASHBOARD_SNAPSHOT_URL ||
  "https://aniccaai.com/.netlify/functions/dashboard-sync";

async function main() {
  let snapshot = null;
  try {
    const res = await fetch(SRC, { signal: AbortSignal.timeout(10_000) });
    if (res.ok) {
      const json = await res.json();
      if (json && typeof json.total_net_worth_usd === "number") snapshot = json;
    }
  } catch (e) {
    console.warn(`[gen-dashboard-snapshot] live fetch failed, shipping empty seed: ${e.message}`);
  }
  await mkdir(dirname(OUT.pathname), { recursive: true });
  await writeFile(OUT, JSON.stringify(snapshot));
  console.log(`[gen-dashboard-snapshot] wrote seed (${snapshot ? "live" : "empty"}) → app/dashboard/_snapshot.json`);
}
main();
