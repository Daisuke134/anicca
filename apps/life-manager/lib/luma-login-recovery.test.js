"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  createLumaLoginRecovery,
} = require("./luma-login-recovery.js");

function driver(page = {}) {
  const calls = [];
  return {
    calls,
    value: {
      async withLumaPage(url, task) {
        calls.push(url);
        return task(page, { existing_page_count: 4 });
      },
    },
  };
}

test("認証済みの共有contextはGoogle操作をせずsafe metadataだけを返す", async () => {
  const daily = driver();
  let signIns = 0;
  const recovery = createLumaLoginRecovery({
    dailyDriver: daily.value,
    inspectAuth: async () => ({ status: "authenticated", origin: "https://luma.com", path: "/home" }),
    signInWithGoogle: async () => { signIns += 1; },
  });

  assert.deepEqual(await recovery.recover(), {
    status: "authenticated",
    origin: "https://luma.com",
    path: "/home",
    recovered: false,
  });
  assert.equal(signIns, 0);
  assert.deepEqual(daily.calls, ["https://luma.com/home"]);
});

test("login切れは既存Google sessionを一度だけ使い認証後readbackで成功する", async () => {
  const daily = driver();
  const snapshots = [
    { status: "login_required", origin: "https://luma.com", path: "/signin" },
    { status: "authenticated", origin: "https://luma.com", path: "/home" },
  ];
  let signIns = 0;
  const recovery = createLumaLoginRecovery({
    dailyDriver: daily.value,
    inspectAuth: async () => snapshots.shift(),
    signInWithGoogle: async () => { signIns += 1; },
  });

  assert.deepEqual(await recovery.recover(), {
    status: "authenticated",
    origin: "https://luma.com",
    path: "/home",
    recovered: true,
  });
  assert.equal(signIns, 1);
});

test("同時のlogin復旧要求は一つの共有操作へまとめる", async () => {
  const daily = driver();
  let inspections = 0;
  let release;
  const gate = new Promise((resolve) => { release = resolve; });
  const recovery = createLumaLoginRecovery({
    dailyDriver: daily.value,
    inspectAuth: async () => {
      inspections += 1;
      return inspections === 1
        ? { status: "login_required", origin: "https://luma.com", path: "/signin" }
        : { status: "authenticated", origin: "https://luma.com", path: "/home" };
    },
    signInWithGoogle: async () => gate,
  });

  const first = recovery.recover();
  const second = recovery.recover();
  release();
  const [a, b] = await Promise.all([first, second]);
  assert.deepEqual(a, b);
  assert.equal(daily.calls.length, 1);
  assert.equal(inspections, 2);
});

test("Google操作後も認証を証明できなければfail closedする", async () => {
  const daily = driver();
  const recovery = createLumaLoginRecovery({
    dailyDriver: daily.value,
    inspectAuth: async () => ({ status: "login_required", origin: "https://luma.com", path: "/signin" }),
    signInWithGoogle: async () => {},
  });

  await assert.rejects(recovery.recover(), /Luma login recovery unverified/);
});
