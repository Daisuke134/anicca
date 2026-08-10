"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  createConnpassBrowserProvider,
  readConnpassRegistrationStateOnPage,
  submitConnpassOnPage,
} = require("./connpass-browser-provider.js");

function contract() {
  return {
    tenant_id: "dais-local",
    event_ref: "connpass-event://event/101",
    canonical_url: "https://tokyo-builders.connpass.com/event/101/",
  };
}

function fixture(states) {
  const calls = [];
  const queue = [...states];
  const page = {
    async evaluate() { return queue.shift(); },
    async screenshot(options) { calls.push(["screenshot", options]); return Buffer.from("png"); },
  };
  return {
    calls, page,
    dailyDriver: {
      async withEventPage(provider, url, task) {
        calls.push(["withEventPage", provider, url]);
        return task(page, { tab_owner_receipt: { target_id: "OWNED" } });
      },
    },
    evidenceStore: {
      async record(input) {
        calls.push(["record", input]);
        return {
          external_receipt_ref: "provider-receipt://connpass/registered-101",
          artifact_ref: `object://sha256/${"a".repeat(64)}`,
        };
      },
    },
  };
}

function domFixture({ pathname, bodyText, controls = [] }) {
  return {
    async evaluate(callback) {
      const previousLocation = globalThis.location;
      const previousDocument = globalThis.document;
      globalThis.location = { pathname };
      globalThis.document = {
        body: { innerText: bodyText },
        querySelectorAll() { return controls; },
      };
      try {
        return await callback();
      } finally {
        if (previousLocation === undefined) delete globalThis.location;
        else globalThis.location = previousLocation;
        if (previousDocument === undefined) delete globalThis.document;
        else globalThis.document = previousDocument;
      }
    },
  };
}

test("join-page attendee-section text does not impersonate pending registration", async () => {
  const page = domFixture({
    pathname: "/event/400028/join/",
    bodyText: "参加枠\n補欠者\n補欠者はいません\n申し込みを確定する",
    controls: [{ innerText: "申し込みを確定する", value: "", getAttribute() { return null; } }],
  });
  assert.deepEqual(await readConnpassRegistrationStateOnPage(page), { state: "unknown" });
});

test("pending requires an exact visible line on the canonical event page", async () => {
  const page = domFixture({ pathname: "/event/400028/", bodyText: "参加状況\n補欠\n" });
  assert.deepEqual(await readConnpassRegistrationStateOnPage(page), { state: "pending" });
});

test("pending markers are rejected for substring-only and non-canonical paths", async () => {
  for (const pathname of ["/event/400028/", "/event/0/", "/event/400028", "/event/400028/join/", "/events/400028/"]) {
    const bodyText = pathname === "/event/400028/" ? "補欠者" : "補欠";
    const page = domFixture({ pathname, bodyText });
    assert.deepEqual(await readConnpassRegistrationStateOnPage(page), { state: "unknown" }, pathname);
  }
});

test("parent readback separates login, absence, unavailable, pending, and registered", async () => {
  for (const [observed, expected] of [
    [{ state: "login_required" }, "login_required"],
    [{ state: "absent" }, "absent"],
    [{ state: "unavailable", reason: "closed" }, "unavailable"],
  ]) {
    const fx = fixture([observed]);
    assert.equal((await createConnpassBrowserProvider(fx).inspectRegistration(contract())).state, expected);
    assert.equal(fx.calls.some(([name]) => name === "record"), false);
  }
  for (const state of ["pending", "registered"]) {
    const fx = fixture([{ state }]);
    const proof = await createConnpassBrowserProvider({
      ...fx, now: () => "2026-08-06T01:02:03.000Z",
    }).inspectRegistration(contract());
    assert.equal(proof.state, "registered");
    assert.equal(proof.registration_status, state);
    assert.match(proof.artifact_ref, /^object:\/\/sha256\//);
  }
});

test("submit uses one exact parent-page control and proves its effect before screenshot", async () => {
  const calls = [];
  const control = {
    first() { return this; }, async count() { return 1; }, async isVisible() { return true; },
    async click() { calls.push("click"); },
  };
  const states = [{ state: "absent" }, { state: "registered" }];
  const page = {
    getByRole(role, options) {
      assert.match(role, /link|button/); assert.equal(options.exact, true);
      assert.equal(options.name.test("このイベントに申し込む"), true);
      return control;
    },
    async waitForTimeout() {},
    async evaluate() { return states.shift(); },
  };
  assert.deepEqual(await submitConnpassOnPage(page), { status: "registered", effect_started: true });
  assert.deepEqual(calls, ["click"]);
});

test("pre-click failures are known and post-click uncertainty is unknown", async () => {
  const known = fixture([{ state: "login_required" }]);
  await assert.rejects(createConnpassBrowserProvider(known).submitRegistration(contract()), (error) => {
    assert.equal(error.unknownEffect, false); return true;
  });

  const unknown = fixture([{ state: "absent" }]);
  unknown.page.getByRole = () => ({
    first() { return this; }, async count() { return 1; }, async isVisible() { return true; }, async click() {},
  });
  unknown.page.waitForTimeout = async () => {};
  await assert.rejects(createConnpassBrowserProvider({
    ...unknown, submitOnPage: async () => ({ status: "unknown", effect_started: true }),
  }).submitRegistration(contract()), (error) => {
    assert.equal(error.unknownEffect, true); return true;
  });
});
