import { test } from "node:test";
import assert from "node:assert/strict";
import {
  mortgage, loanPayoff, roi, npv, irr, dcf, cagr, aprApy, breakEven, presentValue,
  futureValueAnnuity, savingsGoal, percentChange, inflationAdjust, positionSize, kelly,
  liquidationPrice, perpPnl, impermanentLoss, hashText, base64, timestamp,
} from "../primitives.mjs";

test("mortgage calculates amortized and zero-rate loans", () => {
  assert.deepEqual(mortgage({ principal: 300000, rate: 6, years: 30 }), {
    monthlyPayment: 1798.65, totalPaid: 647514.57, totalInterest: 347514.57,
  });
  assert.deepEqual(mortgage({ principal: 1200, rate: 0, years: 1 }), {
    monthlyPayment: 100, totalPaid: 1200, totalInterest: 0,
  });
});
test("mortgage rejects invalid terms", () => assert.throws(() => mortgage({ principal: 1, rate: 1, years: 0 }), /years>0/));

test("loanPayoff calculates the final partial payment", () => {
  assert.deepEqual(loanPayoff({ balance: 10000, rate: 6, monthlyPayment: 500 }), { months: 22, totalInterest: 562.51 });
  assert.deepEqual(loanPayoff({ balance: 1000, rate: 0, monthlyPayment: 300 }), { months: 4, totalInterest: 0 });
});
test("loanPayoff rejects non-amortizing payments", () =>
  assert.throws(() => loanPayoff({ balance: 10000, rate: 6, monthlyPayment: 50 }), /loan never amortizes/));

test("roi calculates total and annualized return", () => {
  assert.deepEqual(roi({ initial: 100, final: 121 }), { roiPercent: 21 });
  assert.deepEqual(roi({ initial: 100, final: 121, years: 2 }), { roiPercent: 21, annualizedPercent: 10 });
});
test("roi rejects a zero initial value", () => assert.throws(() => roi({ initial: 0, final: 1 }), /initial>0/));

test("npv discounts cash flows from t0", () =>
  assert.deepEqual(npv({ rate: 10, cashflows: "-1000,600,600" }), { npv: 41.32 }));
test("npv rejects malformed cash flows", () => assert.throws(() => npv({ rate: 10, cashflows: "-1000,nope" }), /cashflows/));

test("irr uses Newton and bisection paths", () => {
  assert.deepEqual(irr({ cashflows: "-1000,600,600" }), { irrPercent: 13.066239 });
  assert.ok(Math.abs(irr({ cashflows: "90,-220,121" }).irrPercent - (-16.425)) < 0.1);
});
test("irr rejects cash flows without a sign change", () => assert.throws(() => irr({ cashflows: "1,2,3" }), /no sign change/));

test("dcf discounts projected and terminal cash flow", () =>
  assert.deepEqual(dcf({ fcf: 100, growthRate: 5, discountRate: 10, years: 5, terminalGrowth: 2 }), { presentValue: 1446.21 }));
test("dcf rejects terminal growth at or above discount rate", () =>
  assert.throws(() => dcf({ fcf: 100, growthRate: 5, discountRate: 3, years: 5, terminalGrowth: 3 }), /less than discountRate/));

test("cagr calculates annualized growth", () => assert.deepEqual(cagr({ start: 100, end: 121, years: 2 }), { cagrPercent: 10 }));
test("cagr rejects a non-positive start", () => assert.throws(() => cagr({ start: 0, end: 1, years: 1 }), /start>0/));

test("aprApy converts in both directions", () => {
  const fromApr = aprApy({ apr: 12, compoundsPerYear: 12 });
  assert.deepEqual(fromApr, { apr: 12, apy: 12.682503 });
  const fromApy = aprApy({ apy: fromApr.apy, compoundsPerYear: 12 });
  assert.ok(Math.abs(fromApy.apr - 12) < 1e-5);
  assert.equal(fromApy.apy, 12.682503);
});
test("aprApy requires exactly one rate", () => assert.throws(() => aprApy({}), /exactly one/));

test("breakEven rounds units up and calculates revenue", () =>
  assert.deepEqual(breakEven({ fixedCosts: 1000, pricePerUnit: 50, variableCostPerUnit: 30 }), { units: 50, revenue: 2500 }));
test("breakEven rejects a non-positive contribution margin", () =>
  assert.throws(() => breakEven({ fixedCosts: 1000, pricePerUnit: 30, variableCostPerUnit: 30 }), /greater than/));

test("presentValue discounts a future amount", () =>
  assert.deepEqual(presentValue({ future: 1000, rate: 10, years: 2 }), { presentValue: 826.45 }));
test("presentValue rejects rates at or below minus 100 percent", () =>
  assert.throws(() => presentValue({ future: 1000, rate: -100, years: 2 }), /rate>-100/));

test("futureValueAnnuity calculates contributions and interest", () =>
  assert.deepEqual(futureValueAnnuity({ payment: 100, rate: 12, years: 1 }), {
    futureValue: 1268.25, totalContributed: 1200, interestEarned: 68.25,
  }));
test("futureValueAnnuity rejects negative payments", () =>
  assert.throws(() => futureValueAnnuity({ payment: -1, rate: 1, years: 1 }), /payment>=0/));

test("savingsGoal calculates the required periodic contribution", () =>
  assert.deepEqual(savingsGoal({ target: 1200, rate: 0, years: 1 }), { monthlyContribution: 100 }));
test("savingsGoal rejects a zero-year horizon", () =>
  assert.throws(() => savingsGoal({ target: 1200, rate: 1, years: 0 }), /years>0/));

test("percentChange calculates relative change", () =>
  assert.deepEqual(percentChange({ from: 100, to: 125 }), { percentChange: 25 }));
test("percentChange rejects a zero base", () => assert.throws(() => percentChange({ from: 0, to: 1 }), /must not be zero/));

test("inflationAdjust calculates nominal need and present purchasing power", () =>
  assert.deepEqual(inflationAdjust({ amount: 1000, rate: 3, years: 2 }), {
    futureNominalNeeded: 1060.9, presentPurchasingPower: 942.6,
  }));
test("inflationAdjust rejects invalid rates", () =>
  assert.throws(() => inflationAdjust({ amount: 1000, rate: -100, years: 2 }), /rate>-100/));

test("positionSize calculates long and short risk sizing", () => {
  assert.deepEqual(positionSize({ balance: 10000, riskPercent: 1, entry: 100, stop: 95 }), {
    positionSize: 20, notional: 2000, direction: "long",
  });
  assert.equal(positionSize({ balance: 10000, riskPercent: 1, entry: 95, stop: 100 }).direction, "short");
});
test("positionSize rejects an entry equal to the stop", () =>
  assert.throws(() => positionSize({ balance: 10000, riskPercent: 1, entry: 100, stop: 100 }), /entry!=stop/));

test("kelly calculates full and half Kelly and clamps a negative edge", () => {
  assert.deepEqual(kelly({ winProb: 0.6, winLossRatio: 2 }), { kellyFraction: 0.4, halfKelly: 0.2 });
  assert.deepEqual(kelly({ winProb: 0.2, winLossRatio: 1 }), {
    kellyFraction: 0, halfKelly: 0, note: "no edge, do not bet",
  });
});
test("kelly rejects probabilities outside zero to one", () =>
  assert.throws(() => kelly({ winProb: 1.1, winLossRatio: 2 }), /0..1/));

test("liquidationPrice calculates long and short thresholds", () => {
  assert.deepEqual(liquidationPrice({ entry: 100, leverage: 10, side: "long" }), { liquidationPrice: 90.5 });
  assert.deepEqual(liquidationPrice({ entry: 100, leverage: 10, side: "short" }), { liquidationPrice: 109.5 });
});
test("liquidationPrice rejects unknown sides", () =>
  assert.throws(() => liquidationPrice({ entry: 100, leverage: 10, side: "flat" }), /long\|short/));

test("perpPnl calculates PnL, return, and leveraged ROE", () =>
  assert.deepEqual(perpPnl({ entry: 100, exit: 110, size: 2, side: "long", leverage: 5 }), {
    pnl: 20, pnlPercent: 10, roePercent: 50,
  }));
test("perpPnl rejects invalid optional leverage", () =>
  assert.throws(() => perpPnl({ entry: 100, exit: 110, size: 2, side: "long", leverage: 0 }), /leverage must be >0/));

test("impermanentLoss calculates constant-product loss", () =>
  assert.deepEqual(impermanentLoss({ priceRatio: 4 }), { ilPercent: -20 }));
test("impermanentLoss rejects non-positive ratios", () =>
  assert.throws(() => impermanentLoss({ priceRatio: 0 }), /must be >0/));

test("hashText returns deterministic supported digests", () => {
  assert.deepEqual(hashText({ text: "abc" }), {
    digest: "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
  });
  assert.equal(hashText({ text: "abc", algo: "md5" }).digest, "900150983cd24fb0d6963f7d28e17f72");
});
test("hashText rejects unsupported algorithms", () => assert.throws(() => hashText({ text: "abc", algo: "sha1" }), /algo must be/));

test("base64 encodes and decodes UTF-8 text", () => {
  assert.deepEqual(base64({ text: "hello" }), { result: "aGVsbG8=" });
  assert.deepEqual(base64({ text: "aGVsbG8=", decode: "true" }), { result: "hello" });
});
test("base64 rejects malformed encoded input", () => assert.throws(() => base64({ text: "%%%", decode: "1" }), /valid base64/));

test("timestamp auto-detects seconds, milliseconds, and ISO 8601", () => {
  const expected = { unixSeconds: 1704067200, unixMillis: 1704067200000, iso: "2024-01-01T00:00:00.000Z", utc: "Mon, 01 Jan 2024 00:00:00 GMT" };
  assert.deepEqual(timestamp({ value: "1704067200" }), expected);
  assert.deepEqual(timestamp({ value: "1704067200000" }), expected);
  assert.deepEqual(timestamp({ value: "2024-01-01T00:00:00.000Z" }), expected);
});
test("timestamp requires a valid explicit value", () => assert.throws(() => timestamp({ value: "yesterday" }), /unix seconds/));
