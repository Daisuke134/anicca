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

// Fake join-page built from the real DOM structure captured live from
// https://hfs.connpass.com/event/398207/join/:
//   input[name="participation_type"] (radio, id="ptype1")
//   button#FreeButton ("申し込みを確定する")
function joinFlowFixture({
  radioCount = 1, confirmCount = 1, confirmVisible = true,
  confirmLabel = "申し込みを確定する", confirmClickError = null, states,
} = {}) {
  const calls = [];
  const joinLink = {
    first() { return this; },
    async count() { return 1; },
    async isVisible() { return true; },
    async click() { calls.push("click-join"); },
  };
  const radioLocator = {
    first() { return this; },
    async count() { return radioCount; },
    async check() { calls.push("check-radio"); },
  };
  const confirmLocator = {
    async count() { return confirmCount; },
    async isVisible() { return confirmVisible; },
    async innerText() { return confirmLabel; },
    async click() {
      calls.push("click-confirm");
      if (confirmClickError) throw confirmClickError;
    },
  };
  const stateQueue = [...(states || [])];
  const page = {
    calls,
    getByRole(role, options) {
      assert.match(role, /link|button/); assert.equal(options.exact, true);
      assert.equal(options.name.test("このイベントに申し込む"), true);
      return joinLink;
    },
    locator(selector) {
      if (selector === 'input[name="participation_type"]') return radioLocator;
      if (selector === "button#FreeButton") return confirmLocator;
      throw new Error(`unexpected selector ${selector}`);
    },
    async waitForTimeout() { calls.push("wait"); },
    async evaluate() { return stateQueue.shift(); },
  };
  return page;
}

test("submit clicks join link, selects the first participation radio, then confirms — in order", async () => {
  const page = joinFlowFixture({ states: [{ state: "absent" }, { state: "registered" }] });
  assert.deepEqual(await submitConnpassOnPage(page), { status: "registered", effect_started: true });
  assert.deepEqual(page.calls, ["click-join", "wait", "check-radio", "click-confirm", "wait"]);
});

test("already-registered/pending state returns immediately and clicks nothing", async () => {
  for (const state of ["registered", "pending"]) {
    const page = joinFlowFixture({ states: [] });
    const readState = async () => ({ state });
    assert.deepEqual(
      await submitConnpassOnPage(page, undefined, { readState }),
      { status: state, effect_started: false },
    );
    assert.deepEqual(page.calls, []);
  }
});

test("missing or duplicated confirm control fails closed before any click on the join page", async () => {
  for (const overrides of [{ confirmCount: 0 }, { confirmCount: 2 }, { confirmVisible: false }, { confirmLabel: "支払いに進む" }]) {
    const page = joinFlowFixture({ states: [{ state: "absent" }], ...overrides });
    await assert.rejects(submitConnpassOnPage(page), (error) => {
      assert.equal(error.code, "CONNPASS_CONFIRM_UNAVAILABLE");
      assert.equal(error.unknownEffect, false);
      return true;
    });
    // join-link click (navigation only) may have happened; nothing on the
    // join page itself (radio check, confirm click) may have.
    assert.equal(page.calls.includes("check-radio"), false);
    assert.equal(page.calls.includes("click-confirm"), false);
  }
});

test("missing participation-type radio fails closed before the confirm control is touched", async () => {
  const page = joinFlowFixture({ states: [{ state: "absent" }], radioCount: 0 });
  await assert.rejects(submitConnpassOnPage(page), (error) => {
    assert.equal(error.code, "CONNPASS_CONTROL_UNAVAILABLE");
    assert.equal(error.unknownEffect, false);
    return true;
  });
  assert.deepEqual(page.calls, ["click-join", "wait"]);
});

test("a failure after the confirm click is always reported as an unknown effect", async () => {
  const page = joinFlowFixture({
    states: [{ state: "absent" }],
    confirmClickError: Object.assign(new Error("connpass 500"), { unknownEffect: false, code: "CONNPASS_READBACK_UNAVAILABLE" }),
  });
  await assert.rejects(submitConnpassOnPage(page), (error) => {
    assert.equal(error.code, "CONNPASS_BROWSER_ACTION_FAILED");
    assert.equal(error.unknownEffect, true);
    return true;
  });
  assert.deepEqual(page.calls, ["click-join", "wait", "check-radio", "click-confirm"]);
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
