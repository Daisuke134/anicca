"use strict";

const { createHash } = require("node:crypto");
const { isVerifiedFunderWeeklyReflection } = require("./funder-weekly-reflection.js");

const TENANT = /^[a-z0-9][a-z0-9._-]{0,127}$/i;
const DATE = /^\d{4}-\d{2}-\d{2}$/;
const ID = /^[a-z0-9][a-z0-9._-]{1,127}$/i;
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const DIGEST = /^[0-9a-f]{64}$/;
const PLACEHOLDER = /\{\{|\}\}|TODO|TBD|<placeholder>/i;
const INVESTOR_KINDS = new Set(["vc", "angel"]);
const VERIFIED_PLANS = new WeakSet();
const VERIFIED_RESERVATIONS = new WeakSet();

const sha = (value) => createHash("sha256").update(String(value), "utf8").digest("hex");
const fail = () => { throw new Error("funder investor outreach invalid"); };
const wordCount = (value) => String(value || "").trim().split(/\s+/).filter(Boolean).length;

function strategyValidUntil(observedMs) {
  const { tokyoReflectionWeek } = require("./funder-weekly-reflection.js");
  let week = tokyoReflectionWeek(new Date(observedMs).toISOString());
  if (Date.parse(week.week_end) <= observedMs) {
    week = tokyoReflectionWeek(new Date(Date.parse(week.week_start) + (7 * 86_400_000)).toISOString());
  }
  return new Date(Date.parse(week.week_end) - (5 * 60_000)).toISOString();
}

function exactObject(value, keys) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  return Object.keys(value).sort().join("\0") === [...keys].sort().join("\0");
}

function validateDayRows(result) {
  if (!result || !Array.isArray(result.rows) || result.rows.length > 10000
    || result.rows.some((row) => !exactObject(row, ["recipient_sha256", "same_day"])
      || !DIGEST.test(String(row.recipient_sha256 || "")) || typeof row.same_day !== "boolean")) fail();
  const hashes = result.rows.map((row) => row.recipient_sha256);
  if (new Set(hashes).size !== hashes.length) fail();
  const sameDayCount = result.rows.filter((row) => row.same_day).length;
  if (sameDayCount > 5) fail();
  return { hashes, sameDayCount };
}

function validateCandidate(candidate, context) {
  if (!candidate || !ID.test(String(candidate.candidateId || ""))
    || !String(candidate.funderName || "").trim() || String(candidate.funderName).length > 120
    || !EMAIL.test(String(candidate.email || "").trim().toLowerCase())
    || !Number.isInteger(candidate.rank) || candidate.rank < 1
    || !String(candidate.subject || "").trim() || candidate.subject.length > 60
    || !String(candidate.body || "").trim() || wordCount(candidate.body) > 120
    || PLACEHOLDER.test(candidate.subject) || PLACEHOLDER.test(candidate.body)
    || !/https:\/\/aniccaai\.com(?:[\s/]|$)/i.test(candidate.body)
    || !/(15-minute|15 min|15分)/i.test(candidate.body)) fail();

  let reflectionProof = null;
  if (context.reflection && context.reflection.decision === "change") {
    const position = context.reflection.ranked_candidate_ids.indexOf(candidate.candidateId) + 1;
    const directive = context.reflection.pitch_directives.find(
      (item) => item.candidate_id === candidate.candidateId,
    );
    const applied = candidate.reflectionApplication;
    if (position < 1 || !directive || candidate.rank !== position
      || !exactObject(applied, [
        "reflection_id", "ranking_position", "pitch_directive", "outcome_result_ids",
      ]) || applied.reflection_id !== context.reflection.reflection_id
      || applied.ranking_position !== position || applied.pitch_directive !== directive.directive
      || !candidate.body.includes(directive.directive)
      || JSON.stringify(applied.outcome_result_ids) !== JSON.stringify(directive.outcome_result_ids)) fail();
    reflectionProof = {
      reflection_id: context.reflection.reflection_id,
      reflection_week_key: context.reflection.week_key,
      ranking_position: position,
      pitch_directive_sha256: directive.directive_sha256,
      reflection_outcome_result_ids: [...directive.outcome_result_ids],
    };
  } else if (candidate.reflectionApplication !== undefined) fail();

  const email = String(candidate.email).trim().toLowerCase();
  if (context.sent.has(sha(email))) fail();
  let sourceUrl;
  try { sourceUrl = new URL(String(candidate.sourceUrl || "")); } catch { fail(); }
  const sourceMs = Date.parse(String(candidate.sourceObservedAt || ""));
  const source = String(candidate.sourceExcerpt || "");
  if (sourceUrl.protocol !== "https:" || sourceUrl.username || sourceUrl.password
    || !Number.isFinite(sourceMs) || sourceMs > context.observedMs || context.observedMs - sourceMs > 86_400_000
    || !DIGEST.test(String(candidate.sourceDigest || "")) || sha(source) !== candidate.sourceDigest
    || !source.toLowerCase().includes(email)) fail();

  const assessment = candidate.assessment;
  if (!exactObject(assessment, ["kind", "investor_kind", "thesis_match", "summary", "target_evidence_quotes", "message_claims"])
    || assessment.kind !== "agent_judgment" || !INVESTOR_KINDS.has(assessment.investor_kind)
    || assessment.thesis_match !== true || !String(assessment.summary || "").trim()
    || !Array.isArray(assessment.target_evidence_quotes) || assessment.target_evidence_quotes.length < 2
    || !Array.isArray(assessment.message_claims) || assessment.message_claims.length < 2) fail();

  for (const quote of assessment.target_evidence_quotes) {
    if (!String(quote || "").trim() || !source.includes(quote)) fail();
  }
  let targetClaims = 0;
  let companyClaims = 0;
  const companyQuotes = [];
  for (const binding of assessment.message_claims) {
    if (!exactObject(binding, ["claim", "evidence_source", "evidence_quote"])
      || !String(binding.claim || "").trim() || !candidate.body.includes(binding.claim)
      || !String(binding.evidence_quote || "").trim()) fail();
    if (binding.evidence_source === "target") {
      targetClaims += 1;
      if (!source.includes(binding.evidence_quote)) fail();
    } else if (binding.evidence_source === "company") {
      companyClaims += 1;
      if (!context.companyFacts.includes(binding.evidence_quote)) fail();
      companyQuotes.push(binding.evidence_quote);
    } else fail();
  }
  if (targetClaims < 1 || companyClaims < 1) fail();

  const thesisEvidence = {
    source_digest: candidate.sourceDigest,
    investor_kind: assessment.investor_kind,
    thesis_match: assessment.thesis_match,
    target_evidence_quotes: assessment.target_evidence_quotes,
  };
  const companyEvidence = { kit_digest: context.kitDigest, company_evidence_quotes: companyQuotes };
  const personalization = { message_claims: assessment.message_claims };
  return {
    email,
    sourceUrl: sourceUrl.toString(),
    sourceMs,
    thesisEvidenceHash: sha(JSON.stringify(thesisEvidence)),
    companyEvidenceHash: sha(JSON.stringify(companyEvidence)),
    personalizationHash: sha(JSON.stringify(personalization)),
    reflectionProof,
  };
}

function applyWeeklyReflection(candidates, reflection) {
  if (!reflection || reflection.decision !== "change") return candidates;
  return candidates.map((candidate) => {
    const position = reflection.ranked_candidate_ids.indexOf(candidate.candidateId) + 1;
    const directive = reflection.pitch_directives.find(
      (item) => item.candidate_id === candidate.candidateId,
    );
    if (position < 1 || !directive) fail();
    let body = String(candidate.body || "");
    if (!body.includes(directive.directive)) {
      const match = /(?:Would a 15-minute|Would a 15 min|15分)/i.exec(body);
      if (!match) fail();
      body = `${body.slice(0, match.index)}${directive.directive} ${body.slice(match.index)}`;
    }
    return {
      ...candidate,
      rank: position,
      body,
      reflectionApplication: {
        reflection_id: reflection.reflection_id,
        ranking_position: position,
        pitch_directive: directive.directive,
        outcome_result_ids: [...directive.outcome_result_ids],
      },
    };
  });
}

async function buildInvestorOutreachPlan(input = {}, dependencies = {}) {
  const observedMs = Date.parse(String(input.observedAt || ""));
  const target = Number(input.dailyTarget);
  if (!TENANT.test(String(input.tenantId || "")) || !DATE.test(String(input.tokyoDate || ""))
    || !Number.isFinite(observedMs) || !Number.isInteger(target) || target < 3 || target > 5
    || !Array.isArray(input.candidates) || typeof dependencies.query !== "function"
    || typeof dependencies.ensureWeeklyReflection !== "function"
    || typeof dependencies.loadLatestReflection !== "function"
    || !input.applicationKitProvider || typeof input.applicationKitProvider.snapshot !== "function"
    || typeof input.applicationKitProvider.readCompanyFacts !== "function") fail();
  const candidateIds = input.candidates.map((item) => item && item.candidateId);
  if (candidateIds.some((id) => !ID.test(String(id || "")))
    || new Set(candidateIds).size !== candidateIds.length
    || input.candidates.some((item) => wordCount(item && item.body) > 90)) fail();

  const dayResult = await dependencies.query(`
    SELECT recipient_sha256, (tokyo_date=$2::date) AS same_day
    FROM public.lm_funder_outreach_ledger
    WHERE tenant_id=$1
    ORDER BY sent_at, outreach_id
  `, [input.tenantId, input.tokyoDate]);
  const dayState = validateDayRows(dayResult);
  if (dayState.sameDayCount >= target) {
    const batchSeed = {
      tenant_id: input.tenantId,
      tokyo_date: input.tokyoDate,
      observed_at: new Date(observedMs).toISOString(),
      existing_count: dayState.sameDayCount,
      daily_target: target,
      recipient_hashes: [],
    };
    const noOp = Object.freeze({
      schema_version: 2,
      batch_id: `funder-outreach-batch:${sha(JSON.stringify(batchSeed))}`,
      tenant_id: input.tenantId,
      tokyo_date: input.tokyoDate,
      observed_at: new Date(observedMs).toISOString(),
      existing_count: dayState.sameDayCount,
      daily_target: target,
      projected_total: dayState.sameDayCount,
      strategy_valid_until: strategyValidUntil(observedMs),
      reserved: false,
      messages: Object.freeze([]),
    });
    VERIFIED_PLANS.add(noOp);
    return noOp;
  }
  const snapshot = input.applicationKitProvider.snapshot();
  const companyFacts = String(input.applicationKitProvider.readCompanyFacts() || "");
  const snapshotAfter = input.applicationKitProvider.snapshot();
  const snapshotKeys = ["schema_version", "root_ref", "company_facts_ref", "answer_count", "asset_count", "kit_digest"];
  if (!exactObject(snapshot, snapshotKeys) || !exactObject(snapshotAfter, snapshotKeys)
    || snapshot.schema_version !== 1 || snapshot.root_ref !== "application-kit://current"
    || snapshot.company_facts_ref !== "application-kit://KIT.md"
    || snapshot.answer_count !== 20 || snapshot.asset_count !== 6
    || !DIGEST.test(String(snapshot.kit_digest || "")) || snapshotAfter.kit_digest !== snapshot.kit_digest
    || snapshotAfter.root_ref !== snapshot.root_ref || snapshotAfter.company_facts_ref !== snapshot.company_facts_ref
    || snapshotAfter.answer_count !== snapshot.answer_count || snapshotAfter.asset_count !== snapshot.asset_count
    || !companyFacts) fail();

  const ensured = await dependencies.ensureWeeklyReflection({
    tenantId: input.tenantId,
    reflectedAt: new Date(observedMs).toISOString(),
    candidateIds,
  });
  if (!ensured || !new Set(["skipped", "recorded", "duplicate"]).has(ensured.status)
    || !DATE.test(String(ensured.week_key || ""))) fail();
  const reflection = await dependencies.loadLatestReflection({
    tenantId: input.tenantId,
    before: new Date(observedMs).toISOString(),
  });
  if (reflection !== null && (!isVerifiedFunderWeeklyReflection(reflection)
    || reflection.tenant_id !== input.tenantId
    || Date.parse(reflection.week_end) > observedMs
    || Date.parse(reflection.reflected_at) > observedMs)) fail();
  if (reflection && reflection.decision === "change"
    && (reflection.ranked_candidate_ids.length !== input.candidates.length
      || !reflection.ranked_candidate_ids.every((id) => input.candidates.some((item) => item.candidateId === id)))) fail();
  const candidates = applyWeeklyReflection(input.candidates, reflection);
  const context = {
    observedMs,
    sent: new Set(dayState.hashes),
    companyFacts,
    kitDigest: snapshot.kit_digest,
    reflection,
  };
  const seenEmails = new Set();
  const seenRanks = new Set();
  const valid = candidates.map((item) => {
    const normalized = validateCandidate(item, context);
    if (seenEmails.has(normalized.email) || seenRanks.has(item.rank)) fail();
    seenEmails.add(normalized.email);
    seenRanks.add(item.rank);
    return { item, normalized };
  }).sort((left, right) => left.item.rank - right.item.rank);

  const required = Math.max(0, target - dayState.sameDayCount);
  if (required > valid.length) fail();
  const selected = valid.slice(0, required);
  const batchSeed = {
    tenant_id: input.tenantId,
    tokyo_date: input.tokyoDate,
    observed_at: new Date(observedMs).toISOString(),
    existing_count: dayState.sameDayCount,
    daily_target: target,
    recipient_hashes: selected.map(({ normalized }) => sha(normalized.email)),
  };
  const batchId = `funder-outreach-batch:${sha(JSON.stringify(batchSeed))}`;
  const messages = selected.map(({ item, normalized }) => {
    const recipientHash = sha(normalized.email);
    const subjectHash = sha(item.subject.trim());
    const bodyHash = sha(item.body.trim());
    return Object.freeze({
      outreach_id: `funder-outreach:${sha(`${batchId}\n${recipientHash}\n${subjectHash}\n${bodyHash}`)}`,
      batch_id: batchId,
      tenant_id: input.tenantId,
      tokyo_date: input.tokyoDate,
      candidate_id: item.candidateId,
      funder_name: item.funderName.trim(),
      recipient: normalized.email,
      recipient_sha256: recipientHash,
      source_url: normalized.sourceUrl,
      source_observed_at: new Date(normalized.sourceMs).toISOString(),
      source_digest: item.sourceDigest,
      fit_summary_sha256: sha(item.assessment.summary.trim()),
      investor_kind: item.assessment.investor_kind,
      thesis_evidence_sha256: normalized.thesisEvidenceHash,
      company_evidence_sha256: normalized.companyEvidenceHash,
      personalization_sha256: normalized.personalizationHash,
      ...(normalized.reflectionProof || {}),
      subject: item.subject.trim(),
      subject_sha256: subjectHash,
      body: item.body.trim(),
      body_sha256: bodyHash,
    });
  });
  const plan = Object.freeze({
    schema_version: 2,
    batch_id: batchId,
    tenant_id: input.tenantId,
    tokyo_date: input.tokyoDate,
    observed_at: new Date(observedMs).toISOString(),
    existing_count: dayState.sameDayCount,
    daily_target: target,
    projected_total: dayState.sameDayCount + messages.length,
    strategy_valid_until: strategyValidUntil(observedMs),
    reserved: false,
    reflection_id: reflection && reflection.decision === "change" ? reflection.reflection_id : null,
    messages: Object.freeze(messages),
  });
  VERIFIED_PLANS.add(plan);
  return plan;
}

async function buildAutonomousInvestorOutreachPlan(input = {}, options = {}) {
  if (typeof options.query !== "function") fail();
  const { createFunderReflectionMaterializer } = require("./funder-weekly-reflection-runtime.js");
  const { loadLatestFunderWeeklyReflection } = require("./funder-weekly-reflection-store.js");
  return buildInvestorOutreachPlan(input, {
    query: options.query,
    ensureWeeklyReflection: createFunderReflectionMaterializer({
      query: options.query,
      apiKey: options.apiKey,
      fetchImpl: options.fetchImpl,
    }),
    loadLatestReflection: (request) => loadLatestFunderWeeklyReflection(request, {
      query: options.query,
    }),
  });
}

async function reserveInvestorOutreachPlan(plan, dependencies = {}) {
  if (!plan || !VERIFIED_PLANS.has(plan) || plan.schema_version !== 2 || plan.reserved !== false || !Array.isArray(plan.messages)
    || plan.projected_total !== plan.existing_count + plan.messages.length || plan.projected_total > 5
    || typeof dependencies.query !== "function") fail();
  const reserved = [];
  for (const message of plan.messages) {
    const result = await dependencies.query(`
      SELECT outreach_id, daily_slot, reserved_at
      FROM public.lm_reserve_funder_investor_outreach($1,$2::date,$3,$4,$5,$6,$7,$8)
    `, [
      plan.tenant_id, plan.tokyo_date, message.outreach_id, message.recipient_sha256,
      message.investor_kind, message.thesis_evidence_sha256,
      message.company_evidence_sha256, message.personalization_sha256,
    ]);
    if (!result || !Array.isArray(result.rows) || result.rows.length !== 1) fail();
    const row = result.rows[0];
    if (row.outreach_id !== message.outreach_id || !Number.isInteger(Number(row.daily_slot))
      || Number(row.daily_slot) < 1 || Number(row.daily_slot) > 5 || !Number.isFinite(Date.parse(row.reserved_at))) fail();
    reserved.push(Object.freeze({ ...message, daily_slot: Number(row.daily_slot), reserved_at: new Date(row.reserved_at).toISOString() }));
  }
  const result = Object.freeze({ ...plan, reserved: true, messages: Object.freeze(reserved) });
  VERIFIED_RESERVATIONS.add(result);
  return result;
}

function isVerifiedInvestorOutreachReservation(value) {
  return Boolean(value && VERIFIED_RESERVATIONS.has(value));
}

module.exports = {
  buildInvestorOutreachPlan,
  buildAutonomousInvestorOutreachPlan,
  reserveInvestorOutreachPlan,
  isVerifiedInvestorOutreachReservation,
};
