"use strict";
// FIN-c — the earnings ledger and the monthly report.
//
// The thing that can go wrong here is not a crash, it is a flattering number. A ledger that lets a row
// be edited, a rollup that clamps a loss to zero, or a formatter that rounds a fraction of a cent in
// our favour would all keep the tests green while lying to the person the money belongs to. So the
// tests below are mostly about arithmetic that refuses to be generous and copy that refuses to hide.

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  EARNING_KINDS,
  usdMinorFromAtomic,
  formatUsdMinor,
  abbreviateAddress,
  appendEarning,
  monthBounds,
  rollUpMonth,
  formatMonthlyReport,
} = require("./earnings-ledger.js");

// The live agent wallet (FIN-a). Checksummed exactly as the chain knows it.
const WALLET = "0x477EeE969ccfdc0e959F38cE8B83e372FC0262ad";
const OTHER_WALLET = "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf";

function income(overrides = {}) {
  return {
    entry_key: "earn-loop:2026-07-10:001",
    wallet_address: WALLET,
    kind: "financial_external_income",
    amount_minor: 12430,
    currency: "USD",
    occurred_at: "2026-07-10T04:00:00.000Z",
    source: "earn_loop",
    ...overrides,
  };
}

test("the ledger only accepts the kinds spec 9.9 defines, so nothing arrives uncategorised", () => {
  assert.deepEqual([...EARNING_KINDS].sort(), [
    "financial_deposit",
    "financial_external_income",
    "financial_fee",
    "financial_internal_move",
    "financial_realized_loss",
    "financial_self_funding",
    "financial_unverified",
    "financial_user_transfer",
  ]);
  assert.throws(() => appendEarning([], income({ kind: "profit" })), /kind/i);
});

test("appending never mutates what is already recorded", () => {
  const first = appendEarning([], income());
  const second = appendEarning(first, income({ entry_key: "earn-loop:2026-07-11:001", amount_minor: 100 }));

  assert.equal(first.length, 1);
  assert.equal(second.length, 2);
  assert.notEqual(first, second, "append must return a new ledger rather than push into the old one");
  assert.throws(() => {
    second[0].amount_minor = 999999;
  }, "a recorded row must be frozen — a ledger you can edit is not evidence");
  assert.equal(second[0].amount_minor, 12430);
});

test("a repeated entry key is refused, so an earn-loop retry cannot book the same revenue twice", () => {
  const ledger = appendEarning([], income());
  assert.throws(() => appendEarning(ledger, income({ amount_minor: 999 })), /duplicate/i);
  assert.equal(ledger.length, 1);
});

test("an entry without an idempotency key is refused rather than recorded hopefully", () => {
  assert.throws(() => appendEarning([], income({ entry_key: "" })), /entry_key/i);
});

test("the wallet address must be the real checksummed one, so a mistyped address cannot be booked", () => {
  assert.throws(() => appendEarning([], income({ wallet_address: WALLET.toLowerCase() })), /checksum/i);
  assert.throws(() => appendEarning([], income({ wallet_address: "0xdead" })), /address/i);
});

test("amounts are integer minor units — a float is refused instead of being rounded into place", () => {
  for (const bad of [12430.5, "12430.5", Number.NaN, Number.POSITIVE_INFINITY, null, undefined]) {
    assert.throws(() => appendEarning([], income({ amount_minor: bad })), /amount/i, `${bad} must be refused`);
  }
  assert.throws(() => appendEarning([], income({ amount_minor: -1 })), /amount/i,
    "direction is carried by the kind, never by a negative amount");
  assert.equal(appendEarning([], income({ amount_minor: "12430" }))[0].amount_minor, 12430);
});

test("a private key can never enter the ledger, not even nested", () => {
  assert.throws(() => appendEarning([], income({ privateKey: "ab".repeat(32) })), /secret/i);
  assert.throws(() => appendEarning([], income({ meta: { wallet: { private_key: "ab".repeat(32) } } })), /secret/i);
});

test("a transaction hash, when present, has to look like one", () => {
  assert.throws(() => appendEarning([], income({ tx_hash: "0x123" })), /tx_hash/i);
  const ok = appendEarning([], income({ tx_hash: `0x${"a".repeat(64)}` }));
  assert.equal(ok[0].tx_hash, `0x${"a".repeat(64)}`);
});

test("on-chain atomic units convert exactly or not at all — never rounded toward a nicer number", () => {
  // USDC on Base carries six decimals; a US cent is four of those decimals wide.
  assert.equal(usdMinorFromAtomic("124300000", 6), 12430);
  assert.equal(usdMinorFromAtomic(0n, 6), 0);
  assert.equal(usdMinorFromAtomic("1000000", 6), 100);
  // 0.012345 USD is not a whole number of cents. Rounding it down would quietly shave revenue;
  // rounding it up would invent revenue. Both are refused.
  assert.throws(() => usdMinorFromAtomic("12345", 6), /exact/i);
  assert.throws(() => usdMinorFromAtomic("1", 6), /exact/i);
  assert.throws(() => usdMinorFromAtomic("-100", 6), /negative/i);
});

test("money is formatted from integers, so no float error can creep into the report", () => {
  assert.equal(formatUsdMinor(12430), "$124.30");
  assert.equal(formatUsdMinor(0), "$0.00");
  assert.equal(formatUsdMinor(5), "$0.05");
  assert.equal(formatUsdMinor(-1240), "-$12.40");
  assert.equal(formatUsdMinor(12430, { signed: true }), "+$124.30");
  assert.equal(formatUsdMinor(-1240, { signed: true }), "-$12.40");
  assert.equal(formatUsdMinor(0, { signed: true }), "+$0.00");
  // 0.1 + 0.2 territory: the classic float sum must not appear.
  assert.equal(formatUsdMinor(10 + 20), "$0.30");
});

test("the address in the report is abbreviated the way spec 9.11 writes it, casing intact", () => {
  assert.equal(abbreviateAddress(WALLET), "0x477E…62ad");
  assert.equal(abbreviateAddress("0x3EcCaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa8749"), "0x3EcC…8749");
});

test("the month is a calendar month in the user's timezone, half-open", () => {
  const july = monthBounds({ year: 2026, month: 7, timezone: "Asia/Tokyo" });
  assert.equal(new Date(july.startMs).toISOString(), "2026-06-30T15:00:00.000Z");
  assert.equal(new Date(july.endMs).toISOString(), "2026-07-31T15:00:00.000Z");

  const december = monthBounds({ year: 2026, month: 12, timezone: "UTC" });
  assert.equal(new Date(december.startMs).toISOString(), "2026-12-01T00:00:00.000Z");
  assert.equal(new Date(december.endMs).toISOString(), "2027-01-01T00:00:00.000Z");
});

test("the rollup sums the month exactly and keeps the transfer out of the net", () => {
  let ledger = [];
  ledger = appendEarning(ledger, income({ entry_key: "a", amount_minor: 12430 }));
  ledger = appendEarning(ledger, income({ entry_key: "b", kind: "financial_fee", amount_minor: 820 }));
  ledger = appendEarning(ledger, income({ entry_key: "c", kind: "financial_user_transfer", amount_minor: 10000 }));

  const summary = rollUpMonth(ledger, {
    year: 2026, month: 7, timezone: "Asia/Tokyo", walletAddress: WALLET, balanceMinor: 20350,
  });

  assert.equal(summary.gross_income_minor, 12430);
  assert.equal(summary.fee_minor, 820);
  assert.equal(summary.user_transfer_minor, 10000);
  assert.equal(summary.net_minor, 11610, "the transfer is money moved, not money lost");
  assert.equal(summary.balance_minor, 20350);
  assert.equal(summary.is_loss, false);
  assert.equal(summary.counted_rows, 3);
});

test("an atomic pUSD balance stays exact through rollup and report rendering", () => {
  const summary = rollUpMonth([], {
    year: 2026,
    month: 7,
    timezone: "Asia/Tokyo",
    walletAddress: WALLET,
    balanceAtomic: "4422182",
    balanceDecimals: 6,
    currency: "USD",
  });

  assert.equal(summary.balance_minor, null);
  assert.equal(summary.balance_atomic, "4422182");
  assert.equal(summary.balance_decimals, 6);
  assert.match(formatMonthlyReport(summary), /・私の残高: \$4\.422182/);
});

test("the rollup accepts exactly one measured balance representation", () => {
  const base = {
    year: 2026, month: 7, timezone: "Asia/Tokyo", walletAddress: WALLET, currency: "USD",
  };

  assert.throws(() => rollUpMonth([], base), /balance/i);
  assert.throws(() => rollUpMonth([], {
    ...base, balanceMinor: 442, balanceAtomic: "4422182", balanceDecimals: 6,
  }), /balance/i);
  assert.throws(() => rollUpMonth([], {
    ...base, balanceAtomic: "4422182",
  }), /decimals/i);
  assert.throws(() => rollUpMonth([], {
    ...base, balanceAtomic: "4.422182", balanceDecimals: 6,
  }), /atomic/i);
  assert.throws(() => rollUpMonth([], {
    ...base, balanceAtomic: "-1", balanceDecimals: 6,
  }), /atomic|negative/i);
  assert.throws(() => rollUpMonth([], {
    ...base, balanceAtomic: "4422182", balanceDecimals: 37,
  }), /decimals/i);
});

test("a losing month reports the loss — it is never clamped to zero the way the panel ratio clamps it", () => {
  let ledger = [];
  ledger = appendEarning(ledger, income({ entry_key: "a", amount_minor: 800 }));
  ledger = appendEarning(ledger, income({ entry_key: "b", kind: "financial_fee", amount_minor: 320 }));
  ledger = appendEarning(ledger, income({ entry_key: "c", kind: "financial_realized_loss", amount_minor: 1720 }));

  const summary = rollUpMonth(ledger, {
    year: 2026, month: 7, timezone: "Asia/Tokyo", walletAddress: WALLET, balanceMinor: 19110,
  });

  assert.equal(summary.net_minor, -1240);
  assert.equal(summary.is_loss, true);
});

test("excluded rows never reach the numbers, only the count", () => {
  let ledger = [];
  ledger = appendEarning(ledger, income({ entry_key: "a", amount_minor: 5000 }));
  for (const kind of ["financial_self_funding", "financial_deposit", "financial_internal_move", "financial_unverified"]) {
    ledger = appendEarning(ledger, income({ entry_key: kind, kind, amount_minor: 999999 }));
  }
  const summary = rollUpMonth(ledger, {
    year: 2026, month: 7, timezone: "Asia/Tokyo", walletAddress: WALLET, balanceMinor: 5000,
  });
  assert.equal(summary.gross_income_minor, 5000, "our own money is not income");
  assert.equal(summary.excluded_rows, 4);
  assert.equal(summary.counted_rows, 1);
});

test("rows outside the month are left out, and the boundary is half-open", () => {
  let ledger = [];
  ledger = appendEarning(ledger, income({ entry_key: "before", occurred_at: "2026-06-30T14:59:59.999Z", amount_minor: 100 }));
  ledger = appendEarning(ledger, income({ entry_key: "first", occurred_at: "2026-06-30T15:00:00.000Z", amount_minor: 200 }));
  ledger = appendEarning(ledger, income({ entry_key: "last", occurred_at: "2026-07-31T14:59:59.999Z", amount_minor: 400 }));
  ledger = appendEarning(ledger, income({ entry_key: "after", occurred_at: "2026-07-31T15:00:00.000Z", amount_minor: 800 }));

  const summary = rollUpMonth(ledger, {
    year: 2026, month: 7, timezone: "Asia/Tokyo", walletAddress: WALLET, balanceMinor: 600,
  });
  assert.equal(summary.gross_income_minor, 600);
});

test("another wallet's rows are refused outright rather than quietly folded in", () => {
  const ledger = appendEarning([], income({ wallet_address: OTHER_WALLET }));
  assert.throws(() => rollUpMonth(ledger, {
    year: 2026, month: 7, timezone: "Asia/Tokyo", walletAddress: WALLET, balanceMinor: 0,
  }), /wallet/i);
});

test("mixed currencies are refused — adding yen to dollars would produce a fictional total", () => {
  let ledger = appendEarning([], income({ entry_key: "usd", amount_minor: 100 }));
  ledger = appendEarning(ledger, income({ entry_key: "jpy", currency: "JPY", amount_minor: 100 }));
  assert.throws(() => rollUpMonth(ledger, {
    year: 2026, month: 7, timezone: "Asia/Tokyo", walletAddress: WALLET, balanceMinor: 0,
  }), /currency/i);
});

test("a report cannot be produced without a measured balance", () => {
  assert.throws(() => rollUpMonth([], {
    year: 2026, month: 7, timezone: "Asia/Tokyo", walletAddress: WALLET,
  }), /balance/i);
});

test("a profitable month renders spec 9.11 verbatim", () => {
  let ledger = [];
  ledger = appendEarning(ledger, income({ entry_key: "a", amount_minor: 12430 }));
  ledger = appendEarning(ledger, income({ entry_key: "b", kind: "financial_fee", amount_minor: 820 }));
  ledger = appendEarning(ledger, income({ entry_key: "c", kind: "financial_user_transfer", amount_minor: 10000 }));
  const summary = rollUpMonth(ledger, {
    year: 2026, month: 7, timezone: "Asia/Tokyo", walletAddress: WALLET, balanceMinor: 20350,
  });

  assert.equal(formatMonthlyReport(summary), [
    "💰 今月の収支報告です。",
    "・私のwalletでの収益: +$124.30",
    "・あなたへの送金: $100.00（送金済み）",
    "・手数料・実費: $8.20",
    "・私の残高: $203.50",
    "取引はすべてこちらで確認できます: basescan.org/address/0x477E…62ad",
  ].join("\n"));
});

test("a losing month renders the honest 9.11 loss copy, not a suppressed or softened one", () => {
  let ledger = [];
  ledger = appendEarning(ledger, income({ entry_key: "a", amount_minor: 800 }));
  ledger = appendEarning(ledger, income({ entry_key: "b", kind: "financial_fee", amount_minor: 320 }));
  ledger = appendEarning(ledger, income({ entry_key: "c", kind: "financial_realized_loss", amount_minor: 1720 }));
  const summary = rollUpMonth(ledger, {
    year: 2026, month: 7, timezone: "Asia/Tokyo", walletAddress: WALLET, balanceMinor: 19110,
  });

  const text = formatMonthlyReport(summary, {
    cause: "x402の試行が想定より外れたこと",
    plan: "単価の高い依頼だけに絞ること",
  });

  assert.equal(text, [
    "💰 今月の収支報告です。",
    "・収益: -$12.40（マイナスでした）",
    "・送金: なし（利益が出た月のみ送金します）",
    "・私の残高: $191.10",
    "先月比の要因: x402の試行が想定より外れたこと。来月の方針: 単価の高い依頼だけに絞ること。",
    "取引はすべてこちらで確認できます: basescan.org/address/0x477E…62ad",
  ].join("\n"));
});

test("a losing month cannot be reported with placeholder reasoning", () => {
  const summary = rollUpMonth(
    appendEarning([], income({ kind: "financial_realized_loss", amount_minor: 1 })),
    { year: 2026, month: 7, timezone: "Asia/Tokyo", walletAddress: WALLET, balanceMinor: 0 },
  );
  assert.equal(summary.is_loss, true);
  assert.throws(() => formatMonthlyReport(summary), /cause|plan/i);
  assert.throws(() => formatMonthlyReport(summary, { cause: "◯◯", plan: "△△" }), /placeholder/i);
});

test("a losing month that did send money refuses the copy that claims it sent none", () => {
  let ledger = appendEarning([], income({ entry_key: "a", kind: "financial_realized_loss", amount_minor: 5000 }));
  ledger = appendEarning(ledger, income({ entry_key: "b", kind: "financial_user_transfer", amount_minor: 2000 }));
  const summary = rollUpMonth(ledger, {
    year: 2026, month: 7, timezone: "Asia/Tokyo", walletAddress: WALLET, balanceMinor: 0,
  });
  assert.equal(summary.is_loss, true);
  assert.equal(summary.user_transfer_minor, 2000);
  assert.throws(() => formatMonthlyReport(summary, { cause: "gas代", plan: "様子を見ること" }), /transfer/i);
});

test("the report is refused in a currency its copy was never written for", () => {
  const summary = rollUpMonth(appendEarning([], income({ currency: "JPY", amount_minor: 840000 })), {
    year: 2026, month: 7, timezone: "Asia/Tokyo", walletAddress: WALLET, balanceMinor: 840000,
  });
  assert.throws(() => formatMonthlyReport(summary), /currency/i);
});

test("a one-cent loss is still a loss — it does not round into a flat month", () => {
  const summary = rollUpMonth(
    appendEarning([], income({ kind: "financial_realized_loss", amount_minor: 1 })),
    { year: 2026, month: 7, timezone: "Asia/Tokyo", walletAddress: WALLET, balanceMinor: 0 },
  );
  const text = formatMonthlyReport(summary, { cause: "gas代", plan: "手数料の安い時間帯に寄せること" });
  assert.match(text, /・収益: -\$0\.01（マイナスでした）/);
  assert.doesNotMatch(text, /\$0\.00（マイナス/);
});

test("a month with nothing earned is reported as nothing earned, not skipped", () => {
  const summary = rollUpMonth([], {
    year: 2026, month: 7, timezone: "Asia/Tokyo", walletAddress: WALLET, balanceMinor: 0, currency: "USD",
  });
  assert.equal(summary.net_minor, 0);
  assert.equal(summary.is_loss, false);
  const text = formatMonthlyReport(summary);
  assert.match(text, /・私のwalletでの収益: \+\$0\.00/);
  assert.match(text, /・あなたへの送金: なし（利益が出た月のみ送金します）/);
  assert.match(text, /basescan\.org\/address\/0x477E…62ad/);
});

test("a realized loss inside a profitable month is shown, never absorbed silently", () => {
  let ledger = appendEarning([], income({ entry_key: "a", amount_minor: 10000 }));
  ledger = appendEarning(ledger, income({ entry_key: "b", kind: "financial_fee", amount_minor: 100 }));
  ledger = appendEarning(ledger, income({ entry_key: "c", kind: "financial_realized_loss", amount_minor: 2500 }));
  const summary = rollUpMonth(ledger, {
    year: 2026, month: 7, timezone: "Asia/Tokyo", walletAddress: WALLET, balanceMinor: 7400,
  });
  assert.equal(summary.net_minor, 7400);
  assert.match(formatMonthlyReport(summary), /・手数料・実費: \$26\.00/);
});

test("the report never carries a raw address, a table name, or anything secret", () => {
  const summary = rollUpMonth(appendEarning([], income()), {
    year: 2026, month: 7, timezone: "Asia/Tokyo", walletAddress: WALLET, balanceMinor: 12430,
  });
  const text = formatMonthlyReport(summary);
  assert.doesNotMatch(text, /lm_agent_earnings|entry_key|privateKey|SELECT/i);
  assert.equal(text.includes(WALLET), false, "9.11 abbreviates the address; the full one belongs on the chain");
});
