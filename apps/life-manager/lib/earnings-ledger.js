"use strict";
// FIN-c — the agent's earnings ledger and the monthly report it produces.
//
// Spec 9.8 puts FINANCIAL on the crypto rail: the agent earns into its own wallet, and what it tells
// the user each month has to be checkable against that chain. The whole risk in this file is a
// flattering number, not a crash. So three rules run through it.
//
// Money is integers. Every amount is whole minor units held and summed as BigInt, because a cent that
// arrives as 0.1 + 0.2 is a cent nobody can reconcile against a block explorer. On-chain atomic units
// convert exactly or they are refused — rounding down shaves the user's revenue, rounding up invents
// it, and picking one is how a ledger starts drifting from the chain.
//
// Direction lives in the kind, never in a sign. A stored negative amount is the easiest way to book a
// loss as income by accident, so amounts are non-negative and the kind vocabulary is the one spec 9.9
// already fixed for the panel score — sharing it means the report and the score cannot disagree.
//
// A loss is reported as a loss. The panel score clamps net income at zero because a ratio cannot be
// negative; this must not, because the person reading it is owed the real number. Spec 9.11's
// 盛らない原則 is implemented literally: a losing month gets the loss copy, and it cannot be rendered
// without a real cause and a real plan.

const { toChecksumAddress } = require("./agent-wallet.js");
const { FINANCIAL_STRINGS } = require("./i18n.js");

const EARNING_KINDS = Object.freeze([
  "financial_external_income",
  "financial_realized_loss",
  "financial_fee",
  "financial_user_transfer",
  "financial_self_funding",
  "financial_deposit",
  "financial_internal_move",
  "financial_unverified",
]);

// Money we moved to ourselves is not money we earned. Spec 9.9 excludes these from both sides.
const EXCLUDED_KINDS = new Set([
  "financial_self_funding", "financial_deposit", "financial_internal_move", "financial_unverified",
]);

const SECRET_KEYS = new Set([
  "privatekey", "private_key", "mnemonic", "seed", "secretkey", "secret_key", "secret",
]);

const MAX_MINOR = BigInt(Number.MAX_SAFE_INTEGER);

function fail(message) {
  throw new Error(message);
}

// A key nested three objects deep leaks exactly as completely as one at the top, so the scan is deep
// and runs before anything else — an entry carrying a secret is never partially processed.
function assertNoSecret(value, depth = 0) {
  if (depth > 8 || !value || typeof value !== "object") return;
  if (Array.isArray(value)) {
    for (const item of value) assertNoSecret(item, depth + 1);
    return;
  }
  for (const [key, nested] of Object.entries(value)) {
    if (SECRET_KEYS.has(String(key).toLowerCase())) fail("a secret field can never enter the ledger");
    assertNoSecret(nested, depth + 1);
  }
}

function normaliseAddress(value) {
  const raw = String(value == null ? "" : value).trim();
  if (!/^0x[0-9a-fA-F]{40}$/.test(raw)) fail(`wallet address is not an Ethereum address: ${raw.slice(0, 10)}`);
  const checksummed = toChecksumAddress(raw.slice(2).toLowerCase());
  // EIP-55 exists so a mistyped address is detectable. Accepting a lowercase address would throw that
  // away, and money sent to a nearly-right address is gone.
  if (raw !== checksummed) fail("wallet address fails its EIP-55 checksum");
  return checksummed;
}

function normaliseMinor(value) {
  if (typeof value === "bigint") {
    if (value < 0n) fail("amount_minor must not be negative — direction is carried by the kind");
    if (value > MAX_MINOR) fail("amount_minor is outside the supported range");
    return value;
  }
  const raw = String(value == null ? "" : value).trim();
  // Deliberately strict: "124.30" is refused rather than rounded, because whichever way we rounded it
  // the ledger would stop matching the chain.
  if (!/^\d+$/.test(raw)) fail(`amount_minor must be whole minor units, got ${JSON.stringify(value)}`);
  const parsed = BigInt(raw);
  if (parsed > MAX_MINOR) fail("amount_minor is outside the supported range");
  return parsed;
}

function normaliseInstant(value) {
  const ms = Date.parse(String(value == null ? "" : value));
  if (!Number.isFinite(ms)) fail(`occurred_at is not a timestamp: ${JSON.stringify(value)}`);
  return new Date(ms).toISOString();
}

function normaliseEntry(entry) {
  if (!entry || typeof entry !== "object") fail("an earning entry must be an object");
  assertNoSecret(entry);

  const entryKey = String(entry.entry_key == null ? "" : entry.entry_key).trim();
  if (!entryKey) fail("entry_key is required — without it a retry cannot be told from new revenue");
  if (!EARNING_KINDS.includes(entry.kind)) fail(`unknown earning kind ${JSON.stringify(entry.kind)}`);
  const currency = String(entry.currency == null ? "" : entry.currency).trim();
  if (!/^[A-Z]{3}$/.test(currency)) fail(`currency must be a three-letter ISO code, got ${JSON.stringify(entry.currency)}`);

  const row = {
    entry_key: entryKey,
    wallet_address: normaliseAddress(entry.wallet_address),
    kind: entry.kind,
    amount_minor: Number(normaliseMinor(entry.amount_minor)),
    currency,
    occurred_at: normaliseInstant(entry.occurred_at),
    tx_hash: null,
    source: entry.source == null ? null : String(entry.source),
    meta: entry.meta == null ? {} : entry.meta,
  };

  if (entry.tx_hash != null && String(entry.tx_hash) !== "") {
    const hash = String(entry.tx_hash).trim();
    if (!/^0x[0-9a-fA-F]{64}$/.test(hash)) fail(`tx_hash is not a transaction hash: ${hash.slice(0, 12)}`);
    row.tx_hash = hash;
  }

  return Object.freeze(row);
}

// Append-only in the same sense the table is: the caller gets a new array and the rows it already had
// are frozen. A ledger you can quietly edit is not evidence of anything.
function appendEarning(rows, entry) {
  const existing = Array.isArray(rows) ? rows : [];
  const row = normaliseEntry(entry);
  for (const previous of existing) {
    if (previous && previous.entry_key === row.entry_key && previous.wallet_address === row.wallet_address) {
      fail(`duplicate entry_key ${row.entry_key} — this revenue is already recorded`);
    }
  }
  return Object.freeze([...existing, row]);
}

// Exact conversion or nothing. USDC on Base carries six decimals and a US cent is four of them wide,
// so most atomic amounts are not a whole number of cents; the caller has to decide what to do about
// that rather than have this quietly pick the direction that reads better.
function usdMinorFromAtomic(atomicUnits, decimals, minorExponent = 2) {
  const raw = typeof atomicUnits === "bigint" ? atomicUnits.toString() : String(atomicUnits == null ? "" : atomicUnits).trim();
  if (/^-/.test(raw)) fail("atomic amount must not be negative");
  if (!/^\d+$/.test(raw)) fail(`atomic amount must be an integer, got ${JSON.stringify(atomicUnits)}`);
  if (!Number.isInteger(decimals) || decimals < 0 || decimals > 36) fail("decimals must be a small non-negative integer");
  if (decimals < minorExponent) fail("token has fewer decimals than the currency's minor unit");
  const divisor = 10n ** BigInt(decimals - minorExponent);
  const value = BigInt(raw);
  if (value % divisor !== 0n) fail(`${raw} atomic units are not an exact number of minor units`);
  const minor = value / divisor;
  if (minor > MAX_MINOR) fail("amount is outside the supported range");
  return Number(minor);
}

function formatUsdMinor(minor, { signed = false } = {}) {
  const value = typeof minor === "bigint" ? minor : BigInt(Math.trunc(Number(minor)));
  const negative = value < 0n;
  const absolute = negative ? -value : value;
  const body = `$${absolute / 100n}.${String(absolute % 100n).padStart(2, "0")}`;
  if (negative) return `-${body}`;
  return signed ? `+${body}` : body;
}

function normaliseAtomicBalance(value, decimals) {
  const raw = typeof value === "bigint" ? value.toString() : String(value == null ? "" : value).trim();
  if (!/^\d+$/.test(raw)) fail(`balance atomic amount must be a non-negative integer, got ${JSON.stringify(value)}`);
  if (!Number.isInteger(decimals) || decimals < 0 || decimals > 36) {
    fail("balance decimals must be a small non-negative integer");
  }
  return { atomic: BigInt(raw).toString(), decimals };
}

function formatUsdAtomic(atomic, decimals) {
  const balance = normaliseAtomicBalance(atomic, decimals);
  const padded = balance.atomic.padStart(balance.decimals + 1, "0");
  const whole = balance.decimals === 0 ? padded : padded.slice(0, -balance.decimals);
  const fraction = balance.decimals === 0 ? "" : `.${padded.slice(-balance.decimals)}`;
  return `$${whole}${fraction}`;
}

// Spec 9.11 writes the address as 0x3EcC…8749: six leading characters, four trailing, checksum casing
// intact so the abbreviation still matches what a block explorer shows.
function abbreviateAddress(address) {
  const raw = String(address == null ? "" : address).trim();
  if (!/^0x[0-9a-fA-F]{40}$/.test(raw)) fail("cannot abbreviate a value that is not an address");
  return `${raw.slice(0, 6)}…${raw.slice(-4)}`;
}

const FORMATTERS = new Map();
function zoneFormatter(timeZone) {
  if (!FORMATTERS.has(timeZone)) {
    FORMATTERS.set(timeZone, new Intl.DateTimeFormat("en-CA", {
      timeZone, year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
    }));
  }
  return FORMATTERS.get(timeZone);
}

function wallEpoch(ms, timeZone) {
  const parts = Object.fromEntries(zoneFormatter(timeZone).formatToParts(new Date(ms))
    .filter((part) => part.type !== "literal").map((part) => [part.type, part.value]));
  return Date.UTC(Number(parts.year), Number(parts.month) - 1, Number(parts.day), Number(parts.hour), Number(parts.minute), Number(parts.second));
}

// Midnight on the first of a month, resolved in the user's zone. Two passes, because the offset that
// applies is the offset at the answer, not at the guess.
function resolveMonthStart(year, month, timeZone) {
  const target = Date.UTC(year, month - 1, 1);
  let guess = target - (wallEpoch(target, timeZone) - target);
  guess = target - (wallEpoch(guess, timeZone) - guess);
  return guess;
}

function monthBounds({ year, month, timezone = "UTC" } = {}) {
  if (!Number.isInteger(year) || !Number.isInteger(month) || month < 1 || month > 12) {
    fail("a month is an integer year and a month between 1 and 12");
  }
  let zone = String(timezone || "UTC");
  try {
    new Intl.DateTimeFormat("en", { timeZone: zone }).format(0);
  } catch {
    fail(`unknown timezone ${zone}`);
  }
  const nextYear = month === 12 ? year + 1 : year;
  const nextMonth = month === 12 ? 1 : month + 1;
  // Half-open, per spec 9.9: the last instant of the month belongs to the month, the first instant of
  // the next one does not, and no row can land in both.
  return { startMs: resolveMonthStart(year, month, zone), endMs: resolveMonthStart(nextYear, nextMonth, zone), timezone: zone };
}

function rollUpMonth(rows, options = {}) {
  const {
    year, month, timezone = "UTC", walletAddress,
    balanceMinor, balanceAtomic, balanceDecimals,
    explorerBaseUrl = "basescan.org",
    currency: fallbackCurrency = "USD",
  } = options;
  const wallet = normaliseAddress(walletAddress);
  const explorer = String(explorerBaseUrl == null ? "" : explorerBaseUrl).trim();
  if (!/^[a-z0-9.-]+$/i.test(explorer)) fail("explorerBaseUrl must be a plain hostname");
  const hasMinor = balanceMinor != null;
  const hasAtomic = balanceAtomic != null;
  const hasDecimals = balanceDecimals != null;
  if (hasMinor && (hasAtomic || hasDecimals)) {
    fail("supply exactly one measured balance representation, not both minor and atomic");
  }
  if (!hasMinor && !hasAtomic) {
    fail("a measured balance is required — a report without one is a guess");
  }
  if (hasAtomic !== hasDecimals) {
    fail("an atomic balance and its decimals are required together");
  }
  const minorBalance = hasMinor ? normaliseMinor(balanceMinor) : null;
  const atomicBalance = hasAtomic ? normaliseAtomicBalance(balanceAtomic, balanceDecimals) : null;
  const { startMs, endMs } = monthBounds({ year, month, timezone });

  const totals = { financial_external_income: 0n, financial_realized_loss: 0n, financial_fee: 0n, financial_user_transfer: 0n };
  const currencies = new Set();
  let counted = 0;
  let excluded = 0;

  for (const raw of Array.isArray(rows) ? rows : []) {
    const row = normaliseEntry(raw);
    // Refused, not skipped: silently dropping another wallet's rows would let a misrouted write vanish
    // instead of being noticed.
    if (row.wallet_address !== wallet) fail(`row ${row.entry_key} belongs to a different wallet`);
    const at = Date.parse(row.occurred_at);
    if (at < startMs || at >= endMs) continue;
    if (EXCLUDED_KINDS.has(row.kind)) {
      excluded += 1;
      continue;
    }
    counted += 1;
    currencies.add(row.currency);
    totals[row.kind] += BigInt(row.amount_minor);
  }

  if (currencies.size > 1) fail(`the month mixes more than one currency (${[...currencies].sort().join(", ")}) and cannot be summed`);
  const currency = currencies.size ? [...currencies][0] : String(fallbackCurrency || "USD");

  const gross = totals.financial_external_income;
  const loss = totals.financial_realized_loss;
  const fee = totals.financial_fee;
  const transfer = totals.financial_user_transfer;
  // Not clamped. The panel ratio floors this at zero because a percentage cannot be negative; the
  // report must not, or every losing month would read as a flat one.
  const net = gross - loss - fee;

  return Object.freeze({
    year, month, timezone, wallet_address: wallet, currency,
    period_start: new Date(startMs).toISOString(),
    period_end: new Date(endMs).toISOString(),
    gross_income_minor: Number(gross),
    realized_loss_minor: Number(loss),
    fee_minor: Number(fee),
    user_transfer_minor: Number(transfer),
    net_minor: Number(net),
    balance_minor: minorBalance == null ? null : Number(minorBalance),
    balance_atomic: atomicBalance == null ? null : atomicBalance.atomic,
    balance_decimals: atomicBalance == null ? null : atomicBalance.decimals,
    explorer_base_url: explorer,
    is_loss: net < 0n,
    counted_rows: counted,
    excluded_rows: excluded,
  });
}

// The glyphs spec 9.11 uses to stand in for the real reasoning. If one reaches the user it means we
// sent a template instead of an explanation.
const PLACEHOLDER = /[◯○◎△▲▽◇□■●]|\bTBD\b|\bTODO\b|^[.。・…\s]*$/i;

function requireReasoning(value, label) {
  const text = String(value == null ? "" : value).trim();
  if (!text) fail(`a losing month needs a real ${label} before it can be reported`);
  if (PLACEHOLDER.test(text)) fail(`the ${label} is still a placeholder`);
  return text;
}

function fill(template, values) {
  return template.replace(/\{(\w+)\}/g, (_match, key) => String(values[key]));
}

function formatMonthlyReport(summary, { cause, plan, locale = "ja" } = {}) {
  if (!summary || typeof summary !== "object") fail("a report needs a rollup");
  const strings = FINANCIAL_STRINGS[locale];
  if (!strings) fail(`no FINANCIAL copy for locale ${locale}`);
  // The 9.11 copy is written in dollars. Rendering yen through it would put a $ in front of a JPY
  // amount, which is worse than having no report.
  if (summary.currency !== "USD") fail(`the 9.11 monthly copy is written for the USD currency, not ${summary.currency}`);

  const address = abbreviateAddress(summary.wallet_address);
  const verify = fill(strings.monthly.verify, {
    address,
    explorer: summary.explorer_base_url || "basescan.org",
  });
  const balanceValue = summary.balance_atomic == null
    ? formatUsdMinor(summary.balance_minor)
    : formatUsdAtomic(summary.balance_atomic, summary.balance_decimals);
  const balance = fill(strings.monthly.balance, { balance: balanceValue });

  if (summary.is_loss) {
    // The loss copy states outright that nothing was sent. If something was, the copy would be a lie
    // and there is no verbatim line for that case — better to refuse than to improvise one.
    if (summary.user_transfer_minor > 0) {
      fail("a losing month recorded a user transfer; the 9.11 loss copy claims none was sent");
    }
    return [
      strings.monthly.header,
      fill(strings.monthlyLoss.revenue, { revenue: formatUsdMinor(summary.net_minor) }),
      strings.monthlyLoss.transfer,
      balance,
      fill(strings.monthlyLoss.outlook, { cause: requireReasoning(cause, "cause"), plan: requireReasoning(plan, "plan") }),
      verify,
    ].join("\n");
  }

  const transferLine = summary.user_transfer_minor > 0
    ? fill(strings.monthly.transfer, { transfer: formatUsdMinor(summary.user_transfer_minor) })
    : strings.monthly.transferNone;

  return [
    strings.monthly.header,
    fill(strings.monthly.revenue, { revenue: formatUsdMinor(summary.gross_income_minor, { signed: true }) }),
    transferLine,
    // A realized loss inside a profitable month has no line of its own in 9.11. It is shown here with
    // the fees rather than netted invisibly into the revenue figure, because money that left is money
    // the user should see leaving.
    fill(strings.monthly.cost, { cost: formatUsdMinor(summary.fee_minor + summary.realized_loss_minor) }),
    balance,
    verify,
  ].join("\n");
}

module.exports = {
  EARNING_KINDS,
  EXCLUDED_KINDS,
  normaliseEntry,
  appendEarning,
  usdMinorFromAtomic,
  formatUsdMinor,
  formatUsdAtomic,
  abbreviateAddress,
  monthBounds,
  rollUpMonth,
  formatMonthlyReport,
};
