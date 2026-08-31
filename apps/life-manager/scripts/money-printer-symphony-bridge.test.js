"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  claimMoneyPrinterWorkPacket,
  buildMoneyPrinterIssue,
  createGhIssueClient,
  createIssueForPacket,
  reconcileIssueForPacket,
  reconcileResultForIssue,
  formatResultComment,
  parseResultComments,
  main,
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
    answered_human_boundaries: [],
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
    answered_human_boundaries: [],
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
  assert.deepEqual(JSON.parse(calls[0].init.body), {});
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
      answered_human_boundaries: [],
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

test("round2 claim freezes answered boundary references into the private issue packet", async () => {
  const answered = {
    reason_code: "provider/interview",
    answer_ref: `vault-answer://${TENANT}/approve`,
    human_boundary_ref: `human-boundary://sha256/${"a".repeat(64)}`,
  };
  const result = await claimMoneyPrinterWorkPacket(config(), {
    fetchImpl: fakeFetch([
      response(200, { dispatch: dispatch({ round: 2, answered_human_boundaries: [answered] }) }),
      response(200, "<private html>", { "set-cookie": COOKIE }),
      response(200, workroom()),
    ]),
  });

  assert.deepEqual(result.packet.answered_human_boundaries, [answered]);
  assert.equal(Object.isFrozen(result.packet), true);
  assert.equal(Object.isFrozen(result.packet.answered_human_boundaries), true);
  assert.equal(Object.isFrozen(result.packet.answered_human_boundaries[0]), true);
  const issue = buildMoneyPrinterIssue(result.packet);
  assert.match(issue.body, /answered_human_boundaries/);
  assert.match(issue.body, /vault-answer:\/\/tenant-a\/approve/);
  assert.doesNotMatch(issue.body, /private_answer|secret|raw answer/i);

  for (const invalidBoundary of [
    { ...answered, answer_ref: `vault-answer://${FOREIGN_TENANT}/approve` },
    { ...answered, human_boundary_ref: "human-boundary://sha256/not-a-sha" },
    { ...answered, private_answer: "must not leak" },
  ]) {
    await assert.rejects(
      claimMoneyPrinterWorkPacket(config(), {
        fetchImpl: fakeFetch([response(200, {
          dispatch: dispatch({ round: 2, answered_human_boundaries: [invalidBoundary] }),
        })]),
      }),
      /dispatch|boundary|scope|invalid/i,
    );
  }
});

test("claim rejects non-empty round1 and empty round2 boundaries before guest access", async () => {
  const answered = {
    reason_code: "provider/interview",
    answer_ref: `vault-answer://${TENANT}/approve`,
    human_boundary_ref: `human-boundary://sha256/${"a".repeat(64)}`,
  };
  for (const [round, boundaries] of [[1, [answered]], [2, []]]) {
    const calls = [];
    await assert.rejects(
      claimMoneyPrinterWorkPacket(config(), {
        fetchImpl: fakeFetch([response(200, {
          dispatch: dispatch({ round, answered_human_boundaries: boundaries }),
        })], calls),
      }),
      /boundary|dispatch|scope|invalid/i,
    );
    assert.equal(calls.length, 1);
  }
});

test("durable recovery claims preserve only status and issue ref while rebuilding the safe packet", async () => {
  for (const status of ["mirrored", "result_ready", "consumed"]) {
    const calls = [];
    const result = await claimMoneyPrinterWorkPacket(config(), {
      fetchImpl: fakeFetch([
        response(200, { dispatch: {
          tenant_id: TENANT,
          dispatch_id: DISPATCH_ID,
          job_id: JOB_ID,
          round: 1,
          status,
          answered_human_boundaries: [],
          issue_ref: ISSUE_REF,
        } }),
        response(200, "<private html>", { "set-cookie": COOKIE }),
        response(200, workroom()),
      ], calls),
    });
    assert.equal(result.status, status);
    assert.equal(result.issue_ref, ISSUE_REF);
    assert.equal(Object.isFrozen(result), true);
    assert.equal(Object.isFrozen(result.packet), true);
    assert.equal(result.packet.dispatch_id, DISPATCH_ID);
    assert.equal(calls.length, 3);
  }
});

test("claim parser rejects wrong-status, extra, and missing recovery fields before guest access", async () => {
  for (const dispatchRow of [
    { tenant_id: TENANT, dispatch_id: DISPATCH_ID, job_id: JOB_ID, round: 1, status: "failed" },
    { tenant_id: TENANT, dispatch_id: DISPATCH_ID, job_id: JOB_ID, round: 1, status: "mirrored", issue_ref: ISSUE_REF, extra: SECRET },
    { tenant_id: TENANT, dispatch_id: DISPATCH_ID, job_id: JOB_ID, round: 1, status: "consumed" },
  ]) {
    const calls = [];
    await assert.rejects(
      claimMoneyPrinterWorkPacket(config(), {
        fetchImpl: fakeFetch([response(200, { dispatch: dispatchRow })], calls),
      }),
      /dispatch|scope|invalid/i,
    );
    assert.equal(calls.length, 1);
  }
});

test("malformed claimed dispatch stops before either guest GET", async () => {
  for (const invalidDispatch of [
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
    "result_protocol", "answered_human_boundaries",
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

function consumedResult(parsed, overrides = {}) {
  return {
    tenant_id: TENANT,
    dispatch_id: DISPATCH_ID,
    job_id: JOB_ID,
    status: "consumed",
    result_ref: parsed.result_ref,
    result_hash: parsed.result_hash,
    ...overrides,
  };
}

function closedAck(parsed, issueRef = ISSUE_REF, overrides = {}) {
  return {
    tenant_id: TENANT,
    dispatch_id: DISPATCH_ID,
    job_id: JOB_ID,
    status: "closed",
    issue_ref: issueRef,
    result_ref: parsed.result_ref,
    result_hash: parsed.result_hash,
    ...overrides,
  };
}

function stateReadback(state = "OPEN", number = 42, url = ISSUE_URL, overrides = {}) {
  return { number, url, state, ...overrides };
}

test("state and close adapters use exact fixed gh argv and safe readback", () => {
  const calls = [];
  const issueClient = createGhIssueClient({
    execFileSync(command, args, options) {
      calls.push({ command, args, options });
      if (args[0] === "issue" && args[1] === "view") return JSON.stringify(stateReadback());
      return `closed ${SECRET}`;
    },
  });

  assert.deepEqual(issueClient.state(ISSUE_REF), stateReadback());
  assert.equal(issueClient.close(ISSUE_REF), undefined);
  assert.deepEqual(calls.map(({ command, args }) => ({ command, args })), [
    {
      command: "gh",
      args: ["issue", "view", "42", "-R", "Daisuke134/life-manager-workrooms", "--json", "number,url,state"],
    },
    {
      command: "gh",
      args: ["issue", "close", "42", "-R", "Daisuke134/life-manager-workrooms", "--reason", "completed"],
    },
  ]);
  assert.deepEqual(calls[0].options.stdio, ["ignore", "pipe", "pipe"]);
  assert.deepEqual(calls[1].options.stdio, ["ignore", "pipe", "pipe"]);
});

test("state and close adapters reject malformed refs/readbacks and hide raw failures", () => {
  for (const invalidRef of [
    "github-issue://other/repo/42",
    "https://github.com/Daisuke134/life-manager-workrooms/issues/42",
    "github-issue://Daisuke134/life-manager-workrooms/0",
  ]) {
    let calls = 0;
    const issueClient = createGhIssueClient({ execFileSync() { calls += 1; return "{}"; } });
    assert.throws(() => issueClient.state(invalidRef), (error) => error.message === "issue state failed");
    assert.throws(() => issueClient.close(invalidRef), (error) => error.message === "issue close failed");
    assert.equal(calls, 0);
  }

  for (const output of [
    JSON.stringify({ ...stateReadback(), extra: SECRET }),
    JSON.stringify(stateReadback("MERGED")),
    JSON.stringify(stateReadback("OPEN", 43)),
    JSON.stringify(stateReadback("OPEN", 42, "https://github.com/other/repo/issues/42")),
    "not-json",
  ]) {
    const issueClient = createGhIssueClient({ execFileSync() { return output; } });
    assert.throws(() => issueClient.state(ISSUE_REF), (error) => (
      ["issue state failed", "issue state invalid"].includes(error.message)
        && !error.message.includes(SECRET)
    ));
  }

  const issueClient = createGhIssueClient({
    execFileSync() { throw new Error(`gh close failed ${SECRET}`); },
  });
  assert.throws(() => issueClient.close(ISSUE_REF), (error) => (
    error.message === "issue close failed" && !error.message.includes(SECRET)
  ));
});

test("pending result leaves callback, state, and close untouched", async () => {
  let commentsCalls = 0;
  let stateCalls = 0;
  let closeCalls = 0;
  let fetchCalls = 0;
  const result = await reconcileResultForIssue(config(), packet(), ISSUE_REF, {
    issueClient: {
      comments() { commentsCalls += 1; return []; },
      state() { stateCalls += 1; return stateReadback(); },
      close() { closeCalls += 1; },
    },
    fetchImpl: async () => { fetchCalls += 1; return response(500, { error: SECRET }); },
  });

  assert.deepEqual(result, { status: "pending" });
  assert.equal(Object.isFrozen(result), true);
  assert.deepEqual({ commentsCalls, stateCalls, closeCalls, fetchCalls }, {
    commentsCalls: 1, stateCalls: 0, closeCalls: 0, fetchCalls: 0,
  });
});

test("completed callback requires exact readback before closing an open issue", async () => {
  const parsed = parseResultComments(packet(), ISSUE_REF, [commentRow(201)]);
  const calls = [];
  let stateCalls = 0;
  let closeCalls = 0;
  const issueClient = {
    comments(ref) { assert.equal(ref, ISSUE_REF); return [commentRow(201)]; },
    state(ref) {
      assert.equal(ref, ISSUE_REF);
      stateCalls += 1;
      return stateReadback(stateCalls === 1 ? "OPEN" : "CLOSED");
    },
    close(ref) { assert.equal(ref, ISSUE_REF); closeCalls += 1; },
  };
  const result = await reconcileResultForIssue(config(), packet(), ISSUE_REF, {
    issueClient,
    fetchImpl: fakeFetch([
      response(200, consumedResult(parsed)),
      response(200, closedAck(parsed)),
    ], calls),
  });

  assert.deepEqual(result, {
    status: "closed",
    tenant_id: TENANT,
    dispatch_id: DISPATCH_ID,
    job_id: JOB_ID,
    result_ref: parsed.result_ref,
    result_hash: parsed.result_hash,
  });
  assert.equal(Object.isFrozen(result), true);
  assert.equal(stateCalls, 2);
  assert.equal(closeCalls, 1);
  assert.equal(calls.length, 2);
  assert.equal(calls[0].url, `${BASE}/api/internal/money-printer/symphony/result`);
  assert.equal(calls[0].init.method, "POST");
  assert.equal(calls[0].init.headers.authorization, `Bearer ${SECRET}`);
  assert.deepEqual(JSON.parse(calls[0].init.body), {
    tenant_id: TENANT,
    dispatch_id: DISPATCH_ID,
    repo: "Daisuke134/life-manager-workrooms",
    author: "Daisuke134",
    result_ref: parsed.result_ref,
    result_hash: parsed.result_hash,
    payload: resultPayload(),
  });
  assert.equal(calls[1].url, `${BASE}/api/internal/money-printer/symphony/close`);
  assert.deepEqual(JSON.parse(calls[1].init.body), {
    tenant_id: TENANT,
    dispatch_id: DISPATCH_ID,
    issue_ref: ISSUE_REF,
    result_ref: parsed.result_ref,
    result_hash: parsed.result_hash,
  });
  assert.doesNotMatch(JSON.stringify(result), /private|secret|question|context/i);
});

test("already closed issue requires no close and returns the same safe completed result", async () => {
  const parsed = parseResultComments(packet(), ISSUE_REF, [commentRow(202)]);
  let stateCalls = 0;
  let closeCalls = 0;
  const result = await reconcileResultForIssue(config(), packet(), ISSUE_REF, {
    issueClient: {
      comments: () => [commentRow(202)],
      state: () => { stateCalls += 1; return stateReadback("CLOSED"); },
      close: () => { closeCalls += 1; },
    },
    fetchImpl: fakeFetch([
      response(200, consumedResult(parsed)),
      response(200, closedAck(parsed)),
    ]),
  });

  assert.equal(result.status, "closed");
  assert.equal(result.result_ref, parsed.result_ref);
  assert.equal(stateCalls, 1);
  assert.equal(closeCalls, 0);
});

test("needs_human first callback returns task identity and replay accepts base six fields", async () => {
  const humanPacket = packet();
  const humanPayload = resultPayload("needs_human");
  const humanComment = commentRow(203, resultBody(humanPayload));
  const parsed = parseResultComments(humanPacket, ISSUE_REF, [humanComment]);
  const taskId = "f".repeat(64);
  const firstReadback = consumedResult(parsed, {
    task_id: taskId,
    task_status: "open",
    version: 1,
  });
  let firstStateCalls = 0;
  let firstCloseCalls = 0;
  const first = await reconcileResultForIssue(config(), humanPacket, ISSUE_REF, {
    issueClient: {
      comments: () => [humanComment],
      state: () => { firstStateCalls += 1; return stateReadback("CLOSED"); },
      close: () => { firstCloseCalls += 1; },
    },
    fetchImpl: fakeFetch([
      response(200, firstReadback),
      response(200, closedAck(parsed)),
    ]),
  });
  assert.deepEqual(first, {
    status: "closed",
    tenant_id: TENANT,
    dispatch_id: DISPATCH_ID,
    job_id: JOB_ID,
    result_ref: parsed.result_ref,
    result_hash: parsed.result_hash,
    task_id: taskId,
    task_status: "open",
    version: 1,
  });
  assert.equal(firstStateCalls, 1);
  assert.equal(firstCloseCalls, 0);

  let replayStateCalls = 0;
  let replayCloseCalls = 0;
  const replay = await reconcileResultForIssue(config(), humanPacket, ISSUE_REF, {
    issueClient: {
      comments: () => [humanComment],
      state: () => { replayStateCalls += 1; return stateReadback("CLOSED"); },
      close: () => { replayCloseCalls += 1; },
    },
    fetchImpl: fakeFetch([
      response(200, consumedResult(parsed)),
      response(200, closedAck(parsed)),
    ]),
  });
  assert.deepEqual(replay, {
    status: "closed",
    tenant_id: TENANT,
    dispatch_id: DISPATCH_ID,
    job_id: JOB_ID,
    result_ref: parsed.result_ref,
    result_hash: parsed.result_hash,
  });
  assert.equal(replayStateCalls, 1);
  assert.equal(replayCloseCalls, 0);
  assert.doesNotMatch(JSON.stringify(first), /question|context|private|secret/i);
});

test("foreign, stale, and extra callback readbacks never reach issue state or close", async () => {
  const parsed = parseResultComments(packet(), ISSUE_REF, [commentRow(204)]);
  const invalidReadbacks = [
    consumedResult(parsed, { tenant_id: FOREIGN_TENANT }),
    consumedResult(parsed, { dispatch_id: "e".repeat(64) }),
    consumedResult(parsed, { job_id: `goal:${FOREIGN_OPPORTUNITY_ID}` }),
    consumedResult(parsed, { result_hash: "e".repeat(64) }),
    { ...consumedResult(parsed), private_payload: SECRET },
    { ...consumedResult(parsed), task_id: "t".repeat(64), task_status: "open", version: 1 },
  ];
  for (const invalidReadback of invalidReadbacks) {
    let stateCalls = 0;
    let closeCalls = 0;
    await assert.rejects(
      reconcileResultForIssue(config(), packet(), ISSUE_REF, {
        issueClient: {
          comments: () => [commentRow(204)],
          state: () => { stateCalls += 1; return stateReadback("OPEN"); },
          close: () => { closeCalls += 1; },
        },
        fetchImpl: fakeFetch([response(200, invalidReadback)]),
      }),
      (error) => error instanceof Error && error.message === "result readback invalid" && !error.message.includes(SECRET),
    );
    assert.equal(stateCalls, 0);
    assert.equal(closeCalls, 0);
  }
});

test("callback transport failure never reads or closes the issue", async () => {
  let stateCalls = 0;
  let closeCalls = 0;
  await assert.rejects(
    reconcileResultForIssue(config(), packet(), ISSUE_REF, {
      issueClient: {
        comments: () => [commentRow(205)],
        state: () => { stateCalls += 1; return stateReadback("OPEN"); },
        close: () => { closeCalls += 1; },
      },
      fetchImpl: fakeFetch([response(503, { error: SECRET })]),
    }),
    (error) => error instanceof Error && error.message === "bridge request failed" && !error.message.includes(SECRET),
  );
  assert.equal(stateCalls, 0);
  assert.equal(closeCalls, 0);
});

test("close failure is recoverable by the next invocation when the remote issue is already closed", async () => {
  const parsed = parseResultComments(packet(), ISSUE_REF, [commentRow(206)]);
  let firstStateCalls = 0;
  let firstCloseCalls = 0;
  await assert.rejects(
    reconcileResultForIssue(config(), packet(), ISSUE_REF, {
      issueClient: {
        comments: () => [commentRow(206)],
        state: () => { firstStateCalls += 1; return stateReadback("OPEN"); },
        close: () => { firstCloseCalls += 1; throw new Error(`close unknown ${SECRET}`); },
      },
      fetchImpl: fakeFetch([response(200, consumedResult(parsed))]),
    }),
    (error) => error instanceof Error && error.message === "issue close failed" && !error.message.includes(SECRET),
  );
  assert.equal(firstStateCalls, 1);
  assert.equal(firstCloseCalls, 1);

  let secondStateCalls = 0;
  let secondCloseCalls = 0;
  const recovered = await reconcileResultForIssue(config(), packet(), ISSUE_REF, {
    issueClient: {
      comments: () => [commentRow(206)],
      state: () => { secondStateCalls += 1; return stateReadback("CLOSED"); },
      close: () => { secondCloseCalls += 1; },
    },
    fetchImpl: fakeFetch([
      response(200, consumedResult(parsed)),
      response(200, closedAck(parsed)),
    ]),
  });
  assert.equal(recovered.status, "closed");
  assert.equal(secondStateCalls, 1);
  assert.equal(secondCloseCalls, 0);
});

test("close readback that remains open fails after one close", async () => {
  const parsed = parseResultComments(packet(), ISSUE_REF, [commentRow(207)]);
  let stateCalls = 0;
  let closeCalls = 0;
  await assert.rejects(
    reconcileResultForIssue(config(), packet(), ISSUE_REF, {
      issueClient: {
        comments: () => [commentRow(207)],
        state: () => { stateCalls += 1; return stateReadback("OPEN"); },
        close: () => { closeCalls += 1; },
      },
      fetchImpl: fakeFetch([response(200, consumedResult(parsed))]),
    }),
    (error) => error instanceof Error && error.message === "issue close readback failed",
  );
  assert.equal(stateCalls, 2);
  assert.equal(closeCalls, 1);
});

test("main returns idle without touching GitHub and composes a claimed pending cycle", async () => {
  const idleCalls = [];
  const idleIssueClient = {
    get list() { throw new Error("GitHub must not be touched"); },
  };
  const idle = await main({
    LM_SYMPHONY_API_BASE_URL: BASE,
    LM_SYMPHONY_BRIDGE_SECRET: SECRET,
    LM_RUNTIME_TENANT_ID: TENANT,
  }, {
    issueClient: idleIssueClient,
    fetchImpl: fakeFetch([response(200, { dispatch: null })], idleCalls),
  });
  assert.deepEqual(idle, { status: "idle" });
  assert.equal(idleCalls.length, 1);

  const calls = [];
  let createCalls = 0;
  let stateCalls = 0;
  let closeCalls = 0;
  const composed = await main({
    LM_SYMPHONY_API_BASE_URL: BASE,
    LM_SYMPHONY_BRIDGE_SECRET: SECRET,
    LM_RUNTIME_TENANT_ID: TENANT,
  }, {
    issueClient: {
      list: () => [],
      create: () => { createCalls += 1; return ISSUE_URL; },
      comments: () => [],
      state: () => { stateCalls += 1; return stateReadback("OPEN"); },
      close: () => { closeCalls += 1; },
    },
    fetchImpl: fakeFetch([
      response(200, { dispatch: dispatch() }),
      response(200, "<private html>", { "set-cookie": COOKIE }),
      response(200, workroom()),
      response(200, mirroredIssue()),
    ], calls),
  });
  assert.deepEqual(composed, { status: "pending" });
  assert.equal(Object.isFrozen(composed), true);
  assert.equal(createCalls, 1);
  assert.equal(stateCalls, 0);
  assert.equal(closeCalls, 0);
  assert.equal(calls.length, 4);
  assert.doesNotMatch(JSON.stringify(composed), new RegExp(SECRET));
});

test("main recovers a mirrored dispatch on the next invocation and performs result, close, and close-ack once", async () => {
  const env = {
    LM_SYMPHONY_API_BASE_URL: BASE,
    LM_SYMPHONY_BRIDGE_SECRET: SECRET,
    LM_RUNTIME_TENANT_ID: TENANT,
  };
  const firstCalls = [];
  const secondCalls = [];
  let commentCalls = 0;
  let listCalls = 0;
  let createCalls = 0;
  let stateCalls = 0;
  let closeCalls = 0;
  const issueClient = {
    list() { listCalls += 1; return []; },
    create() { createCalls += 1; return ISSUE_URL; },
    comments() {
      commentCalls += 1;
      return commentCalls === 1 ? [] : [commentRow(208)];
    },
    state() {
      stateCalls += 1;
      return stateReadback(stateCalls === 1 ? "OPEN" : "CLOSED");
    },
    close() { closeCalls += 1; },
  };
  const first = await main(env, {
    issueClient,
    fetchImpl: fakeFetch([
      response(200, { dispatch: dispatch() }),
      response(200, "<private html>", { "set-cookie": COOKIE }),
      response(200, workroom()),
      response(200, mirroredIssue()),
    ], firstCalls),
  });
  assert.deepEqual(first, { status: "pending" });
  assert.equal(listCalls, 1);
  assert.equal(createCalls, 1);
  assert.equal(stateCalls, 0);
  assert.equal(closeCalls, 0);
  assert.equal(firstCalls.length, 4);

  const second = await main(env, {
    issueClient,
    fetchImpl: fakeFetch([
      response(200, { dispatch: {
        tenant_id: TENANT,
        dispatch_id: DISPATCH_ID,
        job_id: JOB_ID,
        round: 1,
        status: "mirrored",
        answered_human_boundaries: [],
        issue_ref: ISSUE_REF,
      } }),
      response(200, "<private html>", { "set-cookie": COOKIE }),
      response(200, workroom()),
      response(200, consumedResult(parseResultComments(packet(), ISSUE_REF, [commentRow(208)]))),
      response(200, closedAck(parseResultComments(packet(), ISSUE_REF, [commentRow(208)]))),
    ], secondCalls),
  });
  assert.equal(second.status, "closed");
  assert.equal(second.result_ref, "github-comment://Daisuke134/life-manager-workrooms/42/208");
  assert.equal(listCalls, 1, "recovery must skip issue listing");
  assert.equal(createCalls, 1, "recovery must skip issue creation");
  assert.equal(commentCalls, 2);
  assert.equal(stateCalls, 2);
  assert.equal(closeCalls, 1);
  assert.equal(secondCalls.length, 5);
  assert.deepEqual(secondCalls.map((call) => call.url), [
    `${BASE}/api/internal/money-printer/symphony/claim`,
    `${BASE}/money-printer`,
    `${BASE}/api/panel/money-printer/workroom?opportunity_id=${OPPORTUNITY_ID}`,
    `${BASE}/api/internal/money-printer/symphony/result`,
    `${BASE}/api/internal/money-printer/symphony/close`,
  ]);
  assert.doesNotMatch(JSON.stringify(second), new RegExp(SECRET));
});

test("consumed recovery completes after a close failure without duplicate issue or terminal effects", async () => {
  const env = {
    LM_SYMPHONY_API_BASE_URL: BASE,
    LM_SYMPHONY_BRIDGE_SECRET: SECRET,
    LM_RUNTIME_TENANT_ID: TENANT,
  };
  const parsed = parseResultComments(packet(), ISSUE_REF, [commentRow(209)]);
  const firstCalls = [];
  const secondCalls = [];
  let comments = 0;
  let states = 0;
  let closes = 0;
  const issueClient = {
    list() { throw new Error("recovery must not list"); },
    create() { throw new Error("recovery must not create"); },
    comments() { comments += 1; return [commentRow(209)]; },
    state() { states += 1; return stateReadback(states === 1 ? "OPEN" : "CLOSED"); },
    close() { closes += 1; throw new Error(`close unknown ${SECRET}`); },
  };
  await assert.rejects(
    main(env, {
      issueClient,
      fetchImpl: fakeFetch([
        response(200, { dispatch: {
          tenant_id: TENANT,
          dispatch_id: DISPATCH_ID,
          job_id: JOB_ID,
          round: 1,
          status: "result_ready",
          answered_human_boundaries: [],
          issue_ref: ISSUE_REF,
        } }),
        response(200, "<private html>", { "set-cookie": COOKIE }),
        response(200, workroom()),
        response(200, consumedResult(parsed)),
      ], firstCalls),
    }),
    (error) => error instanceof Error && error.message === "issue close failed" && !error.message.includes(SECRET),
  );
  assert.equal(firstCalls.length, 4);
  assert.equal(states, 1);
  assert.equal(closes, 1);

  const recovered = await main(env, {
    issueClient: {
      list() { throw new Error("recovery must not list"); },
      create() { throw new Error("recovery must not create"); },
      comments() { comments += 1; return [commentRow(209)]; },
      state() { states += 1; return stateReadback("CLOSED"); },
      close() { closes += 1; },
    },
    fetchImpl: fakeFetch([
      response(200, { dispatch: {
        tenant_id: TENANT,
        dispatch_id: DISPATCH_ID,
        job_id: JOB_ID,
        round: 1,
        status: "consumed",
        answered_human_boundaries: [],
        issue_ref: ISSUE_REF,
      } }),
      response(200, "<private html>", { "set-cookie": COOKIE }),
      response(200, workroom()),
      response(200, consumedResult(parsed)),
      response(200, closedAck(parsed)),
    ], secondCalls),
  });
  assert.equal(recovered.status, "closed");
  assert.equal(secondCalls.length, 5);
  assert.equal(comments, 2);
  assert.equal(states, 2);
  assert.equal(closes, 1);
  assert.doesNotMatch(JSON.stringify(recovered), new RegExp(SECRET));
});
