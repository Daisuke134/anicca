"use strict";

const { createHash } = require("node:crypto");

const TENANT_ID = /^[a-z0-9][a-z0-9._-]{0,199}$/;
const MACHINE_ID = /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}$/;
const REFERENCE = /^[a-z][a-z0-9+.-]{1,31}:\/\/[A-Za-z0-9][A-Za-z0-9._~:/?#@!$&'()*+,;=%-]{0,999}$/;
const HUMAN_BOUNDARY = /^human-boundary:\/\/sha256\/[0-9a-f]{64}$/;
const VAULT_ANSWER = /^vault-answer:\/\/([a-z0-9][a-z0-9._-]{0,199})\/[A-Za-z0-9][A-Za-z0-9._~%-]{0,255}$/;

function invalid(label) { throw new Error(`${label} invalid`); }

function text(value, label, pattern, max = 2_000) {
  if (typeof value !== "string") invalid(label);
  const result = value.trim();
  if (!result || result.length > max || (pattern && !pattern.test(result))) invalid(label);
  return result;
}

function stableJson(value) {
  if (Array.isArray(value)) return `[${value.map(stableJson).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableJson(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

function deepFreeze(value) {
  if (value && typeof value === "object" && !Object.isFrozen(value)) {
    Object.values(value).forEach(deepFreeze);
    Object.freeze(value);
  }
  return value;
}

function jsonObject(value, label, max = 4_096) {
  if (!value || typeof value !== "object" || Array.isArray(value)) invalid(label);
  let copy;
  try { copy = JSON.parse(JSON.stringify(value)); } catch { invalid(label); }
  if (Buffer.byteLength(JSON.stringify(copy)) > max) invalid(label);
  return deepFreeze(copy);
}

function jsonValue(value, label, max = 4_096) {
  if (typeof value === "string") return text(value, label, null, max);
  if (!value || typeof value !== "object") invalid(label);
  let copy;
  try { copy = JSON.parse(JSON.stringify(value)); } catch { invalid(label); }
  if (Buffer.byteLength(JSON.stringify(copy)) > max) invalid(label);
  return deepFreeze(copy);
}

function referenceObject(value) {
  const copy = jsonObject(value, "human task context refs", 16_384);
  for (const [key, raw] of Object.entries(copy)) {
    if (!/_(?:ref|refs)$/.test(key)) invalid("human task context refs reference-only");
    const refs = Array.isArray(raw) ? raw : [raw];
    if (!refs.length || refs.some((ref) => typeof ref !== "string" || !REFERENCE.test(ref))) {
      invalid("human task context refs reference-only");
    }
  }
  return copy;
}

function canonicalHumanTaskInput(input = {}) {
  if (!input || typeof input !== "object" || Array.isArray(input)) invalid("human task");
  const uid = text(input.tenantId, "human task tenant", TENANT_ID);
  const canonical = {
    uid,
    job_id: text(input.jobId, "human task job", MACHINE_ID),
    reason_code: text(input.reasonCode, "human task reason", MACHINE_ID),
    question: text(input.question, "human task question"),
    required_format: jsonValue(input.requiredFormat, "human task required format"),
    resume_ref: text(input.resumeRef, "human task resume ref", REFERENCE, 1_000),
    context_refs: referenceObject(input.contextRefs === undefined ? {} : input.contextRefs),
    human_boundary_ref: text(input.humanBoundaryRef, "human boundary ref", HUMAN_BOUNDARY, 100),
  };
  return deepFreeze(canonical);
}

function buildHumanTask(input = {}) {
  const canonical = canonicalHumanTaskInput(input);
  const taskId = createHash("sha256").update(stableJson(canonical), "utf8").digest("hex");
  return Object.freeze({ ...canonical, task_id: taskId, status: "open", version: 1 });
}

function validateHumanAnswer(input = {}) {
  if (!input || typeof input !== "object" || Array.isArray(input)) invalid("human task answer");
  const scope = input.scope;
  const uid = text(scope && scope.uid, "human task scope", TENANT_ID);
  const taskId = text(input.taskId, "human task id", /^[0-9a-f]{64}$/, 64);
  if (!Number.isInteger(input.version) || input.version < 1 || input.version > 1_000_000) invalid("human task version");
  const answerRef = text(input.answerRef, "human task answer ref", VAULT_ANSWER, 400);
  if (answerRef.match(VAULT_ANSWER)[1] !== uid) invalid("human task answer scope");
  return Object.freeze({ uid, taskId, version: input.version, answerRef });
}

async function answerHumanTask(input, store) {
  const answer = validateHumanAnswer(input);
  if (!store || typeof store.answerOnce !== "function") throw new Error("human task store unavailable");
  const closed = await store.answerOnce(answer);
  const answerRef = closed && (closed.answer_ref || closed.answerRef);
  const taskId = closed && (closed.task_id || closed.taskId);
  const uid = closed && (closed.uid || closed.tenant_id);
  const resumeRef = closed && (closed.resume_ref || closed.resumeRef);
  if (!closed || typeof closed !== "object" || Array.isArray(closed)
    || closed.status !== "answered" || answerRef !== answer.answerRef
    || (uid != null && uid !== answer.uid)
    || taskId !== answer.taskId
    || typeof resumeRef !== "string" || !REFERENCE.test(resumeRef)) {
    throw new Error("human task answer not read back");
  }
  return Object.freeze({ task_id: taskId, resume_ref: resumeRef });
}

module.exports = {
  buildHumanTask,
  canonicalHumanTaskInput,
  validateHumanAnswer,
  answerHumanTask,
};
