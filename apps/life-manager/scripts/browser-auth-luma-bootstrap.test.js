"use strict";

const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");

const {
  requestLumaEmailLogin,
  resolveBootstrapEnv,
  runLumaBootstrap,
} = require("./browser-auth-luma-bootstrap.js");

const ENV = {
  BROWSER_AUTH_TENANT_A_UID: "tenant-a",
  LM_AGENT_BROWSER_EMAIL: "agent@example.test",
  LM_AGENTMAIL_INBOX_ID: "browser-agent@example.test",
};

function fixture(overrides = {}) {
  const calls = [];
  const browser = {
    sessionId: "steel-session-1",
    async requestMagicLink(email) {
      calls.push(["requestMagicLink", email]);
    },
    async openMagicLink(link) {
      calls.push(["openMagicLink", link]);
    },
    async inspectAuthenticated() {
      calls.push(["inspectAuthenticated"]);
      return overrides.authenticated || {
        confirmed: true,
        origin: "https://luma.com",
        currentUrl: "https://luma.com/home",
        marker: "create_event",
      };
    },
    async exportContext() {
      calls.push(["exportContext"]);
      return {
        cookies: [
          { name: "session", value: "private-cookie", domain: ".luma.com", path: "/" },
        ],
      };
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
    async readMagicLink(input) {
      calls.push(["readMagicLink", input]);
      return overrides.magicLink === undefined
        ? "https://luma.com/auth/magic-link-token"
        : overrides.magicLink;
    },
    async saveContext(input) {
      calls.push(["saveContext", input]);
      return { context_sha256: "a".repeat(64), key_version: 1 };
    },
  };
  return { calls, deps };
}

test("runtime image allowlists the Luma bootstrap entrypoint", () => {
  const dockerignore = readFileSync(path.join(__dirname, "..", ".dockerignore"), "utf8");
  assert.match(dockerignore, /^!scripts\/browser-auth-luma-bootstrap\.js$/m);
});

test("cloud magic-link login saves only a confirmed Luma context and returns safe metadata", async () => {
  const { calls, deps } = fixture();

  const result = await runLumaBootstrap({ env: ENV, deps });

  assert.deepEqual(result, {
    origin: "https://luma.com",
    current_url: "https://luma.com/home",
    authenticated: true,
    marker: "create_event",
    session_id: "steel-session-1",
    context_sha256: "a".repeat(64),
    key_version: 1,
    released: true,
  });
  assert.deepEqual(calls[0], ["openBrowser"]);
  assert.deepEqual(calls[1], ["requestMagicLink", ENV.LM_AGENTMAIL_INBOX_ID]);
  assert.deepEqual(calls[2], ["readMagicLink", { afterMs: 1_800_000_000_000 }]);
  assert.deepEqual(calls[3], ["openMagicLink", "https://luma.com/auth/magic-link-token"]);
  assert.deepEqual(calls[4], ["inspectAuthenticated"]);
  assert.deepEqual(calls[5], ["exportContext"]);
  assert.deepEqual(calls[6], ["saveContext", {
    uid: ENV.BROWSER_AUTH_TENANT_A_UID,
    origin: "https://luma.com",
    principalKind: "agent_owned",
    context: {
      cookies: [
        { name: "session", value: "private-cookie", domain: ".luma.com", path: "/" },
      ],
    },
  }]);
  assert.deepEqual(calls.at(-1), ["release"]);
  assert.doesNotMatch(
    JSON.stringify(result),
    /agent@example|browser-agent@example|magic-link-token|private-cookie/,
  );
});

test("unsafe link or missing authenticated marker fails closed without saving and still releases", async () => {
  for (const overrides of [
    { magicLink: "https://attacker.example/auth/token" },
    {
      authenticated: {
        confirmed: false,
        origin: "https://luma.com",
        currentUrl: "https://luma.com/signin",
        marker: null,
      },
    },
  ]) {
    const { calls, deps } = fixture(overrides);

    await assert.rejects(
      runLumaBootstrap({ env: ENV, deps }),
      /Luma authentication unavailable/,
    );

    assert.equal(calls.some(([name]) => name === "saveContext"), false);
    assert.deepEqual(calls.at(-1), ["release"]);
  }
});

test("missing runtime identity fails before opening Steel", async () => {
  const { calls, deps } = fixture();

  await assert.rejects(
    runLumaBootstrap({
      env: {
        BROWSER_AUTH_TENANT_A_UID: "",
        LM_AGENT_BROWSER_EMAIL: "",
        LM_AGENTMAIL_INBOX_ID: "",
      },
      deps,
    }),
    /Luma bootstrap configuration unavailable/,
  );

  assert.deepEqual(calls, []);
});

test("production CLI resolves exactly one existing agent-owned Luma tenant without exposing it", async () => {
  const queries = [];
  const resolved = await resolveBootstrapEnv({
    env: { LM_AGENT_BROWSER_EMAIL: ENV.LM_AGENT_BROWSER_EMAIL },
    query: async (sql, params) => {
      queries.push([sql, params]);
      return { rows: [{ uid: "tenant-from-db" }] };
    },
  });

  assert.equal(resolved.BROWSER_AUTH_TENANT_A_UID, "tenant-from-db");
  assert.equal(queries.length, 1);
  assert.match(queries[0][0], /origin = \$1/);
  assert.match(queries[0][0], /principal_kind = 'agent_owned'/);
  assert.deepEqual(queries[0][1], ["https://luma.com"]);

  for (const rows of [[], [{ uid: "a" }, { uid: "b" }]]) {
    await assert.rejects(
      resolveBootstrapEnv({
        env: { LM_AGENT_BROWSER_EMAIL: ENV.LM_AGENT_BROWSER_EMAIL },
        query: async () => ({ rows }),
      }),
      /Luma bootstrap configuration unavailable/,
    );
  }
});

test("Luma login request deterministically fills and submits the measured email form", async () => {
  const calls = [];
  const page = {
    async evaluate(expression) {
      calls.push(["evaluate", expression]);
      return true;
    },
  };

  assert.equal(await requestLumaEmailLogin(page, ENV.LM_AGENTMAIL_INBOX_ID), true);
  assert.equal(calls.length, 1);
  assert.equal(calls[0][0], "evaluate");
  assert.match(calls[0][1], /input\[type="email"\]/);
  assert.match(calls[0][1], /button\[type="submit"\]/);
  assert.match(calls[0][1], /dispatchEvent/);
  assert.match(calls[0][1], /browser-agent@example\.test/);
});
