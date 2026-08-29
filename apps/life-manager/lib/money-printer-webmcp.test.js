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
  const body = { observed_at: "2026-08-29T00:00:00.000Z", metrics: { paid_verified: "0" } };
  const task = {
    task_id: "a".repeat(64), version: 1,
    question: "Approve the prepared delivery.",
    required_format: { kind: "approval" }, reason_code: "model_boundary",
  };
  let next = { task };
  class FakeAbortController {
    constructor() { this.signal = { aborted: false }; }
    abort() { this.signal.aborted = true; }
  }
  vm.runInNewContext(script, {
    document: {
      modelContext: {
        registerTool(tool, options) {
          registrations.push({ tool, options });
          return Promise.resolve();
        },
      },
    },
    fetch: async (url, init) => {
      requests.push({ url, init });
      if (url.endsWith("/money-printer")) return { ok: true, status: 200, json: async () => body };
      if (url.endsWith("/human-task/next")) return { ok: true, status: 200, json: async () => next };
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

  assert.equal(registrations.length, 2);
  const moneyPrinterRegistration = registrations.find(({ tool: candidate }) => candidate.name === "inspect_money_printer");
  const nextTaskRegistration = registrations.find(({ tool: candidate }) => candidate.name === "inspect_next_human_task");
  assert.ok(moneyPrinterRegistration);
  assert.ok(nextTaskRegistration);
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

  assert.deepEqual(await tool.execute({}), body);
  assert.deepEqual(requests[0], {
    url: "/api/panel/money-printer",
    init: { method: "GET", credentials: "same-origin", headers: { Accept: "application/json" } },
  });
  assert.deepEqual(await inspectNextTask.execute({}), { task });
  assert.deepEqual(requests[1], {
    url: "/api/panel/money-printer/human-task/next",
    init: { method: "GET", credentials: "same-origin", headers: { Accept: "application/json" } },
  });
  assert.equal(registrations.length, 3);
  const { tool: answerTool, options } = registrations[2];
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

  const answerResult = await answerTool.execute({ answer_ref: "vault-answer://tenant-a/answer-1" });
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

  assert.doesNotThrow(() => vm.runInNewContext(script, { document: {} }));
});
