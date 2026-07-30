"use strict";

const assert = require("node:assert/strict");
const { spawnSync } = require("node:child_process");
const { readFileSync } = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");

const {
  INQUIRY_FORM,
  TALLY_CREATE_FORM_URL,
  TALLY_LOGIN_URL,
  TALLY_SIGNUP_URL,
  agentProfileName,
  classifyTallyMail,
  completeTallyProfile,
  createTallyInquiryForm,
  derivedTallyPassword,
  insertTallyFieldBlock,
  pollTallyMail,
  publishTallyForm,
  readTallyPublicFormUrl,
  requestTallyPasswordReset,
  requiredEnvironment,
  runTallyInquiryBootstrap,
  safeTallyFormUrl,
  submitTallyLogin,
  submitTallyPasswordReset,
  submitTallySignupEmail,
  submitTallyVerificationCode,
} = require("./browser-matrix-tally-bootstrap.js");

const ENV = Object.freeze({
  BROWSER_MATRIX_TENANT_UID: "tenant-matrix",
  LM_AGENT_BROWSER_NAME: "Life Manager",
  LM_AGENTMAIL_API_KEY: "am-key-secret",
  LM_AGENTMAIL_INBOX_ID: "browser-agent@example.test",
  LM_BROWSER_SESSION_KEY: "f".repeat(64),
  LM_FEEDBACK_DATABASE_URL: "postgres://user:pass@db.example.test/lm",
});

const PUBLIC_FORM_URL = "https://tally.so/r/wA1bC2";
const DERIVED_PASSWORD = derivedTallyPassword(ENV.LM_BROWSER_SESSION_KEY, ENV.LM_AGENTMAIL_INBOX_ID);
const AUTHENTICATED = Object.freeze({
  confirmed: true,
  origin: "https://tally.so",
  currentUrl: "https://tally.so/dashboard",
  marker: "new_form",
});
const UNAUTHENTICATED = Object.freeze({
  confirmed: false,
  origin: "https://tally.so",
  currentUrl: "https://tally.so/login",
  marker: null,
});

function fixture(overrides = {}) {
  const calls = [];
  const authQueue = Array.isArray(overrides.authenticatedQueue) ? [...overrides.authenticatedQueue] : null;
  const mailQueue = Array.isArray(overrides.mailQueue) ? [...overrides.mailQueue] : null;
  const browser = {
    sessionId: "steel-session-tally-1",
    async submitSignupEmail(email) {
      calls.push(["submitSignupEmail", email]);
      if (overrides.signupError) throw overrides.signupError;
    },
    async submitVerificationCode(code) {
      calls.push(["submitVerificationCode", code]);
      if (overrides.codeError) throw overrides.codeError;
    },
    async completeProfile(profile) {
      calls.push(["completeProfile", profile]);
      if (overrides.profileError) throw overrides.profileError;
    },
    async submitLogin(credentials) {
      calls.push(["submitLogin", credentials]);
      if (overrides.loginError) throw overrides.loginError;
    },
    async requestPasswordReset(email) {
      calls.push(["requestPasswordReset", email]);
      if (overrides.resetRequestError) throw overrides.resetRequestError;
    },
    async submitPasswordReset(input) {
      calls.push(["submitPasswordReset", input]);
      if (overrides.resetError) throw overrides.resetError;
    },
    async inspectAuthenticated() {
      calls.push(["inspectAuthenticated"]);
      if (authQueue && authQueue.length) return authQueue.shift();
      return overrides.authenticated || AUTHENTICATED;
    },
    async exportContext() {
      calls.push(["exportContext"]);
      return {
        cookies: [
          { name: "session", value: "private-cookie", domain: ".tally.so", path: "/" },
        ],
      };
    },
    async createInquiryForm(form) {
      calls.push(["createInquiryForm", form]);
      if (overrides.createError) throw overrides.createError;
      return overrides.created === undefined ? true : overrides.created;
    },
    async publishForm() {
      calls.push(["publishForm"]);
      if (overrides.publishError) throw overrides.publishError;
      return overrides.published === undefined ? true : overrides.published;
    },
    async readPublicFormUrl() {
      calls.push(["readPublicFormUrl"]);
      return overrides.formUrl === undefined ? PUBLIC_FORM_URL : overrides.formUrl;
    },
    async release() {
      calls.push(["release"]);
      return true;
    },
  };
  const deps = {
    now: () => 1_800_000_000_000,
    async openBrowser() {
      calls.push(["openBrowser"]);
      return browser;
    },
    async readTallyMail(input) {
      calls.push(["readTallyMail", input]);
      if (mailQueue && mailQueue.length) return mailQueue.shift();
      return overrides.mail === undefined ? { kind: "code", code: "428913" } : overrides.mail;
    },
    async saveContext(input) {
      calls.push(["saveContext", input]);
      return { context_sha256: "b".repeat(64), key_version: 1 };
    },
  };
  return { calls, deps, browser };
}

test("runtime image allowlists the Tally inquiry asset bootstrap entrypoint", () => {
  const dockerignore = readFileSync(path.join(__dirname, "..", ".dockerignore"), "utf8");
  assert.match(dockerignore, /^!scripts\/browser-matrix-tally-bootstrap\.js$/m);
});

test("the measured provider URLs are the only ones this bootstrap knows", () => {
  const source = readFileSync(path.join(__dirname, "browser-matrix-tally-bootstrap.js"), "utf8");

  assert.equal(TALLY_SIGNUP_URL, "https://tally.so/signup");
  assert.equal(TALLY_LOGIN_URL, "https://tally.so/login");
  assert.equal(TALLY_CREATE_FORM_URL, "https://tally.so/forms/create");
  // /signin is a live 404 and /new is not the editor: neither may come back as a constant.
  assert.doesNotMatch(source, /"https:\/\/tally\.so\/signin"/);
  assert.doesNotMatch(source, /"https:\/\/tally\.so\/new"/);
});

test("missing runtime configuration fails closed listing only variable names", async () => {
  for (const name of Object.keys(ENV)) {
    const { calls, deps } = fixture();
    const env = { ...ENV, [name]: "" };

    const failure = await runTallyInquiryBootstrap({ env, deps }).then(() => null, (error) => error);

    assert.equal(failure.code, "CONFIG");
    assert.match(failure.message, new RegExp(`missing (?:[A-Z_, ]*)${name}`));
    assert.doesNotMatch(
      failure.message,
      /browser-agent@example|am-key-secret|postgres:\/\/|ffffff/,
    );
    assert.deepEqual(calls, []);
  }
});

test("a non-address account identity fails before opening Steel", async () => {
  const { calls, deps } = fixture();

  await assert.rejects(
    runTallyInquiryBootstrap({ env: { ...ENV, LM_AGENTMAIL_INBOX_ID: "not-an-address" }, deps }),
    /configuration unavailable: missing LM_AGENTMAIL_INBOX_ID/,
  );

  assert.deepEqual(calls, []);
});

test("requiredEnvironment lists every missing name at once", () => {
  const failure = (() => {
    try { requiredEnvironment({ LM_AGENT_BROWSER_NAME: "Life Manager" }); return null; }
    catch (error) { return error; }
  })();

  assert.equal(failure.code, "CONFIG");
  assert.equal(
    failure.message,
    "Tally inquiry asset configuration unavailable: missing BROWSER_MATRIX_TENANT_UID, "
    + "LM_AGENTMAIL_API_KEY, LM_AGENTMAIL_INBOX_ID, LM_BROWSER_SESSION_KEY, "
    + "LM_FEEDBACK_DATABASE_URL",
  );
  assert.equal(requiredEnvironment(ENV), true);
});

// ─── derived credential ─────────────────────────────────────────────────────────────────────────

test("the account password is derived, stable, tenant-bound and never emitted", async () => {
  assert.equal(
    derivedTallyPassword(ENV.LM_BROWSER_SESSION_KEY, ENV.LM_AGENTMAIL_INBOX_ID),
    derivedTallyPassword(ENV.LM_BROWSER_SESSION_KEY, ENV.LM_AGENTMAIL_INBOX_ID),
  );
  assert.notEqual(
    derivedTallyPassword(ENV.LM_BROWSER_SESSION_KEY, "other-agent@example.test"),
    DERIVED_PASSWORD,
  );
  assert.notEqual(
    derivedTallyPassword("a".repeat(64), ENV.LM_AGENTMAIL_INBOX_ID),
    DERIVED_PASSWORD,
  );
  // Tally's complexity rule: the affixes guarantee all four classes whatever base64url emits.
  assert.equal(DERIVED_PASSWORD.length, 33);
  assert.match(DERIVED_PASSWORD, /[a-z]/);
  assert.match(DERIVED_PASSWORD, /[A-Z]/);
  assert.match(DERIVED_PASSWORD, /[0-9]/);
  assert.match(DERIVED_PASSWORD, /[^A-Za-z0-9]/);
  // It must never be reconstructible from what the account key alone looks like.
  assert.doesNotMatch(DERIVED_PASSWORD, /browser-agent|example\.test/);

  const { deps } = fixture();
  const result = await runTallyInquiryBootstrap({ env: ENV, deps });
  assert.equal(JSON.stringify(result).includes(DERIVED_PASSWORD), false);
});

test("a display name always yields both profile fields", () => {
  assert.deepEqual(agentProfileName("Life Manager"), { firstName: "Life", lastName: "Manager" });
  assert.deepEqual(agentProfileName("  Anicca  "), { firstName: "Anicca", lastName: "Anicca" });
  assert.deepEqual(agentProfileName("Life Manager Agent"), { firstName: "Life", lastName: "Manager Agent" });
  assert.throws(() => agentProfileName("   "), /missing LM_AGENT_BROWSER_NAME/);
});

// ─── the two measured account paths ─────────────────────────────────────────────────────────────

test("a fresh account signs up, verifies the code, completes the profile and publishes", async () => {
  const { calls, deps } = fixture();

  const result = await runTallyInquiryBootstrap({ env: ENV, deps });

  assert.deepEqual(result, {
    origin: "https://tally.so",
    form_url: PUBLIC_FORM_URL,
    context_saved: true,
    steel_released: true,
  });
  assert.deepEqual(Object.keys(result), ["origin", "form_url", "context_saved", "steel_released"]);
  assert.deepEqual(calls[0], ["openBrowser"]);
  // The AgentMail address is the account — the unreadable gmail plus-address is never used.
  assert.deepEqual(calls[1], ["submitSignupEmail", ENV.LM_AGENTMAIL_INBOX_ID]);
  assert.deepEqual(calls[2], ["readTallyMail", { afterMs: 1_800_000_000_000 }]);
  assert.deepEqual(calls[3], ["submitVerificationCode", "428913"]);
  assert.deepEqual(calls[4], ["completeProfile", {
    firstName: "Life",
    lastName: "Manager",
    password: DERIVED_PASSWORD,
  }]);
  assert.deepEqual(calls[5], ["inspectAuthenticated"]);
  assert.deepEqual(calls[6], ["exportContext"]);
  assert.deepEqual(calls[7], ["saveContext", {
    uid: "tenant-matrix",
    origin: "https://tally.so",
    principalKind: "agent_owned",
    context: {
      cookies: [
        { name: "session", value: "private-cookie", domain: ".tally.so", path: "/" },
      ],
    },
  }]);
  assert.deepEqual(calls[8], ["createInquiryForm", INQUIRY_FORM]);
  assert.deepEqual(calls[9], ["publishForm"]);
  assert.deepEqual(calls[10], ["readPublicFormUrl"]);
  assert.deepEqual(calls.at(-1), ["release"]);
  assert.equal(calls.some(([name]) => name === "submitLogin"), false);
  assert.equal(calls.some(([name]) => name === "requestPasswordReset"), false);
  assert.deepEqual(
    INQUIRY_FORM.fields.map((field) => [field.label, field.kind, field.block]),
    [["name", "text", "Short answer"], ["email", "email", "Email"], ["message", "long_text", "Long answer"]],
  );
  assert.equal(INQUIRY_FORM.title, "Life Manager inquiry");
});

test("an existing account logs in with the derived password and never signs up twice", async () => {
  const { calls, deps } = fixture({ mail: { kind: "account_exists" } });

  const result = await runTallyInquiryBootstrap({ env: ENV, deps });

  assert.equal(result.form_url, PUBLIC_FORM_URL);
  assert.deepEqual(calls[1], ["submitSignupEmail", ENV.LM_AGENTMAIL_INBOX_ID]);
  assert.deepEqual(calls[3], ["submitLogin", {
    email: ENV.LM_AGENTMAIL_INBOX_ID,
    password: DERIVED_PASSWORD,
  }]);
  assert.equal(calls.some(([name]) => name === "submitVerificationCode"), false);
  assert.equal(calls.some(([name]) => name === "completeProfile"), false);
  assert.equal(calls.some(([name]) => name === "requestPasswordReset"), false);
  assert.deepEqual(calls.at(-1), ["release"]);
});

test("an existing account whose password predates this key is reclaimed through the reset flow", async () => {
  const { calls, deps } = fixture({
    mailQueue: [{ kind: "account_exists" }, { kind: "code", code: "775501" }],
    authenticatedQueue: [UNAUTHENTICATED, AUTHENTICATED],
  });

  const result = await runTallyInquiryBootstrap({ env: ENV, deps });

  assert.equal(result.form_url, PUBLIC_FORM_URL);
  const names = calls.map(([name]) => name);
  assert.deepEqual(names.slice(0, 9), [
    "openBrowser",
    "submitSignupEmail",
    "readTallyMail",
    "submitLogin",
    "inspectAuthenticated",
    "requestPasswordReset",
    "readTallyMail",
    "submitPasswordReset",
    "inspectAuthenticated",
  ]);
  assert.deepEqual(calls[5], ["requestPasswordReset", ENV.LM_AGENTMAIL_INBOX_ID]);
  // The reset code AND the new password go together, exactly as the measured page demands.
  assert.deepEqual(calls[7], ["submitPasswordReset", {
    code: "775501",
    password: DERIVED_PASSWORD,
  }]);
  assert.deepEqual(calls.at(-1), ["release"]);
});

test("a reset that never yields a code fails closed at its own stage and still releases", async () => {
  const { calls, deps } = fixture({
    mailQueue: [{ kind: "account_exists" }, { kind: "account_exists" }],
    authenticatedQueue: [UNAUTHENTICATED, AUTHENTICATED],
  });

  const failure = await runTallyInquiryBootstrap({ env: ENV, deps }).then(() => null, (error) => error);

  assert.equal(failure.code, "RESET_PASSWORD");
  assert.equal(failure.message, "Tally inquiry asset unavailable");
  assert.equal(calls.some(([name]) => name === "submitPasswordReset"), false);
  assert.equal(calls.some(([name]) => name === "saveContext"), false);
  assert.deepEqual(calls.at(-1), ["release"]);
});

test("an unrecognised mailbox verdict never guesses a branch", async () => {
  for (const mail of [null, {}, { kind: "magic_link" }, { kind: "code" }]) {
    const { calls, deps } = fixture({ mail });

    const failure = await runTallyInquiryBootstrap({ env: ENV, deps }).then(() => null, (error) => error);

    assert.equal(failure.message, "Tally inquiry asset unavailable");
    assert.equal(
      failure.code,
      mail && mail.kind === "code" ? "SUBMIT_CODE" : "POLL_EMAIL",
    );
    assert.equal(calls.some(([name]) => name === "saveContext"), false);
    assert.deepEqual(calls.at(-1), ["release"]);
  }
});

test("the emitted payload carries no code, mail body, cookie, password or credential", async () => {
  const { deps } = fixture();

  const result = await runTallyInquiryBootstrap({ env: ENV, deps });
  const serialized = JSON.stringify(result);

  assert.doesNotMatch(
    serialized,
    /428913|otp|code|cookie|session|authorization|bearer|browser-agent@example|am-key-secret|postgres:\/\//i,
  );
  assert.doesNotMatch(serialized, /tally\.so\/(?!r\/)/);
  assert.equal(serialized.match(/https:\/\//g).length, 2);
});

test("a mid-flow provider failure still releases the cloud session and exposes only a stage", async () => {
  for (const [overrides, code] of [
    [{ signupError: new Error("provider response contained private diagnostics") }, "SUBMIT_EMAIL"],
    [{ codeError: new Error("code field missing") }, "SUBMIT_CODE"],
    [{ profileError: new Error("complete-profile DOM drifted") }, "COMPLETE_PROFILE"],
    [{ mail: { kind: "account_exists" }, loginError: new Error("login refused") }, "LOGIN"],
    [{
      mailQueue: [{ kind: "account_exists" }, { kind: "code", code: "775501" }],
      authenticatedQueue: [UNAUTHENTICATED, AUTHENTICATED],
      resetError: new Error("reset refused"),
    }, "RESET_PASSWORD"],
    [{ createError: new Error("editor DOM drifted: browser-agent@example.test") }, "CREATE_FORM"],
    [{ publishError: new Error("publish button missing") }, "PUBLISH_FORM"],
    [{ published: false }, "PUBLISH_FORM"],
    [{ created: false }, "CREATE_FORM"],
  ]) {
    const { calls, deps } = fixture(overrides);

    const failure = await runTallyInquiryBootstrap({ env: ENV, deps }).then(
      () => null,
      (error) => error,
    );

    assert.equal(failure.message, "Tally inquiry asset unavailable");
    assert.equal(failure.code, code);
    assert.doesNotMatch(
      `${failure.message} ${failure.code}`,
      /private diagnostics|DOM drifted|refused|browser-agent@example/,
    );
    assert.deepEqual(calls.at(-1), ["release"]);
  }
});

test("an unconfirmed dashboard never saves a context and still releases", async () => {
  const { calls, deps } = fixture({ authenticated: UNAUTHENTICATED });

  await assert.rejects(
    runTallyInquiryBootstrap({ env: ENV, deps }),
    /Tally inquiry asset unavailable/,
  );

  assert.equal(calls.some(([name]) => name === "saveContext"), false);
  assert.equal(calls.some(([name]) => name === "createInquiryForm"), false);
  assert.deepEqual(calls.at(-1), ["release"]);
});

test("an auth snapshot taken on an auth page is never accepted as a dashboard", async () => {
  for (const currentUrl of [
    "https://tally.so/login",
    "https://tally.so/signup",
    "https://tally.so/forgot-password/reset",
    "https://tally.so/complete-profile",
    "https://impostor.example/dashboard",
  ]) {
    const { calls, deps } = fixture({
      authenticated: { confirmed: true, origin: "https://tally.so", currentUrl, marker: "new_form" },
    });

    await assert.rejects(
      runTallyInquiryBootstrap({ env: ENV, deps }),
      /Tally inquiry asset unavailable/,
    );

    assert.equal(calls.some(([name]) => name === "saveContext"), false);
    assert.deepEqual(calls.at(-1), ["release"]);
  }
});

test("only an exact six-digit challenge is submitted to the provider", async () => {
  for (const code of ["12345", "1234567", "https://tally.so/verify?code=428913", "", null]) {
    const { calls, deps } = fixture({ mail: { kind: "code", code } });

    await assert.rejects(
      runTallyInquiryBootstrap({ env: ENV, deps }),
      /Tally inquiry asset unavailable/,
    );

    assert.equal(calls.some(([name]) => name === "submitVerificationCode"), false);
    assert.deepEqual(calls.at(-1), ["release"]);
  }
});

test("only a published public responder URL is accepted as the form URL", async () => {
  assert.equal(safeTallyFormUrl(PUBLIC_FORM_URL), PUBLIC_FORM_URL);
  for (const candidate of [
    "https://tally.so/forms/wA1bC2/edit",
    "https://tally.so/forms/wA1bC2/share",
    "https://tally.so/r/wA1bC2?edit-token=secret",
    "https://tally.so/r/wA1bC2#admin",
    "http://tally.so/r/wA1bC2",
    "https://attacker.example/r/wA1bC2",
    "https://user:pass@tally.so/r/wA1bC2",
    "not-a-url",
    "",
  ]) {
    assert.throws(() => safeTallyFormUrl(candidate), /Tally inquiry asset unavailable/);
    const { calls, deps } = fixture({ formUrl: candidate });
    await assert.rejects(
      runTallyInquiryBootstrap({ env: ENV, deps }),
      /Tally inquiry asset unavailable/,
    );
    assert.deepEqual(calls.at(-1), ["release"]);
  }
});

// ─── mailbox reading ────────────────────────────────────────────────────────────────────────────

test("the mailbox verdict distinguishes a verification code from an existing account", () => {
  // Measured subject for BOTH the signup code and the reset code.
  assert.deepEqual(classifyTallyMail({
    from: "Tally <noreply@tally.so>",
    subject: "Confirm your email address",
    text: "Your verification code is 428913. It expires in 10 minutes.",
  }), { kind: "code", code: "428913" });
  assert.deepEqual(classifyTallyMail({
    from: "Tally <noreply@tally.so>",
    html: '<p>Code: <b>428913</b></p><a style="color:#123456" href="https://track.example/c/998877">Open</a>',
  }), { kind: "code", code: "428913" });
  // Measured mail when the address already has an account: no code, a different branch.
  assert.deepEqual(classifyTallyMail({
    from: "Tally <noreply@tally.so>",
    subject: "You already have a Tally account",
    text: "Someone tried to create a new account using this email address, but an account already exists.",
  }), { kind: "account_exists" });
  // A tracking link is the only six-digit run: nothing is extracted from it.
  assert.equal(classifyTallyMail({
    from: "Tally <noreply@tally.so>",
    text: "Open https://track.example/click/998877 to continue.",
  }), null);
  // Ambiguity fails closed rather than guessing between two candidates.
  assert.equal(classifyTallyMail({
    from: "Tally <noreply@tally.so>",
    text: "Code 428913 or 100200?",
  }), null);
  assert.equal(classifyTallyMail({
    from: "Tally <noreply@tally.so>",
    text: "Code 42891",
  }), null);
  assert.equal(classifyTallyMail({
    from: "attacker@example.test",
    subject: "Your Tally login code",
    text: "Use 428913 now.",
  }), null);
});

function mailboxTransport(messages) {
  const requests = [];
  return {
    requests,
    async fetchImpl(url, options) {
      requests.push([String(url), options && options.headers && options.headers.Authorization]);
      if (/\/messages\?limit=/.test(String(url))) {
        return { ok: true, async json() { return { messages }; } };
      }
      const id = decodeURIComponent(String(url).split("/").pop());
      const message = messages.find((candidate) => candidate.message_id === id);
      return { ok: true, async json() { return message ? message.detail : {}; } };
    },
  };
}

test("bounded mailbox polling returns the newest provider verdict without echoing the mail", async () => {
  const transport = mailboxTransport([
    {
      message_id: "old",
      from: "Tally <noreply@tally.so>",
      timestamp: "2027-01-01T00:00:00.000Z",
      detail: { from: "Tally <noreply@tally.so>", text: "Your Tally code is 111111" },
    },
    {
      message_id: "new",
      from: "Tally <noreply@tally.so>",
      timestamp: "2027-01-01T00:05:00.000Z",
      detail: { from: "Tally <noreply@tally.so>", text: "Your Tally code is 428913" },
    },
  ]);
  const sleeps = [];

  const verdict = await pollTallyMail({
    afterMs: Date.parse("2027-01-01T00:00:00.000Z"),
    apiKey: "am-key-secret",
    inbox: "browser-agent@example.test",
    fetchImpl: transport.fetchImpl,
    now: () => Date.parse("2027-01-01T00:06:00.000Z"),
    sleep: async (ms) => { sleeps.push(ms); },
  });

  assert.deepEqual(verdict, { kind: "code", code: "428913" });
  assert.deepEqual(sleeps, []);
  assert.equal(transport.requests[0][1], "Bearer am-key-secret");
  assert.match(transport.requests[0][0], /\/inboxes\/browser-agent%40example\.test\/messages\?limit=20$/);
});

test("mailbox polling reports an existing account instead of waiting for a code that never comes", async () => {
  const transport = mailboxTransport([
    {
      message_id: "exists",
      from: "Tally <noreply@tally.so>",
      subject: "You already have a Tally account",
      timestamp: "2027-01-01T00:05:00.000Z",
      detail: {
        from: "Tally <noreply@tally.so>",
        text: "Someone tried to create a new account using this email address, but an account already exists.",
      },
    },
  ]);

  const verdict = await pollTallyMail({
    afterMs: Date.parse("2027-01-01T00:00:00.000Z"),
    apiKey: "am-key-secret",
    inbox: "browser-agent@example.test",
    fetchImpl: transport.fetchImpl,
    now: () => Date.parse("2027-01-01T00:06:00.000Z"),
    sleep: async () => {},
  });

  assert.deepEqual(verdict, { kind: "account_exists" });
});

test("mailbox polling gives up at the bounded deadline on a fake clock", async () => {
  const transport = mailboxTransport([]);
  let current = 1_800_000_000_000;
  const sleeps = [];

  await assert.rejects(
    pollTallyMail({
      afterMs: current,
      apiKey: "am-key-secret",
      inbox: "browser-agent@example.test",
      fetchImpl: transport.fetchImpl,
      now: () => current,
      sleep: async (ms) => { sleeps.push(ms); current += ms; },
    }),
    /Tally inquiry asset unavailable/,
  );

  assert.equal(transport.requests.length, 40);
  assert.equal(sleeps.length, 40);
  assert.equal(new Set(sleeps).size, 1);
  assert.equal(current - 1_800_000_000_000, 120_000);
});

// ─── page steps ─────────────────────────────────────────────────────────────────────────────────

function recordingPage(result = true) {
  const expressions = [];
  return {
    expressions,
    async evaluate(expression) {
      expressions.push(expression);
      return result;
    },
  };
}

test("every auth step drives the measured ids and refuses the Google/Apple buttons", async () => {
  const page = recordingPage();

  await submitTallySignupEmail(page, ENV.LM_AGENTMAIL_INBOX_ID);
  await submitTallyVerificationCode(page, "428913");
  await completeTallyProfile(page, { firstName: "Life", lastName: "Manager", password: DERIVED_PASSWORD });
  await submitTallyLogin(page, { email: ENV.LM_AGENTMAIL_INBOX_ID, password: DERIVED_PASSWORD });
  await requestTallyPasswordReset(page, ENV.LM_AGENTMAIL_INBOX_ID);
  await submitTallyPasswordReset(page, { code: "775501", password: DERIVED_PASSWORD });

  const [signup, code, profile, login, forgot, reset] = page.expressions;
  assert.equal(page.expressions.length, 6);
  assert.match(signup, /#email/);
  assert.match(signup, /browser-agent@example\.test/);
  assert.match(code, /#code/);
  assert.match(code, /428913/);
  assert.match(profile, /#firstName/);
  assert.match(profile, /#lastName/);
  assert.match(profile, /#password/);
  assert.match(login, /#email/);
  assert.match(login, /#password/);
  assert.match(forgot, /#email/);
  // Measured: the reset page takes the code and BOTH password fields together.
  assert.match(reset, /#code/);
  assert.match(reset, /#password/);
  assert.match(reset, /#confirmPassword/);
  for (const expression of page.expressions) {
    assert.match(expression, /google\|apple/i);
    assert.match(expression, /submit/);
    assert.match(expression, /dispatchEvent/);
    // No <form> lookup: the measured login page reports zero forms in some renders.
    assert.doesNotMatch(expression, /closest\("form"\)/);
  }
});

test("an auth step that cannot find its measured control fails closed", async () => {
  const page = recordingPage(false);

  await assert.rejects(
    submitTallySignupEmail(page, ENV.LM_AGENTMAIL_INBOX_ID),
    /Tally inquiry asset unavailable/,
  );
  await assert.rejects(
    submitTallyLogin(page, { email: ENV.LM_AGENTMAIL_INBOX_ID, password: DERIVED_PASSWORD }),
    /Tally inquiry asset unavailable/,
  );
});

function editorPage(blockNames) {
  const events = [];
  let filtered = null;
  const page = {
    events,
    async navigate(url) { events.push(["navigate", url]); },
    async evaluate(expression) {
      if (/contenteditable/.test(expression)) {
        events.push(["point"]);
        return { x: 120, y: 240 };
      }
      if (/Open block selection modal/.test(expression)) {
        events.push(["openBlockModal"]);
        return true;
      }
      if (/find questions/i.test(expression)) {
        filtered = (expression.match(/set\.call\(search, "([^"]+)"\)/) || [])[1] || null;
        events.push(["filter", filtered]);
        return true;
      }
      if (/class~="selected"/.test(expression)) {
        events.push(["highlighted"]);
        return blockNames ? blockNames.shift() : filtered;
      }
      events.push(["evaluate"]);
      return true;
    },
    async clickAt(point) { events.push(["clickAt", point]); },
    async insertText(text) { events.push(["insertText", text]); },
    async pressKey(key) { events.push(["pressKey", key.key]); },
  };
  return page;
}

test("form creation drives the measured editor affordances in a fixed order", async () => {
  const page = editorPage(null);

  assert.equal(await createTallyInquiryForm(page, INQUIRY_FORM, async () => {}), true);

  assert.deepEqual(page.events[0], ["navigate", "https://tally.so/forms/create"]);
  assert.deepEqual(page.events[1], ["point"]);
  assert.deepEqual(page.events[2], ["clickAt", { x: 120, y: 240 }]);
  assert.deepEqual(page.events[3], ["insertText", "Life Manager inquiry"]);
  // Per field: Enter for a new block, focus it, open the modal, filter, read the highlight back,
  // Enter to insert, then type the label.
  assert.deepEqual(page.events.slice(4, 12), [
    ["pressKey", "Enter"],
    ["point"],
    ["clickAt", { x: 120, y: 240 }],
    ["openBlockModal"],
    ["filter", "Short answer"],
    ["highlighted"],
    ["pressKey", "Enter"],
    ["insertText", "name"],
  ]);
  assert.deepEqual(
    page.events.filter(([kind]) => kind === "filter").map(([, value]) => value),
    ["Short answer", "Email", "Long answer"],
  );
  assert.deepEqual(
    page.events.filter(([kind]) => kind === "insertText").map(([, value]) => value),
    ["Life Manager inquiry", "name", "email", "message"],
  );
  // The measured editor never opens a block menu by typing "/".
  assert.equal(page.events.some(([kind, value]) => kind === "insertText" && value === "/"), false);
});

test("a drifted block highlight is never inserted", async () => {
  const page = editorPage(["Long answer"]);

  await assert.rejects(
    insertTallyFieldBlock(page, INQUIRY_FORM.fields[0], async () => {}),
    /Tally inquiry asset unavailable/,
  );

  // It fails BEFORE the Enter that would have inserted the wrong block type.
  assert.equal(page.events.filter(([kind]) => kind === "pressKey").length, 1);
  assert.equal(page.events.some(([kind]) => kind === "insertText"), false);
});

test("publish and share readback use name/text lookups and only /r/ links", async () => {
  const publishExpressions = [];
  await publishTallyForm({
    async evaluate(expression) { publishExpressions.push(expression); return true; },
  });
  assert.match(publishExpressions[0], /publish/i);
  await assert.rejects(
    publishTallyForm({ async evaluate() { return false; } }),
    /Tally inquiry asset unavailable/,
  );

  const readExpressions = [];
  const found = await readTallyPublicFormUrl({
    async evaluate(expression) { readExpressions.push(expression); return PUBLIC_FORM_URL; },
  });
  assert.equal(found, PUBLIC_FORM_URL);
  assert.match(readExpressions[0], /tally\\\.so\\\/r\\\//);
  assert.doesNotMatch(readExpressions[0], /\/edit/);
});

test("the CLI exits nonzero with an empty stdout when configuration is absent", () => {
  const run = spawnSync(
    process.execPath,
    [path.join(__dirname, "browser-matrix-tally-bootstrap.js")],
    { env: { PATH: process.env.PATH }, encoding: "utf8" },
  );

  assert.equal(run.status, 1);
  assert.equal(run.stdout, "");
  assert.match(run.stderr, /Tally inquiry asset configuration unavailable: missing /);
  assert.match(run.stderr, /\[CONFIG\]\n$/);
  assert.doesNotMatch(run.stderr, /browser-agent@example|am-key-secret|postgres:\/\/|Bearer/);
});
