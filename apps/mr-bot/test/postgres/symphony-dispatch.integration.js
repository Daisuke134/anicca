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
  ["CLOSE_RECOVERY_MIGRATION_B64", "migrations/2026-08-31-lm-symphony-close-recovery.sql"],
  ["SYMPHONY_CAPACITY_MIGRATION_B64", "migrations/2026-08-31-lm-symphony-capacity-fairness.sql"],
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

function insertRacePair(tenantId) {
  for (let index = 0; index < 256; index += 1) {
    const left = opportunity(tenantId, `https://public.example/symphony-insert-race-a-${index}`, "Insert race A");
    const right = opportunity(tenantId, `https://public.example/symphony-insert-race-b-${index}`, "Insert race B");
    if (left.opportunityId !== right.opportunityId) {
      return left.opportunityId < right.opportunityId
        ? { low: left, high: right }
        : { low: right, high: left };
    }
  }
  throw new Error("could not generate ordered insert-race opportunity IDs");
}

function stableJson(value) {
  if (Array.isArray(value)) return `[${value.map(stableJson).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableJson(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

async function concurrentClaimRows(clients, tenantId) {
  let committed = false;
  try {
    await Promise.all(clients.map((client) => client.query("BEGIN")));
    const results = await Promise.all(clients.map((client) => (
      client.query("SELECT * FROM public.claim_lm_symphony_job($1)", [tenantId])
    )));
    await Promise.all(clients.map((client) => client.query("COMMIT")));
    committed = true;
    return results.flatMap((result) => result.rows);
  } finally {
    if (!committed) await Promise.allSettled(clients.map((client) => client.query("ROLLBACK")));
  }
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

async function createRuntimeJob(client, { tenantId, jobId, inputRefs = {}, maxAttempts = 3 }) {
  await client.query(`
    INSERT INTO public.lm_runtime_jobs (
      job_id, tenant_id, loop_id, capability, effect_class, effect_key,
      input_refs, max_attempts, status, available_at
    ) VALUES ($1, $2, 'mr-bot.manager', 'general-agent.work', 'none', NULL,
      $3::jsonb, $4, 'queued', clock_timestamp())
  `, [jobId, tenantId, JSON.stringify(inputRefs), maxAttempts]);
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
  let thirdContender;
  await admin.connect();
  try {
    await admin.query(`CREATE DATABASE ${database}`);
    const isolated = databaseUrl(source, database);
    primary = new Client({ connectionString: isolated });
    contender = new Client({ connectionString: isolated });
    thirdContender = new Client({ connectionString: isolated });
    await Promise.all([primary.connect(), contender.connect(), thirdContender.connect()]);
    await primary.query("CREATE EXTENSION IF NOT EXISTS pgcrypto");
    for (const item of MIGRATIONS) await primary.query(migration(item));

    const tenant = "tenant-a";
    const hostedJobId = "hosted-non-money-job";
    await createRuntimeJob(primary, { tenantId: tenant, jobId: hostedJobId });
    const completed = opportunity(tenant, "https://public.example/symphony-completed", "Completed work");
    await createOpportunity(primary, completed);

    const claimedRows = await concurrentClaimRows([primary, contender], tenant);
    if (claimedRows.length !== 1) throw new Error(`claim winner count ${claimedRows.length}`);
    const first = claimedRows[0];
    if (first.job_id !== completed.jobId || first.round !== 1 || first.status !== "claimed") {
      throw new Error("first claim readback mismatch");
    }
    const recovered = await primary.query("SELECT * FROM public.claim_lm_symphony_job($1)", [tenant]);
    if (recovered.rowCount !== 1 || recovered.rows[0].dispatch_id !== first.dispatch_id
      || recovered.rows[0].job_id !== first.job_id || recovered.rows[0].round !== first.round
      || recovered.rows[0].status !== "claimed") {
      throw new Error("claimed dispatch recovery mismatch");
    }
    const recoveryState = (await primary.query(`
      SELECT jobs.status AS job_status,
        (SELECT count(*)::int FROM public.lm_symphony_dispatches
         WHERE tenant_id=$1 AND job_id=$2) AS dispatch_count
      FROM public.lm_runtime_jobs jobs
      WHERE jobs.tenant_id=$1 AND jobs.job_id=$2
    `, [tenant, first.job_id])).rows[0];
    if (JSON.stringify(recoveryState) !== JSON.stringify({ job_status: "waiting_agent", dispatch_count: 1 })) {
      throw new Error(`claimed dispatch recovery state mismatch ${JSON.stringify(recoveryState)}`);
    }
    const hostedState = (await primary.query(
      "SELECT status FROM public.lm_runtime_jobs WHERE tenant_id=$1 AND job_id=$2",
      [tenant, hostedJobId],
    )).rows[0];
    if (!hostedState || hostedState.status !== "queued") throw new Error("non-money job was claimed");
    if ((await primary.query("SELECT * FROM public.claim_lm_symphony_job($1)", ["tenant-b"])).rowCount !== 0) {
      throw new Error("cross-tenant claim succeeded");
    }

    const raceTenant = "tenant-race";
    const raceOpportunity = opportunity(raceTenant, "https://public.example/symphony-race", "Race work");
    await createOpportunity(primary, raceOpportunity);
    const raceClaims = await Promise.all([
      primary.query("SELECT * FROM public.claim_lm_symphony_job($1)", [raceTenant]),
      contender.query("SELECT * FROM public.claim_lm_runtime_jobs($1,$2,$3)", [
        "runtime-race", ["general-agent.work"], raceTenant,
      ]),
    ]);
    const raceSymphonyRows = raceClaims[0].rows;
    const raceRuntimeRows = raceClaims[1].rows;
    if (raceSymphonyRows.length + raceRuntimeRows.length !== 1) {
      throw new Error("claim race winner count " + (raceSymphonyRows.length + raceRuntimeRows.length));
    }
    const raceState = (await primary.query(
      "SELECT status FROM public.lm_runtime_jobs WHERE tenant_id=$1 AND job_id=$2",
      [raceTenant, raceOpportunity.jobId],
    )).rows[0];
    const raceDispatches = (await primary.query(
      "SELECT status FROM public.lm_symphony_dispatches WHERE tenant_id=$1 AND job_id=$2",
      [raceTenant, raceOpportunity.jobId],
    )).rows;
    if (raceSymphonyRows.length === 1) {
      if (raceState.status !== "waiting_agent" || raceDispatches.length !== 1) {
        throw new Error("Symphony/runtime claim race double state");
      }
    } else if (raceState.status !== "running" || raceDispatches.length !== 0) {
      throw new Error("runtime claim race double state");
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

    const human = opportunity(tenant, "https://public.example/symphony-human", "Human boundary work");
    await createOpportunity(primary, human);
    const second = (await primary.query("SELECT * FROM public.claim_lm_symphony_job($1)", [tenant])).rows[0];
    if (!second || second.dispatch_id === first.dispatch_id || second.job_id !== human.jobId
      || second.round !== 1 || second.status !== "claimed") {
      throw new Error("queued Money Printer claim after mirrored mismatch");
    }

    const completedPayload = {
      protocol: "LM_RESULT_V1", tenant_id: tenant, dispatch_id: first.dispatch_id,
      job_id: first.job_id, status: "completed", execution_id: "codex-completed-1",
      artifact_refs: ["artifact://tenant-a/completed-1"],
    };
    const completedHash = createHash("sha256").update(JSON.stringify(completedPayload), "utf8").digest("hex");
    const resultRef1 = "github-comment://Daisuke134/life-manager-workrooms/1/2";
    const result1 = await primary.query("SELECT * FROM public.record_lm_symphony_result($1,$2,$3,$4,$5::jsonb)", [tenant, first.dispatch_id, resultRef1, completedHash, completedPayload]);
    await expectReject(
      () => primary.query(
        "SELECT * FROM public.record_lm_symphony_result($1,$2,$3,$4,$5::jsonb)",
        [tenant, first.dispatch_id, resultRef1, "f".repeat(64), completedPayload],
      ),
      /symphony result conflict/i,
    );
    await expectReject(
      () => primary.query(
        "SELECT * FROM public.record_lm_symphony_result($1,$2,$3,$4,$5::jsonb)",
        [tenant, first.dispatch_id, resultRef1, completedHash, { ...completedPayload, execution_id: "codex-completed-2" }],
      ),
      /symphony result conflict/i,
    );
    const resultReplay = await primary.query("SELECT * FROM public.record_lm_symphony_result($1,$2,$3,$4,$5::jsonb)", [tenant, first.dispatch_id, resultRef1, completedHash, completedPayload]);
    if (result1.rows[0].status !== "result_ready" || resultReplay.rows[0].result_hash !== completedHash) {
      throw new Error("result idempotency failed");
    }
    const consumed = await primary.query("SELECT * FROM public.consume_lm_symphony_completed($1,$2)", [tenant, first.dispatch_id]);
    if (consumed.rows[0].status !== "consumed") throw new Error("completed dispatch not consumed");
    const completedResultReplayAfterConsume = await primary.query(
      "SELECT * FROM public.record_lm_symphony_result($1,$2,$3,$4,$5::jsonb)",
      [tenant, first.dispatch_id, resultRef1, completedHash, completedPayload],
    );
    if (completedResultReplayAfterConsume.rowCount !== 1
      || completedResultReplayAfterConsume.rows[0].status !== "consumed"
      || completedResultReplayAfterConsume.rows[0].result_ref !== resultRef1
      || completedResultReplayAfterConsume.rows[0].result_hash !== completedHash
      || stableJson(completedResultReplayAfterConsume.rows[0].result_payload) !== stableJson(completedPayload)) {
      throw new Error(`consumed result replay readback mismatch ${JSON.stringify(completedResultReplayAfterConsume.rows[0])}`);
    }
    const consumedRecovery = (await primary.query(
      "SELECT * FROM public.claim_lm_symphony_job($1)", [tenant],
    )).rows[0];
    if (!consumedRecovery || consumedRecovery.dispatch_id !== first.dispatch_id
      || consumedRecovery.status !== "consumed") {
      throw new Error("unclosed consumed dispatch recovery mismatch");
    }
    const closedFirst = (await primary.query(
      "SELECT * FROM public.ack_lm_symphony_issue_closed($1,$2,$3,$4,$5)",
      [tenant, first.dispatch_id, issue1, resultRef1, completedHash],
    )).rows[0];
    if (!closedFirst || closedFirst.status !== "consumed" || !closedFirst.issue_closed_at) {
      throw new Error("completed dispatch close ack mismatch");
    }
    await expectReject(
      () => primary.query("SELECT * FROM public.consume_lm_symphony_completed($1,$2)", [tenant, first.dispatch_id]),
      /symphony completion conflict/i,
    );
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
    const foreignIssue = await primary.query(
      "SELECT * FROM public.record_lm_symphony_issue($1,$2,$3)",
      ["tenant-b", first.dispatch_id, issue1],
    );
    const foreignPayload = { ...completedPayload, tenant_id: "tenant-b" };
    const foreignResult = await primary.query(
      "SELECT * FROM public.record_lm_symphony_result($1,$2,$3,$4,$5::jsonb)",
      ["tenant-b", first.dispatch_id, resultRef1, "a".repeat(64), foreignPayload],
    );
    const foreignConsume = await primary.query(
      "SELECT * FROM public.consume_lm_symphony_completed($1,$2)",
      ["tenant-b", first.dispatch_id],
    );
    if (foreignIssue.rowCount !== 0 || foreignResult.rowCount !== 0 || foreignConsume.rowCount !== 0) {
      throw new Error("foreign tenant mutated Symphony dispatch");
    }
    const unchanged = (await primary.query(
      "SELECT status, issue_ref, result_ref, result_hash FROM public.lm_symphony_dispatches WHERE tenant_id=$1 AND dispatch_id=$2",
      [tenant, first.dispatch_id],
    )).rows[0];
    if (
      unchanged.status !== "consumed"
      || unchanged.issue_ref !== issue1
      || unchanged.result_ref !== resultRef1
      || unchanged.result_hash !== completedHash
    ) throw new Error("foreign tenant changed Symphony dispatch");
    await expectReject(
      () => primary.query("UPDATE public.lm_runtime_job_receipts SET receipt='{}'::jsonb WHERE job_id=$1", [first.job_id]),
      /immutable/i,
    );

    const capacityTenant = "tenant-capacity";
    const capacityFirst = opportunity(capacityTenant, "https://public.example/symphony-capacity-first", "Capacity first");
    const capacitySecond = opportunity(capacityTenant, "https://public.example/symphony-capacity-second", "Capacity second");
    const capacityThird = opportunity(capacityTenant, "https://public.example/symphony-capacity-third", "Capacity third");
    await createOpportunity(primary, capacityFirst);
    await createOpportunity(primary, capacitySecond);
    await createOpportunity(primary, capacityThird);
    const capacityInitialRows = await concurrentClaimRows(
      [primary, contender, thirdContender], capacityTenant,
    );
    if (capacityInitialRows.length !== 1
      || new Set(capacityInitialRows.map((row) => row.dispatch_id)).size !== 1
      || capacityInitialRows[0].status !== "claimed") {
      throw new Error(`capacity concurrent claim winner count ${capacityInitialRows.length}`);
    }
    const capacityFirstDispatch = capacityInitialRows[0];
    const capacityInitialState = (await primary.query(`
      SELECT
        (SELECT count(*)::int FROM public.lm_symphony_dispatches WHERE tenant_id=$1) AS dispatch_count,
        (SELECT count(*)::int FROM public.lm_runtime_jobs WHERE tenant_id=$1 AND status='queued') AS queued_count
    `, [capacityTenant])).rows[0];
    if (JSON.stringify(capacityInitialState) !== JSON.stringify({ dispatch_count: 1, queued_count: 2 })) {
      throw new Error(`capacity initial state mismatch ${JSON.stringify(capacityInitialState)}`);
    }
    const capacityRecoveryRows = await concurrentClaimRows(
      [primary, contender, thirdContender], capacityTenant,
    );
    if (capacityRecoveryRows.length !== 1
      || capacityRecoveryRows[0].dispatch_id !== capacityFirstDispatch.dispatch_id) {
      throw new Error(`capacity claimed recovery count ${capacityRecoveryRows.length}`);
    }
    const capacityIssue1 = "github-issue://Daisuke134/life-manager-workrooms/11";
    const capacityMirrored1 = (await primary.query(
      "SELECT * FROM public.record_lm_symphony_issue($1,$2,$3)",
      [capacityTenant, capacityFirstDispatch.dispatch_id, capacityIssue1],
    )).rows[0];
    if (!capacityMirrored1 || capacityMirrored1.status !== "mirrored") {
      throw new Error("capacity first mirror mismatch");
    }
    const capacitySecondDispatch = (await primary.query(
      "SELECT * FROM public.claim_lm_symphony_job($1)", [capacityTenant],
    )).rows[0];
    if (!capacitySecondDispatch || capacitySecondDispatch.job_id !== capacitySecond.jobId
      || capacitySecondDispatch.dispatch_id === capacityFirstDispatch.dispatch_id
      || capacitySecondDispatch.status !== "claimed") {
      throw new Error("queued job was not claimed below capacity");
    }
    const capacityIssue2 = "github-issue://Daisuke134/life-manager-workrooms/12";
    const capacityMirrored2 = (await primary.query(
      "SELECT * FROM public.record_lm_symphony_issue($1,$2,$3)",
      [capacityTenant, capacitySecondDispatch.dispatch_id, capacityIssue2],
    )).rows[0];
    if (!capacityMirrored2 || capacityMirrored2.status !== "mirrored") {
      throw new Error("capacity second mirror mismatch");
    }
    const capacityMirroredRows = await concurrentClaimRows(
      [primary, contender, thirdContender], capacityTenant,
    );
    if (capacityMirroredRows.length !== 1
      || capacityMirroredRows[0].status !== "mirrored"
      || !capacityMirroredRows[0].last_polled_at) {
      throw new Error(`mirrored concurrent poll count ${capacityMirroredRows.length}`);
    }
    const capacityOtherPoll = (await primary.query(
      "SELECT * FROM public.claim_lm_symphony_job($1)", [capacityTenant],
    )).rows[0];
    if (!capacityOtherPoll || capacityOtherPoll.status !== "mirrored"
      || capacityOtherPoll.dispatch_id === capacityMirroredRows[0].dispatch_id
      || !capacityOtherPoll.last_polled_at) {
      throw new Error("mirrored sequential poll did not return the other dispatch");
    }
    const capacityAtLimit = (await primary.query(
      "SELECT * FROM public.claim_lm_symphony_job($1)", [capacityTenant],
    )).rows[0];
    if (!capacityAtLimit || capacityAtLimit.job_id === capacityThird.jobId) {
      throw new Error("third queued job bypassed open dispatch capacity");
    }
    const capacityState = (await primary.query(`
      SELECT
        (SELECT count(*)::int FROM public.lm_symphony_dispatches
         WHERE tenant_id=$1 AND status IN ('claimed','mirrored','result_ready','consumed')
           AND issue_closed_at IS NULL) AS open_count,
        (SELECT status FROM public.lm_runtime_jobs WHERE tenant_id=$1 AND job_id=$2) AS third_job_status,
        (SELECT count(*)::int FROM public.lm_symphony_dispatches
         WHERE tenant_id=$1 AND job_id=$2) AS third_dispatch_count
    `, [capacityTenant, capacityThird.jobId])).rows[0];
    if (JSON.stringify(capacityState) !== JSON.stringify({
      open_count: 2, third_job_status: "queued", third_dispatch_count: 0,
    })) {
      throw new Error(`capacity state mismatch ${JSON.stringify(capacityState)}`);
    }

    const insertRaceTenant = "tenant-insert-race";
    const insertRace = insertRacePair(insertRaceTenant);
    await createOpportunity(primary, insertRace.high);
    await primary.query("BEGIN");
    try {
      const firstInsertClaim = (await primary.query(
        "SELECT * FROM public.claim_lm_symphony_job($1)", [insertRaceTenant],
      )).rows[0];
      if (!firstInsertClaim || firstInsertClaim.job_id !== insertRace.high.jobId) {
        throw new Error("insert-race high opportunity was not first claim");
      }
      await createOpportunity(contender, insertRace.low);
      const blockedInsertClaim = await contender.query(
        "SELECT * FROM public.claim_lm_symphony_job($1)", [insertRaceTenant],
      );
      if (blockedInsertClaim.rowCount !== 0) {
        throw new Error(`insert-race claim bypassed tenant mutex: ${blockedInsertClaim.rowCount}`);
      }
    } finally {
      await primary.query("COMMIT");
    }
    const resumedInsertClaim = (await contender.query(
      "SELECT * FROM public.claim_lm_symphony_job($1)", [insertRaceTenant],
    )).rows[0];
    if (!resumedInsertClaim || resumedInsertClaim.dispatch_id === undefined
      || resumedInsertClaim.job_id !== insertRace.high.jobId
      || resumedInsertClaim.status !== "claimed") {
      throw new Error("insert-race recovery mismatch");
    }
    const insertRaceState = (await primary.query(`
      SELECT
        (SELECT count(*)::int FROM public.lm_symphony_dispatches WHERE tenant_id=$1) AS dispatch_count,
        (SELECT status FROM public.lm_runtime_jobs WHERE tenant_id=$1 AND job_id=$2) AS low_job_status,
        (SELECT count(*)::int FROM public.lm_symphony_dispatches WHERE tenant_id=$1 AND job_id=$2) AS low_dispatch_count
    `, [insertRaceTenant, insertRace.low.jobId])).rows[0];
    if (JSON.stringify(insertRaceState) !== JSON.stringify({
      dispatch_count: 1, low_job_status: "queued", low_dispatch_count: 0,
    })) {
      throw new Error(`insert-race state mismatch ${JSON.stringify(insertRaceState)}`);
    }

    const humanIssue = "github-issue://Daisuke134/life-manager-workrooms/3";
    await primary.query("SELECT * FROM public.record_lm_symphony_issue($1,$2,$3)", [tenant, second.dispatch_id, humanIssue]);
    const humanPayload = {
      protocol: "LM_RESULT_V1", tenant_id: tenant, dispatch_id: second.dispatch_id,
      job_id: second.job_id, status: "needs_human", execution_id: "codex-human-1",
      artifact_refs: ["artifact://tenant-a/prepared-application"],
      reason_code: "provider_interview", question: "Complete the provider interview.",
      required_format: { type: "confirmation" },
    };
    const humanHash = createHash("sha256").update(JSON.stringify(humanPayload), "utf8").digest("hex");
    const humanResultRef = "github-comment://Daisuke134/life-manager-workrooms/3/4";
    await primary.query("SELECT * FROM public.record_lm_symphony_result($1,$2,$3,$4,$5::jsonb)", [tenant, second.dispatch_id, humanResultRef, humanHash, humanPayload]);
    const task = (await primary.query("SELECT * FROM public.consume_lm_symphony_human_task($1,$2)", [tenant, second.dispatch_id])).rows[0];
    if (task.status !== "open" || task.job_id !== second.job_id) throw new Error("human task missing");
    const waiting = (await primary.query("SELECT status,attempt FROM public.lm_runtime_jobs WHERE tenant_id=$1 AND job_id=$2", [tenant, second.job_id])).rows[0];
    if (waiting.status !== "waiting_human" || waiting.attempt !== 0) throw new Error("human wait state mismatch");
    const closedHuman = (await primary.query(
      "SELECT * FROM public.ack_lm_symphony_issue_closed($1,$2,$3,$4,$5)",
      [tenant, second.dispatch_id, humanIssue, humanResultRef, humanHash],
    )).rows[0];
    if (!closedHuman || closedHuman.status !== "consumed" || !closedHuman.issue_closed_at) {
      throw new Error("human dispatch close ack mismatch");
    }
    await primary.query("SELECT * FROM public.answer_lm_human_task($1,$2,$3,$4)", [tenant, task.task_id, task.version, "vault-answer://tenant-a/interview-complete"]);
    const nextRound = (await primary.query("SELECT * FROM public.claim_lm_symphony_job($1)", [tenant])).rows[0];
    if (nextRound.job_id !== second.job_id || nextRound.round !== 2) throw new Error("same-job next round mismatch");
    const humanReplayBefore = (await primary.query(`
      SELECT jobs.status AS job_status, jobs.attempt,
        (SELECT count(*)::int FROM public.lm_symphony_dispatches
         WHERE tenant_id=$1 AND job_id=$2) AS dispatch_count,
        (SELECT count(*)::int FROM public.lm_human_tasks
         WHERE uid=$1 AND job_id=$2) AS task_count
      FROM public.lm_runtime_jobs jobs
      WHERE jobs.tenant_id=$1 AND jobs.job_id=$2
    `, [tenant, second.job_id])).rows[0];
    const humanResultReplay = await primary.query(
      "SELECT * FROM public.record_lm_symphony_result($1,$2,$3,$4,$5::jsonb)",
      [tenant, second.dispatch_id, humanResultRef, humanHash, humanPayload],
    );
    if (humanResultReplay.rowCount !== 1 || humanResultReplay.rows[0].status !== "consumed"
      || humanResultReplay.rows[0].result_hash !== humanHash
      || stableJson(humanResultReplay.rows[0].result_payload) !== stableJson(humanPayload)) {
      throw new Error("old human result replay readback mismatch");
    }
    const humanReplayAfter = (await primary.query(`
      SELECT jobs.status AS job_status, jobs.attempt,
        (SELECT count(*)::int FROM public.lm_symphony_dispatches
         WHERE tenant_id=$1 AND job_id=$2) AS dispatch_count,
        (SELECT count(*)::int FROM public.lm_human_tasks
         WHERE uid=$1 AND job_id=$2) AS task_count
      FROM public.lm_runtime_jobs jobs
      WHERE jobs.tenant_id=$1 AND jobs.job_id=$2
    `, [tenant, second.job_id])).rows[0];
    if (JSON.stringify(humanReplayAfter) !== JSON.stringify(humanReplayBefore)) {
      throw new Error(`old human result replay mutated state ${JSON.stringify({ before: humanReplayBefore, after: humanReplayAfter })}`);
    }
    const humanRounds = (await primary.query(
      "SELECT round, status FROM public.lm_symphony_dispatches WHERE tenant_id=$1 AND job_id=$2 ORDER BY round",
      [tenant, second.job_id],
    )).rows;
    const humanJob = (await primary.query(
      "SELECT status, attempt FROM public.lm_runtime_jobs WHERE tenant_id=$1 AND job_id=$2",
      [tenant, second.job_id],
    )).rows[0];
    if (
      humanRounds.length !== 2
      || humanRounds[0].round !== 1 || humanRounds[0].status !== "consumed"
      || humanRounds[1].round !== 2 || humanRounds[1].status !== "claimed"
      || humanJob.status !== "waiting_agent" || humanJob.attempt !== 0
    ) throw new Error("same-job human resume state changed");

    console.log(JSON.stringify({
      status: "pass", claim_winners: 1, cross_tenant_claims: 0,
      non_money_claims: 0, claim_race_winners: 1, foreign_mutations: 0,
      issue_replay_duplicates: 0, result_replay_duplicates: 0,
      completed_receipts: 1, receipt_mutation: "rejected", consume_replay: "rejected",
      old_result_replay: "consumed_readback",
      capacity_open_count: capacityState.open_count, capacity_third_job: capacityState.third_job_status,
      mirrored_fair_poll_distinct: 2,
      human_task_status: "answered", same_job_round: 2,
    }));
  } finally {
    await Promise.allSettled([primary?.end(), contender?.end(), thirdContender?.end()]);
    await admin.query("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=$1", [database]).catch(() => {});
    await admin.query(`DROP DATABASE IF EXISTS ${database}`).catch(() => {});
    await admin.end();
  }
}

main().catch((error) => {
  console.error(error.stack || error.message || error);
  process.exit(1);
});
