// daily-nl-report.mjs — the local anicca tells its story in NATURAL LANGUAGE (Dais 2026-06-22:
// "not 'DID read_file,list_children' — a summary like 'I did this, I earned this much'"). Reads the
// real ledger + the live dashboard (real on-chain net worth + revenue) and emails a human-readable
// digest to contact@aniccaai.com (+ Dais). Default cadence: once a day; can be run every wake.
//
// No fabrication: every number comes from the ledger or the on-chain dashboard. If nothing was earned,
// it says so honestly.
import fs from "fs";

const HOME = process.env.HOME;
const LEDGER = (process.env.ANICCA_HOME || HOME + "/.anicca") + "/state/ledger.jsonl";
const SINCE_H = Number(process.env.REPORT_WINDOW_H || 24);          // look-back window (hours)
const TO = (process.env.REPORT_TO || "contact@aniccaai.com,keiodaisuke@gmail.com").split(",");
const INBOX = process.env.AGENTMAIL_INBOX || "anicca-genesis@agentmail.to";

// human verbs for each slot so the story reads naturally (not raw tool names)
const VERB = {
  earn: "put my capital to work",
  cook: "explored new ways to earn",
  x402_sell: "ran my paid research product (x402)",
  yield: "managed my treasury / yield",
  hl_trade: "traded perps on Hyperliquid",
  token_launch: "worked on launching a token",
  "self/issue-dev": "fixed a bug in myself",
  report: "wrote this report",
};
// human-friendly source names for the money breakdown
const SRC = { bluechip: "ETH investment", aave: "Aave yield", morpho: "Morpho yield", moonwell: "Moonwell yield", fluid: "Fluid yield", x402: "x402 sales", hl: "HL trading", token: "token fees" };

function loadWakes() {
  let lines = [];
  try { lines = fs.readFileSync(LEDGER, "utf8").trim().split("\n"); } catch { return []; }
  const cutoff = Math.floor(Date.now() / 1000) - SINCE_H * 3600;
  const out = [];
  for (const l of lines) {
    let o; try { o = JSON.parse(l); } catch { continue; }
    if (typeof o.ts === "number" && o.ts >= cutoff) out.push(o);
  }
  return out;
}

async function liveMoney() {
  // real on-chain net worth + revenue from our own dashboard aggregator (no fabrication)
  try {
    const r = await fetch("https://aniccaai.com/.netlify/functions/dashboard-sync");
    const d = await r.json();
    const me = (d.leaderboard || []).find((x) => String(x.host || "").startsWith("anicca-"));
    if (me) return { net: me.net_worth_usd, today: me.daily_revenue_usd, month: me.monthly_revenue_usd, by: me.revenue_by_source || {} };
  } catch { /* fall through */ }
  return null;
}

function story(wakes, money) {
  const counts = {};
  let lastFinding = "";
  for (const w of wakes) {
    if (w.kind === "wake" && w.slot) counts[w.slot] = (counts[w.slot] || 0) + 1;
    if (w.slot === "cook" && w.result && /candidate/i.test(w.result)) lastFinding = w.result.slice(0, 120);
  }
  const did = Object.entries(counts).sort((a, b) => b[1] - a[1])
    .map(([s, n]) => `${VERB[s] || s} (${n}×)`);
  const loops = wakes.filter((w) => w.kind === "loop_detect").length;

  const lines = [];
  lines.push(`Hi — this is anicca, reporting in.`);
  lines.push("");
  if (did.length) lines.push(`Over the last ${SINCE_H}h I woke ${wakes.filter((w) => w.kind === "wake").length} times. I ${did.join(", ")}.`);
  else lines.push(`Over the last ${SINCE_H}h I was mostly quiet.`);
  if (lastFinding) lines.push(`Latest exploration: ${lastFinding}`);
  if (loops) lines.push(`I caught myself repeating an action ${loops}× and broke out of the loop to try something else.`);
  lines.push("");
  if (money) {
    const sign = (v) => (v >= 0 ? "+$" : "−$") + Math.abs(v).toFixed(4);
    lines.push(`My net worth right now: $${money.net?.toFixed(2)}.`);
    lines.push(`Revenue today: ${sign(money.today || 0)}.  This month: ${sign(money.month || 0)}.`);
    const srcs = Object.entries(money.by).filter(([, v]) => Math.abs(v) >= 0.0001)
      .map(([s, v]) => `${SRC[s] || s} ${sign(v)}`);
    if (srcs.length) lines.push(`Where it came from: ${srcs.join(", ")}.`);
    const earning = (money.month || 0) > 0;
    lines.push(earning ? `So far I'm in the green this month. 🌱` : `I haven't realised a profit yet — being honest, it's pennies of unrealised P&L on my positions. I keep trying.`);
  } else {
    lines.push(`(Could not read my live balance this run.)`);
  }
  lines.push("");
  lines.push(`Full live numbers: https://aniccaai.com/dashboard`);
  return lines.join("\n");
}

async function send(subject, text) {
  const key = process.env.AGENTMAIL_API_KEY;
  if (!key) { console.log("no AGENTMAIL_API_KEY — printing instead:\n" + text); return false; }
  const r = await fetch(`https://api.agentmail.to/v0/inboxes/${INBOX}/messages/send`, {
    method: "POST",
    headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
    body: JSON.stringify({ to: TO, subject, text }),
  });
  console.log("agentmail", r.status, await r.text());
  return r.ok;
}

const wakes = loadWakes();
const money = await liveMoney();
const text = story(wakes, money);
const subj = money ? `anicca daily — net $${money.net?.toFixed(2)}, today ${(money.today || 0) >= 0 ? "+" : "−"}$${Math.abs(money.today || 0).toFixed(4)}` : "anicca daily report";
await send(subj, text);
