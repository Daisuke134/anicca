"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { makeStagehandSteelDriver } = require("./stagehand-steel-driver.js");

function fixture(fixtureOptions = {}) {
  const calls = [];
  let options;
  const page = {
    async goto(url) { calls.push(["goto", url]); },
    async waitForTimeout(ms) { calls.push(["waitForTimeout", ms]); },
    async screenshot(options) {
      calls.push(["screenshot", options]);
      return Buffer.from("real-cloud-png");
    },
    url() { return "https://fresh-events.example/ai/confirmed"; },
  };
  class FakeStagehand {
    constructor(value) {
      options = value;
      this.context = { awaitActivePage: async () => page };
    }
    async init() { calls.push(["init"]); }
    async act(instruction, actOptions) {
      calls.push(["act", instruction, actOptions]);
      return { success: true, message: "done", actionDescription: instruction, actions: [] };
    }
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
        isSpecificActionPage: true,
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
    agentName: "Browser Owner",
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
  const agents = calls.filter(([name]) => name === "agent").map(([, value]) => value);
  assert.deepEqual(agents, [{
    model: "google/gemini-2.5-flash",
    executionModel: "google/gemini-2.5-flash",
  }, {
    mode: "cua",
    model: "google/gemini-2.5-computer-use-preview-10-2025",
    systemPrompt: "Operate the remote cloud browser carefully. Use only truthful supplied identity data, never invent personal data, and stop at login, CAPTCHA, 2FA, KYC, or payment.",
  }]);
  assert.match(calls.find(([name]) => name === "goto")[1], /^https:\/\/www\.google\.com\/$/);
  const tasks = calls.filter(([name]) => name === "execute").map(([, task]) => task);
  assert.equal(tasks.length, 2, "discovery/selection and the one action are separate phases");
  assert.match(tasks[0], /search the live web/i);
  assert.match(tasks[0], /compare at least two/i);
  assert.match(tasks[0], /do not perform/i);
  assert.match(tasks[1], /browser-owner@example\.test/i, "the runtime identity is available to the action phase");
  assert.match(tasks[1], /Browser Owner/i, "the runtime-owned name is available to the action phase");
  assert.match(tasks[1], /company or organization.*Browser Owner/i);
  assert.match(tasks[1], /role or job title.*AI agent/i);
  assert.match(tasks[1], /optional social.*blank/i);
  assert.match(tasks[1], /decline.*marketing.*data-sharing/i);
  assert.match(tasks[1], /exactly one/i);
  assert.doesNotMatch(tasks.join("\n"), /fresh-events\.example/i, "the target comes from discovery, never configuration");
  assert.doesNotMatch(JSON.stringify(action), /browser-owner@example\.test/i, "the identity never enters durable results");
});

test("a listing/search page is never accepted as the selected provider action page", async () => {
  const calls = [];
  let currentUrl = "https://events.example/search?q=ai";
  let selectionReads = 0;
  const page = {
    async goto() {},
    async screenshot() { return Buffer.from("png"); },
    url() { return currentUrl; },
  };
  class FakeStagehand {
    constructor() { this.context = { awaitActivePage: async () => page }; }
    async init() {}
    agent() {
      return {
        execute: async (task) => {
          calls.push(task);
          if (/open one specific candidate/i.test(task)) {
            currentUrl = "https://events.example/e/ai-summit";
          }
        },
      };
    }
    async extract(instruction) {
      if (/identify the selected site/i.test(instruction)) {
        selectionReads += 1;
        return {
          selectedSiteName: "AI Summit",
          selectionReason: "free and online",
          isSpecificActionPage: selectionReads > 1,
        };
      }
      return { actionSummary: "registered" };
    }
  }
  const driver = makeStagehandSteelDriver({
    Stagehand: FakeStagehand,
    apiKey: "key",
    agentEmail: "owner@example.test",
    agentName: "Browser Owner",
    steelClient: {
      baseUrl: "http://steel-browser.railway.internal:8080",
      async createRawSession() {
        return { id: "s", websocketUrl: "ws://steel-browser.railway.internal:8080/" };
      },
      async releaseSession() { return true; },
    },
  });
  const session = await driver.openSession();
  const result = await driver.discoverAndAct(session, { goal: "register" });
  assert.equal(result.selectedUrl, "https://events.example/e/ai-summit");
  assert.equal(selectionReads, 2);
  assert.match(calls[1], /open one specific candidate/i);
});

test("a runtime-supplied public HTTPS detail URL skips search and goes straight to CUA action", async () => {
  const { driver, calls } = fixture();
  const session = await driver.openSession();
  await driver.discoverAndAct(session, {
    goal: "Open https://fresh-events.example/ai/confirmed and register the agent-owned identity",
  });

  const gotos = calls.filter(([name]) => name === "goto").map(([, url]) => url);
  assert.deepEqual(gotos, [
    "https://www.google.com/",
    "https://fresh-events.example/ai/confirmed",
  ]);
  assert.equal(calls.filter(([name]) => name === "agent").length, 0);
  const acts = calls.filter(([name]) => name === "act");
  assert.equal(acts.length, 8);
  assert.match(acts[0][1], /open.*registration form/i);
  assert.deepEqual(acts[1][2].variables, { agentName: "Browser Owner" });
  assert.deepEqual(acts[2][2].variables, { agentEmail: "browser-owner@example.test" });
  assert.match(acts[5][1], /Which best describes you.*AI Researcher/i);
  assert.match(acts[6][1], /consent dropdown.*Register.*No.*do not consent/i);
  assert.match(acts[7][1], /submit.*registration/i);
  assert.deepEqual(calls.find(([name]) => name === "waitForTimeout"), ["waitForTimeout", 15_000]);
});

test("runtime URL shortcut rejects local and Railway-private destinations", async () => {
  for (const unsafe of [
    "http://localhost:8080/admin",
    "https://steel-browser.railway.internal/admin",
    "https://127.0.0.1/private",
    "https://169.254.169.254/latest/meta-data",
  ]) {
    const { driver } = fixture();
    const session = await driver.openSession();
    await assert.rejects(
      driver.discoverAndAct(session, { goal: `Open ${unsafe} and register` }),
      /public HTTPS URL/i,
    );
  }
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

test("evidence is a PNG captured from the connected Steel page before release", async () => {
  const { driver, calls } = fixture();
  const session = await driver.openSession();
  await driver.discoverAndAct(session, { goal: "Find and register", locale: "en" });
  const evidence = await driver.captureEvidence(session);
  assert.equal(evidence.mimeType, "image/png");
  assert.equal(evidence.bytes.toString(), "real-cloud-png");
  assert.deepEqual(calls.find(([name]) => name === "screenshot"), [
    "screenshot",
    { type: "png", fullPage: false },
  ]);
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

test("provider-authored You're In is confirmed even when email verification is only for managing it", async () => {
  const { driver } = fixture({
    receipt: {
      confirmed: false,
      status: "confirmed",
      confirmationId: null,
      providerText: "You're In. Please verify your email to manage your registration and see more event details.",
    },
  });
  const session = await driver.openSession();
  await driver.discoverAndAct(session, { goal: "Find and register", locale: "en" });
  const receipt = await driver.readProviderReceipt(session);
  assert.equal(receipt.confirmed, true);
  assert.equal(receipt.handoffRequired, false);
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
