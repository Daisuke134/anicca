"use strict";

const { createHash } = require("node:crypto");

const TENANT = /^[a-z0-9][a-z0-9._-]{0,127}$/i;
const DATE = /^\d{4}-\d{2}-\d{2}$/;
const ID = /^[a-z0-9][a-z0-9._-]{1,127}$/i;
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const DIGEST = /^[0-9a-f]{64}$/;
const PLACEHOLDER = /\{\{|\}\}|TODO|TBD|<placeholder>/i;

const sha = (value) => createHash("sha256").update(value, "utf8").digest("hex");

function fail() { throw new Error("funder outreach batch invalid"); }

function wordCount(body) {
  return String(body || "").trim().split(/\s+/).filter(Boolean).length;
}

function validateCandidate(candidate, observedMs, sent) {
  const email = String(candidate && candidate.email || "").trim().toLowerCase();
  const excerpt = String(candidate && candidate.sourceExcerpt || "");
  const sourceMs = Date.parse(String(candidate && candidate.sourceObservedAt || ""));
  let url;
  try { url = new URL(String(candidate && candidate.sourceUrl || "")); } catch { fail(); }
  if (
    !candidate || !ID.test(String(candidate.candidateId || ""))
    || !String(candidate.funderName || "").trim() || String(candidate.funderName).length > 120
    || !EMAIL.test(email) || sent.has(sha(email))
    || url.protocol !== "https:" || url.username || url.password
    || !Number.isFinite(sourceMs) || sourceMs > observedMs || observedMs - sourceMs > 24 * 60 * 60 * 1000
    || !DIGEST.test(String(candidate.sourceDigest || "")) || sha(excerpt) !== candidate.sourceDigest
    || !excerpt.toLowerCase().includes(email)
    || !candidate.fitAssessment || candidate.fitAssessment.kind !== "agent_judgment"
    || !String(candidate.fitAssessment.summary || "").trim()
    || !Number.isInteger(candidate.rank) || candidate.rank < 1
    || !String(candidate.subject || "").trim() || candidate.subject.length > 60
    || !String(candidate.body || "").trim() || wordCount(candidate.body) > 120
    || PLACEHOLDER.test(candidate.subject) || PLACEHOLDER.test(candidate.body)
    || !/https:\/\/aniccaai\.com(?:[\s/]|$)/i.test(candidate.body)
    || !/(15-minute|15 min|15分)/i.test(candidate.body)
  ) fail();
  return { email, url: url.toString(), sourceMs };
}

function buildFunderOutreachBatch(input = {}) {
  const observedMs = Date.parse(String(input.observedAt || ""));
  const target = Number(input.dailyTarget);
  if (!TENANT.test(String(input.tenantId || "")) || !DATE.test(String(input.tokyoDate || ""))
    || !Number.isFinite(observedMs) || !Number.isInteger(target) || target < 3 || target > 5
    || !Array.isArray(input.candidates) || !Array.isArray(input.sentRecipientHashes)
    || input.sentRecipientHashes.some((value) => !DIGEST.test(String(value)))) fail();
  const sent = new Set(input.sentRecipientHashes);
  const seenEmails = new Set();
  const seenRanks = new Set();
  const valid = input.candidates.map((candidate) => {
    const normalized = validateCandidate(candidate, observedMs, sent);
    if (seenEmails.has(normalized.email) || seenRanks.has(candidate.rank)) fail();
    seenEmails.add(normalized.email);
    seenRanks.add(candidate.rank);
    return { candidate, normalized };
  }).sort((a, b) => a.candidate.rank - b.candidate.rank);
  if (valid.length < target) fail();
  const selected = valid.slice(0, target);
  const batchSeed = {
    tenant_id: input.tenantId,
    tokyo_date: input.tokyoDate,
    observed_at: new Date(observedMs).toISOString(),
    recipient_hashes: selected.map(({ normalized }) => sha(normalized.email)),
  };
  const batchId = `funder-outreach-batch:${sha(JSON.stringify(batchSeed))}`;
  const messages = selected.map(({ candidate, normalized }) => {
    const recipientHash = sha(normalized.email);
    const subjectHash = sha(candidate.subject);
    const bodyHash = sha(candidate.body);
    return Object.freeze({
      outreach_id: `funder-outreach:${sha(`${batchId}\n${recipientHash}\n${subjectHash}\n${bodyHash}`)}`,
      batch_id: batchId,
      tenant_id: input.tenantId,
      tokyo_date: input.tokyoDate,
      candidate_id: candidate.candidateId,
      funder_name: candidate.funderName.trim(),
      recipient: normalized.email,
      recipient_sha256: recipientHash,
      source_url: normalized.url,
      source_observed_at: new Date(normalized.sourceMs).toISOString(),
      source_digest: candidate.sourceDigest,
      fit_summary_sha256: sha(candidate.fitAssessment.summary.trim()),
      subject: candidate.subject.trim(),
      subject_sha256: subjectHash,
      body: candidate.body.trim(),
      body_sha256: bodyHash,
    });
  });
  return Object.freeze({
    schema_version: 1,
    batch_id: batchId,
    tenant_id: input.tenantId,
    tokyo_date: input.tokyoDate,
    observed_at: new Date(observedMs).toISOString(),
    daily_target: target,
    messages: Object.freeze(messages),
  });
}

module.exports = { buildFunderOutreachBatch };
