"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const STARTING_EQUITY = 100000;

function stateDir(env = process.env) {
  const configured = String(env.ALPACA_INVESTMENT_STATE_DIR || "").trim();
  return configured ? configured.replace(/^~(?=\/|$)/, os.homedir())
    : path.join(os.homedir(), ".local/state/life-manager/alpaca-investment");
}

function readJson(file) {
  try {
    const value = JSON.parse(fs.readFileSync(file, "utf8"));
    return value && typeof value === "object" && !Array.isArray(value) ? value : {};
  } catch {
    return {};
  }
}

function readRows(file) {
  try {
    return fs.readFileSync(file, "utf8").split("\n").filter(Boolean).flatMap((line) => {
      try {
        const value = JSON.parse(line);
        return value && typeof value === "object" && !Array.isArray(value) ? [value] : [];
      } catch {
        return [];
      }
    });
  } catch {
    return [];
  }
}

function number(value, fallback = 0) {
  const result = Number(value);
  return Number.isFinite(result) ? result : fallback;
}

function rounded(value) {
  return Math.round(number(value) * 100) / 100;
}

function publicId(value) {
  return `public-${crypto.createHash("sha256").update(String(value)).digest("hex").slice(0, 12)}`;
}

function text(value, max = 300) {
  return String(value == null ? "" : value).slice(0, max);
}

function publicDecision(decision) {
  if (!decision || typeof decision !== "object") return null;
  return {
    candidate_ref: text(decision.candidate_ref, 200),
    gate: text(decision.gate, 100),
    approved: decision.approved === true,
    probability_profit: number(decision.probability_profit),
    expected_gain_usd: rounded(decision.expected_gain_usd),
    reason: text(decision.reason, 600),
    observed_at: text(decision.observed_at, 60),
  };
}

function buildAlpacaPublicProjection(input = {}) {
  const dir = input.stateDir || stateDir(input.env);
  const observation = input.observation || readJson(path.join(dir, "observation-latest.json"));
  const campaign = input.campaign || readJson(path.join(dir, "campaign.json"));
  const decision = input.decision || readJson(path.join(dir, "allocation-latest.json"));
  const telegram = input.telegram || readJson(path.join(dir, "telegram-latest.json"));
  const receipts = input.receipts || readRows(path.join(dir, "receipts.jsonl"));
  const account = observation.account && typeof observation.account === "object" ? observation.account : {};
  const positions = Array.isArray(campaign.positions) ? campaign.positions : [];
  const fills = Array.isArray(campaign.fills) ? campaign.fills : [];
  const equity = number(account.equity);
  const cash = number(account.cash);
  const latestReceipt = receipts.slice().reverse().find((row) => row.receipt_type === "outcome" || row.receipt_type === "decision") || {};
  const timeline = receipts.filter((row) => row.receipt_type === "effect_intent" || row.receipt_type === "outcome").map((row) => ({
    type: text(row.receipt_type, 40),
    status: text(row.status || row.outcome, 80),
    effect: row.effect_id ? publicId(row.effect_id) : null,
    recorded_at: text(row.recorded_at, 60),
  }));
  return Object.freeze({
    paper: true,
    observed_at: text(observation.clock && observation.clock.observed_at || campaign.observed_at, 60),
    starting_equity_usd: STARTING_EQUITY,
    equity_usd: rounded(equity),
    cash_usd: rounded(cash),
    total_pnl_usd: rounded(equity - STARTING_EQUITY),
    daily_pnl_usd: rounded(equity - number(account.last_equity, equity)),
    realized_pnl_usd: rounded(campaign.realized_pnl_usd),
    unrealized_pnl_usd: rounded(campaign.unrealized_pnl_usd),
    positions: positions.map((position) => ({
      symbol: text(position.symbol, 32),
      side: text(position.side, 20),
      quantity: number(position.qty ?? position.quantity),
      average_entry_price: rounded(position.average_entry_price),
      current_price: rounded(position.current_price),
      market_value: rounded(position.market_value),
      unrealized_pnl: rounded(position.unrealized_pl ?? position.unrealized_pnl),
    })),
    fills: fills.map((fill) => ({
      id: publicId(fill.id || fill.order_id || fill.symbol),
      symbol: text(fill.symbol, 32),
      side: text(fill.side, 20),
      quantity: number(fill.qty ?? fill.quantity),
      price: rounded(fill.price),
      transaction_at: text(fill.transaction_time || fill.transaction_at, 60),
    })),
    latest_decision: publicDecision(decision),
    reconciliation: {
      status: "OFFICIAL_CLI_READBACK",
      positions: positions.length,
      fills: fills.length,
      broker_orders: number(observation.open_and_closed_orders_count),
      last_receipt: text(latestReceipt.recorded_at, 60) || null,
    },
    telegram: { delivered: telegram.status === "delivered" },
    timeline,
  });
}

function renderAlpacaPublicPage() {
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="Life Manager Alpaca paper-trading evidence"><title>Life Manager — Alpaca Paper Loop</title><style>
  :root{color-scheme:dark;--bg:#07110f;--panel:#0d1c18;--line:#23453b;--mint:#66f2bd;--text:#edf8f3;--muted:#91aaa0;--red:#ff8c8c}*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 80% 0,#12382d 0,transparent 35%),var(--bg);color:var(--text);font:15px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace}main{width:min(1120px,calc(100% - 32px));margin:auto;padding:42px 0 64px}header{display:flex;justify-content:space-between;gap:24px;align-items:flex-start;margin-bottom:24px}h1{font:700 clamp(32px,6vw,64px)/.95 system-ui,sans-serif;letter-spacing:-.06em;margin:8px 0 12px}.eyebrow,.badge{color:var(--mint);text-transform:uppercase;letter-spacing:.14em;font-size:12px}.badge{border:1px solid var(--mint);border-radius:999px;padding:8px 12px;white-space:nowrap}.lede{color:var(--muted);max-width:700px}.grid{display:grid;grid-template-columns:repeat(12,1fr);gap:14px}.card{background:linear-gradient(145deg,rgba(17,40,33,.95),rgba(9,24,20,.95));border:1px solid var(--line);border-radius:16px;padding:18px;min-width:0}.metric{grid-column:span 3}.wide{grid-column:span 8}.side{grid-column:span 4}.full{grid-column:1/-1}h2{font:650 17px system-ui,sans-serif;margin:0 0 14px}.label{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.1em}.value{font:650 26px system-ui,sans-serif;margin-top:6px}.positive{color:var(--mint)}.negative{color:var(--red)}dl{display:grid;grid-template-columns:auto 1fr;gap:7px 14px;margin:0}dt{color:var(--muted)}dd{margin:0;overflow-wrap:anywhere}.muted{color:var(--muted)}table{width:100%;border-collapse:collapse;font-size:12px}th,td{text-align:left;padding:9px 7px;border-bottom:1px solid var(--line)}th{color:var(--muted);font-weight:400}.error{color:var(--red)}footer{color:var(--muted);font-size:11px;margin-top:18px}@media(max-width:800px){header{display:block}.badge{display:inline-block;margin-top:12px}.metric,.wide,.side{grid-column:1/-1}main{padding-top:26px}.card{padding:15px}}
  </style></head><body><main><header><div><div class="eyebrow">Life Manager / investment loop</div><h1>Evidence, not a profit promise.</h1><p class="lede">One bounded process observes Alpaca, lets the model propose or decline, applies deterministic gates, and reports official paper readback.</p></div><div class="badge">Paper trading only</div></header><section class="grid" aria-live="polite"><article class="card metric"><div class="label">Starting equity</div><div class="value" id="starting">—</div></article><article class="card metric"><div class="label">Current equity</div><div class="value" id="equity">—</div></article><article class="card metric"><div class="label">Total P&amp;L</div><div class="value" id="pnl">—</div></article><article class="card metric"><div class="label">Unrealised P&amp;L</div><div class="value" id="unrealized">—</div></article><article class="card wide"><h2>Latest model decision</h2><dl id="decision"><dt>Status</dt><dd class="muted">Loading official evidence…</dd></dl></article><article class="card side"><h2>Reconciliation</h2><dl id="reconciliation"><dt>Status</dt><dd>Loading…</dd></dl></article><article class="card full"><h2>Positions</h2><div id="positions" class="muted">Loading…</div></article><article class="card full"><h2>Broker fills</h2><div id="fills" class="muted">Loading…</div></article></section><footer>Read-only projection · identifiers redacted · no order-placement surface · paper results are not revenue.</footer></main><script>
  const money=n=>typeof n==='number'?new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(n):'—';const esc=v=>String(v??'—');const set=(id,v)=>document.getElementById(id).textContent=esc(v);const tone=(id,n)=>{const e=document.getElementById(id);e.classList.toggle('positive',typeof n==='number'&&n>=0);e.classList.toggle('negative',typeof n==='number'&&n<0)};const table=(id,heads,rows)=>{const host=document.getElementById(id);host.textContent='';if(!rows.length){host.textContent='None';return}const t=document.createElement('table'),h=document.createElement('tr');heads.forEach(x=>{const e=document.createElement('th');e.textContent=x;h.append(e)});t.append(h);rows.forEach(r=>{const tr=document.createElement('tr');r.forEach(x=>{const e=document.createElement('td');e.textContent=esc(x);tr.append(e)});t.append(tr)});host.append(t)};fetch('/api/life-manager/alpaca/public',{headers:{accept:'application/json'}}).then(r=>{if(!r.ok)throw Error('unavailable');return r.json()}).then(p=>{set('starting',money(p.starting_equity_usd));set('equity',money(p.equity_usd));set('pnl',money(p.total_pnl_usd));set('unrealized',money(p.unrealized_pnl_usd));tone('pnl',p.total_pnl_usd);tone('unrealized',p.unrealized_pnl_usd);const d=p.latest_decision||{},dl=document.getElementById('decision');dl.textContent='';[['Status',d.candidate_ref],['Gate',d.gate],['Reason',d.reason],['Expected gain',money(d.expected_gain_usd)],['Observed',d.observed_at]].forEach(([k,v])=>{const a=document.createElement('dt'),b=document.createElement('dd');a.textContent=k;b.textContent=esc(v);dl.append(a,b)});const r=p.reconciliation||{};document.getElementById('reconciliation').innerHTML='';[['Status',r.status],['Positions',r.positions],['Fills',r.fills],['Broker orders',r.broker_orders],['Telegram',p.telegram&&p.telegram.delivered?'delivered':'unavailable'],['Observed',p.observed_at]].forEach(([k,v])=>{const a=document.createElement('dt'),b=document.createElement('dd');a.textContent=k;b.textContent=esc(v);document.getElementById('reconciliation').append(a,b)});table('positions',['Symbol','Side','Qty','Entry','Current','Value','Unrealised'],(p.positions||[]).map(x=>[x.symbol,x.side,x.quantity,money(x.average_entry_price),money(x.current_price),money(x.market_value),money(x.unrealized_pnl)]));table('fills',['Public fill','Symbol','Side','Qty','Price','Time'],(p.fills||[]).map(x=>[x.id,x.symbol,x.side,x.quantity,money(x.price),x.transaction_at]))}).catch(()=>{document.querySelectorAll('.muted').forEach(e=>e.textContent='Read-only evidence is temporarily unavailable.');document.getElementById('reconciliation').textContent='Unavailable'})</script></body></html>`;
}

module.exports = { buildAlpacaPublicProjection, renderAlpacaPublicPage, stateDir };
