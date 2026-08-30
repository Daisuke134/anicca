"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  claimMoneyPrinterWorkPacket,
  buildMoneyPrinterIssue,
  createGhIssueClient,
  createIssueForPacket,
  reconcileIssueForPacket,
  formatResultComment,
  parseResultComments,
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

function resultPayload(status = "completed", overrides = {}) {
  const base = {
    protocol: "LM_RESULT_V1",
    tenant_id: TENANT,
    dispatch_id: DISPATCH_ID,
    job_id: JOB_ID,
    status,
    execution_id: "codex-round-1",
    artifact_refs: ["artifact://tenant-a/result-1"],
  };
  if (status === "needs_human") {
    Object.assign(base, {
      reason_code: "provider_interview",
      question: "Complete the provider interview.",
      required_format: { type: "confirmation", values: ["approve", "request_changes"] },
    });
  }
  return { ...base, ...overrides };
}

function resultBody(payload = resultPayload()) {
  return formatResultComment(payload);
}

function rawResultBody(payload) {
  return `LM_RESULT_V1\n${JSON.stringify(payload)}`;
}

function commentRow(id, body = resultBody(), author = "Daisuke134", issueNumber = 42) {
  return {
    id,
    author,
    body,
    url: `https://github.com/Daisuke134/life-manager-workrooms/issues/${issueNumber}#issuecomment-${id}`,
  };
}

function rawCommentRow(id, body = resultBody(), author = "Daisuke134", issueNumber = 42, overrides = {}) {
  return {
    id,
    user: { login: author, id: 9001, node_id: "user-node" },
    body,
    html_url: `https://github.com/Daisuke134/life-manager-workrooms/issues/${issueNumber}#issuecomment-${id}`,
    created_at: "2026-08-31T00:00:00Z",
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

test("comments adapter uses the fixed issue endpoint, pagination, projection, and safe flattened rows", () => {
  const calls = [];
  const issueClient = createGhIssueClient({
    execFileSync(command, args, options) {
      calls.push({ command, args, options });
      return JSON.stringify([[rawCommentRow(7)], [rawCommentRow(8, "status update", "octocat")]]);
    },
  });

  assert.deepEqual(issueClient.comments(ISSUE_REF), [
    commentRow(7),
    commentRow(8, "", ""),
  ]);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].command, "gh");
  assert.deepEqual(calls[0].args, [
    "api",
    "repos/Daisuke134/life-manager-workrooms/issues/42/comments?per_page=100",
    "--paginate",
    "--slurp",
  ]);
  assert.equal(calls[0].args.includes("-R"), false);
  assert.equal(calls[0].args.includes("--repo"), false);
  assert.equal(calls[0].args.includes("--jq"), false);
  assert.equal(calls[0].args.includes("--template"), false);
  assert.equal(calls[0].options.encoding, "utf8");
  assert.deepEqual(calls[0].options.stdio, ["ignore", "pipe", "pipe"]);
  assert.equal(Object.isFrozen(issueClient.comments(ISSUE_REF)), true);
});

test("comments adapter rejects foreign issue refs, malformed rows, oversized output, and transport errors generically", () => {
  const invalidRefs = [
    "github-issue://other/repo/42",
    "https://github.com/Daisuke134/life-manager-workrooms/issues/42",
    "github-issue://Daisuke134/life-manager-workrooms/0",
  ];
  for (const invalidRef of invalidRefs) {
    let calls = 0;
    const issueClient = createGhIssueClient({ execFileSync() { calls += 1; return "[]"; } });
    assert.throws(() => issueClient.comments(invalidRef), (error) => error.message === "issue comments failed");
    assert.equal(calls, 0);
  }

  for (const output of [
    JSON.stringify([[rawCommentRow(7, "body", "octocat", 43)]]),
    JSON.stringify([Array.from({ length: 501 }, (_, index) => rawCommentRow(index + 1, "body", "octocat"))]),
    JSON.stringify([[rawCommentRow(7, "body", "octocat", 42, { id: 0 })]]),
    JSON.stringify([[rawCommentRow(7, "body", "octocat", 42, { html_url: "https://github.com/other/repo/issues/42#issuecomment-7" })]]),
    JSON.stringify([[rawCommentRow(7, "body", "octocat", 42, { body: null })]]),
    JSON.stringify([[rawCommentRow(7, "body", "x".repeat(101))]]),
    JSON.stringify({ error: SECRET }),
    "not-json",
  ]) {
    const issueClient = createGhIssueClient({ execFileSync() { return output; } });
    assert.throws(() => issueClient.comments(ISSUE_REF), (error) => (
      error.message === "issue comments failed" && !error.message.includes(SECRET)
    ));
  }
  const issueClient = createGhIssueClient({ execFileSync() { throw new Error(`gh ${SECRET}`); } });
  assert.throws(() => issueClient.comments(ISSUE_REF), (error) => (
    error.message === "issue comments failed" && !error.message.includes(SECRET)
  ));
});

test("bot, weird, and deleted users are ignored without retaining oversized or control bodies", () => {
  const rows = [
    rawCommentRow(9, `${"x".repeat(32 * 1024 + 1)}\u0000`, "github-actions[bot]"),
    rawCommentRow(10, "looks strange\u0000", "not a login"),
    rawCommentRow(11, "deleted body", "octocat", 42, { user: null }),
    rawCommentRow(12, "missing user body", "octocat", 42, { user: { id: 1 } }),
  ];
  const issueClient = createGhIssueClient({
    execFileSync() { return JSON.stringify([rows]); },
  });

  assert.deepEqual(issueClient.comments(ISSUE_REF), [
    commentRow(9, "", ""),
    commentRow(10, "", ""),
    commentRow(11, "", ""),
    commentRow(12, "", ""),
  ]);
});

test("completed result comment is strictly scoped, canonical, hashed, and deeply frozen", () => {
  const result = parseResultComments(packet(), ISSUE_REF, [commentRow(101)]);

  assert.equal(result.status, "ready");
  assert.equal(result.result_ref, "github-comment://Daisuke134/life-manager-workrooms/42/101");
  assert.match(result.result_hash, /^[0-9a-f]{64}$/);
  assert.deepEqual(result.payload, resultPayload());
  assert.equal(Object.isFrozen(result), true);
  assert.equal(Object.isFrozen(result.payload), true);
  assert.equal(Object.isFrozen(result.payload.artifact_refs), true);
  assert.doesNotMatch(JSON.stringify(result), /private|secret|session|author|body/i);
});

test("canonical result payload stays below the database byte limit", () => {
  const largePayload = resultPayload("completed", {
    artifact_refs: Array.from({ length: 20 }, (_, index) => (
      `artifact://tenant-a/${index}-${"x".repeat(950)}`
    )),
  });
  assert.ok(largePayload.artifact_refs.every((ref) => ref.length <= 1000));
  assert.ok(JSON.stringify(largePayload).length > 12 * 1024);
  assert.throws(
    () => formatResultComment(largePayload),
    (error) => error.message === "result comment invalid",
  );
  assert.throws(
    () => parseResultComments(packet(), ISSUE_REF, [commentRow(111, rawResultBody(largePayload))]),
    (error) => error.message === "result comment conflict",
  );
});

test("needs_human result preserves nested data but hashes key-order variants identically", () => {
  const firstPayload = resultPayload("needs_human", {
    required_format: { z: ["last", { b: true, a: "first" }], a: "first-key" },
  });
  const secondPayload = {
    required_format: { a: "first-key", z: ["last", { a: "first", b: true }] },
    artifact_refs: firstPayload.artifact_refs,
    execution_id: firstPayload.execution_id,
    status: firstPayload.status,
    question: firstPayload.question,
    reason_code: firstPayload.reason_code,
    job_id: firstPayload.job_id,
    dispatch_id: firstPayload.dispatch_id,
    tenant_id: firstPayload.tenant_id,
    protocol: firstPayload.protocol,
  };
  const first = parseResultComments(packet(), ISSUE_REF, [commentRow(102, resultBody(firstPayload))]);
  const second = parseResultComments(packet(), ISSUE_REF, [commentRow(103, resultBody(secondPayload))]);

  assert.equal(first.status, "ready");
  assert.equal(second.status, "ready");
  assert.equal(first.result_hash, second.result_hash);
  assert.deepEqual(first.payload, second.payload);
  assert.equal(Object.isFrozen(first.payload.required_format), true);
  assert.equal(Object.isFrozen(first.payload.required_format.z), true);
  assert.equal(Object.isFrozen(first.payload.required_format.z[1]), true);
});

test("wrong authors and non-result comments are ignored, leaving a frozen pending result", () => {
  const comments = [
    commentRow(104, resultBody(resultPayload("completed", { dispatch_id: "e".repeat(64) })), "octocat"),
    commentRow(105, "ordinary progress update", "Daisuke134"),
  ];
  const result = parseResultComments(packet(), ISSUE_REF, comments);

  assert.deepEqual(result, { status: "pending" });
  assert.equal(Object.isFrozen(result), true);
});

test("wrong-author oversized/control bodies are discarded, while expected-author bodies remain bounded", () => {
  const pending = parseResultComments(packet(), ISSUE_REF, [
    commentRow(112, `${"x".repeat(32 * 1024 + 1)}\u0000`, "github-actions[bot]"),
  ]);
  assert.deepEqual(pending, { status: "pending" });
  assert.equal(Object.isFrozen(pending), true);
  assert.throws(
    () => parseResultComments(packet(), ISSUE_REF, [
      commentRow(113, `${"x".repeat(32 * 1024 + 1)}\u0000`, "Daisuke134"),
    ]),
    (error) => error.message === "issue comments failed",
  );
});

test("zero comments is pending and duplicate valid results are a conflict", () => {
  assert.deepEqual(parseResultComments(packet(), ISSUE_REF, []), { status: "pending" });
  assert.throws(
    () => parseResultComments(packet(), ISSUE_REF, [commentRow(106), commentRow(107)]),
    (error) => error.message === "result comment conflict",
  );
});

test("expected-author malformed, foreign, extra, and trailing result payloads fail before readiness", () => {
  const invalidBodies = [
    "LM_RESULT_V1",
    "LM_RESULT_V1x\n{}",
    "LM_RESULT_V1\nnot-json",
    `${resultBody(resultPayload())}\n`,
    rawResultBody(resultPayload("completed", { dispatch_id: "e".repeat(64) })),
    rawResultBody(resultPayload("completed", { unexpected: "extra" })),
    rawResultBody(resultPayload("completed", { artifact_refs: ["not-a-uri"] })),
    rawResultBody(resultPayload("needs_human", { required_format: "x".repeat(4097) })),
  ];
  for (const body of invalidBodies) {
    assert.throws(
      () => parseResultComments(packet(), ISSUE_REF, [commentRow(108, body)]),
      (error) => error.message === "result comment conflict" && !error.message.includes(SECRET),
    );
  }
  assert.throws(
    () => parseResultComments(packet(), ISSUE_REF, [commentRow(109, resultBody(resultPayload()), "Daisuke134", 43)]),
    (error) => error.message === "issue comments failed",
  );
});

test("formatter emits the exact anchored result wire format and rejects non-JSON required formats", () => {
  const body = formatResultComment(resultPayload("needs_human"));
  assert.match(body, /^LM_RESULT_V1\n\{/);
  assert.equal(body.endsWith("\n"), false);
  assert.equal(body, resultBody(resultPayload("needs_human")));
  assert.throws(
    () => formatResultComment(resultPayload("needs_human", { required_format: null })),
    /result comment invalid/,
  );
  assert.throws(
    () => formatResultComment(resultPayload("needs_human", { required_format: Object.create(null) })),
    /result comment invalid/,
  );
});
