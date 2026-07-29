"use strict";

const assert = require("node:assert/strict");
const { spawnSync } = require("node:child_process");
const { readFileSync } = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");

const {
  INQUIRY_FORM,
  createTallyInquiryForm,
  extractTallyLoginCode,
  pollTallyLoginCode,
  publishTallyForm,
  readTallyPublicFormUrl,
  requestTallyEmailLogin,
  requiredEnvironment,
  runTallyInquiryBootstrap,
  safeTallyFormUrl,
  submitTallyLoginCode,
} = require("./browser-matrix-tally-bootstrap.js");

const ENV = Object.freeze({
  BROWSER_MATRIX_TENANT_UID: "tenant-matrix",
  LM_AGENT_BROWSER_EMAIL: "agent@example.test",
  LM_AGENT_BROWSER_NAME: "Life Manager",
  LM_AGENTMAIL_API_KEY: "am-key-secret",
  LM_AGENTMAIL_INBOX_ID: "browser-agent@example.test",
  LM_BROWSER_SESSION_KEY: "f".repeat(64),
  LM_FEEDBACK_DATABASE_URL: "postgres://user:pass@db.example.test/lm",
});

const PUBLIC_FORM_URL = "https://tally.so/r/wA1bC2";

function fixture(overrides = {}) {
  const calls = [];
  const browser = {
    sessionId: "steel-session-tally-1",
    async requestLoginCode(email) {
      calls.push(["requestLoginCode", email]);
      if (overrides.requestError) throw overrides.requestError;
    },
    async submitLoginCode(code) {
      calls.push(["submitLoginCode", code]);
    },
    async inspectAuthenticated() {
      calls.push(["inspectAuthenticated"]);
      return overrides.authenticated || {
        confirmed: true,
        origin: "https://tally.so",
        currentUrl: "https://tally.so/forms",
        marker: "new_form",
      };
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
    async readLoginCode(input) {
      calls.push(["readLoginCode", input]);
      return overrides.loginCode === undefined ? "428913" : overrides.loginCode;
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

test("missing runtime configuration fails closed listing only variable names", async () => {
  for (const name of Object.keys(ENV)) {
    const { calls, deps } = fixture();
    const env = { ...ENV, [name]: "" };

    const failure = await runTallyInquiryBootstrap({ env, deps }).then(() => null, (error) => error);

    assert.equal(failure.code, "CONFIG");
    assert.match(failure.message, new RegExp(`missing (?:[A-Z_, ]*)${name}`));
    assert.doesNotMatch(
      failure.message,
      /agent@example|browser-agent@example|am-key-secret|postgres:\/\/|ffffff/,
    );
    assert.deepEqual(calls, []);
  }
});

test("a non-address login identity fails before opening Steel", async () => {
  const { calls, deps } = fixture();

  await assert.rejects(
    runTallyInquiryBootstrap({ env: { ...ENV, LM_AGENT_BROWSER_EMAIL: "not-an-address" }, deps }),
    /configuration unavailable: missing LM_AGENT_BROWSER_EMAIL/,
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
    + "LM_AGENT_BROWSER_EMAIL, LM_AGENTMAIL_API_KEY, LM_AGENTMAIL_INBOX_ID, "
    + "LM_BROWSER_SESSION_KEY, LM_FEEDBACK_DATABASE_URL",
  );
  assert.equal(requiredEnvironment(ENV), true);
});

test("cloud email-code login creates the controlled inquiry form and emits only the public URL", async () => {
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
  assert.deepEqual(calls[1], ["requestLoginCode", ENV.LM_AGENT_BROWSER_EMAIL]);
  assert.deepEqual(calls[2], ["readLoginCode", { afterMs: 1_800_000_000_000 }]);
  assert.deepEqual(calls[3], ["submitLoginCode", "428913"]);
  assert.deepEqual(calls[4], ["inspectAuthenticated"]);
  assert.deepEqual(calls[5], ["exportContext"]);
  assert.deepEqual(calls[6], ["saveContext", {
    uid: "tenant-matrix",
    origin: "https://tally.so",
    principalKind: "agent_owned",
    context: {
      cookies: [
        { name: "session", value: "private-cookie", domain: ".tally.so", path: "/" },
      ],
    },
  }]);
  assert.deepEqual(calls[7], ["createInquiryForm", INQUIRY_FORM]);
  assert.deepEqual(calls[8], ["publishForm"]);
  assert.deepEqual(calls[9], ["readPublicFormUrl"]);
  assert.deepEqual(calls.at(-1), ["release"]);
  assert.deepEqual(
    INQUIRY_FORM.fields.map((field) => [field.label, field.kind]),
    [["name", "text"], ["email", "email"], ["message", "long_text"]],
  );
  assert.equal(INQUIRY_FORM.title, "Life Manager inquiry");
});

test("the emitted payload carries no OTP, mail body, cookie, or credential", async () => {
  const { deps } = fixture();

  const result = await runTallyInquiryBootstrap({ env: ENV, deps });
  const serialized = JSON.stringify(result);

  assert.doesNotMatch(
    serialized,
    /428913|otp|code|cookie|session|authorization|bearer|agent@example|browser-agent@example|am-key-secret|postgres:\/\//i,
  );
  assert.doesNotMatch(serialized, /tally\.so\/(?!r\/)/);
  assert.equal(serialized.match(/https:\/\//g).length, 2);
});

test("a mid-flow provider failure still releases the cloud session and exposes only a stage", async () => {
  for (const [overrides, code] of [
    [{ requestError: new Error("provider response contained private diagnostics") }, "SUBMIT_EMAIL"],
    [{ createError: new Error("editor DOM drifted: agent@example.test") }, "CREATE_FORM"],
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
      /private diagnostics|DOM drifted|agent@example|browser-agent@example/,
    );
    assert.deepEqual(calls.at(-1), ["release"]);
  }
});

test("an unconfirmed dashboard never saves a context and still releases", async () => {
  const { calls, deps } = fixture({
    authenticated: {
      confirmed: false,
      origin: "https://tally.so",
      currentUrl: "https://tally.so/signin",
      marker: null,
    },
  });

  await assert.rejects(
    runTallyInquiryBootstrap({ env: ENV, deps }),
    /Tally inquiry asset unavailable/,
  );

  assert.equal(calls.some(([name]) => name === "saveContext"), false);
  assert.equal(calls.some(([name]) => name === "createInquiryForm"), false);
  assert.deepEqual(calls.at(-1), ["release"]);
});

test("only an exact six-digit challenge is submitted to the provider", async () => {
  for (const loginCode of ["12345", "1234567", "https://tally.so/verify?code=428913", "", null]) {
    const { calls, deps } = fixture({ loginCode });

    await assert.rejects(
      runTallyInquiryBootstrap({ env: ENV, deps }),
      /Tally inquiry asset unavailable/,
    );

    assert.equal(calls.some(([name]) => name === "submitLoginCode"), false);
    assert.deepEqual(calls.at(-1), ["release"]);
  }
});

test("only a published public responder URL is accepted as the form URL", async () => {
  assert.equal(safeTallyFormUrl(PUBLIC_FORM_URL), PUBLIC_FORM_URL);
  for (const candidate of [
    "https://tally.so/forms/wA1bC2/edit",
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

test("the login code is read as six digits only, never from links or ambiguous bodies", () => {
  assert.equal(extractTallyLoginCode({
    from: "Tally <noreply@tally.so>",
    subject: "Your login code",
    text: "Your Tally login code is 428913. It expires in 10 minutes.",
  }), "428913");
  assert.equal(extractTallyLoginCode({
    from: "Tally <noreply@tally.so>",
    html: '<p>Code: <b>428913</b></p><a style="color:#123456" href="https://track.example/c/998877">Open</a>',
  }), "428913");
  // A tracking link is the only six-digit run: nothing is extracted from it.
  assert.equal(extractTallyLoginCode({
    from: "Tally <noreply@tally.so>",
    text: "Open https://track.example/click/998877 to continue.",
  }), null);
  // Ambiguity fails closed rather than guessing between two candidates.
  assert.equal(extractTallyLoginCode({
    from: "Tally <noreply@tally.so>",
    text: "Code 428913 or 100200?",
  }), null);
  assert.equal(extractTallyLoginCode({
    from: "Tally <noreply@tally.so>",
    text: "Code 42891",
  }), null);
  assert.equal(extractTallyLoginCode({
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

test("bounded mailbox polling returns the newest provider code without echoing the mail", async () => {
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

  const code = await pollTallyLoginCode({
    afterMs: Date.parse("2027-01-01T00:00:00.000Z"),
    apiKey: "am-key-secret",
    inbox: "browser-agent@example.test",
    fetchImpl: transport.fetchImpl,
    now: () => Date.parse("2027-01-01T00:06:00.000Z"),
    sleep: async (ms) => { sleeps.push(ms); },
  });

  assert.equal(code, "428913");
  assert.deepEqual(sleeps, []);
  assert.equal(transport.requests[0][1], "Bearer am-key-secret");
  assert.match(transport.requests[0][0], /\/inboxes\/browser-agent%40example\.test\/messages\?limit=20$/);
});

test("mailbox polling gives up at the bounded deadline on a fake clock", async () => {
  const transport = mailboxTransport([]);
  let current = 1_800_000_000_000;
  const sleeps = [];

  await assert.rejects(
    pollTallyLoginCode({
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

test("the login form is filled and submitted through measured page controls", async () => {
  const expressions = [];
  const page = {
    async evaluate(expression) {
      expressions.push(expression);
      return true;
    },
  };

  assert.equal(await requestTallyEmailLogin(page, ENV.LM_AGENT_BROWSER_EMAIL), true);
  assert.equal(expressions.length, 1);
  assert.match(expressions[0], /input\[type="email"\]/);
  assert.match(expressions[0], /agent@example\.test/);
  assert.match(expressions[0], /dispatchEvent/);

  assert.equal(await submitTallyLoginCode(page, "428913"), true);
  assert.equal(expressions.length, 2);
  assert.match(expressions[1], /one-time-code/);
  assert.match(expressions[1], /428913/);
});

test("form creation drives the SPA editor with trusted input in a fixed order", async () => {
  const events = [];
  const page = {
    async navigate(url) { events.push(["navigate", url]); },
    async evaluate() { events.push(["evaluate"]); return { x: 120, y: 240 }; },
    async clickAt(point) { events.push(["clickAt", point]); },
    async insertText(text) { events.push(["insertText", text]); },
    async pressKey(key) { events.push(["pressKey", key.key]); },
  };

  assert.equal(await createTallyInquiryForm(page, INQUIRY_FORM, async () => {}), true);

  assert.deepEqual(events[0], ["navigate", "https://tally.so/new"]);
  assert.deepEqual(events[1], ["evaluate"]);
  assert.deepEqual(events[2], ["clickAt", { x: 120, y: 240 }]);
  assert.deepEqual(events[3], ["insertText", "Life Manager inquiry"]);
  assert.deepEqual(
    events.slice(4).filter(([kind]) => kind === "insertText").map(([, value]) => value),
    ["/", "Short answer", "name", "/", "Email", "email", "/", "Long answer", "message"],
  );
  assert.equal(events.filter(([kind]) => kind === "pressKey").length, 6);
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
  assert.doesNotMatch(run.stderr, /agent@example|am-key-secret|postgres:\/\/|Bearer/);
});
