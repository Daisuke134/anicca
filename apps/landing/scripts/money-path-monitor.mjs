// money-path-monitor.mjs — C5/C6 standalone 15-min monitor (runs OUTSIDE Railway/Netlify so it never
// dies with the monitored). Reuses the SINGLE tested source (apps/life-call/lib/money-path.js):
// assertMoneyPath + RollbackController (debounce ≥2 consecutive FAIL, flap guard, one-alert-per-incident).
// State persists in a JSON file so debounce/dedup survive across runs. Intended cron host = OpenClaw
// (~/.openclaw/cron/jobs.json), per the project "no new GHA cron" rule.
// Usage: node money-path-monitor.mjs   (env: NETLIFY_AUTH_TOKEN, NETLIFY_SITE_ID, LM_TELEGRAM_BOT_TOKEN, LM_ALERT_CHAT_ID)
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { createRequire } from "node:module";

const here = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const { assertMoneyPath, RollbackController } = require(join(here, "../../life-call/lib/money-path.js"));

// FIND-103: a corrupt/partial state file must NOT crash the only continuous monitor. Guard the parse and
// fall back to a fresh controller. Exported for tests.
export function loadController(statePath) {
  const rc = new RollbackController();
  try {
    if (existsSync(statePath)) {
      const s = JSON.parse(readFileSync(statePath, "utf8"));
      if (s && typeof s === "object") {
        rc.consecutiveFail = Number(s.consecutiveFail) || 0;
        rc.incidentOpen = Boolean(s.incidentOpen);
        rc.rollbackFired = Boolean(s.rollbackFired);
      }
    }
  } catch { /* corrupt state → start fresh */ }
  return rc;
}

async function liveOk(base, registry) {
  try {
    for (const p of ["/", "/life-manager", "/lm"]) {
      if ((await fetch(base + p)).status !== 200) return { ok: false, reason: `${p} not 200` };
    }
    const html = await (await fetch(`${base}/lm?cb=${Date.now()}`)).text();
    const chunkPath = (html.match(/\/_next\/static\/chunks\/app\/lm\/page-[A-Za-z0-9]+\.js/) || [])[0];
    if (!chunkPath) return { ok: false, reason: "no /lm chunk" };
    const chunk = await (await fetch(base + chunkPath)).text();
    return assertMoneyPath({ chunk }, registry);
  } catch (e) { return { ok: false, reason: String(e.message || e) }; }
}
async function prevDeployId() {
  try {
    const r = await fetch(`https://api.netlify.com/api/v1/sites/${process.env.NETLIFY_SITE_ID}/deploys?per_page=10`,
      { headers: { Authorization: `Bearer ${process.env.NETLIFY_AUTH_TOKEN}` } });
    const a = (await r.json()).filter((x) => x.state === "ready" && x.published_at);
    return (a[1] || {}).id || null;
  } catch { return null; }
}
async function restore(id) {
  await fetch(`https://api.netlify.com/api/v1/sites/${process.env.NETLIFY_SITE_ID}/deploys/${id}/restore`,
    { method: "POST", headers: { Authorization: `Bearer ${process.env.NETLIFY_AUTH_TOKEN}` } }).catch(() => {});
}
async function tg(msg) {
  const t = process.env.LM_TELEGRAM_BOT_TOKEN, chat = process.env.LM_ALERT_CHAT_ID;
  if (!t || !chat) { console.log("[alert]", msg); return; }
  await fetch(`https://api.telegram.org/bot${t}/sendMessage`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: chat, text: msg }),
  }).catch(() => {});
}

async function main() {
  const base = process.env.MONITOR_BASE || "https://aniccaai.com";
  const registry = JSON.parse(readFileSync(join(here, "../monitors/registry.json"), "utf8"));
  const statePath = join(here, "../monitors/.monitor-state.json");
  const rc = loadController(statePath);

  const verdict = await liveOk(base, registry);
  const prev = verdict.ok ? "n/a" : await prevDeployId();
  const d = rc.onResult(verdict.ok, { lastGoodPasses: Boolean(prev) });
  const save = () => writeFileSync(statePath, JSON.stringify({ consecutiveFail: rc.consecutiveFail, incidentOpen: rc.incidentOpen, rollbackFired: rc.rollbackFired }));

  if (verdict.ok) { save(); console.log(`OK: ${base} money-path healthy`); return 0; }
  console.error(`FAIL: ${verdict.reason} (consecutiveFail=${rc.consecutiveFail})`);

  let healthy = false;
  if (d.rollback && prev) {
    await restore(prev);
    await new Promise((r) => setTimeout(r, 20000));
    // FIND-102: flap guard = verify the site is actually HEALTHY after the restore, not merely that a
    // previous deploy existed. If it's still failing, the rollback target was also bad → escalate.
    healthy = (await liveOk(base, registry)).ok;
    console.error(healthy ? `rolled back to ${prev} — healthy` : `FLAP GUARD: restored ${prev} but site STILL failing — escalate`);
  } else if (d.escalate) {
    console.error("FLAP GUARD: no healthy last-good to roll back to — escalate");
  }
  save();
  if (d.notify) await tg(`⚠️ Life Manager money-path FAIL: ${verdict.reason}. rolledBack=${d.rollback} healthyAfter=${healthy} escalate=${d.escalate || (d.rollback && !healthy)}`);
  return 1;
}

// Run only when invoked directly (not when imported by a test).
if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  main().then((c) => process.exit(c)).catch((e) => { console.error(e); process.exit(1); });
}
