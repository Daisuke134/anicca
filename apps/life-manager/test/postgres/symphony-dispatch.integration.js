"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { createHash } = require("node:crypto");
const { Client } = require("pg");

const ROOT = path.resolve(__dirname, "../..");
const MIGRATIONS = [
  ["RUNTIME_MIGRATION_B64", "migrations/20260729_runtime_jobs.sql"],
  ["OPPORTUNITY_MIGRATION_B64", "migrations/2026-08-29-lm-money-printer-opportunities.sql"],
  ["HUMAN_MIGRATION_B64", "migrations/2026-08-29-lm-money-printer-human-tasks.sql"],
  ["SYMPHONY_MIGRATION_B64", "migrations/2026-08-30-lm-symphony-dispatches.sql"],
];

function migration([envName, relativePath]) {
  const encoded = process.env[envName];
  return encoded
    ? Buffer.from(encoded, "base64").toString("utf8")
    : fs.readFileSync(path.join(ROOT, relativePath), "utf8");
}

function databaseUrl(source, database) {
  const url = new URL(source);
  url.pathname = `/${database}`;
  return url.toString();
}

function opportunity(tenantId, sourceUrl, title) {
  const opportunityId = createHash("sha256").update(`${tenantId}\n${sourceUrl}`, "utf8").digest("hex");
  return {
    tenantId, opportunityId, sourceUrl, title,
    goalRef: `intent-entry://${tenantId}/${opportunityId}`,
    jobId: `goal:${opportunityId}`,
  };
}

async function createOpportunity(client, value) {
  await client.query(`
    SELECT * FROM public.create_lm_money_opportunity($1,$2,$3,$4,$5,$6,$7,$8,$9)
  `, [
    value.tenantId, value.opportunityId, value.sourceUrl, value.title,
    "Research and complete feasible bounded work.", "10000", "USD",
    "2026-08-30T00:00:00.000Z", value.goalRef,
  ]);
}

async function expectReject(action, pattern) {
  try {
    await action();
  } catch (error) {
    if (pattern.test(String(error.message || error))) return;
    throw error;
  }
  throw new Error(`expected rejection ${pattern}`);
}

async function main() {
  const source = process.env.LM_RUNTIME_DATABASE_URL;
  if (!source) throw new Error("LM_RUNTIME_DATABASE_URL is required");
  const database = `webmcp_r09_${Date.now()}`;
  const admin = new Client({ connectionString: source });
  let primary;
  let contender;
  await admin.connect();
  try {
    await admin.query(`CREATE DATABASE ${database}`);
    const isolated = databaseUrl(source, database);
    primary = new Client({ connectionString: isolated });
    contender = new Client({ connectionString: isolated });
    await Promise.all([primary.connect(), contender.connect()]);
    await primary.query("CREATE EXTENSION IF NOT EXISTS pgcrypto");
    for (const item of MIGRATIONS) await primary.query(migration(item));

    const tenant = "tenant-a";
    const completed = opportunity(tenant, "https://public.example/symphony-completed", "Completed work");
    await createOpportunity(primary, completed);

    const claims = await Promise.all([
      primary.query("SELECT * FROM public.claim_lm_symphony_job($1)", [tenant]),
      contender.query("SELECT * FROM public.claim_lm_symphony_job($1)", [tenant]),
    ]);
    const claimedRows = claims.flatMap((result) => result.rows);
    if (claimedRows.length !== 1) throw new Error(`claim winner count ${claimedRows.length}`);
    const first = claimedRows[0];
    if (first.job_id !== completed.jobId || first.round !== 1 || first.status !== "claimed") {
      throw new Error("first claim readback mismatch");
    }
    if ((await primary.query("SELECT * FROM public.claim_lm_symphony_job($1)", ["tenant-b"])).rowCount !== 0) {
      throw new Error("cross-tenant claim succeeded");
    }

    const issue1 = "github-issue://Daisuke134/life-manager-workrooms/1";
    const mirrored1 = await primary.query("SELECT * FROM public.record_lm_symphony_issue($1,$2,$3)", [tenant, first.dispatch_id, issue1]);
    const mirroredReplay = await primary.query("SELECT * FROM public.record_lm_symphony_issue($1,$2,$3)", [tenant, first.dispatch_id, issue1]);
    if (mirrored1.rows[0].issue_ref !== issue1 || mirroredReplay.rows[0].issue_ref !== issue1) {
      throw new Error("issue idempotency failed");
    }
    await expectReject(
      () => primary.query("SELECT * FROM public.record_lm_symphony_issue($1,$2,$3)", [tenant, first.dispatch_id, "github-issue://Daisuke134/life-manager-workrooms/9"]),
      /symphony issue conflict/i,
    );

    const completedPayload = {
      protocol: "LM_RESULT_V1", tenant_id: tenant, dispatch_id: first.dispatch_id,
      job_id: first.job_id, status: "completed", execution_id: "codex-completed-1",
      artifact_refs: ["artifact://tenant-a/completed-1"],
    };
    const completedHash = createHash("sha256").update(JSON.stringify(completedPayload), "utf8").digest("hex");
    const resultRef1 = "github-comment://Daisuke134/life-manager-workrooms/1/2";
    const result1 = await primary.query("SELECT * FROM public.record_lm_symphony_result($1,$2,$3,$4,$5::jsonb)", [tenant, first.dispatch_id, resultRef1, completedHash, completedPayload]);
    const resultReplay = await primary.query("SELECT * FROM public.record_lm_symphony_result($1,$2,$3,$4,$5::jsonb)", [tenant, first.dispatch_id, resultRef1, completedHash, completedPayload]);
    if (result1.rows[0].status !== "result_ready" || resultReplay.rows[0].result_hash !== completedHash) {
      throw new Error("result idempotency failed");
    }
    const consumed = await primary.query("SELECT * FROM public.consume_lm_symphony_completed($1,$2)", [tenant, first.dispatch_id]);
    if (consumed.rows[0].status !== "consumed") throw new Error("completed dispatch not consumed");
    const completedState = await primary.query(`
      SELECT jobs.status AS job_status, jobs.attempt, opportunities.status AS opportunity_status,
        (SELECT count(*)::int FROM public.lm_runtime_job_receipts WHERE job_id = jobs.job_id) AS receipts
      FROM public.lm_runtime_jobs jobs
      JOIN public.lm_money_opportunities opportunities
        ON opportunities.uid = jobs.tenant_id AND jobs.job_id = 'goal:' || opportunities.opportunity_id
      WHERE jobs.tenant_id=$1 AND jobs.job_id=$2
    `, [tenant, first.job_id]);
    if (JSON.stringify(completedState.rows[0]) !== JSON.stringify({ job_status: "completed", attempt: 1, opportunity_status: "QUALIFIED", receipts: 1 })) {
      throw new Error(`completed state mismatch ${JSON.stringify(completedState.rows[0])}`);
    }
    await expectReject(
      () => primary.query("UPDATE public.lm_runtime_job_receipts SET receipt='{}'::jsonb WHERE job_id=$1", [first.job_id]),
      /immutable/i,
    );

    const human = opportunity(tenant, "https://public.example/symphony-human", "Human boundary work");
    await createOpportunity(primary, human);
    const second = (await primary.query("SELECT * FROM public.claim_lm_symphony_job($1)", [tenant])).rows[0];
    await primary.query("SELECT * FROM public.record_lm_symphony_issue($1,$2,$3)", [tenant, second.dispatch_id, "github-issue://Daisuke134/life-manager-workrooms/3"]);
    const humanPayload = {
      protocol: "LM_RESULT_V1", tenant_id: tenant, dispatch_id: second.dispatch_id,
      job_id: second.job_id, status: "needs_human", execution_id: "codex-human-1",
      artifact_refs: ["artifact://tenant-a/prepared-application"],
      reason_code: "provider_interview", question: "Complete the provider interview.",
      required_format: { type: "confirmation" },
    };
    const humanHash = createHash("sha256").update(JSON.stringify(humanPayload), "utf8").digest("hex");
    await primary.query("SELECT * FROM public.record_lm_symphony_result($1,$2,$3,$4,$5::jsonb)", [tenant, second.dispatch_id, "github-comment://Daisuke134/life-manager-workrooms/3/4", humanHash, humanPayload]);
    const task = (await primary.query("SELECT * FROM public.consume_lm_symphony_human_task($1,$2)", [tenant, second.dispatch_id])).rows[0];
    if (task.status !== "open" || task.job_id !== second.job_id) throw new Error("human task missing");
    const waiting = (await primary.query("SELECT status,attempt FROM public.lm_runtime_jobs WHERE tenant_id=$1 AND job_id=$2", [tenant, second.job_id])).rows[0];
    if (waiting.status !== "waiting_human" || waiting.attempt !== 0) throw new Error("human wait state mismatch");
    await primary.query("SELECT * FROM public.answer_lm_human_task($1,$2,$3,$4)", [tenant, task.task_id, task.version, "vault-answer://tenant-a/interview-complete"]);
    const nextRound = (await primary.query("SELECT * FROM public.claim_lm_symphony_job($1)", [tenant])).rows[0];
    if (nextRound.job_id !== second.job_id || nextRound.round !== 2) throw new Error("same-job next round mismatch");

    console.log(JSON.stringify({
      status: "pass", claim_winners: 1, cross_tenant_claims: 0,
      issue_replay_duplicates: 0, result_replay_duplicates: 0,
      completed_receipts: 1, receipt_mutation: "rejected",
      human_task_status: "answered", same_job_round: 2,
    }));
  } finally {
    await Promise.allSettled([primary?.end(), contender?.end()]);
    await admin.query("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=$1", [database]).catch(() => {});
    await admin.query(`DROP DATABASE IF EXISTS ${database}`).catch(() => {});
    await admin.end();
  }
}

main().catch((error) => {
  console.error(error.stack || error.message || error);
  process.exit(1);
});
