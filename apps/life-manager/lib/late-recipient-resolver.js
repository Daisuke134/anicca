"use strict";

// Recipient discovery is deliberately separate from delivery.  This module only returns
// evidence-backed identities; a caller must still obtain a durable approval before sending.

const DECLINED_STATUSES = new Set(["declined", "cancelled", "canceled"]);
const SOURCE_RANK = Object.freeze({ calendar: 0, gmail: 1, contacts: 2, public_web: 3, user_confirmation: 4 });
const DEFAULT_CONFIDENCE = Object.freeze({ calendar: 1, gmail: 0.9, contacts: 0.9, public_web: 0.4, user_confirmation: 1 });
const EMAIL_RE = /^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/;
const APPROVED_CONTACT_PROVIDER_NAMES = new Set(["approvedContacts", "approved_contacts", "searchApprovedContacts"]);

const PROVIDER_NAMES = Object.freeze({
  gmail: ["connectedGmail", "connected_gmail", "searchConnectedGmail", "searchGmail", "gmail"],
  contacts: [
    "approvedContacts", "approved_contacts", "googleContacts", "searchApprovedContacts", "searchContacts", "contacts",
  ],
  public_web: [
    "publicWeb", "public_web", "searchPublicWeb", "publicWebEvidence", "searchPublicWebEvidence",
  ],
  confirmation: [
    "requestUserConfirmation", "request_user_confirmation", "requestRecipientConfirmation",
    "askUserForRecipient", "confirmRecipient", "userConfirmation",
  ],
});

function text(value) {
  const result = String(value == null ? "" : value).replace(/\s+/g, " ").trim();
  return result || null;
}

function normalizeEmail(value) {
  const raw = text(value);
  if (!raw) return null;
  const bracketed = raw.match(/<([^<>\s]+@[^<>\s]+)>/);
  const email = (bracketed ? bracketed[1] : raw).toLowerCase();
  return EMAIL_RE.test(email) ? email : null;
}

function eventReference(event) {
  const id = text(event && (event.id || event.eventId || event.event_id));
  return id ? id.replace(/\s+/g, "_").slice(0, 120) : "unknown";
}

function asArray(value) {
  if (Array.isArray(value)) return value;
  return value == null ? [] : [value];
}

function normalizeActorEmails(actorEmails) {
  const values = asArray(actorEmails).flatMap((value) => {
    if (value && typeof value === "object") return [value.email || value.address || value.emailAddress];
    return [value];
  });
  return new Set(values.map(normalizeEmail).filter(Boolean));
}

function isDeclined(value) {
  const status = text(value && (value.responseStatus || value.response_status || value.status));
  return Boolean(status && DECLINED_STATUSES.has(status.toLowerCase()));
}

function isResource(value) {
  if (!value || typeof value !== "object") return false;
  return value.resource === true || value.isResource === true || value.resource_type === "room" ||
    value.type === "resource" || value.kind === "resource" ||
    String(value.resource || "").toLowerCase() === "true";
}

function readReferenceValues(value) {
  const values = asArray(value);
  return values.map((item) => {
    if (item && typeof item === "object") return item.ref || item.reference || item.uri || item.id;
    return item;
  }).map(text).filter(Boolean);
}

function readEvidenceRefs(value) {
  if (!value || typeof value !== "object") return [];
  return [
    ...readReferenceValues(value.evidence_refs),
    ...readReferenceValues(value.evidenceRefs),
    ...readReferenceValues(value.evidence_ref),
    ...readReferenceValues(value.evidenceReference),
    ...readReferenceValues(value.evidence),
  ];
}

function firstEmail(value) {
  if (value == null) return null;
  if (typeof value === "string") return normalizeEmail(value);
  if (Array.isArray(value)) {
    for (const item of value) {
      const email = firstEmail(item);
      if (email) return email;
    }
    return null;
  }
  if (typeof value !== "object") return null;
  for (const key of [
    "email", "email_address", "emailAddress", "address", "identifier", "primaryEmail", "contactEmail", "value",
  ]) {
    const email = normalizeEmail(value[key]);
    if (email) return email;
  }
  for (const key of ["emailAddresses", "email_addresses", "from", "sender", "to", "cc", "replyTo", "reply_to", "headers"]) {
    const email = firstEmail(value[key]);
    if (email) return email;
  }
  return null;
}

function displayName(value) {
  if (!value || typeof value !== "object") return null;
  for (const key of ["display_name", "displayName", "full_name", "fullName", "name", "label"]) {
    const name = text(value[key]);
    if (name) return name;
  }
  for (const key of ["person", "contact", "profile"]) {
    const name = displayName(value[key]);
    if (name) return name;
  }
  return null;
}

function eventRole(value, fallback) {
  if (!value || typeof value !== "object") return fallback;
  return text(value.event_role || value.eventRole || value.role) || fallback;
}

function providerCandidates(payload) {
  if (Array.isArray(payload)) return payload;
  if (!payload || typeof payload !== "object") return [];
  for (const key of ["candidates", "candidate", "matches", "results", "items", "contacts", "people", "connections", "messages"]) {
    if (payload[key] !== undefined) return asArray(payload[key]);
  }
  return firstEmail(payload) ? [payload] : [];
}

function providerEvidenceRefs(payload) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) return [];
  return [
    ...readEvidenceRefs(payload),
    ...readReferenceValues(payload.evidence),
  ];
}

function providerFunction(deps, names) {
  if (!deps || typeof deps !== "object") return null;
  for (const name of names) {
    if (typeof deps[name] === "function") return { name, fn: deps[name].bind(deps) };
    const adapter = deps[name];
    if (adapter && typeof adapter.search === "function") return { name, fn: adapter.search.bind(adapter) };
    if (adapter && typeof adapter.resolve === "function") return { name, fn: adapter.resolve.bind(adapter) };
  }
  return null;
}

function fallbackEvidenceRef(stage, event, index) {
  return `${stage}:event:${eventReference(event)}:candidate:${index}`;
}

function normalizeCandidate(raw, {
  stage, event, index, actorSet, defaultRole, defaultRefs = [], requireApproved = false,
}) {
  if (!raw || typeof raw !== "object") return null;
  if (raw.verified === false || raw.isVerified === false) return null;
  if (stage === "contacts" && (requireApproved && raw.approved !== true && raw.isApproved !== true)) return null;
  if (stage === "contacts" && (raw.approved === false || raw.isApproved === false)) return null;
  if (stage === "public_web" && (raw.public === false || raw.isPublic === false ||
      String(raw.visibility || "").toLowerCase() === "private")) return null;
  const email = firstEmail(raw);
  if (!email || actorSet.has(email)) return null;
  const refs = [
    ...defaultRefs,
    ...readEvidenceRefs(raw),
  ];
  if (refs.length === 0) {
    if (stage !== "calendar" && stage !== "user_confirmation") return null;
    refs.push(fallbackEvidenceRef(stage, event, index));
  }
  const source = text(raw.source || raw.source_type || raw.sourceType) || stage;
  const confidence = raw.confidence === undefined || raw.confidence === null
    ? DEFAULT_CONFIDENCE[stage]
    : raw.confidence;
  return {
    display_name: displayName(raw),
    email,
    source,
    evidence_refs: [...new Set(refs)].sort(),
    confidence,
    event_role: eventRole(raw, defaultRole),
    _stage: stage,
    _stageRank: SOURCE_RANK[stage],
  };
}

function mergeConfidence(left, right) {
  if (typeof left === "number" && typeof right === "number") return Math.max(left, right);
  return left === undefined || left === null ? right : left;
}

function mergeCandidate(existing, incoming) {
  const preferred = incoming._stageRank < existing._stageRank ? incoming : existing;
  return {
    display_name: existing.display_name || incoming.display_name,
    email: existing.email,
    source: preferred.source,
    evidence_refs: [...new Set([...existing.evidence_refs, ...incoming.evidence_refs])].sort(),
    confidence: mergeConfidence(existing.confidence, incoming.confidence),
    event_role: existing.event_role || incoming.event_role,
    _stage: preferred._stage,
    _stageRank: Math.min(existing._stageRank, incoming._stageRank),
  };
}

function publicCandidate(candidate) {
  return {
    display_name: candidate.display_name,
    email: candidate.email,
    source: candidate.source,
    evidence_refs: [...candidate.evidence_refs],
    confidence: candidate.confidence,
    event_role: candidate.event_role,
  };
}

function unwrapConfirmation(payload) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) return payload;
  if (payload.selectedCandidate && typeof payload.selectedCandidate === "object") return payload.selectedCandidate;
  if (payload.selected_candidate && typeof payload.selected_candidate === "object") return payload.selected_candidate;
  if (payload.candidate && typeof payload.candidate === "object") return payload.candidate;
  if (payload.confirmedCandidate && typeof payload.confirmedCandidate === "object") return payload.confirmedCandidate;
  if (payload.confirmed_candidate && typeof payload.confirmed_candidate === "object") return payload.confirmed_candidate;
  return payload;
}

function confirmationSelection(payload, existing, context) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) return null;
  const providerRefs = providerEvidenceRefs(payload);
  const selectedEmail = normalizeEmail(
    payload.selectedEmail || payload.selected_email || payload.confirmedEmail || payload.confirmed_email,
  );
  if (selectedEmail) {
    const found = existing.find((candidate) => candidate.email === selectedEmail);
    if (found) {
      return {
        ...found,
        evidence_refs: [...new Set([
          ...found.evidence_refs,
          ...readEvidenceRefs(payload),
          ...providerRefs,
          `user_confirmation:event:${eventReference(context.event)}:selected`,
        ])].sort(),
      };
    }
    return normalizeCandidate({
      email: selectedEmail,
      display_name: payload.display_name || payload.displayName || payload.name,
      evidence_refs: [...readEvidenceRefs(payload), ...providerRefs],
      confidence: payload.confidence,
      event_role: payload.event_role || payload.eventRole,
    }, { stage: "user_confirmation", event: context.event, index: 0, actorSet: context.actorSet,
      defaultRole: "attendee", defaultRefs: providerRefs });
  }

  const selected = unwrapConfirmation(payload);
  const candidates = providerCandidates(selected);
  if (candidates.length === 0) return null;
  const normalized = candidates.map((raw, index) => normalizeCandidate(raw, {
    stage: "user_confirmation", event: context.event, index, actorSet: context.actorSet,
    defaultRole: "attendee", defaultRefs: providerRefs,
  })).filter(Boolean);
  return normalized.length === 1 ? normalized[0] : normalized;
}

function calendarCandidates(event, actorSet) {
  const entries = [];
  for (const organizer of asArray(event && event.organizer)) {
    entries.push({ raw: organizer, role: "organizer", label: "organizer" });
  }
  for (const attendee of asArray(event && event.attendees)) {
    entries.push({ raw: attendee, role: "attendee", label: "attendee" });
  }
  return entries.map(({ raw, role, label }, index) => {
    if (!raw || typeof raw !== "object" || raw.self === true || raw.isSelf === true || isResource(raw) || isDeclined(raw)) {
      return null;
    }
    const email = firstEmail(raw);
    if (!email || actorSet.has(email)) return null;
    const ref = `calendar:event:${eventReference(event)}:${label}:${index}`;
    return normalizeCandidate(raw, {
      stage: "calendar", event, index, actorSet,
      defaultRole: raw.organizer === true ? "organizer" : role, defaultRefs: [ref],
    });
  }).filter(Boolean);
}

function orderedOutput(merged) {
  return [...merged.values()].sort((a, b) => a._stageRank - b._stageRank || a.email.localeCompare(b.email));
}

async function resolveLateRecipients({ uid, event, actorEmails } = {}, deps = {}) {
  const inputEvent = event && typeof event === "object" ? event : {};
  const actorSet = normalizeActorEmails(actorEmails);
  const context = { uid: text(uid), event: inputEvent, actorEmails: [...actorSet] };
  const merged = new Map();
  const evidenceRefs = new Set();

  const add = (raw, stage, index, defaultRole = "attendee", defaultRefs = [], options = {}) => {
    const candidate = normalizeCandidate(raw, {
      stage, event: inputEvent, index, actorSet, defaultRole, defaultRefs, ...options,
    });
    if (!candidate) return;
    for (const ref of candidate.evidence_refs) evidenceRefs.add(ref);
    const prior = merged.get(candidate.email);
    merged.set(candidate.email, prior ? mergeCandidate(prior, candidate) : candidate);
  };

  for (const candidate of calendarCandidates(inputEvent, actorSet)) {
    for (const ref of candidate.evidence_refs) evidenceRefs.add(ref);
    const prior = merged.get(candidate.email);
    merged.set(candidate.email, prior ? mergeCandidate(prior, candidate) : candidate);
  }

  const runStage = async (stage, names) => {
    const provider = providerFunction(deps, names);
    if (!provider) return;
    let payload;
    try {
      payload = await provider.fn(context);
    } catch {
      return;
    }
    const stageEvidenceRefs = providerEvidenceRefs(payload);
    for (const ref of stageEvidenceRefs) evidenceRefs.add(ref);
    const requireApproved = stage === "contacts" && !APPROVED_CONTACT_PROVIDER_NAMES.has(provider.name);
    for (const [index, candidate] of providerCandidates(payload).entries()) {
      add(candidate, stage, index, "attendee", stageEvidenceRefs, { requireApproved });
    }
  };

  await runStage("gmail", PROVIDER_NAMES.gmail);
  await runStage("contacts", PROVIDER_NAMES.contacts);
  await runStage("public_web", PROVIDER_NAMES.public_web);

  let candidates = orderedOutput(merged);
  const webOnly = candidates.length === 1 && candidates[0]._stage === "public_web";
  let status = candidates.length === 0 ? "missing" : (candidates.length === 1 && !webOnly ? "resolved" : "ambiguous");

  if (status !== "resolved") {
    const confirmation = providerFunction(deps, PROVIDER_NAMES.confirmation);
    if (confirmation) {
      let payload;
      try {
        payload = await confirmation.fn({
          ...context,
          candidates: candidates.map(publicCandidate),
          evidenceRefs: [...evidenceRefs].sort(),
          reason: status,
        });
      } catch {
        payload = null;
      }
      for (const ref of providerEvidenceRefs(payload)) evidenceRefs.add(ref);
      const selection = confirmationSelection(payload, candidates, { event: inputEvent, actorSet });
      const selectedCandidates = Array.isArray(selection) ? selection : [selection];
      for (const selected of selectedCandidates) {
        for (const ref of (selected && selected.evidence_refs) || []) evidenceRefs.add(ref);
      }
      if (Array.isArray(selection)) {
        if (selection.length === 1) {
          merged.clear();
          add(selection[0], "user_confirmation", 0);
        }
      } else if (selection) {
        merged.clear();
        add(selection, "user_confirmation", 0);
      }
      candidates = orderedOutput(merged);
      const confirmed = Boolean(selection) && (!Array.isArray(selection) || selection.length === 1);
      if (confirmed) {
        status = candidates.length === 1 ? "resolved" : (candidates.length === 0 ? "missing" : "ambiguous");
      }
    }
  }

  return {
    status,
    candidates: candidates.map(publicCandidate),
    evidenceRefs: [...evidenceRefs].sort(),
  };
}

module.exports = { resolveLateRecipients };
