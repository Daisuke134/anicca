"use strict";

const TENANT_ID = /^[a-z0-9][a-z0-9._-]{0,199}$/;

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

function createMoneyPrinterRuntimeStore({ query } = {}) {
  if (typeof query !== "function") unavailable();

  return Object.freeze({
    async createOpportunity(canonical) {
      const uid = tenant(canonical && canonical.uid);
      const row = oneRow(await query(`
        SELECT * FROM public.create_lm_money_opportunity($1, $2, $3, $4, $5, $6, $7, $8, $9)
      `, [
        uid, canonical.opportunity_id, canonical.source_url, canonical.title, canonical.goal_statement,
        canonical.value_minor, canonical.currency, canonical.observed_at, canonical.goal_ref,
      ]), "opportunity", uid);
      if (row.opportunity_id !== canonical.opportunity_id) throw new Error("money printer runtime store opportunity readback invalid");
      return row;
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
