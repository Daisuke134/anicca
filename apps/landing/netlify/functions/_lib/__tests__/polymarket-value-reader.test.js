const { test } = require("node:test");
const assert = require("node:assert");
const { fetchPortfolioValueUsd } = require("../polymarket-value-reader");

const okJson = (body) => ({ ok: true, json: async () => body });

test("T1: parses the [{user,value}] array shape the real API returns", async () => {
  const f = async () => okJson([{ user: "0x904b50d2e214da947d83d6a2d32c4e3ffc17eb74", value: 20.59 }]);
  const v = await fetchPortfolioValueUsd("0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74", f);
  assert.strictEqual(v, 20.59);
});

test("fail-closed: non-ok HTTP throws instead of guessing $0", async () => {
  const f = async () => ({ ok: false, status: 500, json: async () => ({}) });
  await assert.rejects(() => fetchPortfolioValueUsd("0xaddr", f));
});

test("fail-closed: malformed/non-finite value throws", async () => {
  const f = async () => okJson([{ user: "0xaddr", value: "not-a-number" }]);
  await assert.rejects(() => fetchPortfolioValueUsd("0xaddr", f));
});

test("an account with no positions/deposit reports 0, not a throw", async () => {
  const f = async () => okJson([{ user: "0xaddr", value: 0 }]);
  const v = await fetchPortfolioValueUsd("0xaddr", f);
  assert.strictEqual(v, 0);
});
