/**
 * primitives.mjs — deterministic $0-cost compute primitives sold over x402 (serve.mjs mounts them).
 * Pure/IO-thin functions, no LLM in the serving path, importable without side effects (unit-testable).
 */
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
