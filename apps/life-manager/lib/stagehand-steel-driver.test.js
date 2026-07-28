"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { makeStagehandSteelDriver } = require("./stagehand-steel-driver.js");

function fixture(fixtureOptions = {}) {
  const calls = [];
  const authCalls = [];
  let options;
  const page = {
    async goto(url) { calls.push(["goto", url]); },
    async waitForTimeout(ms) { calls.push(["waitForTimeout", ms]); },
    async screenshot(options) {
      calls.push(["screenshot", options]);
      return Buffer.from("real-cloud-png");
    },
    async evaluate(_callback, input) {
      calls.push(["evaluate", input]);
      return fixtureOptions.domGuard || {
        passwordVisible: false,
        otpVisible: false,
        authVisible: false,
        challengeVisible: false,
        captchaVisible: false,
        kycVisible: false,
        paymentVisible: false,
        markerPresent: true,
      };
    },
    url() { return fixtureOptions.pageUrl || "https://fresh-events.example/ai/confirmed"; },
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
      if (/authenticated provider continuity page/i.test(instruction)
        && fixtureOptions.authReceipt) {
        return fixtureOptions.authReceipt;
      }
      if (/provider-authored result page/i.test(instruction) && fixtureOptions.receipt) {
        return fixtureOptions.receipt;
      }
      if (/identify the selected site/i.test(instruction) && fixtureOptions.selection) {
        return fixtureOptions.selection;
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
    async createRawSession(createOptions) {
      calls.push(["create", createOptions]);
      const id = `steel-${calls.filter(([name]) => name === "create").length}`;
      return {
        id,
        websocketUrl: fixtureOptions.websocketUrl ||
          "ws://steel-browser.railway.internal:8080/",
      };
    },
    async getSessionContext(id) {
      calls.push(["getContext", id]);
      if (fixtureOptions.exportError) throw fixtureOptions.exportError;
      return fixtureOptions.exportContext || {};
    },
    async releaseSession(id) {
      calls.push(["release", id]);
      return true;
    },
  };
  const readBrowserAuthSession = async (input) => {
    authCalls.push(["read", input]);
    return fixtureOptions.authRecords && fixtureOptions.authRecords[input.uid] || null;
  };
  const upsertBrowserAuthSession = async (input) => {
    authCalls.push(["upsert", input]);
    if (fixtureOptions.saveError) throw fixtureOptions.saveError;
    return fixtureOptions.savedRecord || {};
  };
  const invalidateBrowserAuthSession = async (input) => {
    authCalls.push(["invalidate", input]);
    if (fixtureOptions.invalidateError) throw fixtureOptions.invalidateError;
    return true;
  };
  const driver = makeStagehandSteelDriver({
    steelClient,
    Stagehand: FakeStagehand,
    apiKey: "gemini-key",
    agentEmail: "browser-owner@example.test",
    agentName: "Browser Owner",
    readBrowserAuthSession,
    upsertBrowserAuthSession,
    invalidateBrowserAuthSession,
  });
  return { driver, calls, authCalls, getOptions: () => options };
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

test("a runtime-supplied public HTTPS detail URL skips search and uses the general CUA action", async () => {
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
  const agents = calls.filter(([name]) => name === "agent");
  assert.equal(agents.length, 1);
  assert.equal(agents[0][1].mode, "cua");
  const tasks = calls.filter(([name]) => name === "execute").map(([, task]) => task);
  assert.equal(tasks.length, 1);
  assert.match(tasks[0], /browser-owner@example\.test/i);
  assert.match(tasks[0], /Browser Owner/i);
  assert.match(tasks[0], /exactly one/i);
  assert.equal(calls.filter(([name]) => name === "act").length, 0);
});

test("an explicit auth continuity readback navigates and reads without starting a provider action", async () => {
  const { driver, calls } = fixture();
  const session = await driver.openSession();
  const action = await driver.discoverAndAct(session, {
    goal: "Read https://fresh-events.example/ai/confirmed with the existing authenticated session",
    actionKind: "browser_auth_continuity_readback",
  });

  assert.equal(action.selectedUrl, "https://fresh-events.example/ai/confirmed");
  assert.equal(action.sideEffectStarted, false);
  assert.match(action.action, /authenticated provider page/i);
  assert.equal(calls.filter(([name]) => name === "agent").length, 0);
  assert.equal(calls.filter(([name]) => name === "execute").length, 0);
  assert.equal(calls.filter(([name]) => name === "act").length, 0);
});

test("an explicit auth continuity readback does not apply the normal action-page LLM gate", async () => {
  const { driver, calls } = fixture({
    selection: {
      selectedSiteName: "Secure Area",
      selectionReason: "authenticated account page, not an event action page",
      isSpecificActionPage: false,
    },
  });
  const session = await driver.openSession();
  const action = await driver.discoverAndAct(session, {
    goal: "Read https://fresh-events.example/secure with the existing authenticated session",
    actionKind: "browser_auth_continuity_readback",
  });

  assert.equal(action.selectedUrl, "https://fresh-events.example/ai/confirmed");
  assert.equal(action.sideEffectStarted, false);
  assert.equal(
    calls.filter(([name, instruction]) =>
      name === "extract" && /identify the selected site/i.test(instruction)).length,
    0,
  );
});

test("auth continuity confirms provider content without requiring action-success language", async () => {
  const { driver } = fixture({
    receipt: {
      confirmed: false,
      status: "unknown",
      confirmationId: null,
      providerText: "Products inventory",
      activeRegistrationForm: false,
      activeAuthenticationForm: false,
    },
    authReceipt: {
      confirmed: true,
      status: "authenticated",
      confirmationId: null,
      providerText: "Products inventory",
      activeRegistrationForm: false,
      activeAuthenticationForm: false,
    },
  });
  const session = await driver.openSession();
  const action = await driver.discoverAndAct(session, {
    goal: "Read https://fresh-events.example/ai/confirmed with the existing authenticated session",
    actionKind: "browser_auth_continuity_readback",
  });

  const receipt = await driver.readProviderReceipt(session, action);

  assert.equal(receipt.confirmed, true);
  assert.equal(receipt.status, "authenticated");
  assert.equal(receipt.handoffRequired, false);
});

test("auth continuity redirect to a root login page reaches structured login handoff", async () => {
  const { driver } = fixture({
    pageUrl: "https://fresh-events.example/",
    authReceipt: {
      confirmed: false,
      status: "login required",
      confirmationId: null,
      providerText: "Sign in to continue",
      activeRegistrationForm: false,
      activeAuthenticationForm: true,
    },
  });
  const session = await driver.openSession();
  const action = await driver.discoverAndAct(session, {
    goal: "Read https://fresh-events.example/account with the existing authenticated session",
    actionKind: "browser_auth_continuity_readback",
  });

  const receipt = await driver.readProviderReceipt(session, action);

  assert.equal(receipt.confirmed, false);
  assert.equal(receipt.handoffRequired, true);
  assert.equal(receipt.handoffReason, "login");
});

test("auth continuity never confirms when the typed readback also reports an auth or risk handoff", async () => {
  const cases = [
    ["login", "Login required"],
    ["challenge", "CAPTCHA challenge"],
    ["challenge", "Security challenge"],
    ["2fa", "Enter OTP"],
    ["2fa", "Complete 2FA"],
    ["kyc", "KYC identity verification"],
    ["payment", "Payment required"],
  ];

  for (const [expectedReason, providerText] of cases) {
    const { driver } = fixture({
      authReceipt: {
        confirmed: true,
        status: "authenticated",
        confirmationId: null,
        providerText,
        activeRegistrationForm: false,
        activeAuthenticationForm: false,
      },
    });
    const session = await driver.openSession();
    const action = await driver.discoverAndAct(session, {
      goal: "Read https://fresh-events.example/ai/confirmed with the existing authenticated session",
      actionKind: "browser_auth_continuity_readback",
    });

    const receipt = await driver.readProviderReceipt(session, action);

    assert.equal(receipt.confirmed, false, providerText);
    assert.equal(receipt.handoffRequired, true, providerText);
    assert.equal(receipt.handoffReason, expectedReason, providerText);
  }
});

test("auth continuity rejects a lying model on a login URL or visible password and one-time-code forms", async () => {
  const cases = [
    {
      pageUrl: "https://fresh-events.example/login",
      domGuard: {
        passwordVisible: false, otpVisible: false, authVisible: false,
        challengeVisible: false, captchaVisible: false, kycVisible: false,
        paymentVisible: false, markerPresent: true,
      },
      reason: "login",
    },
    {
      pageUrl: "https://fresh-events.example/account",
      domGuard: {
        passwordVisible: true, otpVisible: false, authVisible: true,
        challengeVisible: false, captchaVisible: false, kycVisible: false,
        paymentVisible: false, markerPresent: true,
      },
      reason: "login",
    },
    {
      pageUrl: "https://fresh-events.example/account",
      domGuard: {
        passwordVisible: false, otpVisible: true, authVisible: true,
        challengeVisible: false, captchaVisible: false, kycVisible: false,
        paymentVisible: false, markerPresent: true,
      },
      reason: "2fa",
    },
  ];

  for (const value of cases) {
    const { driver } = fixture({
      ...value,
      authReceipt: {
        confirmed: true,
        status: "authenticated",
        confirmationId: null,
        providerText: "Products",
        activeRegistrationForm: false,
        activeAuthenticationForm: false,
      },
    });
    const session = await driver.openSession();
    const action = await driver.discoverAndAct(session, {
      goal: "Read https://fresh-events.example/account with the existing authenticated session",
      actionKind: "browser_auth_continuity_readback",
    });

    const receipt = await driver.readProviderReceipt(session, action);

    assert.equal(receipt.confirmed, false, value.reason);
    assert.equal(receipt.handoffRequired, true, value.reason);
    assert.equal(receipt.handoffReason, value.reason);
  }
});

test("auth continuity rejects an unsafe or cross-origin final redirect", async () => {
  for (const pageUrl of [
    "http://fresh-events.example/account",
    "https://127.0.0.1/account",
    "https://attacker.example/account",
  ]) {
    const { driver } = fixture({
      pageUrl,
      authReceipt: {
        confirmed: true,
        status: "authenticated",
        confirmationId: null,
        providerText: "Products",
        activeRegistrationForm: false,
        activeAuthenticationForm: false,
      },
    });
    const session = await driver.openSession();
    const action = await driver.discoverAndAct(session, {
      goal: "Read https://fresh-events.example/account with the existing authenticated session",
      actionKind: "browser_auth_continuity_readback",
    });

    const receipt = await driver.readProviderReceipt(session, action);

    assert.equal(receipt.confirmed, false, pageUrl);
    assert.equal(receipt.handoffRequired, true, pageUrl);
  }
});

test("auth continuity does not confirm an unknown page without the independently visible protected marker", async () => {
  const { driver } = fixture({
    domGuard: {
      passwordVisible: false, otpVisible: false, authVisible: false,
      challengeVisible: false, captchaVisible: false, kycVisible: false,
      paymentVisible: false, markerPresent: false,
    },
    authReceipt: {
      confirmed: true,
      status: "unknown",
      confirmationId: null,
      providerText: "Products",
      activeRegistrationForm: false,
      activeAuthenticationForm: false,
    },
  });
  const session = await driver.openSession();
  const action = await driver.discoverAndAct(session, {
    goal: "Read https://fresh-events.example/ai/confirmed with the existing authenticated session",
    actionKind: "browser_auth_continuity_readback",
  });

  const receipt = await driver.readProviderReceipt(session, action);

  assert.equal(receipt.confirmed, false);
  assert.equal(receipt.handoffRequired, true);
});

test("Sauce-style inventory confirms only with same-origin final URL, visible Products marker, and no auth or risk UI", async () => {
  const { driver, calls } = fixture({
    pageUrl: "https://fresh-events.example/inventory.html",
    domGuard: {
      passwordVisible: false, otpVisible: false, authVisible: false,
      challengeVisible: false, captchaVisible: false, kycVisible: false,
      paymentVisible: false, markerPresent: true,
    },
    authReceipt: {
      confirmed: true,
      status: "authenticated",
      confirmationId: null,
      providerText: "Products",
      activeRegistrationForm: false,
      activeAuthenticationForm: false,
    },
  });
  const session = await driver.openSession();
  const action = await driver.discoverAndAct(session, {
    goal: "Read https://fresh-events.example/inventory.html with the existing authenticated session",
    actionKind: "browser_auth_continuity_readback",
  });

  const receipt = await driver.readProviderReceipt(session, action);

  assert.equal(receipt.confirmed, true);
  assert.equal(receipt.handoffRequired, false);
  assert.equal(receipt.handoffReason, null);
  assert.deepEqual(calls.filter(([name]) => name === "evaluate").map(([, input]) => input), [
    { marker: "Products" },
  ]);
  assert.equal(calls.filter(([name]) => name === "agent").length, 0);
  assert.equal(calls.filter(([name]) => name === "execute").length, 0);
  assert.equal(calls.filter(([name]) => name === "act").length, 0);
});

test("auth continuity receipts close and scrub model-supplied status and confirmation identifiers", async () => {
  const secrets = [
    `token=${["tok", "fixture", "123456789"].join("-")}`,
    "cookie=sid-cookie-secret",
    "browser-owner@example.test",
    "https://private.example/reset?token=url-secret",
    "line-one\r\ninjected-trace",
  ];
  const { driver } = fixture({
    authReceipt: {
      confirmed: true,
      status: secrets.join(" "),
      confirmationId: secrets.join("|"),
      providerText: "Products",
      activeRegistrationForm: false,
      activeAuthenticationForm: false,
    },
  });
  const session = await driver.openSession();
  const action = await driver.discoverAndAct(session, {
    goal: "Read https://fresh-events.example/ai/confirmed with the existing authenticated session",
    actionKind: "browser_auth_continuity_readback",
  });

  const receipt = await driver.readProviderReceipt(session, action);
  const durable = JSON.stringify({ result: action, receipt });

  assert.equal(receipt.confirmed, true);
  assert.equal(receipt.status, "authenticated");
  assert.equal(receipt.confirmationId, null);
  for (const secret of secrets) {
    assert.equal(durable.includes(secret), false, secret);
  }
  assert.doesNotMatch(durable, /[\r\n]/);
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

test("provider payment requirements are classified as an honest payment handoff", async () => {
  const { driver } = fixture({
    receipt: {
      confirmed: false,
      status: "Payment required",
      confirmationId: null,
      providerText: "Enter credit card details to continue",
    },
  });
  const session = await driver.openSession();
  await driver.discoverAndAct(session, { goal: "Find and register", locale: "en" });
  const receipt = await driver.readProviderReceipt(session);
  assert.equal(receipt.confirmed, false);
  assert.equal(receipt.handoffRequired, true);
  assert.equal(receipt.handoffReason, "payment");
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

test("Add to Calendar with optional management verification and no active form is confirmed", async () => {
  const { driver } = fixture({
    receipt: {
      confirmed: false,
      status: "event_page_registration_pending",
      confirmationId: null,
      providerText: "Add to Calendar. Verify Email to manage your registration.",
      activeRegistrationForm: false,
      activeAuthenticationForm: false,
    },
  });
  const session = await driver.openSession();
  await driver.discoverAndAct(session, {
    goal: "Open https://fresh-events.example/ai/confirmed",
    actionKind: "browser_auth_continuity_readback",
  });
  const receipt = await driver.readProviderReceipt(session);
  assert.equal(receipt.confirmed, true);
  assert.equal(receipt.handoffRequired, false);
  assert.equal(receipt.handoffReason, null);
});

test("Add to Calendar does not confirm while a registration form is still active", async () => {
  const { driver } = fixture({
    receipt: {
      confirmed: false,
      status: "event_page_registration_pending",
      confirmationId: null,
      providerText: "Add to Calendar. Verify Email to manage your registration.",
      activeRegistrationForm: true,
      activeAuthenticationForm: false,
    },
  });
  const session = await driver.openSession();
  await driver.discoverAndAct(session, {
    goal: "Open https://fresh-events.example/ai/confirmed",
    actionKind: "browser_auth_continuity_readback",
  });
  const receipt = await driver.readProviderReceipt(session);
  assert.equal(receipt.confirmed, false);
  assert.equal(receipt.handoffRequired, false);
});

test("active provider OTP form remains a structured 2FA handoff", async () => {
  const { driver } = fixture({
    receipt: {
      confirmed: false,
      status: "verification required",
      confirmationId: null,
      providerText: "Add to Calendar. Enter the verification code to continue.",
      activeRegistrationForm: false,
      activeAuthenticationForm: true,
    },
  });
  const session = await driver.openSession();
  await driver.discoverAndAct(session, {
    goal: "Open https://fresh-events.example/ai/confirmed",
    actionKind: "browser_auth_continuity_readback",
  });
  const receipt = await driver.readProviderReceipt(session);
  assert.equal(receipt.confirmed, false);
  assert.equal(receipt.handoffRequired, true);
  assert.equal(receipt.handoffReason, "2fa");
});

test("login-dependent sessions restore only the exact tenant, origin, and principal context", async () => {
  const one = {
    cookies: [
      { name: "sid", value: "tenant-one-cookie", domain: "auth.fixture.dev", path: "/" },
      { name: "foreign", value: "foreign-one-cookie", domain: "other.example", path: "/" },
    ],
    localStorage: {
      "https://auth.fixture.dev": { marker: "tenant-one-storage" },
      "https://other.example": { marker: "foreign-one-storage" },
    },
  };
  const two = {
    cookies: [
      { name: "sid", value: "tenant-two-cookie", domain: "auth.fixture.dev", path: "/" },
      { name: "foreign", value: "foreign-two-cookie", domain: "other.example", path: "/" },
    ],
    localStorage: {
      "https://auth.fixture.dev": { marker: "tenant-two-storage" },
      "https://other.example": { marker: "foreign-two-storage" },
    },
  };
  const { driver, calls, authCalls } = fixture({
    authRecords: {
      "u-one": { context: one },
      "u-two": { context: two },
    },
  });

  const sessionOne = await driver.openSession({
    uid: "u-one",
    goal: "Open https://auth.fixture.dev/account?tab=profile",
    requiresLogin: true,
    principalKind: "user_provided",
  });
  const sessionTwo = await driver.openSession({
    uid: "u-two",
    goal: "Open https://auth.fixture.dev/account",
    requiresLogin: true,
    principalKind: "agent_owned",
  });

  assert.deepEqual(authCalls, [
    ["read", {
      uid: "u-one",
      origin: "https://auth.fixture.dev",
      principalKind: "user_provided",
    }],
    ["read", {
      uid: "u-two",
      origin: "https://auth.fixture.dev",
      principalKind: "agent_owned",
    }],
  ]);
  assert.deepEqual(calls.filter(([name]) => name === "create").map(([, body]) => body), [
    {
      blockAds: true,
      sessionContext: {
        cookies: [one.cookies[0]],
        localStorage: { "https://auth.fixture.dev": { marker: "tenant-one-storage" } },
      },
    },
    {
      blockAds: true,
      sessionContext: {
        cookies: [two.cookies[0]],
        localStorage: { "https://auth.fixture.dev": { marker: "tenant-two-storage" } },
      },
    },
  ]);
  assert.equal(Object.hasOwn(calls[0][1], "persist"), false);
  assert.equal(Object.hasOwn(calls[0][1], "userDataDir"), false);
  assert.doesNotMatch(
    JSON.stringify([sessionOne, sessionTwo]),
    /(?:tenant|foreign)-(?:one|two)-(?:cookie|storage)/,
    "raw context never enters the public session result",
  );
});

test("a discovery goal without an explicit URL never performs an auth lookup", async () => {
  const { driver, calls, authCalls } = fixture();
  await driver.openSession({
    uid: "u-one",
    goal: "Find a suitable free public AI event",
    requiresLogin: false,
    principalKind: "none",
  });

  assert.deepEqual(authCalls, []);
  assert.deepEqual(calls.find(([name]) => name === "create")[1], { blockAds: true });
});

test("an invalid post-create CDP endpoint releases the exact opened Steel session", async () => {
  const { driver, calls } = fixture({ websocketUrl: "ws://public-steel.example/ws" });

  await assert.rejects(() => driver.openSession(), /Railway-private Steel/i);

  assert.deepEqual(calls, [
    ["create", { blockAds: true }],
    ["release", "steel-1"],
  ]);
});

test("release exports context before Steel release, saves exact identity, and returns secret-free metadata", async () => {
  const restored = {
    cookies: [{ name: "sid", value: "restored-cookie-secret", domain: "auth.fixture.dev", path: "/" }],
  };
  const exported = {
    cookies: [{ name: "sid", value: "exported-cookie-secret", domain: "auth.fixture.dev", path: "/" }],
    localStorage: { "https://auth.fixture.dev": { marker: "exported-storage-secret" } },
  };
  const { driver, calls, authCalls } = fixture({
    authRecords: { "u-one": { context: restored } },
    exportContext: exported,
    savedRecord: { context_sha256: "a".repeat(64), key_version: 1 },
  });
  const session = await driver.openSession({
    uid: "u-one",
    goal: "Open https://auth.fixture.dev/account",
    requiresLogin: true,
    principalKind: "user_provided",
  });
  const action = await driver.discoverAndAct(session, {
    goal: "Open https://auth.fixture.dev/account",
  });

  const release = await driver.releaseSession(session.id, {
    providerReceipt: { handoff_required: false, handoff_reason: null },
  });

  assert.deepEqual(authCalls[1], ["upsert", {
    uid: "u-one",
    origin: "https://auth.fixture.dev",
    principalKind: "user_provided",
    context: exported,
  }]);
  assert.ok(
    calls.findIndex(([name]) => name === "getContext") <
      calls.findIndex(([name]) => name === "release"),
    "context export must finish before Steel is released",
  );
  assert.deepEqual(release, {
    released: true,
    origin: "https://auth.fixture.dev",
    principal_kind: "user_provided",
    auth_context_loaded: true,
    auth_context_saved: true,
    auth_context_invalidated: false,
    context_sha256: "a".repeat(64),
    key_version: 1,
  });
  assert.doesNotMatch(
    JSON.stringify({ action, release }),
    /restored-cookie-secret|exported-cookie-secret|exported-storage-secret/,
    "action output and release/trace metadata never contain browser auth material",
  );
});

test("a provider login handoff invalidates only the exact row and still releases Steel", async () => {
  const context = {
    cookies: [{ name: "sid", value: "stale-cookie-secret", domain: "auth.fixture.dev", path: "/" }],
  };
  const { driver, calls, authCalls } = fixture({
    authRecords: { "u-one": { context } },
    exportContext: context,
  });
  const session = await driver.openSession({
    uid: "u-one",
    goal: "Open https://auth.fixture.dev/account",
    requiresLogin: true,
    principalKind: "user_provided",
  });

  const release = await driver.releaseSession(session.id, {
    providerReceipt: { handoff_required: true, handoff_reason: "login" },
  });

  assert.deepEqual(authCalls[1], ["invalidate", {
    uid: "u-one",
    origin: "https://auth.fixture.dev",
    principalKind: "user_provided",
  }]);
  assert.equal(authCalls.some(([name]) => name === "upsert"), false);
  assert.equal(calls.some(([name]) => name === "getContext"), false);
  assert.deepEqual(calls.at(-1), ["release", session.id]);
  assert.equal(release.auth_context_invalidated, true);
  assert.equal(release.auth_context_saved, false);
  assert.doesNotMatch(JSON.stringify(release), /stale-cookie-secret/);
});

test("a non-login handoff exports and saves context without invalidating the row", async () => {
  const restored = {
    cookies: [{ name: "sid", value: "restored-challenge-secret", domain: "auth.fixture.dev", path: "/" }],
  };
  const exported = {
    sessionStorage: { "https://auth.fixture.dev": { marker: "challenge-session-secret" } },
  };
  const { driver, calls, authCalls } = fixture({
    authRecords: { "u-one": { context: restored } },
    exportContext: exported,
    savedRecord: { context_sha256: "b".repeat(64), key_version: 1 },
  });
  const session = await driver.openSession({
    uid: "u-one",
    goal: "Open https://auth.fixture.dev/account",
    requiresLogin: true,
    principalKind: "user_provided",
  });

  const release = await driver.releaseSession(session.id, {
    providerReceipt: { handoff_required: true, handoff_reason: "challenge" },
  });

  assert.deepEqual(authCalls[1], ["upsert", {
    uid: "u-one",
    origin: "https://auth.fixture.dev",
    principalKind: "user_provided",
    context: exported,
  }]);
  assert.equal(authCalls.some(([name]) => name === "invalidate"), false);
  assert.ok(
    calls.findIndex(([name]) => name === "getContext") <
      calls.findIndex(([name]) => name === "release"),
  );
  assert.equal(release.auth_context_saved, true);
  assert.equal(release.auth_context_invalidated, false);
  assert.doesNotMatch(
    JSON.stringify(release),
    /restored-challenge-secret|challenge-session-secret/,
  );
});

test("context save failure preserves the prior row and Steel release remains unconditional", async () => {
  const prior = {
    cookies: [{ name: "sid", value: "prior-cookie-secret", domain: "auth.fixture.dev", path: "/" }],
  };
  const exported = {
    sessionStorage: { "https://auth.fixture.dev": { marker: "new-storage-secret" } },
  };
  const { driver, calls, authCalls } = fixture({
    authRecords: { "u-one": { context: prior } },
    exportContext: exported,
    saveError: new Error("database unavailable"),
  });
  const session = await driver.openSession({
    uid: "u-one",
    goal: "Open https://auth.fixture.dev/account",
    requiresLogin: true,
    principalKind: "agent_owned",
  });

  const release = await driver.releaseSession(session.id, {
    providerReceipt: { handoff_required: false, handoff_reason: null },
  });

  assert.equal(authCalls.some(([name]) => name === "invalidate"), false, "the prior row is preserved");
  assert.deepEqual(calls.at(-1), ["release", session.id]);
  assert.equal(release.released, true);
  assert.equal(release.auth_context_saved, false);
  assert.equal(release.auth_context_invalidated, false);
  assert.doesNotMatch(JSON.stringify(release), /prior-cookie-secret|new-storage-secret|database unavailable/);
});

test("context export failure still releases Steel and never mutates the prior row", async () => {
  const prior = {
    cookies: [{ name: "sid", value: "prior-cookie-secret", domain: "auth.fixture.dev", path: "/" }],
  };
  const { driver, calls, authCalls } = fixture({
    authRecords: { "u-one": { context: prior } },
    exportError: new Error("context contained raw-cookie-secret"),
  });
  const session = await driver.openSession({
    uid: "u-one",
    goal: "Open https://auth.fixture.dev/account",
    requiresLogin: true,
    principalKind: "user_provided",
  });

  const release = await driver.releaseSession(session.id, {
    providerReceipt: { handoff_required: false, handoff_reason: null },
  });

  assert.equal(authCalls.some(([name]) => name === "upsert" || name === "invalidate"), false);
  assert.deepEqual(calls.at(-1), ["release", session.id]);
  assert.equal(release.released, true);
  assert.equal(release.auth_context_saved, false);
  assert.doesNotMatch(JSON.stringify(release), /prior-cookie-secret|raw-cookie-secret/);
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
