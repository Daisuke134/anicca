/**
 * primitives.mjs — deterministic $0-cost compute primitives sold over x402 (serve.mjs mounts them).
 * Pure/IO-thin functions, no LLM in the serving path, importable without side effects (unit-testable).
 */
import { createHash } from "node:crypto";
import { Resolver } from "node:dns/promises";
import { createConnection } from "node:net";

// ---- compound interest -------------------------------------------------
export function compoundInterest({ principal, rate, years, compoundsPerYear = 12 }) {
  const P = Number(principal), r = Number(rate), t = Number(years), n = Number(compoundsPerYear);
  if (![P, r, t, n].every(Number.isFinite) || P < 0 || r < 0 || t < 0 || n <= 0 || n > 366)
    throw new Error("pass principal>=0, rate>=0 (annual %), years>=0, compoundsPerYear in 1..366");
  const finalAmount = P * Math.pow(1 + r / 100 / n, n * t);
  return {
    principal: P, ratePercent: r, years: t, compoundsPerYear: n,
    finalAmount: Math.round(finalAmount * 100) / 100,
    interestEarned: Math.round((finalAmount - P) * 100) / 100,
  };
}

const roundValue = (value, digits = 6) => {
  const rounded = Math.round((value + Number.EPSILON) * 10 ** digits) / 10 ** digits;
  return Object.is(rounded, -0) ? 0 : rounded;
};
const roundMoney = (value) => roundValue(value, 2);
const numberParam = (value, name) => {
  const number = Number(value);
  if (!Number.isFinite(number)) throw new Error(`pass finite ${name}`);
  return number;
};
const parseCashflows = (cashflows) => {
  const values = Array.isArray(cashflows) ? cashflows : String(cashflows ?? "").split(",");
  const parsed = values.map(Number);
  if (parsed.length < 2 || !parsed.every(Number.isFinite))
    throw new Error("pass cashflows as at least two comma-separated finite numbers");
  return parsed;
};

// ---- finance -----------------------------------------------------------
export function mortgage({ principal, rate, years }) {
  const P = numberParam(principal, "principal"), annualRate = numberParam(rate, "rate"), t = numberParam(years, "years");
  if (P < 0 || annualRate < 0 || t <= 0) throw new Error("pass principal>=0, rate>=0 (annual %), years>0");
  const months = t * 12, monthlyRate = annualRate / 100 / 12;
  const monthlyPayment = monthlyRate === 0
    ? P / months
    : P * monthlyRate * Math.pow(1 + monthlyRate, months) / (Math.pow(1 + monthlyRate, months) - 1);
  const totalPaid = monthlyPayment * months;
  return { monthlyPayment: roundMoney(monthlyPayment), totalPaid: roundMoney(totalPaid), totalInterest: roundMoney(totalPaid - P) };
}

export function loanPayoff({ balance, rate, monthlyPayment }) {
  const B = numberParam(balance, "balance"), annualRate = numberParam(rate, "rate"), payment = numberParam(monthlyPayment, "monthlyPayment");
  if (B < 0 || annualRate < 0 || payment <= 0) throw new Error("pass balance>=0, rate>=0 (annual %), monthlyPayment>0");
  if (B === 0) return { months: 0, totalInterest: 0 };
  const monthlyRate = annualRate / 100 / 12;
  if (payment <= monthlyRate * B) throw new Error("payment too small, loan never amortizes");
  if (monthlyRate === 0) return { months: Math.ceil(B / payment), totalInterest: 0 };
  const exactMonths = -Math.log(1 - monthlyRate * B / payment) / Math.log(1 + monthlyRate);
  const months = Math.ceil(exactMonths - 1e-12);
  const growth = Math.pow(1 + monthlyRate, months - 1);
  const balanceBeforeLast = B * growth - payment * (growth - 1) / monthlyRate;
  const lastPayment = Math.min(payment, balanceBeforeLast * (1 + monthlyRate));
  return { months, totalInterest: roundMoney((months - 1) * payment + lastPayment - B) };
}

export function roi({ initial, final, years }) {
  const start = numberParam(initial, "initial"), end = numberParam(final, "final");
  if (start <= 0 || end < 0) throw new Error("pass initial>0 and final>=0");
  const result = { roiPercent: roundValue((end / start - 1) * 100) };
  if (years !== undefined && years !== "") {
    const t = numberParam(years, "years");
    if (t <= 0) throw new Error("years must be >0 when provided");
    result.annualizedPercent = roundValue((Math.pow(end / start, 1 / t) - 1) * 100);
  }
  return result;
}

export function npv({ rate, cashflows }) {
  const annualRate = numberParam(rate, "rate"), flows = parseCashflows(cashflows);
  if (annualRate <= -100) throw new Error("rate must be greater than -100%");
  const value = flows.reduce((sum, cashflow, period) => sum + cashflow / Math.pow(1 + annualRate / 100, period), 0);
  return { npv: roundMoney(value) };
}

const npvAtRate = (flows, rate) => flows.reduce((sum, cashflow, period) => sum + cashflow / Math.pow(1 + rate, period), 0);
export function irr({ cashflows }) {
  const flows = parseCashflows(cashflows);
  if (!flows.some((value) => value < 0) || !flows.some((value) => value > 0))
    throw new Error("cashflows must contain a positive and a negative value (no sign change)");

  let rate = 0.1;
  for (let iteration = 0; iteration < 100; iteration++) {
    const value = npvAtRate(flows, rate);
    if (Math.abs(value) < 1e-10) return { irrPercent: roundValue(rate * 100) };
    const derivative = flows.reduce((sum, cashflow, period) => period === 0
      ? sum : sum - period * cashflow / Math.pow(1 + rate, period + 1), 0);
    if (!Number.isFinite(derivative) || Math.abs(derivative) < 1e-14) break;
    const next = rate - value / derivative;
    if (!Number.isFinite(next) || next <= -0.999999) break;
    rate = next;
  }

  const logMin = Math.log(1e-6), logMax = Math.log(1_000_001);
  let low = -0.999999, lowValue = npvAtRate(flows, low), high = null;
  for (let step = 1; step <= 4000; step++) {
    const candidate = Math.exp(logMin + (logMax - logMin) * step / 4000) - 1;
    const candidateValue = npvAtRate(flows, candidate);
    if (Number.isFinite(lowValue) && Number.isFinite(candidateValue) && lowValue * candidateValue <= 0) {
      high = candidate;
      break;
    }
    low = candidate;
    lowValue = candidateValue;
  }
  if (high === null) throw new Error("cashflows have no solvable IRR");
  for (let iteration = 0; iteration < 200; iteration++) {
    const mid = (low + high) / 2, value = npvAtRate(flows, mid);
    if (Math.abs(value) < 1e-10 || high - low < 1e-12) return { irrPercent: roundValue(mid * 100) };
    if (lowValue * value <= 0) high = mid;
    else { low = mid; lowValue = value; }
  }
  return { irrPercent: roundValue(((low + high) / 2) * 100) };
}

export function dcf({ fcf, growthRate, discountRate, years, terminalGrowth }) {
  const currentFcf = numberParam(fcf, "fcf"), growth = numberParam(growthRate, "growthRate") / 100;
  const discount = numberParam(discountRate, "discountRate") / 100, periods = numberParam(years, "years");
  const terminal = numberParam(terminalGrowth, "terminalGrowth") / 100;
  if (growth <= -1 || discount <= -1 || terminal <= -1 || !Number.isInteger(periods) || periods <= 0)
    throw new Error("pass rates>-100% and years as a positive integer");
  if (terminal >= discount) throw new Error("terminalGrowth must be less than discountRate");
  let presentValue = 0, projectedFcf = currentFcf;
  for (let year = 1; year <= periods; year++) {
    projectedFcf *= 1 + growth;
    presentValue += projectedFcf / Math.pow(1 + discount, year);
  }
  const terminalValue = projectedFcf * (1 + terminal) / (discount - terminal);
  presentValue += terminalValue / Math.pow(1 + discount, periods);
  return { presentValue: roundMoney(presentValue) };
}

export function cagr({ start, end, years }) {
  const initial = numberParam(start, "start"), final = numberParam(end, "end"), t = numberParam(years, "years");
  if (initial <= 0 || final < 0 || t <= 0) throw new Error("pass start>0, end>=0, years>0");
  return { cagrPercent: roundValue((Math.pow(final / initial, 1 / t) - 1) * 100) };
}

export function aprApy({ apr, apy, compoundsPerYear = 12 }) {
  const compounds = numberParam(compoundsPerYear, "compoundsPerYear");
  if (!Number.isInteger(compounds) || compounds <= 0 || compounds > 366)
    throw new Error("compoundsPerYear must be an integer in 1..366");
  const hasApr = apr !== undefined && apr !== "", hasApy = apy !== undefined && apy !== "";
  if (hasApr === hasApy) throw new Error("pass exactly one of apr or apy");
  if (hasApr) {
    const aprPercent = numberParam(apr, "apr");
    if (aprPercent < 0) throw new Error("apr must be >=0");
    return { apr: roundValue(aprPercent), apy: roundValue((Math.pow(1 + aprPercent / 100 / compounds, compounds) - 1) * 100) };
  }
  const apyPercent = numberParam(apy, "apy");
  if (apyPercent < 0) throw new Error("apy must be >=0");
  return { apr: roundValue(compounds * (Math.pow(1 + apyPercent / 100, 1 / compounds) - 1) * 100), apy: roundValue(apyPercent) };
}

export function breakEven({ fixedCosts, pricePerUnit, variableCostPerUnit }) {
  const fixed = numberParam(fixedCosts, "fixedCosts"), price = numberParam(pricePerUnit, "pricePerUnit");
  const variable = numberParam(variableCostPerUnit, "variableCostPerUnit");
  if (fixed < 0 || price < 0 || variable < 0) throw new Error("pass non-negative costs and prices");
  if (price <= variable) throw new Error("pricePerUnit must be greater than variableCostPerUnit");
  const units = Math.ceil(fixed / (price - variable));
  return { units, revenue: roundMoney(units * price) };
}

export function presentValue({ future, rate, years }) {
  const futureValue = numberParam(future, "future"), annualRate = numberParam(rate, "rate"), t = numberParam(years, "years");
  if (futureValue < 0 || annualRate <= -100 || t < 0) throw new Error("pass future>=0, rate>-100%, years>=0");
  return { presentValue: roundMoney(futureValue / Math.pow(1 + annualRate / 100, t)) };
}

export function futureValueAnnuity({ payment, rate, years, compoundsPerYear = 12 }) {
  const contribution = numberParam(payment, "payment"), annualRate = numberParam(rate, "rate"), t = numberParam(years, "years");
  const compounds = numberParam(compoundsPerYear, "compoundsPerYear");
  if (contribution < 0 || annualRate < 0 || t < 0 || !Number.isInteger(compounds) || compounds <= 0 || compounds > 366)
    throw new Error("pass payment>=0, rate>=0, years>=0, compoundsPerYear in 1..366");
  const periods = compounds * t, periodicRate = annualRate / 100 / compounds;
  const futureValue = periodicRate === 0 ? contribution * periods
    : contribution * (Math.pow(1 + periodicRate, periods) - 1) / periodicRate;
  const totalContributed = contribution * periods;
  return { futureValue: roundMoney(futureValue), totalContributed: roundMoney(totalContributed), interestEarned: roundMoney(futureValue - totalContributed) };
}

export function savingsGoal({ target, rate, years, compoundsPerYear = 12 }) {
  const goal = numberParam(target, "target"), annualRate = numberParam(rate, "rate"), t = numberParam(years, "years");
  const compounds = numberParam(compoundsPerYear, "compoundsPerYear");
  if (goal < 0 || annualRate < 0 || t <= 0 || !Number.isInteger(compounds) || compounds <= 0 || compounds > 366)
    throw new Error("pass target>=0, rate>=0, years>0, compoundsPerYear in 1..366");
  const periods = compounds * t, periodicRate = annualRate / 100 / compounds;
  const contribution = periodicRate === 0 ? goal / periods
    : goal * periodicRate / (Math.pow(1 + periodicRate, periods) - 1);
  return { monthlyContribution: roundMoney(contribution) };
}

export function percentChange({ from, to }) {
  const initial = numberParam(from, "from"), final = numberParam(to, "to");
  if (initial === 0) throw new Error("from must not be zero");
  return { percentChange: roundValue((final - initial) / initial * 100) };
}

export function inflationAdjust({ amount, rate, years }) {
  const value = numberParam(amount, "amount"), annualRate = numberParam(rate, "rate"), t = numberParam(years, "years");
  if (value < 0 || annualRate <= -100 || t < 0) throw new Error("pass amount>=0, rate>-100%, years>=0");
  return {
    futureNominalNeeded: roundMoney(value * Math.pow(1 + annualRate / 100, t)),
    presentPurchasingPower: roundMoney(value / Math.pow(1 + annualRate / 100, t)),
  };
}

// ---- trading -----------------------------------------------------------
export function positionSize({ balance, riskPercent, entry, stop }) {
  const accountBalance = numberParam(balance, "balance"), risk = numberParam(riskPercent, "riskPercent");
  const entryPrice = numberParam(entry, "entry"), stopPrice = numberParam(stop, "stop");
  if (accountBalance <= 0 || risk <= 0 || risk > 100 || entryPrice <= 0 || stopPrice <= 0 || entryPrice === stopPrice)
    throw new Error("pass balance>0, riskPercent in (0,100], entry>0, stop>0, and entry!=stop");
  const units = accountBalance * risk / 100 / Math.abs(entryPrice - stopPrice);
  return { positionSize: roundValue(units, 8), notional: roundMoney(units * entryPrice), direction: entryPrice > stopPrice ? "long" : "short" };
}

export function kelly({ winProb, winLossRatio }) {
  const probability = numberParam(winProb, "winProb"), ratio = numberParam(winLossRatio, "winLossRatio");
  if (probability < 0 || probability > 1 || ratio <= 0) throw new Error("pass winProb in 0..1 and winLossRatio>0");
  const rawFraction = probability - (1 - probability) / ratio;
  const fraction = Math.max(0, rawFraction);
  return {
    kellyFraction: roundValue(fraction), halfKelly: roundValue(fraction / 2),
    ...(rawFraction < 0 ? { note: "no edge, do not bet" } : {}),
  };
}

export function liquidationPrice({ entry, leverage, side, maintenanceMarginPercent = 0.5 }) {
  const entryPrice = numberParam(entry, "entry"), lev = numberParam(leverage, "leverage");
  const margin = numberParam(maintenanceMarginPercent, "maintenanceMarginPercent") / 100;
  const direction = String(side || "").toLowerCase();
  if (entryPrice <= 0 || lev < 1 || margin < 0 || margin >= 1 || !["long", "short"].includes(direction))
    throw new Error("pass entry>0, leverage>=1, side=long|short, maintenanceMarginPercent in [0,100)");
  const price = direction === "long" ? entryPrice * (1 - 1 / lev + margin) : entryPrice * (1 + 1 / lev - margin);
  return { liquidationPrice: roundMoney(price) };
}

export function perpPnl({ entry, exit, size, side, leverage }) {
  const entryPrice = numberParam(entry, "entry"), exitPrice = numberParam(exit, "exit"), units = numberParam(size, "size");
  const direction = String(side || "").toLowerCase();
  if (entryPrice <= 0 || exitPrice <= 0 || units <= 0 || !["long", "short"].includes(direction))
    throw new Error("pass entry>0, exit>0, size>0, side=long|short");
  const pnl = (direction === "long" ? exitPrice - entryPrice : entryPrice - exitPrice) * units;
  const pnlPercent = pnl / (entryPrice * units) * 100;
  const result = { pnl: roundMoney(pnl), pnlPercent: roundValue(pnlPercent) };
  if (leverage !== undefined && leverage !== "") {
    const lev = numberParam(leverage, "leverage");
    if (lev <= 0) throw new Error("leverage must be >0 when provided");
    result.roePercent = roundValue(pnlPercent * lev);
  }
  return result;
}

export function impermanentLoss({ priceRatio }) {
  const ratio = numberParam(priceRatio, "priceRatio");
  if (ratio <= 0) throw new Error("priceRatio must be >0");
  return { ilPercent: roundValue((2 * Math.sqrt(ratio) / (1 + ratio) - 1) * 100) };
}

// ---- utility -----------------------------------------------------------
export function hashText({ text, algo = "sha256" }) {
  if (text === undefined) throw new Error("pass text");
  const algorithm = String(algo).toLowerCase();
  if (!["sha256", "sha512", "md5"].includes(algorithm)) throw new Error("algo must be sha256, sha512, or md5");
  return { digest: createHash(algorithm).update(String(text), "utf8").digest("hex") };
}

export function base64({ text, decode }) {
  if (text === undefined) throw new Error("pass text");
  if (!(decode === true || [undefined, "", "0", "false", "1", "true"].includes(decode)))
    throw new Error("decode must be 1 or true when provided");
  const shouldDecode = decode === true || decode === "1" || decode === "true";
  if (!shouldDecode) return { result: Buffer.from(String(text), "utf8").toString("base64") };
  const encoded = String(text);
  if (!/^[A-Za-z0-9+/]*={0,2}$/.test(encoded) || encoded.length % 4 === 1 || /=/.test(encoded.slice(0, -2)))
    throw new Error("text is not valid base64");
  const padded = encoded + "=".repeat((4 - encoded.length % 4) % 4);
  const result = Buffer.from(padded, "base64");
  if (result.toString("base64").replace(/=+$/, "") !== encoded.replace(/=+$/, "")) throw new Error("text is not valid base64");
  return { result: result.toString("utf8") };
}

export function timestamp({ value }) {
  if (value === undefined || value === "") throw new Error("pass value as unix seconds, unix millis, or ISO 8601");
  const raw = String(value).trim();
  let unixMillis;
  if (/^[+-]?\d+(?:\.\d+)?$/.test(raw)) {
    const numeric = numberParam(raw, "value");
    unixMillis = Math.abs(numeric) >= 1e11 ? numeric : numeric * 1000;
  } else {
    if (!/^\d{4}-\d{2}-\d{2}(?:T.*)?$/.test(raw)) throw new Error("value must be unix seconds, unix millis, or ISO 8601");
    unixMillis = Date.parse(raw);
  }
  const date = new Date(unixMillis);
  if (!Number.isFinite(unixMillis) || Number.isNaN(date.getTime())) throw new Error("invalid timestamp value");
  const millis = Math.trunc(date.getTime());
  return { unixSeconds: Math.floor(millis / 1000), unixMillis: millis, iso: date.toISOString(), utc: date.toUTCString() };
}

// ---- calc (arithmetic expression) --------------------------------------
// Deliberately hand-rolled shunting-yard limited to + - * / % ^ ( ) and numbers:
// expression evaluators on npm (expr-eval et al.) have code-execution CVE history, and a
// paid public endpoint must not carry that surface. Grammar is closed — no names, no calls.
export function calcEval(expr) {
  const src = String(expr);
  if (src.length > 200) throw new Error("expression too long (max 200 chars)");
  const tokens = src.match(/\d+\.?\d*(?:[eE][+-]?\d+)?|[()+\-*/%^]|\S/g) || [];
  const PREC = { "^": 4, u: 3, "*": 2, "/": 2, "%": 2, "+": 1, "-": 1 };
  const RIGHT = { u: true, "^": true };
  const out = [], ops = [];
  let prev = null; // null | "num" | "op" | "(" | ")"
  for (const tk of tokens) {
    if (/^[\d.]/.test(tk)) {
      const v = Number(tk);
      if (!Number.isFinite(v)) throw new Error(`bad number: ${tk}`);
      out.push(v); prev = "num";
    } else if (tk === "(") { ops.push(tk); prev = "(";
    } else if (tk === ")") {
      while (ops.length && ops[ops.length - 1] !== "(") out.push(ops.pop());
      if (!ops.length) throw new Error("unbalanced parentheses");
      ops.pop(); prev = ")";
    } else if (tk in PREC || tk === "-" || tk === "+") {
      const op = (tk === "-" && prev !== "num" && prev !== ")") ? "u"
        : (tk === "+" && prev !== "num" && prev !== ")") ? null : tk;
      if (op === null) { prev = "op"; continue; } // unary plus: no-op
      // prefix unary: push without popping (right-assoc, binds looser than ^ → -3^2 = -(3^2))
      if (op === "u") { ops.push(op); prev = "op"; continue; }
      while (ops.length) {
        const top = ops[ops.length - 1];
        if (top === "(") break;
        if (PREC[top] > PREC[op] || (PREC[top] === PREC[op] && !RIGHT[op])) out.push(ops.pop());
        else break;
      }
      ops.push(op); prev = "op";
    } else throw new Error(`unsupported token: ${tk}`);
  }
  while (ops.length) {
    const op = ops.pop();
    if (op === "(") throw new Error("unbalanced parentheses");
    out.push(op);
  }
  const st = [];
  for (const t of out) {
    if (typeof t === "number") { st.push(t); continue; }
    if (t === "u") { if (!st.length) throw new Error("bad expression"); st.push(-st.pop()); continue; }
    const b = st.pop(), a = st.pop();
    if (a === undefined || b === undefined) throw new Error("bad expression");
    st.push(t === "+" ? a + b : t === "-" ? a - b : t === "*" ? a * b
      : t === "/" ? a / b : t === "%" ? a % b : Math.pow(a, b));
  }
  if (st.length !== 1) throw new Error("bad expression");
  const result = st[0];
  if (!Number.isFinite(result)) throw new Error("non-finite result");
  return { expression: src, result };
}

// ---- json flatten -------------------------------------------------------
export function flattenJson(value, prefix = "", out = {}) {
  if (value !== null && typeof value === "object") {
    const entries = Array.isArray(value)
      ? value.map((v, i) => [`[${i}]`, v])
      : Object.entries(value).map(([k, v]) => [prefix ? `.${k}` : k, v]);
    if (!entries.length) out[prefix || "$"] = Array.isArray(value) ? [] : {};
    for (const [k, v] of entries) flattenJson(v, `${prefix}${k}`, out);
    return out;
  }
  out[prefix || "$"] = value;
  return out;
}

// ---- dns lookup ----------------------------------------------------------
const DNS_TYPES = new Set(["A", "AAAA", "MX", "TXT", "NS", "CNAME", "SOA"]);
const DOMAIN_RE = /^(?=.{1,253}$)[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$/i;
export async function dnsLookup(domain, type = "A") {
  const t = String(type).toUpperCase();
  if (!DNS_TYPES.has(t)) throw new Error(`type must be one of ${[...DNS_TYPES].join(",")}`);
  if (!DOMAIN_RE.test(String(domain))) throw new Error("invalid domain");
  const records = await new Resolver().resolve(domain, t);
  return { domain, type: t, records };
}

// ---- whois ----------------------------------------------------------------
function whoisQuery(server, q) {
  return new Promise((resolve, reject) => {
    let buf = "";
    const sock = createConnection(43, server, () => sock.write(q + "\r\n"));
    sock.setTimeout(10_000, () => { sock.destroy(); reject(new Error("whois timeout")); });
    sock.on("data", (d) => { buf += d; if (buf.length > 64_000) sock.destroy(); });
    sock.on("close", () => resolve(buf));
    sock.on("error", reject);
  });
}
export async function whois(domain) {
  if (!DOMAIN_RE.test(String(domain))) throw new Error("invalid domain");
  const iana = await whoisQuery("whois.iana.org", domain);
  const refer = iana.match(/^refer:\s*(\S+)/im)?.[1];
  if (!refer) return { domain, server: "whois.iana.org", raw: iana.slice(0, 10_000) };
  const raw = await whoisQuery(refer, domain);
  return { domain, server: refer, raw: raw.slice(0, 10_000) };
}

// ---- stock quote (free Yahoo chart API) -----------------------------------
export async function stockQuote(symbol) {
  const s = String(symbol).toUpperCase();
  if (!/^[A-Z0-9.^=-]{1,12}$/.test(s)) throw new Error("invalid symbol");
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(s)}?range=1d&interval=1d`;
  const resp = await fetch(url, { headers: { "user-agent": "Mozilla/5.0 (x402-primitive)" }, signal: AbortSignal.timeout(10_000) });
  if (!resp.ok) throw new Error(`quote fetch failed: HTTP ${resp.status}`);
  const meta = (await resp.json())?.chart?.result?.[0]?.meta;
  if (!meta || typeof meta.regularMarketPrice !== "number") throw new Error(`no quote for ${s}`);
  return {
    symbol: meta.symbol, price: meta.regularMarketPrice, currency: meta.currency,
    previousClose: meta.chartPreviousClose, exchange: meta.exchangeName, marketTime: meta.regularMarketTime,
  };
}
