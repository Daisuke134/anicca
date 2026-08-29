"use strict";

function scriptString(value) {
  return JSON.stringify(String(value == null ? "" : value))
    .replace(/</g, "\\u003c")
    .replace(/>/g, "\\u003e")
    .replace(/&/g, "\\u0026")
    .replace(/\u2028/g, "\\u2028")
    .replace(/\u2029/g, "\\u2029");
}

function renderMoneyPrinterWebMcpScript({ csrf } = {}) {
  const pageCsrf = scriptString(csrf);
  return `
(async () => {
  if (typeof document === "undefined"
    || !document.modelContext
    || typeof document.modelContext.registerTool !== "function") return;

  const pageCsrf = ${pageCsrf};
  const taskKeys = ["task_id", "version", "question", "required_format", "reason_code"];
  let answerController = null;
  let answerTask = null;

  const abortAnswerTool = () => {
    if (answerController) answerController.abort();
    answerController = null;
    answerTask = null;
  };
  const exactTask = (value) => {
    if (!value || typeof value !== "object" || Array.isArray(value)
      || Object.keys(value).length !== taskKeys.length
      || taskKeys.some((key) => !Object.hasOwn(value, key))
      || !/^[0-9a-f]{64}$/.test(String(value.task_id || ""))
      || !Number.isInteger(value.version) || value.version < 1
      || typeof value.question !== "string" || !value.question.trim()
      || !(typeof value.required_format === "string"
        || (value.required_format && typeof value.required_format === "object"))
      || typeof value.reason_code !== "string" || !value.reason_code.trim()) return null;
    return {
      task_id: value.task_id,
      version: value.version,
      question: value.question,
      required_format: value.required_format,
      reason_code: value.reason_code,
    };
  };
  const sameTask = (left, right) => Boolean(left && right
    && left.task_id === right.task_id && left.version === right.version);
  const idempotencyKey = (prefix) => {
    const randomUuid = globalThis.crypto && typeof globalThis.crypto.randomUUID === "function"
      ? globalThis.crypto.randomUUID()
      : String(Date.now()) + "-" + Math.random().toString(36).slice(2);
    return prefix + randomUuid;
  };
  const answerResult = (value) => {
    if (!value || typeof value !== "object" || Array.isArray(value)
      || typeof value.task_id !== "string" || typeof value.resume_ref !== "string") {
      throw new Error("record_human_answer unavailable");
    }
    return { task_id: value.task_id, resume_ref: value.resume_ref };
  };
  const registerAnswerTool = async (task) => {
    abortAnswerTool();
    const controller = new AbortController();
    answerController = controller;
    answerTask = task;
    const tool = {
      name: "record_human_answer",
      description: "Record the human answer reference, write the paused state, and resume the same workroom; this side effect never creates a new workroom.",
      inputSchema: {
        type: "object",
        properties: { answer_ref: { type: "string" } },
        required: ["answer_ref"],
        additionalProperties: false,
      },
      annotations: { readOnlyHint: false },
      execute: async (input = {}) => {
        if (!input || typeof input !== "object" || Array.isArray(input)
          || typeof input.answer_ref !== "string") throw new Error("record_human_answer invalid");
        const response = await fetch("/api/panel/money-printer/human-task/answer", {
          method: "POST",
          credentials: "same-origin",
          headers: {
            Accept: "application/json",
            "content-type": "application/json",
            "x-lm-csrf": pageCsrf,
            "idempotency-key": idempotencyKey("human-answer-"),
          },
          body: JSON.stringify({ task_id: task.task_id, version: task.version, answer_ref: input.answer_ref }),
        });
        let value = {};
        try { value = await response.json(); } catch {}
        if (!response.ok) throw new Error(String(value && value.error || "record_human_answer unavailable"));
        const result = answerResult(value);
        controller.abort();
        if (answerController === controller) {
          answerController = null;
          answerTask = null;
        }
        await refreshMoneyPrinter();
        return result;
      },
    };
    await document.modelContext.registerTool(tool, { signal: controller.signal });
  };
  const getJson = async (path, failure) => {
    const response = await fetch(path, {
      method: "GET",
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    });
    if (!response.ok) throw new Error(failure);
    return response.json();
  };
  const refreshMoneyPrinter = async () => {
    if (!document || typeof document.dispatchEvent !== "function") return;
    const detail = {};
    try {
      const event = typeof CustomEvent === "function"
        ? new CustomEvent("money-printer:refresh", { detail })
        : { type: "money-printer:refresh", detail };
      document.dispatchEvent(event);
      if (detail.promise && typeof detail.promise.then === "function") await detail.promise;
    } catch {}
  };
  const request = () => getJson("/api/panel/money-printer", "inspect_money_printer unavailable");
  const opportunityKeys = ["source_url", "title", "goal_statement", "value_minor", "currency"];
  const exactOpportunityInput = (value) => {
    if (!value || typeof value !== "object" || Array.isArray(value)
      || Object.keys(value).length !== opportunityKeys.length
      || opportunityKeys.some((key) => !Object.hasOwn(value, key) || typeof value[key] !== "string")) return null;
    return {
      source_url: value.source_url,
      title: value.title,
      goal_statement: value.goal_statement,
      value_minor: value.value_minor,
      currency: value.currency,
    };
  };
  const exactOpportunityResult = (value) => {
    if (!value || typeof value !== "object" || Array.isArray(value)
      || Object.keys(value).length !== 3
      || !/^[0-9a-f]{64}$/.test(String(value.opportunity_id || ""))
      || typeof value.job_ref !== "string" || !value.job_ref
      || typeof value.status !== "string" || !value.status) throw new Error("add_opportunity unavailable");
    return { opportunity_id: value.opportunity_id, job_ref: value.job_ref, status: value.status };
  };
  const addOpportunityRequest = async (input) => {
    const body = exactOpportunityInput(input);
    if (!body) throw new Error("add_opportunity invalid");
    const response = await fetch("/api/panel/money-printer/opportunity", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "content-type": "application/json",
        "x-lm-csrf": pageCsrf,
        "idempotency-key": idempotencyKey("add-opportunity-"),
      },
      body: JSON.stringify(body),
    });
    let value = {};
    try { value = await response.json(); } catch {}
    if (!response.ok) throw new Error(String(value && value.error || "add_opportunity unavailable"));
    const result = exactOpportunityResult(value);
    await refreshMoneyPrinter();
    return result;
  };
  const inspectWorkroomRequest = (input) => {
    if (!input || typeof input !== "object" || Array.isArray(input)
      || Object.keys(input).length !== 1 || !/^[0-9a-f]{64}$/.test(String(input.opportunity_id || ""))) {
      throw new Error("inspect_workroom invalid");
    }
    return getJson("/api/panel/money-printer/workroom?opportunity_id=" + encodeURIComponent(input.opportunity_id), "inspect_workroom unavailable");
  };
  const requestNextTask = async () => {
    const value = await getJson("/api/panel/money-printer/human-task/next", "inspect_next_human_task unavailable");
    if (value && value.task === null) {
      abortAnswerTool();
      return { task: null };
    }
    const task = exactTask(value && value.task);
    if (!task) throw new Error("inspect_next_human_task unavailable");
    if (!sameTask(answerTask, task)) await registerAnswerTool(task);
    return { task };
  };

  const initialRegistration = Promise.all([
    document.modelContext.registerTool({
    name: "inspect_money_printer",
    description: "Inspect the current Money Printer state.",
    inputSchema: {
      type: "object",
      properties: {},
      additionalProperties: false,
    },
    annotations: { readOnlyHint: true, untrustedContentHint: true },
    execute: () => request(),
    }),
    document.modelContext.registerTool({
    name: "inspect_next_human_task",
    description: "Inspect the next exact human task that can be answered to resume its paused workroom.",
    inputSchema: {
      type: "object",
      properties: {},
      additionalProperties: false,
    },
    annotations: { readOnlyHint: true, untrustedContentHint: true },
    execute: () => requestNextTask(),
    }),
    document.modelContext.registerTool({
      name: "add_opportunity",
      description: "Add one public paid opportunity and open its tenant-scoped workroom.",
      inputSchema: {
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
      },
      annotations: { readOnlyHint: false },
      execute: addOpportunityRequest,
    }),
    document.modelContext.registerTool({
      name: "inspect_workroom",
      description: "Inspect one tenant-scoped opportunity workroom and its matching activity.",
      inputSchema: {
        type: "object",
        properties: { opportunity_id: { type: "string" } },
        required: ["opportunity_id"],
        additionalProperties: false,
      },
      annotations: { readOnlyHint: true, untrustedContentHint: true },
      execute: inspectWorkroomRequest,
    }),
  ]);
  await initialRegistration;
})();`;
}

module.exports = { renderMoneyPrinterWebMcpScript };
