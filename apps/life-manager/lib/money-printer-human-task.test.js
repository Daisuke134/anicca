"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { answerHumanTask, buildHumanTask } = require("./money-printer-human-task.js");

const MIGRATION = fs.readFileSync(path.join(
  __dirname,
  "../migrations/2026-08-29-lm-money-printer-human-tasks.sql",
), "utf8");

function input(overrides = {}) {
  return {
    tenantId: "tenant-1", jobId: "job-1", reasonCode: "model_boundary",
    question: "Approve the prepared public delivery.",
    requiredFormat: { kind: "approval", values: ["approve", "request_changes"] },
    resumeRef: "runtime-job://tenant-1/job-1",
    contextRefs: {
      opportunity_ref: "opportunity://tenant-1/op-1",
      artifact_ref: `object://sha256/${"b".repeat(64)}`,
    },
    humanBoundaryRef: `human-boundary://sha256/${"a".repeat(64)}`,
    ...overrides,
  };
}

test("builds one stable task from model-selected reason and bound judgment receipt", () => {
  const first = buildHumanTask(input());
  const second = buildHumanTask(input());
  assert.equal(first.task_id, second.task_id);
  assert.equal(first.uid, "tenant-1");
  assert.equal(first.status, "open");
  assert.equal(first.version, 1);
  assert.equal(first.human_boundary_ref, input().humanBoundaryRef);
  assert.equal(Object.isFrozen(first), true);
  assert.equal(buildHumanTask(input({ reasonCode: "arbitrary_model_reason" })).reason_code, "arbitrary_model_reason");
  assert.throws(() => buildHumanTask(input({ humanBoundaryRef: undefined })), /human boundary/i);
  assert.throws(() => buildHumanTask(input({ humanBoundaryRef: "human-boundary://raw" })), /human boundary/i);
});

test("answers the tenant task once, rejects stale or cross-tenant input, and returns original resume", async () => {
  const task = buildHumanTask(input());
  let row = { ...task };
  const calls = [];
  const store = {
    async answerOnce(answer) {
      calls.push(answer);
      if (answer.uid !== row.uid) throw new Error("human task scope mismatch");
      if (row.status === "answered") {
        if (row.answer_ref !== answer.answerRef) throw new Error("human task answer conflict");
        return { ...row };
      }
      if (answer.version !== row.version) throw new Error("human task version conflict");
      row = { ...row, status: "answered", version: 2, answer_ref: answer.answerRef };
      return { ...row };
    },
  };
  const request = {
    scope: { uid: "tenant-1" }, taskId: task.task_id, version: 1,
    answerRef: "vault-answer://tenant-1/answer-1",
  };
  const result = await answerHumanTask(request, store);
  assert.deepEqual(result, { task_id: task.task_id, resume_ref: task.resume_ref });
  assert.deepEqual(await answerHumanTask(request, store), result);
  assert.equal(calls.length, 2);

  await assert.rejects(answerHumanTask({ ...request, version: 0 }, store), /version|invalid/i);
  await assert.rejects(answerHumanTask({ ...request, scope: { uid: "tenant-2" }, answerRef: "vault-answer://tenant-2/a" }, store), /scope/i);
});

test("rejects plaintext task context and non-vault answer references", () => {
  assert.throws(() => buildHumanTask(input({ contextRefs: { answer: "private value" } })), /reference-only/i);
  assert.rejects(() => answerHumanTask({
    scope: { uid: "tenant-1" }, taskId: "not-a-task-id", version: 1, answerRef: "private answer",
  }, { answerOnce: async () => ({}) }), /task|vault|reference/i);
});

test("migration adds tenant-safe tasks and requeues the same runtime job atomically", () => {
  assert.match(MIGRATION, /CREATE TABLE IF NOT EXISTS public\.lm_human_tasks/i);
  assert.match(MIGRATION, /PRIMARY KEY \(uid, task_id\)/i);
  assert.match(MIGRATION, /status[^\n]*CHECK[\s\S]*'open'[\s\S]*'answered'/i);
  assert.match(MIGRATION, /version[^\n]*CHECK[\s\S]*version[^\n]*>= 1/i);
  assert.match(MIGRATION, /UNIQUE INDEX[\s\S]*\(uid, job_id, reason_code\)[\s\S]*WHERE status = 'open'/i);
  assert.match(MIGRATION, /ALTER TABLE public\.lm_runtime_jobs[\s\S]*waiting_human/i);
  assert.match(MIGRATION, /ALTER TABLE public\.lm_human_tasks ENABLE ROW LEVEL SECURITY/i);
  assert.match(MIGRATION, /FORCE ROW LEVEL SECURITY/i);
  assert.match(MIGRATION, /REVOKE ALL ON TABLE[\s\S]*lm_human_tasks[\s\S]*FROM PUBLIC, anon, authenticated/i);
  assert.match(MIGRATION, /CREATE OR REPLACE FUNCTION public\.create_lm_human_task/i);
  assert.match(MIGRATION, /CREATE OR REPLACE FUNCTION public\.answer_lm_human_task/i);
  assert.match(MIGRATION, /GRANT EXECUTE ON FUNCTION public\.(?:create|answer)_lm_human_task/i);
  assert.match(MIGRATION, /FOR UPDATE/i);
  assert.match(MIGRATION, /status = 'waiting_human'[\s\S]*status = 'queued'/i);
  assert.match(MIGRATION, /WHERE tenant_id = p_uid[\s\S]*AND job_id = p_job_id/i);
  const answerRpc = MIGRATION.slice(MIGRATION.indexOf("CREATE OR REPLACE FUNCTION public.answer_lm_human_task"));
  assert.doesNotMatch(answerRpc, /INSERT INTO public\.lm_runtime_jobs/i);
  assert.match(MIGRATION, /answer_ref[^\n]*vault-answer:\/\//i);
});
