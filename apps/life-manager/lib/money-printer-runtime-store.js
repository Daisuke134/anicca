"use strict";

const { canonicalOpportunityInput } = require("./money-printer-opportunity.js");

const TENANT_ID = /^[a-z0-9][a-z0-9._-]{0,199}$/;
const OPPORTUNITY_ID = /^[0-9a-f]{64}$/;
const JOB_ID = /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}$/;
const GITHUB_ISSUE_REF = /^github-issue:\/\/Daisuke134\/life-manager-workrooms\/[1-9][0-9]*$/;

function unavailable() { throw new Error("money printer runtime store unavailable"); }

function tenant(value) {
  const uid = String(value && typeof value === "object" ? value.uid : value == null ? "" : value).trim();
  if (!TENANT_ID.test(uid)) throw new Error("money printer runtime store tenant invalid");
  return uid;
}

function oneRow(result, label, uid) {
  const rows = result && Array.isArray(result.rows) ? result.rows : [];
  if (rows.length !== 1 || !rows[0] || typeof rows[0] !== "object" || Array.isArray(rows[0])) {
    throw new Error(`money printer runtime store ${label} readback invalid`);
  }
  const rowUid = rows[0].uid == null ? rows[0].tenant_id : rows[0].uid;
  if (String(rowUid || "") !== uid) throw new Error(`money printer runtime store ${label} readback invalid`);
  return rows[0];
}

function scopedRows(result, uid, label) {
  const rows = result && Array.isArray(result.rows) ? result.rows : [];
  if (rows.some((row) => !row || typeof row !== "object" || Array.isArray(row)
    || String((row.uid == null ? row.tenant_id : row.uid) || "") !== uid)) {
    throw new Error(`money printer runtime store ${label} readback invalid`);
  }
  return rows;
}

function claimedSymphonyDispatch(result, uid) {
  const rows = result && Array.isArray(result.rows) ? result.rows : [];
  if (rows.length === 0) return null;
  if (rows.length !== 1) throw new Error("money printer runtime store Symphony claim readback invalid");
  const row = rows[0];
  if (!row || typeof row !== "object" || Array.isArray(row)
    || row.tenant_id !== uid || !OPPORTUNITY_ID.test(String(row.dispatch_id || ""))
    || !JOB_ID.test(String(row.job_id || "")) || !Number.isInteger(row.round) || row.round < 1
    || row.status !== "claimed" || row.issue_ref != null || row.result_ref != null
    || row.result_hash != null || row.result_payload != null || row.failure_code != null) {
    throw new Error("money printer runtime store Symphony claim readback invalid");
  }
  return row;
}

function mirroredSymphonyDispatch(result, expected) {
  const rows = result && Array.isArray(result.rows) ? result.rows : [];
  const row = rows.length === 1 ? rows[0] : null;
  if (!row || rows.length !== 1 || typeof row !== "object" || Array.isArray(row)
    || row.tenant_id !== expected.uid || row.dispatch_id !== expected.dispatchId
    || !JOB_ID.test(String(row.job_id || "")) || !Number.isInteger(row.round) || row.round < 1
    || row.status !== "mirrored" || row.issue_ref !== expected.issueRef
    || row.result_ref != null || row.result_hash != null || row.result_payload != null
    || row.failure_code != null) {
    throw new Error("money printer runtime store Symphony issue readback invalid");
  }
  return row;
}

function expectedOpportunity(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("money printer runtime store opportunity expected invalid");
  }
  const uid = tenant(value.uid == null ? value.tenant_id : value.uid);
  if (value.uid != null && value.tenant_id != null && String(value.tenant_id).trim() !== uid) {
    throw new Error("money printer runtime store opportunity expected invalid");
  }
  const opportunityId = String(value.opportunity_id || "").trim();
  const goalRef = String(value.goal_ref || "").trim();
  if (!OPPORTUNITY_ID.test(opportunityId) || goalRef !== `intent-entry://${uid}/${opportunityId}`) {
    throw new Error("money printer runtime store opportunity expected invalid");
  }
  return Object.freeze({ uid, opportunityId, goalRef });
}

function expectedOpportunitySource(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("money printer runtime store opportunity source expected invalid");
  }
  const uid = tenant(value.uid == null ? value.tenant_id : value.uid);
  if (value.uid != null && value.tenant_id != null && String(value.tenant_id).trim() !== uid) {
    throw new Error("money printer runtime store opportunity source expected invalid");
  }
  const sourceUrl = String(value.source_url == null ? "" : value.source_url).trim();
  const canonical = canonicalOpportunityInput({
    tenantId: uid,
    sourceUrl,
    title: "source lookup",
    goalStatement: "source lookup",
    valueMinor: "0",
    currency: "USD",
    observedAt: "2026-01-01T00:00:00.000Z",
  });
  return Object.freeze({ uid, sourceUrl: canonical.source_url });
}

function expectedHumanJob(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("money printer runtime store human job expected invalid");
  }
  const uid = tenant(value.uid == null ? value.tenant_id : value.uid);
  const jobId = String(value.job_id || "").trim();
  if (!JOB_ID.test(jobId)) throw new Error("money printer runtime store human job expected invalid");
  return Object.freeze({ uid, jobId });
}

function opportunityRow(result, expected, label) {
  const row = oneRow(result, label, expected.uid);
  if (
    String(row.opportunity_id || "") !== expected.opportunityId
    || String(row.goal_ref || "") !== expected.goalRef
  ) throw new Error(`money printer runtime store ${label} readback invalid`);
  return row;
}

function normalizeOpportunityReadback(row) {
  if (row.observed_at instanceof Date) {
    if (!Number.isFinite(row.observed_at.getTime())) throw new Error("money printer runtime store opportunity readback invalid");
    return { ...row, observed_at: row.observed_at.toISOString() };
  }
  if (typeof row.observed_at !== "string" || !Number.isFinite(Date.parse(row.observed_at))) {
    throw new Error("money printer runtime store opportunity readback invalid");
  }
  return row;
}

function sourceOpportunityRow(result, expected) {
  const rows = result && Array.isArray(result.rows) ? result.rows : [];
  if (rows.length === 0) return null;
  if (rows.length !== 1 || !rows[0] || typeof rows[0] !== "object" || Array.isArray(rows[0])) {
    throw new Error("money printer runtime store opportunity source readback invalid");
  }
  const row = normalizeOpportunityReadback(rows[0]);
  const actual = canonicalOpportunityInput({
    tenantId: row.uid == null ? row.tenant_id : row.uid,
    sourceUrl: row.source_url,
    title: row.title,
    goalStatement: row.goal_statement,
    valueMinor: row.value_minor,
    currency: row.currency,
    observedAt: row.observed_at,
  });
  if (
    actual.uid !== expected.uid || actual.source_url !== expected.sourceUrl
    || String(row.opportunity_id || "") !== actual.opportunity_id
    || String(row.goal_ref || "") !== actual.goal_ref
    || typeof row.status !== "string" || !row.status.trim()
  ) throw new Error("money printer runtime store opportunity source readback invalid");
  return row;
}

function createMoneyPrinterRuntimeStore({ query } = {}) {
  if (typeof query !== "function") unavailable();

  return Object.freeze({
    async claimSymphony(value) {
      const uid = tenant(value);
      return claimedSymphonyDispatch(await query(`
        SELECT * FROM public.claim_lm_symphony_job($1)
      `, [uid]), uid);
    },
    async recordSymphonyIssue(value) {
      const uid = tenant(value && value.uid);
      const dispatchId = String(value && value.dispatchId || "").trim();
      const issueRef = String(value && value.issueRef || "").trim();
      if (!OPPORTUNITY_ID.test(dispatchId) || !GITHUB_ISSUE_REF.test(issueRef)) {
        throw new Error("money printer runtime store Symphony issue invalid");
      }
      return mirroredSymphonyDispatch(await query(`
        SELECT * FROM public.record_lm_symphony_issue($1, $2, $3)
      `, [uid, dispatchId, issueRef]), { uid, dispatchId, issueRef });
    },
    async createOpportunity(canonical) {
      const uid = tenant(canonical && canonical.uid);
      const row = oneRow(await query(`
        SELECT * FROM public.create_lm_money_opportunity($1, $2, $3, $4, $5, $6, $7, $8, $9)
      `, [
        uid, canonical.opportunity_id, canonical.source_url, canonical.title, canonical.goal_statement,
        canonical.value_minor, canonical.currency, canonical.observed_at, canonical.goal_ref,
      ]), "opportunity", uid);
      if (row.opportunity_id !== canonical.opportunity_id) throw new Error("money printer runtime store opportunity readback invalid");
      return normalizeOpportunityReadback(row);
    },
    async readOpportunity(value) {
      const expected = expectedOpportunity(value);
      return opportunityRow(await query(`
        SELECT uid, opportunity_id, source_url, title, goal_statement, value_minor, currency, status, goal_ref, observed_at
        FROM public.lm_money_opportunities
        WHERE uid = $1 AND opportunity_id = $2 AND goal_ref = $3
        LIMIT 2
      `, [expected.uid, expected.opportunityId, expected.goalRef]), expected, "opportunity");
    },
    async readOpportunityBySource(value) {
      const expected = expectedOpportunitySource(value);
      return sourceOpportunityRow(await query(`
        SELECT uid, opportunity_id, source_url, title, goal_statement, value_minor, currency, status, goal_ref, observed_at
        FROM public.lm_money_opportunities
        WHERE uid = $1 AND source_url = $2
        LIMIT 2
      `, [expected.uid, expected.sourceUrl]), expected);
    },
    async updateOpportunity(value, status) {
      const expected = expectedOpportunity(value);
      if (status !== "QUALIFIED") throw new Error("money printer runtime store opportunity status invalid");
      const row = opportunityRow(await query(`
        WITH updated AS (
          UPDATE public.lm_money_opportunities
          SET status = $4, updated_at = clock_timestamp()
          WHERE uid = $1 AND opportunity_id = $2 AND goal_ref = $3
            AND status IN ('DISCOVERED', 'QUALIFYING')
          RETURNING uid, opportunity_id, source_url, title, goal_statement, value_minor, currency, status, goal_ref, observed_at
        )
        SELECT * FROM updated
        UNION ALL
        SELECT uid, opportunity_id, source_url, title, goal_statement, value_minor, currency, status, goal_ref, observed_at
        FROM public.lm_money_opportunities
        WHERE uid = $1 AND opportunity_id = $2 AND goal_ref = $3
          AND status = 'QUALIFIED'
          AND NOT EXISTS (SELECT 1 FROM updated)
      `, [expected.uid, expected.opportunityId, expected.goalRef, status]), expected, "opportunity");
      if (row.status !== status) throw new Error("money printer runtime store opportunity readback invalid");
      return row;
    },
    async createOnce(task) {
      const uid = tenant(task && task.uid);
      const row = oneRow(await query(`
        SELECT * FROM public.create_lm_human_task($1, $2, $3, $4, $5, $6, $7, $8, $9)
      `, [
        uid, task.task_id, task.job_id, task.reason_code, task.question,
        JSON.stringify(task.required_format), task.resume_ref, JSON.stringify(task.context_refs), task.human_boundary_ref,
      ]), "human task", uid);
      if (row.task_id !== task.task_id || row.job_id !== task.job_id || row.status !== "open") {
        throw new Error("money printer runtime store human task readback invalid");
      }
      return row;
    },
    async readAnsweredForJob(value) {
      const expected = expectedHumanJob(value);
      const rows = scopedRows(await query(`
        SELECT uid, job_id, reason_code, answer_ref, human_boundary_ref, version, updated_at
        FROM public.lm_human_tasks
        WHERE uid = $1 AND job_id = $2 AND status = 'answered'
        ORDER BY updated_at ASC, task_id ASC
      `, [expected.uid, expected.jobId]), expected.uid, "answered human tasks");
      return rows.map((row) => {
        if (row.job_id !== expected.jobId
          || !JOB_ID.test(String(row.reason_code || ""))
          || !String(row.answer_ref || "").startsWith(`vault-answer://${expected.uid}/`)
          || !/^human-boundary:\/\/sha256\/[0-9a-f]{64}$/.test(String(row.human_boundary_ref || ""))
          || !Number.isInteger(row.version) || !Number.isFinite(Date.parse(row.updated_at))) {
          throw new Error("money printer runtime store answered human tasks readback invalid");
        }
        return Object.freeze({
          uid: expected.uid, job_id: expected.jobId, reason_code: row.reason_code,
          answer_ref: row.answer_ref, human_boundary_ref: row.human_boundary_ref,
          version: row.version, updated_at: row.updated_at,
        });
      });
    },
    async readNext(scope) {
      const uid = tenant(scope);
      const rows = scopedRows(await query(`
        SELECT uid, task_id, version, question, required_format, reason_code, resume_ref, status, created_at, updated_at
        FROM public.lm_human_tasks
        WHERE uid = $1 AND status = 'open'
        ORDER BY created_at ASC, task_id ASC
        LIMIT 1
      `, [uid]), uid, "human task");
      if (rows.length > 1) throw new Error("money printer runtime store human task readback invalid");
      return rows[0] || null;
    },
    async answerOnce(answer) {
      const uid = tenant(answer && answer.uid);
      const row = oneRow(await query(`
        SELECT * FROM public.answer_lm_human_task($1, $2, $3, $4)
      `, [uid, answer.taskId, answer.version, answer.answerRef]), "human task", uid);
      if (row.task_id !== answer.taskId || row.answer_ref !== answer.answerRef || row.status !== "answered") {
        throw new Error("money printer runtime store human task readback invalid");
      }
      return row;
    },
    async readRuntimeSnapshot(value) {
      const uid = tenant(value);
      const [opportunities, runtimeJobs, humanTasks, receipts] = await Promise.all([
        query(`
          SELECT uid, opportunity_id, source_url, title, value_minor, currency, status, goal_ref, observed_at
          FROM public.lm_money_opportunities WHERE uid = $1
          ORDER BY updated_at DESC, opportunity_id ASC
        `, [uid]),
        query(`
          SELECT tenant_id, job_id, status, created_at, updated_at
          FROM public.lm_runtime_jobs WHERE tenant_id = $1
          ORDER BY updated_at DESC, job_id ASC
        `, [uid]),
        query(`
          SELECT uid, task_id, status, created_at, updated_at
          FROM public.lm_human_tasks WHERE uid = $1
          ORDER BY updated_at DESC, task_id ASC
        `, [uid]),
        query(`
          SELECT tenant_id, job_id, attempt, outcome, created_at, receipt
          FROM public.lm_runtime_job_receipts WHERE tenant_id = $1
          ORDER BY created_at DESC, job_id ASC, attempt DESC
        `, [uid]),
      ]);
      return Object.freeze({
        opportunities: scopedRows(opportunities, uid, "opportunities"),
        runtimeJobs: scopedRows(runtimeJobs, uid, "runtime jobs"),
        humanTasks: scopedRows(humanTasks, uid, "human tasks"),
        receipts: scopedRows(receipts, uid, "runtime receipts"),
      });
    },
  });
}

module.exports = { createMoneyPrinterRuntimeStore };
