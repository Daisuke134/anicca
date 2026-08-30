"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  claimMoneyPrinterWorkPacket,
  buildMoneyPrinterIssue,
  createGhIssueClient,
  createIssueForPacket,
  reconcileIssueForPacket,
} = require("./money-printer-symphony-bridge.js");

const SECRET = "s".repeat(64);
const TENANT = "tenant-a";
const FOREIGN_TENANT = "tenant-b";
const OPPORTUNITY_ID = "a".repeat(64);
const FOREIGN_OPPORTUNITY_ID = "b".repeat(64);
const DISPATCH_ID = "d".repeat(64);
const JOB_ID = `goal:${OPPORTUNITY_ID}`;
const COOKIE = "__Host-lm_panel_session=session-secret";
const BASE = "https://life-call.example.test";
const ISSUE_URL = "https://github.com/Daisuke134/life-manager-workrooms/issues/42";
const ISSUE_REF = "github-issue://Daisuke134/life-manager-workrooms/42";

function packet(overrides = {}) {
  return Object.freeze({
    protocol: "LM_DISPATCH_V1",
    tenant_id: TENANT,
    dispatch_id: DISPATCH_ID,
    job_id: JOB_ID,
    round: 1,
    opportunity_ref: `opportunity://${encodeURIComponent(TENANT)}/${encodeURIComponent(OPPORTUNITY_ID)}`,
    job_ref: `runtime-job://${encodeURIComponent(TENANT)}/${encodeURIComponent(JOB_ID)}`,
    title: "A bounded opportunity",
    source_url: "https://example.test/opportunity",
    value_minor: "2500",
    currency: "USD",
    workroom_status: "WORKING",
    result_protocol: "LM_RESULT_V1",
    ...overrides,
  });
}

function response(status, body, headers = {}) {
  const values = new Map(Object.entries(headers).map(([key, value]) => [key.toLowerCase(), value]));
  return {
    status,
    ok: status >= 200 && status < 300,
    headers: {
      get(name) { return values.get(String(name).toLowerCase()) || null; },
      getSetCookie() {
        const value = values.get("set-cookie");
        return value == null ? [] : (Array.isArray(value) ? value : [value]);
      },
    },
    async json() { return body; },
  };
}

function dispatch(overrides = {}) {
  return {
    tenant_id: TENANT,
    dispatch_id: DISPATCH_ID,
    job_id: JOB_ID,
    round: 1,
    status: "claimed",
    private_payload: SECRET,
    ...overrides,
  };
}

function workroom(overrides = {}) {
  return {
    opportunity_id: OPPORTUNITY_ID,
    title: "A bounded opportunity",
    source_url: "https://example.test/opportunity",
    value_minor: "2500",
    currency: "USD",
    status: "WORKING",
    job_ref: `runtime-job://${encodeURIComponent(TENANT)}/${encodeURIComponent(JOB_ID)}`,
    activity: [{ kind: "private", secret: SECRET }],
    ...overrides,
  };
}

function fakeFetch(steps, calls = []) {
  return async (url, init = {}) => {
    calls.push({ url: String(url), init });
    const step = steps.shift();
    if (!step) throw new Error("unexpected fetch");
    return typeof step === "function" ? step(url, init) : step;
  };
}

function config(overrides = {}) {
  return { apiBaseUrl: BASE, secret: SECRET, tenantId: TENANT, ...overrides };
}

function issueRow(number, body = buildMoneyPrinterIssue(packet()).body, overrides = {}) {
  return {
    number,
    url: `https://github.com/Daisuke134/life-manager-workrooms/issues/${number}`,
    body,
    ...overrides,
  };
}

function mirroredIssue(issueRef = ISSUE_REF, overrides = {}) {
  return {
    tenant_id: TENANT,
    dispatch_id: DISPATCH_ID,
    job_id: JOB_ID,
    round: 1,
    status: "mirrored",
    issue_ref: issueRef,
    ...overrides,
  };
}

test("idle claim returns frozen idle state and makes no guest request", async () => {
  const calls = [];
  const result = await claimMoneyPrinterWorkPacket(config(), {
    fetchImpl: fakeFetch([response(200, { dispatch: null })], calls),
  });

  assert.deepEqual(result, { status: "idle" });
  assert.equal(Object.isFrozen(result), true);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, `${BASE}/api/internal/money-printer/symphony/claim`);
  assert.equal(calls[0].init.method, "POST");
  assert.deepEqual(JSON.parse(calls[0].init.body), { tenant_id: TENANT });
  assert.equal(calls[0].init.headers.authorization, `Bearer ${SECRET}`);
});

test("claimed dispatch produces one safe packet after exactly two guest/workroom GETs", async () => {
  const calls = [];
  const result = await claimMoneyPrinterWorkPacket(config(), {
    fetchImpl: fakeFetch([
      response(200, { dispatch: dispatch() }),
      response(200, "<private html>", { "set-cookie": COOKIE }),
      response(200, workroom()),
    ], calls),
  });

  const expected = {
    status: "claimed",
    packet: {
      protocol: "LM_DISPATCH_V1",
      tenant_id: TENANT,
      dispatch_id: DISPATCH_ID,
      job_id: JOB_ID,
      round: 1,
      opportunity_ref: `opportunity://${encodeURIComponent(TENANT)}/${encodeURIComponent(OPPORTUNITY_ID)}`,
      job_ref: `runtime-job://${encodeURIComponent(TENANT)}/${encodeURIComponent(JOB_ID)}`,
      title: "A bounded opportunity",
      source_url: "https://example.test/opportunity",
      value_minor: "2500",
      currency: "USD",
      workroom_status: "WORKING",
      result_protocol: "LM_RESULT_V1",
    },
  };
  assert.deepEqual(result, expected);
  assert.equal(Object.isFrozen(result), true);
  assert.equal(Object.isFrozen(result.packet), true);
  assert.equal(calls.length, 3);
  assert.equal(calls[1].url, `${BASE}/money-printer`);
  assert.equal(calls[1].init.method, "GET");
  assert.equal(calls[2].url, `${BASE}/api/panel/money-printer/workroom?opportunity_id=${OPPORTUNITY_ID}`);
  assert.equal(calls[2].init.method, "GET");
  assert.equal(calls[2].init.headers.Cookie, COOKIE);
  assert.doesNotMatch(JSON.stringify(result), /private|secret|session/);
});

test("foreign or malformed claimed dispatch stops before either guest GET", async () => {
  for (const invalidDispatch of [
    dispatch({ tenant_id: FOREIGN_TENANT }),
    dispatch({ dispatch_id: "not-a-dispatch" }),
    dispatch({ job_id: "goal:not-a-64-hex-id" }),
    dispatch({ round: 0 }),
    dispatch({ status: "mirrored" }),
  ]) {
    const calls = [];
    await assert.rejects(
      claimMoneyPrinterWorkPacket(config(), {
        fetchImpl: fakeFetch([response(200, { dispatch: invalidDispatch })], calls),
      }),
      /invalid|scope|dispatch/i,
    );
    assert.equal(calls.length, 1);
  }
});

test("missing guest cookie is a generic failure and prevents workroom access", async () => {
  const calls = [];
  await assert.rejects(
    claimMoneyPrinterWorkPacket(config(), {
      fetchImpl: fakeFetch([
        response(200, { dispatch: dispatch() }),
        response(200, "<private html>"),
      ], calls),
    }),
    /cookie|guest/i,
  );
  assert.equal(calls.length, 2);
});

test("foreign or mixed workroom is rejected after claim without returning its fields", async () => {
  for (const invalidWorkroom of [
    workroom({ opportunity_id: FOREIGN_OPPORTUNITY_ID }),
    workroom({ job_ref: `runtime-job://${encodeURIComponent(FOREIGN_TENANT)}/${encodeURIComponent(JOB_ID)}` }),
  ]) {
    const calls = [];
    await assert.rejects(
      claimMoneyPrinterWorkPacket(config(), {
        fetchImpl: fakeFetch([
          response(200, { dispatch: dispatch() }),
          response(200, "<private html>", { "set-cookie": COOKIE }),
          response(200, invalidWorkroom),
        ], calls),
      }),
      /workroom|scope|opportunity/i,
    );
    assert.equal(calls.length, 3);
  }
});

test("invalid config fails before network and exported function emits no stdout or stderr", async () => {
  const calls = [];
  let stdout = "";
  let stderr = "";
  const stdoutWrite = process.stdout.write;
  const stderrWrite = process.stderr.write;
  process.stdout.write = (chunk) => { stdout += String(chunk); return true; };
  process.stderr.write = (chunk) => { stderr += String(chunk); return true; };
  try {
    await assert.rejects(
      claimMoneyPrinterWorkPacket(config({ apiBaseUrl: "http://insecure.example.test" }), {
        fetchImpl: fakeFetch([], calls),
      }),
      /config|https/i,
    );
  } finally {
    process.stdout.write = stdoutWrite;
    process.stderr.write = stderrWrite;
  }
  assert.equal(calls.length, 0);
  assert.equal(stdout, "");
  assert.equal(stderr, "");
  assert.doesNotMatch(JSON.stringify({ result: null, stdout, stderr }), new RegExp(SECRET));
});

test("issue builder includes only the frozen public packet, full marker, and one-result instruction", () => {
  const issue = buildMoneyPrinterIssue(packet());

  assert.equal(Object.isFrozen(issue), true);
  assert.equal(Object.isFrozen(issue.labels), true);
  assert.equal(issue.labels.length, 1);
  assert.equal(issue.labels[0], "money-printer");
  assert.match(issue.title, new RegExp(DISPATCH_ID));
  assert.ok(issue.title.length <= 220);
  assert.match(issue.body, new RegExp(`^<!-- lm-dispatch:${DISPATCH_ID} -->$`, "m"));
  assert.deepEqual(issue.body.match(/<!-- lm-dispatch:[0-9a-f]{64} -->/g), [
    `<!-- lm-dispatch:${DISPATCH_ID} -->`,
  ]);
  assert.match(issue.body, /exactly one comment.*LM_RESULT_V1/i);

  const bodyFields = [...issue.body.matchAll(/^- ([a-z_]+): /gm)].map((match) => match[1]);
  assert.deepEqual(bodyFields, [
    "protocol", "tenant_id", "dispatch_id", "job_id", "round", "opportunity_ref",
    "job_ref", "title", "source_url", "value_minor", "currency", "workroom_status",
    "result_protocol",
  ]);
  assert.doesNotMatch(issue.body, /bearer|cookie|private|activity|pii|raw error|authorization|token|secret/i);
  assert.doesNotMatch(issue.body, new RegExp(SECRET));
});

test("create adapter uses the fixed repo and label, and result returns only the canonical internal issue ref", () => {
  const calls = [];
  const issueClient = createGhIssueClient({
    execFileSync(command, args, options) {
      calls.push({ command, args, options });
      return `${ISSUE_URL}\n`;
    },
  });
  const result = createIssueForPacket(packet(), { issueClient, tenantId: TENANT });

  assert.deepEqual(result, { status: "created", dispatch_id: DISPATCH_ID, issue_ref: ISSUE_REF });
  assert.equal(Object.isFrozen(result), true);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].command, "gh");
  assert.deepEqual(calls[0].args.slice(0, 4), ["issue", "create", "-R", "Daisuke134/life-manager-workrooms"]);
  assert.deepEqual(calls[0].args.slice(-2), ["--label", "money-printer"]);
  assert.equal(calls[0].options.encoding, "utf8");
  assert.deepEqual(calls[0].options.stdio, ["ignore", "pipe", "pipe"]);
  assert.equal(calls[0].args[calls[0].args.indexOf("--title") + 1], buildMoneyPrinterIssue(packet()).title);
  assert.equal(calls[0].args[calls[0].args.indexOf("--body") + 1], buildMoneyPrinterIssue(packet()).body);
  assert.doesNotMatch(result.issue_ref, /https?:/i);
});

test("malformed or foreign packet fails before the injected issue client is called", () => {
  const valid = packet();
  const invalidPackets = [
    { ...valid },
    Object.freeze({ ...valid, unexpected: "extra" }),
    Object.freeze({ ...valid, tenant_id: FOREIGN_TENANT }),
    Object.freeze({ ...valid, opportunity_ref: "opportunity://other/id" }),
    Object.freeze({ ...valid, protocol: "LM_DISPATCH_V0" }),
  ];
  let calls = 0;
  const issueClient = { create() { calls += 1; return ISSUE_URL; } };

  for (const invalidPacket of invalidPackets) {
    assert.throws(
      () => createIssueForPacket(invalidPacket, { issueClient }),
      /issue|packet|scope|invalid/i,
    );
  }
  assert.equal(calls, 0);
});

test("reserved hidden marker injection is rejected before issue creation", () => {
  const foreignMarker = `<!-- lm-dispatch:${"e".repeat(64)} -->`;
  const invalidPacket = packet({ title: `A bounded opportunity ${foreignMarker}` });
  let calls = 0;

  assert.throws(
    () => createIssueForPacket(invalidPacket, {
      tenantId: TENANT,
      issueClient: { create: () => { calls += 1; return ISSUE_URL; } },
    }),
    /issue|packet|marker|invalid/i,
  );
  assert.equal(calls, 0);
});

test("issue creation requires a matching configured tenant before calling the client", () => {
  const foreignTenantPacket = packet({
    tenant_id: FOREIGN_TENANT,
    opportunity_ref: `opportunity://${encodeURIComponent(FOREIGN_TENANT)}/${encodeURIComponent(OPPORTUNITY_ID)}`,
    job_ref: `runtime-job://${encodeURIComponent(FOREIGN_TENANT)}/${encodeURIComponent(JOB_ID)}`,
  });
  let calls = 0;
  const issueClient = { create: () => { calls += 1; return ISSUE_URL; } };

  for (const dependencies of [
    { issueClient },
    { issueClient, tenantId: "" },
    { issueClient, tenantId: "Tenant-A" },
    { issueClient, tenantId: FOREIGN_TENANT },
  ]) {
    assert.throws(
      () => createIssueForPacket(packet(), dependencies),
      /tenant|scope|invalid/i,
    );
  }
  assert.throws(
    () => createIssueForPacket(foreignTenantPacket, { issueClient, tenantId: TENANT }),
    /tenant|scope|invalid/i,
  );
  assert.equal(calls, 0);
});

test("foreign, noncanonical, and malformed issue URLs are rejected with a generic error", () => {
  for (const invalidUrl of [
    "https://github.com/other/repo/issues/42",
    "http://github.com/Daisuke134/life-manager-workrooms/issues/42",
    "https://github.com/Daisuke134/life-manager-workrooms/issues/0",
    "https://github.com/Daisuke134/life-manager-workrooms/issues/42?x=1",
    "github-issue://Daisuke134/life-manager-workrooms/42",
  ]) {
    assert.throws(
      () => createIssueForPacket(packet(), { tenantId: TENANT, issueClient: { create: () => invalidUrl } }),
      (error) => error instanceof Error && error.message === "issue create failed",
    );
  }
});

test("client failures never surface the raw error or secret", () => {
  assert.throws(
    () => createIssueForPacket(packet(), {
      tenantId: TENANT,
      issueClient: { create: () => { throw new Error(`gh failed ${SECRET}`); } },
    }),
    (error) => error instanceof Error && error.message === "issue create failed" && !error.message.includes(SECRET),
  );

  const issue = buildMoneyPrinterIssue(packet());
  const issueClient = createGhIssueClient({
    execFileSync() { throw new Error(`exec failed ${SECRET}`); },
  });
  assert.throws(
    () => issueClient.create(issue),
    (error) => error instanceof Error && error.message === "issue create failed" && !error.message.includes(SECRET),
  );
});

test("issue list adapter uses the fixed all-state bounded JSON query and returns safe rows", () => {
  const calls = [];
  const issueClient = createGhIssueClient({
    execFileSync(command, args, options) {
      calls.push({ command, args, options });
      return JSON.stringify([issueRow(42, "existing")]);
    },
  });

  assert.deepEqual(issueClient.list(), [issueRow(42, "existing")]);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].command, "gh");
  assert.deepEqual(calls[0].args, [
    "issue", "list", "-R", "Daisuke134/life-manager-workrooms",
    "--state", "all", "--limit", "100", "--json", "number,url,body",
  ]);
  assert.equal(calls[0].options.encoding, "utf8");
  assert.deepEqual(calls[0].options.stdio, ["ignore", "pipe", "pipe"]);
});

test("empty issue list creates once and posts the exact mirrored callback", async () => {
  const calls = [];
  let creates = 0;
  const issueClient = {
    list: () => [],
    create(issue) {
      creates += 1;
      assert.equal(issue.body, buildMoneyPrinterIssue(packet()).body);
      return ISSUE_URL;
    },
  };
  const result = await reconcileIssueForPacket(config(), packet(), {
    issueClient,
    fetchImpl: fakeFetch([response(200, mirroredIssue())], calls),
  });

  assert.deepEqual(result, {
    tenant_id: TENANT,
    dispatch_id: DISPATCH_ID,
    job_id: JOB_ID,
    round: 1,
    status: "mirrored",
    issue_ref: ISSUE_REF,
    created: true,
  });
  assert.equal(Object.isFrozen(result), true);
  assert.equal(creates, 1);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, `${BASE}/api/internal/money-printer/symphony/issue`);
  assert.equal(calls[0].init.method, "POST");
  assert.deepEqual(JSON.parse(calls[0].init.body), {
    tenant_id: TENANT,
    dispatch_id: DISPATCH_ID,
    issue_ref: ISSUE_REF,
  });
  assert.equal(calls[0].init.headers.authorization, `Bearer ${SECRET}`);
});

test("an existing exact marker reuses its canonical issue and never creates", async () => {
  const calls = [];
  let creates = 0;
  const existingRef = "github-issue://Daisuke134/life-manager-workrooms/77";
  const issueClient = {
    list: () => [issueRow(77)],
    create: () => { creates += 1; return ISSUE_URL; },
  };
  const result = await reconcileIssueForPacket(config(), packet(), {
    issueClient,
    fetchImpl: fakeFetch([response(200, mirroredIssue(existingRef))], calls),
  });

  assert.equal(result.issue_ref, existingRef);
  assert.equal(result.created, false);
  assert.equal(creates, 0);
  assert.deepEqual(JSON.parse(calls[0].init.body), {
    tenant_id: TENANT,
    dispatch_id: DISPATCH_ID,
    issue_ref: existingRef,
  });
});

test("a single marker in a corrupt body stops before reuse, creation, or callback", async () => {
  let creates = 0;
  let callbacks = 0;
  const corruptBody = [
    "unrelated body",
    `<!-- lm-dispatch:${DISPATCH_ID} -->`,
    "corrupt payload",
  ].join("\n");
  const issueClient = {
    list: () => [issueRow(42, corruptBody)],
    create: () => { creates += 1; return ISSUE_URL; },
  };
  await assert.rejects(
    reconcileIssueForPacket(config(), packet(), {
      issueClient,
      fetchImpl: async () => { callbacks += 1; return response(200, mirroredIssue()); },
    }),
    /conflict/i,
  );
  assert.equal(creates, 0);
  assert.equal(callbacks, 0);
});

test("an exact callback replay remains safe and creates zero issues", async () => {
  const calls = [];
  let creates = 0;
  const issueClient = {
    list: () => [issueRow(42)],
    create: () => { creates += 1; return ISSUE_URL; },
  };
  const fetchImpl = fakeFetch([
    response(200, mirroredIssue()),
    response(200, mirroredIssue()),
  ], calls);

  const first = await reconcileIssueForPacket(config(), packet(), { issueClient, fetchImpl });
  const second = await reconcileIssueForPacket(config(), packet(), { issueClient, fetchImpl });
  assert.equal(first.created, false);
  assert.equal(second.created, false);
  assert.equal(creates, 0);
  assert.equal(calls.length, 2);
});

test("duplicate exact markers stop before callback or creation", async () => {
  let creates = 0;
  let callbacks = 0;
  const issueClient = {
    list: () => [issueRow(41), issueRow(42)],
    create: () => { creates += 1; return ISSUE_URL; },
  };
  await assert.rejects(
    reconcileIssueForPacket(config(), packet(), {
      issueClient,
      fetchImpl: async () => { callbacks += 1; return response(200, mirroredIssue()); },
    }),
    /conflict|duplicate/i,
  );
  assert.equal(creates, 0);
  assert.equal(callbacks, 0);
});

test("a full list without the marker is unknown and stops without creation", async () => {
  let creates = 0;
  let callbacks = 0;
  const rows = Array.from({ length: 100 }, (_, index) => issueRow(index + 1, "unrelated"));
  const issueClient = {
    list: () => rows,
    create: () => { creates += 1; return ISSUE_URL; },
  };
  await assert.rejects(
    reconcileIssueForPacket(config(), packet(), {
      issueClient,
      fetchImpl: async () => { callbacks += 1; return response(200, mirroredIssue()); },
    }),
    /uncertain|unknown/i,
  );
  assert.equal(creates, 0);
  assert.equal(callbacks, 0);
});

test("malformed or foreign list rows stop all downstream effects", async () => {
  for (const invalidRow of [
    { ...issueRow(42), extra: SECRET },
    issueRow(42, "body", { url: "https://github.com/other/repo/issues/42" }),
    issueRow(0, "body"),
  ]) {
    let creates = 0;
    let callbacks = 0;
    const issueClient = {
      list: () => [invalidRow],
      create: () => { creates += 1; return ISSUE_URL; },
    };
    await assert.rejects(
      reconcileIssueForPacket(config(), packet(), {
        issueClient,
        fetchImpl: async () => { callbacks += 1; return response(200, mirroredIssue()); },
      }),
      /issue list failed|invalid/i,
    );
    assert.equal(creates, 0);
    assert.equal(callbacks, 0);
  }
});

test("list transport and JSON failures stay generic with zero effects", async () => {
  const failureClients = [
    { list: () => { throw new Error(`gh output ${SECRET}`); }, create: () => { throw new Error("must not create"); } },
    createGhIssueClient({ execFileSync: () => "not-json" }),
  ];
  for (const issueClient of failureClients) {
    let callbacks = 0;
    await assert.rejects(
      reconcileIssueForPacket(config(), packet(), {
        issueClient,
        fetchImpl: async () => { callbacks += 1; return response(200, mirroredIssue()); },
      }),
      (error) => error instanceof Error && error.message === "issue list failed" && !error.message.includes(SECRET),
    );
    assert.equal(callbacks, 0);
  }
});

test("successful create followed by callback failure is recovered by marker reuse", async () => {
  const calls = [];
  const rows = [];
  let creates = 0;
  const issueClient = {
    list: () => rows,
    create(issue) {
      creates += 1;
      rows.push(issueRow(42, issue.body));
      return ISSUE_URL;
    },
  };
  await assert.rejects(
    reconcileIssueForPacket(config(), packet(), {
      issueClient,
      fetchImpl: fakeFetch([response(503, { error: SECRET })], calls),
    }),
    /bridge request failed/,
  );
  const result = await reconcileIssueForPacket(config(), packet(), {
    issueClient,
    fetchImpl: fakeFetch([response(200, mirroredIssue())], calls),
  });
  assert.equal(result.created, false);
  assert.equal(creates, 1);
  assert.equal(calls.length, 2);
});

test("foreign or stale callback readback is rejected without leaking private data", async () => {
  for (const invalidReadback of [
    mirroredIssue(ISSUE_REF, { tenant_id: FOREIGN_TENANT }),
    mirroredIssue(ISSUE_REF, { dispatch_id: "e".repeat(64) }),
    mirroredIssue(ISSUE_REF, { job_id: `goal:${FOREIGN_OPPORTUNITY_ID}` }),
    mirroredIssue(ISSUE_REF, { round: 2 }),
    mirroredIssue(ISSUE_REF, { status: "result_ready" }),
    mirroredIssue("github-issue://Daisuke134/life-manager-workrooms/43"),
    { ...mirroredIssue(), private_payload: SECRET },
  ]) {
    let creates = 0;
    const issueClient = {
      list: () => [issueRow(42)],
      create: () => { creates += 1; return ISSUE_URL; },
    };
    await assert.rejects(
      reconcileIssueForPacket(config(), packet(), {
        issueClient,
        fetchImpl: fakeFetch([response(200, invalidReadback)]),
      }),
      (error) => error instanceof Error
        && error.message === "issue readback invalid"
        && !error.message.includes(SECRET),
    );
    assert.equal(creates, 0);
  }
});
