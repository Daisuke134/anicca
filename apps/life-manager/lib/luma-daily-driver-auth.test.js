"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const {
  createAuthAwareLumaDailyDriver,
  createLumaDailyDriverAuth,
} = require("./luma-daily-driver-auth.js");

function fixture(states) {
  const calls = [];
  const page = { id: "shared-daily-driver-page" };
  const dailyDriver = {
    async withLumaPage(url, task) {
      calls.push(["page", url]);
      return task(page);
    },
  };
  let index = 0;
  const auth = createLumaDailyDriverAuth({
    dailyDriver,
    email: "dais@example.test",
    name: "Dais",
    now: () => 1_722_500_000_000,
    inspectAuth: async () => {
      calls.push(["inspect"]);
      return states[Math.min(index++, states.length - 1)];
    },
    requestLogin: async (_page, email) => calls.push(["request", email]),
    readLoginCode: async (input) => {
      calls.push(["read", input.afterMs]);
      return "123456";
    },
    submitCode: async (_page, code) => calls.push(["submit", code]),
    finishPostAuth: async (_page, name) => calls.push(["finish", name]),
  });
  return { auth, calls, dailyDriver };
}

test("an authenticated shared Luma session is reused without requesting mail", async () => {
  const fx = fixture([{ status: "authenticated" }]);
  const result = await fx.auth.ensureAuthenticated();

  assert.deepEqual(result, { status: "authenticated", recovered: false });
  assert.deepEqual(fx.calls, [
    ["page", "https://luma.com/home"],
    ["inspect"],
  ]);
});

test("a logged-out session is recovered with only a fresh six-digit Gmail code", async () => {
  const fx = fixture([
    { status: "login_required" },
    { status: "authenticated" },
  ]);
  const result = await fx.auth.ensureAuthenticated();

  assert.deepEqual(result, { status: "authenticated", recovered: true });
  assert.deepEqual(fx.calls, [
    ["page", "https://luma.com/home"],
    ["inspect"],
    ["request", "dais@example.test"],
    ["read", 1_722_500_000_000],
    ["submit", "123456"],
    ["finish", "Dais"],
    ["inspect"],
  ]);
  assert.equal(JSON.stringify(result).includes("123456"), false);
});

test("invalid or stale-reader output never reaches the Luma code fields", async () => {
  const fx = fixture([{ status: "login_required" }]);
  fx.auth = createLumaDailyDriverAuth({
    dailyDriver: fx.dailyDriver,
    email: "dais@example.test",
    name: "Dais",
    now: () => 10,
    inspectAuth: async () => ({ status: "login_required" }),
    requestLogin: async () => {},
    readLoginCode: async () => "code=123456",
    submitCode: async () => assert.fail("invalid code must not be submitted"),
    finishPostAuth: async () => {},
  });

  await assert.rejects(fx.auth.ensureAuthenticated(), /authentication unavailable/i);
});

test("recovery is not reported when authenticated readback is still absent", async () => {
  const fx = fixture([
    { status: "login_required" },
    { status: "unknown" },
  ]);
  await assert.rejects(fx.auth.ensureAuthenticated(), /authentication unavailable/i);
});

test("the auth-aware driver never starts an event task before authentication succeeds", async () => {
  const calls = [];
  const dailyDriver = {
    async withLumaPage(url, task) {
      calls.push(["task", url]);
      return task({});
    },
  };
  const blocked = createAuthAwareLumaDailyDriver({
    dailyDriver,
    auth: { async ensureAuthenticated() { throw new Error("Luma authentication unavailable"); } },
  });
  await assert.rejects(
    blocked.withLumaPage("https://luma.com/event-one", async () => "effect"),
    /authentication unavailable/i,
  );
  assert.deepEqual(calls, []);

  const ready = createAuthAwareLumaDailyDriver({
    dailyDriver,
    auth: { async ensureAuthenticated() { calls.push(["auth"]); } },
  });
  assert.equal(
    await ready.withLumaPage("https://luma.com/event-one", async () => "effect"),
    "effect",
  );
  assert.deepEqual(calls, [["auth"], ["task", "https://luma.com/event-one"]]);
});

test("concurrent callers share one login recovery attempt", async () => {
  let releases;
  let attempts = 0;
  const auth = createLumaDailyDriverAuth({
    dailyDriver: { async withLumaPage(_url, task) { return task({}); } },
    email: "dais@example.test",
    name: "Dais",
    now: () => 20,
    inspectAuth: async () => attempts === 0
      ? { status: "login_required" }
      : { status: "authenticated" },
    requestLogin: async () => { attempts += 1; },
    readLoginCode: async () => new Promise((resolve) => { releases = () => resolve("123456"); }),
    submitCode: async () => {},
    finishPostAuth: async () => {},
  });
  const first = auth.ensureAuthenticated();
  const second = auth.ensureAuthenticated();
  await new Promise((resolve) => setImmediate(resolve));
  releases();
  assert.deepEqual(await Promise.all([first, second]), [
    { status: "authenticated", recovered: true },
    { status: "authenticated", recovered: true },
  ]);
  assert.equal(attempts, 1);
});
