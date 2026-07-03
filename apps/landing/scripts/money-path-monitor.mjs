// money-path-monitor.mjs — C5/C6 standalone 15-min monitor (runs OUTSIDE Railway/Netlify so it never
// dies with the monitored). It reuses the SINGLE tested source (apps/life-call/lib/money-path.js):
// assertMoneyPath + RollbackController (debounce ≥2 consecutive FAIL, flap guard, one-alert-per-incident).
// State persists in a small JSON file so debounce/dedup survive across the 15-min runs.
// Intended cron host = OpenClaw (~/.openclaw/cron/jobs.json), per the project "no new GHA cron" rule.
// Usage: node money-path-monitor.mjs   (env: NETLIFY_AUTH_TOKEN, NETLIFY_SITE_ID, optional LM_TELEGRAM_* )
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { createRequire } from "node:module";

const here = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const { assertMoneyPath, RollbackController } = require(join(here, "../../life-call/lib/money-path.js"));
const registry = JSON.parse(readFileSync(join(here, "../monitors/registry.json"), "utf8"));
const STATE = join(here, "../monitors/.monitor-state.json");
const BASE = process.env.MONITOR_BASE || "https://aniccaai.com";

// Load persisted controller state (consecutiveFail / incidentOpen / rollbackFired) so debounce survives.
const rc = new RollbackController();
if (existsSync(STATE)) Object.assign(rc, JSON.parse(readFileSync(STATE, "utf8")));

async function liveOk() {
  try {
    for (const p of ["/", "/life-manager", "/lm"]) {
      if ((await fetch(BASE + p)).status !== 200) return { ok: false, reason: `${p} not 200` };
    }
    const html = await (await fetch(`${BASE}/lm?cb=${Date.now()}`)).text();
    const chunkPath = (html.match(/\/_next\/static\/chunks\/app\/lm\/page-[A-Za-z0-9]+\.js/) || [])[0];
    if (!chunkPath) return { ok: false, reason: "no /lm chunk" };
    const chunk = await (await fetch(BASE + chunkPath)).text();
    return assertMoneyPath({ chunk }, registry);
  } catch (e) { return { ok: false, reason: String(e.message || e) }; }
}
async function lastGoodDeployReachable() {
  try {
    const r = await fetch(`https://api.netlify.com/api/v1/sites/${process.env.NETLIFY_SITE_ID}/deploys?per_page=10`,
      { headers: { Authorization: `Bearer ${process.env.NETLIFY_AUTH_TOKEN}` } });
    const a = (await r.json()).filter((x) => x.state === "ready" && x.published_at);
    return { id: (a[1] || {}).id || null };
  } catch { return { id: null }; }
}
async function tg(msg) {
  const t = process.env.LM_TELEGRAM_BOT_TOKEN, chat = process.env.LM_ALERT_CHAT_ID;
  if (!t || !chat) { console.log("[alert]", msg); return; }
  await fetch(`https://api.telegram.org/bot${t}/sendMessage`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: chat, text: msg }),
  }).catch(() => {});
}

const verdict = await liveOk();
const prev = verdict.ok ? { id: "n/a" } : await lastGoodDeployReachable();
const d = rc.onResult(verdict.ok, { lastGoodPasses: Boolean(prev.id) });
writeFileSync(STATE, JSON.stringify({ consecutiveFail: rc.consecutiveFail, incidentOpen: rc.incidentOpen, rollbackFired: rc.rollbackFired }));

if (verdict.ok) { console.log(`OK: ${BASE} money-path healthy`); process.exit(0); }
console.error(`FAIL: ${verdict.reason} (consecutiveFail=${rc.consecutiveFail})`);
if (d.rollback && prev.id) {
  await fetch(`https://api.netlify.com/api/v1/sites/${process.env.NETLIFY_SITE_ID}/deploys/${prev.id}/restore`,
    { method: "POST", headers: { Authorization: `Bearer ${process.env.NETLIFY_AUTH_TOKEN}` } });
  console.error(`rolled back to ${prev.id}`);
}
if (d.escalate) console.error("FLAP GUARD: last-good also failing — not rolling back");
if (d.notify) await tg(`⚠️ Life Manager money-path FAIL: ${verdict.reason}. rollback=${d.rollback} escalate=${d.escalate}`);
process.exit(1);
