"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { makeStagehandSteelDriver } = require("./stagehand-steel-driver.js");

function fixture(fixtureOptions = {}) {
  const calls = [];
  let options;
  const page = {
    async goto(url) { calls.push(["goto", url]); },
    url() { return "https://fresh-events.example/ai/confirmed"; },
  };
  class FakeStagehand {
    constructor(value) {
      options = value;
      this.context = { awaitActivePage: async () => page };
    }
    async init() { calls.push(["init"]); }
    agent(value) {
      calls.push(["agent", value]);
      return {
        execute: async (task) => {
          calls.push(["execute", task]);
          return { success: true, message: "registration submitted" };
        },
      };
    }
    async extract(instruction, _schema) {
      calls.push(["extract", instruction]);
      if (/provider-authored result page/i.test(instruction) && fixtureOptions.receipt) {
        return fixtureOptions.receipt;
      }
      return {
        confirmed: true,
        status: "registered",
        confirmationId: "provider-77",
        providerText: "Registration confirmed",
        selectedSiteName: "Fresh Events",
        selectionReason: "free, public, online, and relevant",
        actionSummary: "registered browser-owner@example.test",
      };
    }
    async close() { calls.push(["close"]); }
  }
  const steelClient = {
    baseUrl: "http://steel-browser.railway.internal:8080",
    async createRawSession() {
      calls.push(["create"]);
      return { id: "steel-1", websocketUrl: "ws://steel-browser.railway.internal:8080/" };
    },
    async releaseSession(id) {
      calls.push(["release", id]);
      return true;
    },
  };
  const driver = makeStagehandSteelDriver({
    steelClient,
    Stagehand: FakeStagehand,
    apiKey: "gemini-key",
    agentEmail: "browser-owner@example.test",
  });
  return { driver, calls, getOptions: () => options };
}

test("Stagehand reasons over a Railway-private Steel session and discovers the target at runtime", async () => {
  const { driver, calls, getOptions } = fixture();
  const session = await driver.openSession();
  const action = await driver.discoverAndAct(session, {
    goal: "Find a suitable free public online AI event and register the agent-owned email",
    locale: "en",
  });

  assert.equal(action.selectedUrl, "https://fresh-events.example/ai/confirmed");
  assert.equal(action.selectedOrigin, "https://fresh-events.example");
  assert.equal(action.sideEffectStarted, true);
  assert.equal(action.selectionReason, "free, public, online, and relevant");
  assert.equal(action.action, "registered the agent-owned email");

  const options = getOptions();
  assert.equal(options.env, "LOCAL");
  assert.equal(options.localBrowserLaunchOptions.cdpUrl, "ws://steel-browser.railway.internal:8080/");
  assert.deepEqual(options.localBrowserLaunchOptions.cdpHeaders, { Host: "localhost:8080" });
  assert.deepEqual(options.model, {
    modelName: "google/gemini-2.5-flash",
    apiKey: "gemini-key",
  });
  assert.match(calls.find(([name]) => name === "goto")[1], /^https:\/\/www\.google\.com\/$/);
  const tasks = calls.filter(([name]) => name === "execute").map(([, task]) => task);
  assert.equal(tasks.length, 2, "discovery/selection and the one action are separate phases");
  assert.match(tasks[0], /search the live web/i);
  assert.match(tasks[0], /compare at least two/i);
  assert.match(tasks[0], /do not perform/i);
  assert.match(tasks[1], /browser-owner@example\.test/i, "the runtime identity is available to the action phase");
  assert.match(tasks[1], /exactly one/i);
  assert.doesNotMatch(tasks.join("\n"), /fresh-events\.example/i, "the target comes from discovery, never configuration");
  assert.doesNotMatch(JSON.stringify(action), /browser-owner@example\.test/i, "the identity never enters durable results");
});

test("provider success comes from a separate typed page readback, not agent narration", async () => {
  const { driver } = fixture();
  const session = await driver.openSession();
  const action = await driver.discoverAndAct(session, {
    goal: "Find and register",
    locale: "en",
  });
  const receipt = await driver.readProviderReceipt(session, action);
  assert.deepEqual(receipt, {
    confirmed: true,
    status: "registered",
    confirmationId: "provider-77",
    currentUrl: "https://fresh-events.example/ai/confirmed",
    handoffRequired: false,
    handoffReason: null,
  });
});

test("login, challenge, CAPTCHA, 2FA, or KYC readback requires handoff", async () => {
  const { driver } = fixture({
    receipt: {
      confirmed: false,
      status: "CAPTCHA challenge",
      confirmationId: null,
      providerText: "Complete CAPTCHA to continue",
    },
  });
  const session = await driver.openSession();
  await driver.discoverAndAct(session, { goal: "Find and register", locale: "en" });
  const receipt = await driver.readProviderReceipt(session);
  assert.equal(receipt.confirmed, false);
  assert.equal(receipt.handoffRequired, true);
  assert.equal(receipt.handoffReason, "challenge");
});

test("release closes Stagehand before releasing the one Steel slot", async () => {
  const { driver, calls } = fixture();
  const session = await driver.openSession();
  await driver.discoverAndAct(session, { goal: "Find and register", locale: "en" });
  assert.deepEqual(await driver.releaseSession(session.id), { released: true });
  assert.deepEqual(calls.slice(-2), [["close"], ["release", "steel-1"]]);
});

test("public or local browser endpoints are rejected before a browser is created", () => {
  for (const baseUrl of ["https://steel.example.com", "http://localhost:3000"]) {
    assert.throws(() => makeStagehandSteelDriver({
      steelClient: { baseUrl },
      Stagehand: class {},
      apiKey: "key",
    }), /Railway-private Steel/i);
  }
});
