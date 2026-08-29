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
(() => {
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
  const idempotencyKey = () => {
    const randomUuid = globalThis.crypto && typeof globalThis.crypto.randomUUID === "function"
      ? globalThis.crypto.randomUUID()
      : String(Date.now()) + "-" + Math.random().toString(36).slice(2);
    return "human-answer-" + randomUuid;
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
            "idempotency-key": idempotencyKey(),
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
  const request = () => getJson("/api/panel/money-printer", "inspect_money_printer unavailable");
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

  document.modelContext.registerTool({
    name: "inspect_money_printer",
    description: "Inspect the current Money Printer state.",
    inputSchema: {
      type: "object",
      properties: {},
      additionalProperties: false,
    },
    annotations: { readOnlyHint: true },
    execute: () => request(),
  });
  document.modelContext.registerTool({
    name: "inspect_next_human_task",
    description: "Inspect the next exact human task that can be answered to resume its paused workroom.",
    inputSchema: {
      type: "object",
      properties: {},
      additionalProperties: false,
    },
    annotations: { readOnlyHint: true },
    execute: () => requestNextTask(),
  });
})();`;
}

module.exports = { renderMoneyPrinterWebMcpScript };
