"use strict";

const test = require("node:test");
const assert = require("node:assert");
const vm = require("node:vm");
const { renderMoneyPrinterWebMcpScript } = require("./money-printer-webmcp.js");

test("Money Printer registers inspection and state-dependent human answer tools", async () => {
  const csrf = "csrf-page-value";
  const script = renderMoneyPrinterWebMcpScript({ csrf });
  assert.match(script, /document\.modelContext\.registerTool\(/);
  assert.match(script, /x-lm-csrf/);
  assert.match(script, /idempotency-key/);
  assert.doesNotMatch(script, /authorization|bearer/i);

  const registrations = [];
  const requests = [];
  const refreshEvents = [];
  let releaseRefresh;
  const refreshGate = new Promise((resolve) => { releaseRefresh = resolve; });
  let nextRefresh = refreshGate;
  const body = { observed_at: "2026-08-29T00:00:00.000Z", metrics: { paid_verified: "0" } };
  const task = {
    task_id: "a".repeat(64), version: 1,
    question: "Approve the prepared delivery.",
    required_format: { kind: "approval" }, reason_code: "model_boundary",
  };
  let next = { task };
  let resolveAnswerRegistration;
  let resolveRegistrationStarted;
  const answerRegistration = new Promise((resolve) => { resolveAnswerRegistration = resolve; });
  const registrationStarted = new Promise((resolve) => { resolveRegistrationStarted = resolve; });
  class FakeAbortController {
    constructor() { this.signal = { aborted: false }; }
    abort() { this.signal.aborted = true; }
  }
  const initialized = vm.runInNewContext(script, {
    document: {
      modelContext: {
        registerTool(tool, options) {
          registrations.push({ tool, options });
          if (tool.name === "record_human_answer") resolveRegistrationStarted();
          return tool.name === "record_human_answer" ? answerRegistration : Promise.resolve();
        },
      },
      dispatchEvent(event) {
        refreshEvents.push(event);
        if (event.detail && typeof event.detail === "object") event.detail.promise = nextRefresh;
        return true;
      },
    },
    fetch: async (url, init) => {
      requests.push({ url, init });
      if (url.endsWith("/money-printer")) return { ok: true, status: 200, json: async () => body };
      if (url.endsWith("/human-task/next")) return { ok: true, status: 200, json: async () => next };
      if (url.endsWith("/money-printer/opportunity")) return { ok: true, status: 200, json: async () => ({ opportunity_id: "c".repeat(64), job_ref: "runtime-job://tenant-a/goal%3Ac", status: "DISCOVERED" }) };
      if (url.includes("/money-printer/workroom?opportunity_id=")) return { ok: true, status: 200, json: async () => ({ opportunity_id: "c".repeat(64), job_ref: "runtime-job://tenant-a/goal%3Ac", status: "DISCOVERED", activity: [] }) };
      return { ok: true, status: 200, json: async () => ({ task_id: task.task_id, resume_ref: "runtime-job://tenant-a/job-1" }) };
    },
    Promise,
    Error,
    Object,
    String,
    AbortController: FakeAbortController,
    Date: { now: () => 1724889600000 },
    Math: { random: () => 0.123456 },
  });
  await initialized;

  assert.equal(registrations.length, 4);
  const moneyPrinterRegistration = registrations.find(({ tool: candidate }) => candidate.name === "inspect_money_printer");
  const nextTaskRegistration = registrations.find(({ tool: candidate }) => candidate.name === "inspect_next_human_task");
  const addOpportunityRegistration = registrations.find(({ tool: candidate }) => candidate.name === "add_opportunity");
  const inspectWorkroomRegistration = registrations.find(({ tool: candidate }) => candidate.name === "inspect_workroom");
  assert.ok(moneyPrinterRegistration);
  assert.ok(nextTaskRegistration);
  assert.ok(addOpportunityRegistration);
  assert.ok(inspectWorkroomRegistration);
  const { tool } = moneyPrinterRegistration;
  const { tool: inspectNextTask } = nextTaskRegistration;
  assert.equal(tool.name, "inspect_money_printer");
  assert.deepEqual(Object.keys(tool).sort(), ["annotations", "description", "execute", "inputSchema", "name"]);
  assert.deepEqual(JSON.parse(JSON.stringify(tool.inputSchema)), {
    type: "object",
    properties: {},
    additionalProperties: false,
  });
  assert.equal(tool.annotations.readOnlyHint, true);
  assert.equal(tool.annotations.untrustedContentHint, true);
  assert.equal(inspectNextTask.annotations.untrustedContentHint, true);

  const { tool: addOpportunity } = addOpportunityRegistration;
  assert.deepEqual(JSON.parse(JSON.stringify(addOpportunity.inputSchema)), {
    type: "object",
    properties: {
      source_url: { type: "string" },
      title: { type: "string" },
      goal_statement: { type: "string" },
      value_minor: { type: "string" },
      currency: { type: "string" },
    },
    required: ["source_url", "title", "goal_statement", "value_minor", "currency"],
    additionalProperties: false,
  });
  assert.equal(addOpportunity.annotations.readOnlyHint, false);

  const { tool: inspectWorkroom } = inspectWorkroomRegistration;
  assert.deepEqual(JSON.parse(JSON.stringify(inspectWorkroom.inputSchema)), {
    type: "object",
    properties: { opportunity_id: { type: "string" } },
    required: ["opportunity_id"],
    additionalProperties: false,
  });
  assert.equal(inspectWorkroom.annotations.readOnlyHint, true);
  assert.equal(inspectWorkroom.annotations.untrustedContentHint, true);

  assert.deepEqual(await tool.execute({}), body);
  assert.deepEqual(requests[0], {
    url: "/api/panel/money-printer",
    init: { method: "GET", credentials: "same-origin", headers: { Accept: "application/json" } },
  });
  const inspected = inspectNextTask.execute({});
  await registrationStarted;
  let inspectedResolved = false;
  const inspectedResult = inspected.then((result) => { inspectedResolved = true; return result; });
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(inspectedResolved, false);
  resolveAnswerRegistration();
  assert.deepEqual(await inspectedResult, { task });
  assert.deepEqual(requests[1], {
    url: "/api/panel/money-printer/human-task/next",
    init: { method: "GET", credentials: "same-origin", headers: { Accept: "application/json" } },
  });
  assert.equal(registrations.length, 5);
  const { tool: answerTool, options } = registrations.find(({ tool: candidate }) => candidate.name === "record_human_answer");
  assert.equal(answerTool.name, "record_human_answer");
  assert.match(answerTool.description, /resume|side effect|write/i);
  assert.deepEqual(JSON.parse(JSON.stringify(answerTool.inputSchema)), {
    type: "object",
    properties: { answer_ref: { type: "string" } },
    required: ["answer_ref"],
    additionalProperties: false,
  });
  assert.ok(options && options.signal);
  assert.equal(options.signal.aborted, false);

  let answerSettled = false;
  const answerResultPromise = answerTool.execute({ answer_ref: "vault-answer://tenant-a/answer-1" }).then((result) => {
    answerSettled = true;
    return result;
  });
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(answerSettled, false);
  releaseRefresh();
  const answerResult = await answerResultPromise;
  assert.deepEqual(answerResult, { task_id: task.task_id, resume_ref: "runtime-job://tenant-a/job-1" });
  assert.equal(options.signal.aborted, true);
  assert.equal(requests[2].url, "/api/panel/money-printer/human-task/answer");
  assert.deepEqual(requests[2].init, {
    method: "POST",
    credentials: "same-origin",
    headers: {
      Accept: "application/json",
      "content-type": "application/json",
      "x-lm-csrf": csrf,
      "idempotency-key": requests[2].init.headers["idempotency-key"],
    },
    body: JSON.stringify({ task_id: task.task_id, version: 1, answer_ref: "vault-answer://tenant-a/answer-1" }),
  });
  assert.match(requests[2].init.headers["idempotency-key"], /^human-answer-[A-Za-z0-9._:-]{8,128}$/);

  next = { task: null };
  await inspectNextTask.execute({});
  assert.equal(options.signal.aborted, true);

  const opportunityInput = {
    source_url: "https://public.example/opportunity",
    title: "Public opportunity",
    goal_statement: "Complete it.",
    value_minor: "50000",
    currency: "JPY",
  };
  const created = { opportunity_id: "c".repeat(64), job_ref: "runtime-job://tenant-a/goal%3Ac", status: "DISCOVERED" };
  const addResultPromise = addOpportunity.execute(opportunityInput);
  const addResult = await addResultPromise;
  assert.deepEqual(addResult, created);
  assert.equal(requests[4].url, "/api/panel/money-printer/opportunity");
  assert.equal(requests[4].init.method, "POST");
  assert.equal(requests[4].init.credentials, "same-origin");
  assert.deepEqual(JSON.parse(requests[4].init.body), opportunityInput);
  assert.equal(requests[4].init.headers["x-lm-csrf"], csrf);
  assert.match(requests[4].init.headers["idempotency-key"], /^add-opportunity-[A-Za-z0-9._:-]{8,128}$/);
  assert.equal(refreshEvents.length, 2);
  assert.deepEqual(refreshEvents.map((event) => event.type), ["money-printer:refresh", "money-printer:refresh"]);

  let rejectRefresh;
  nextRefresh = new Promise((_resolve, reject) => { rejectRefresh = reject; });
  const failedRefresh = addOpportunity.execute(opportunityInput);
  rejectRefresh(new Error("money printer reload failed"));
  await assert.rejects(failedRefresh, /money printer reload failed/);

  const workroom = { opportunity_id: "c".repeat(64), job_ref: created.job_ref, status: "DISCOVERED", activity: [] };
  const inspectResult = await inspectWorkroom.execute({ opportunity_id: workroom.opportunity_id });
  assert.deepEqual(inspectResult, workroom);
  assert.equal(requests[6].url, "/api/panel/money-printer/workroom?opportunity_id=" + encodeURIComponent(workroom.opportunity_id));
  assert.deepEqual(requests[6].init, {
    method: "GET",
    credentials: "same-origin",
    headers: { Accept: "application/json" },
  });

  assert.doesNotThrow(() => vm.runInNewContext(script, { document: {} }));
});
