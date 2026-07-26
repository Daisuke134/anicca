"use strict";
// lib/care-booking-executor.js — 11c: the PHYSICAL organ's booking executor.
//
// 11a detects overdue care, 11b finds real providers and judges their reservation route. This module
// is the leg that actually books one: it drives the self-hosted steel-browser rail (§10.0-12,
// private networking only) through the provider's own web form and reads a confirmation back. §9.5
// governs everything here — the AI never phones a provider, and a failure is REPORTED honestly
// rather than dressed up or silently retried.
//
// ─── WHAT THIS FILLER CAN AND CANNOT DO (the honest boundary) ────────────────────────────────────
// This ships a GENERIC, DETERMINISTIC form filler. It maps a field to a value by matching the
// field's visible label / name / input type against ONE fixed vocabulary:
//
//     name     ← 名前 / 氏名 / お名前 / name
//     phone    ← 電話 / TEL / tel / phone
//     email    ← メール / mail / email / e-mail
//     datetime ← 日時 / 希望日 / 予約日 / date / time  (+ input types date/time/datetime-local)
//
// Anything outside that vocabulary is NOT guessed. The rules, in order of how much they matter:
//   1. It never submits a form whose REQUIRED fields it cannot all fill. A 保険証番号 it has no
//      value for, a select/radio slot picker it would have to CHOOSE from, a password field — each
//      one ends the attempt as {outcome:"honest_failure"} with ZERO submits.
//   2. It never invents a value. A required 電話番号 with no phone on the user's row is a failure,
//      not a blank or a placeholder.
//   3. Unmapped OPTIONAL fields are left empty and listed in `unfilled_optional_fields`, so the
//      report says exactly what was left blank.
//   4. §10.1 U8: the name it types is the AI's own identification —
//      「Life Manager（AI secretary, acting for <user>）」 — never the user's bare name. It does not
//      impersonate the person it works for, in this or any other free-text field.
//
// ─── THE FUTURE LLM ASSIST BOUNDARY ──────────────────────────────────────────────────────────────
// Choosing which field is which, and which offered slot to take, are JUDGMENT calls — the kind that
// belongs to a model, not to a keyword table. This atomic deliberately ships the deterministic half
// so the rail is provable today, and shapes the seam for the model to take over tomorrow:
// `matchFieldKind(field)` is a pure function from one field descriptor to a kind-or-null, and
// `planFormFill()` collects EVERY unresolved field (with its label, name and type) into the failure
// it returns. An assist implementation replaces matchFieldKind and inherits every safety rule above
// unchanged — the "never submit what you cannot fully map" gate lives in planFormFill, not in the
// matcher, precisely so a smarter matcher cannot loosen it.
//
// ─── DOUBLE-BOOKING ─────────────────────────────────────────────────────────────────────────────
// A submit happens AT MOST ONCE. After it, any uncertainty at all — the submit threw, the readback
// threw, the page shows no confirmation signal — resolves to {outcome:"possibly_booked"}, which is
// reported to the user and NEVER retried. Re-submitting to find out whether the first one worked is
// how you double-book a clinic; not knowing and saying so is the honest outcome.

const { formatU8Identification } = require("./care-identity.js");

const SCHEMA_VERSION = 1;

// Input types this filler can type into. Everything else (select, radio, checkbox, file, …) is a
// choice, not a transcription, and a required one of those ends the attempt.
const FILLABLE_TYPES = new Set(["text", "tel", "email", "url", "search", "textarea", "date", "time", "datetime-local", "number"]);

const KIND_PATTERNS = [
  ["email", /メール|mail|e-?mail/i],
  ["phone", /電話|tel(?:ephone)?|phone|携帯/i],
  ["datetime", /日時|希望日|予約日|来院日|date|time/i],
  ["name", /氏名|名前|お名前|name/i],
];

// A field descriptor → one of the four kinds, or null when this deterministic matcher does not know.
// Pure: the seam a future LLM assist replaces.
function matchFieldKind(field) {
  const type = String(field?.type || "").toLowerCase();
  if (type === "email") return "email";
  if (type === "tel") return "phone";
  if (type === "date" || type === "time" || type === "datetime-local") return "datetime";
  const haystack = `${field?.label || ""} ${field?.name || ""}`;
  for (const [kind, pattern] of KIND_PATTERNS) {
    if (pattern.test(haystack)) return kind;
  }
  return null;
}

// The literal local clock the ISO string carries — no timezone conversion, because the provider's
// form means the provider's local time and re-deriving it would be a chance to be wrong.
function slotParts(iso) {
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(String(iso || ""));
  if (!match) return null;
  const [, y, mo, d, hh, mm] = match;
  return { date: `${y}-${mo}-${d}`, time: `${hh}:${mm}` };
}

function slotValueFor(type, parts) {
  if (type === "date") return parts.date;
  if (type === "time") return parts.time;
  if (type === "datetime-local") return `${parts.date}T${parts.time}`;
  return `${parts.date} ${parts.time}`;
}

const label = (field) => String(field?.label || field?.name || field?.selector || "(無題の項目)");

// Decide the whole fill BEFORE touching the page: a plan that cannot be completed must cost zero
// keystrokes and zero submits. Returns {status:"mappable", assignments, unfilledOptional}
// or {status:"unmappable", reasonCode, reason, unresolved}.
function planFormPlan(form, values) {
  const fields = Array.isArray(form?.fields) ? form.fields : [];
  if (fields.length === 0) {
    return { status: "unmappable", reason_code: "no_form_fields", reason: "予約フォームの入力欄が見つかりませんでした", unresolved: [] };
  }
  const password = fields.find((field) => String(field?.type || "").toLowerCase() === "password");
  if (password) {
    return {
      status: "unmappable",
      reason_code: "login_required",
      reason: `この予約経路はログイン（${label(password)}）が必要で、私はアカウントを持っていません`,
      unresolved: [{ label: label(password), name: password.name || null, type: password.type || null }],
    };
  }
  if (!form.submitSelector) {
    return { status: "unmappable", reason_code: "no_submit_control", reason: "送信ボタンが見つかりませんでした", unresolved: [] };
  }

  const assignments = [];
  const unfilledOptional = [];
  const unresolved = [];
  for (const field of fields) {
    const required = field?.required === true;
    const type = String(field?.type || "text").toLowerCase();
    const kind = FILLABLE_TYPES.has(type) ? matchFieldKind(field) : null;
    const descriptor = { label: label(field), name: field?.name || null, type: field?.type || null, required };

    if (!kind) {
      if (required) {
        unresolved.push(descriptor);
        return {
          status: "unmappable",
          reason_code: "unmappable_required_field",
          reason: `予約フォームに私が埋められない必須項目があります: ${label(field)}`,
          unresolved,
        };
      }
      unfilledOptional.push(label(field));
      continue;
    }

    const value = kind === "datetime"
      ? (values.slotParts ? slotValueFor(type, values.slotParts) : null)
      : values[kind];
    if (value === null || value === undefined || value === "") {
      if (!required) { unfilledOptional.push(label(field)); continue; }
      if (kind === "datetime") {
        return {
          status: "unmappable",
          reason_code: "missing_slot_preference",
          reason: `予約フォームが希望日時（${label(field)}）を求めていますが、希望枠が指定されていません`,
          unresolved: [descriptor],
        };
      }
      return {
        status: "unmappable",
        reason_code: "missing_user_field",
        reason: `予約フォームが必須にしている${label(field)}を、私はまだ預かっていません`,
        unresolved: [descriptor],
      };
    }
    assignments.push({ selector: field.selector, kind, value });
  }
  return { status: "mappable", assignments, unfilledOptional };
}

const CONFIRMED_TEXT = [
  /予約を?受け付けました/,
  /ご?予約(?:が)?完了/,
  /予約(?:が)?確定/,
  /reservation (?:is )?confirmed/i,
  /booking confirmed/i,
];
const NUMBER_PATTERNS = [
  /(?:予約|受付|確認)番号[\s:：#]*([A-Za-z0-9][A-Za-z0-9-]{1,})/,
  /confirmation (?:number|code|id)[\s:：#]*([A-Za-z0-9][A-Za-z0-9-]{1,})/i,
];

// A readback is a confirmation ONLY on an explicit signal: a booking id the provider handed back, a
// reservation number, or the provider's own "received your booking" sentence. Silence is not yes.
function readConfirmationSignal(readback) {
  const text = String(readback?.text || "");
  const bookingId = readback?.bookingId || readback?.booking_id || null;
  let number = readback?.confirmationNumber || readback?.confirmation_number || null;
  if (!number) {
    for (const pattern of NUMBER_PATTERNS) {
      const match = pattern.exec(text);
      if (match) { number = match[1]; break; }
    }
  }
  const confirmed = Boolean(bookingId) || Boolean(number) || CONFIRMED_TEXT.some((p) => p.test(text));
  return { confirmed, number: number || null, booking_id: bookingId || null, text };
}

function failure(candidate, reasonCode, reason, extra = {}) {
  return {
    schema_version: SCHEMA_VERSION,
    outcome: "honest_failure",
    provider_id: candidate?.provider_id || null,
    reservation_url: candidate?.reservation_url || null,
    reason_code: reasonCode,
    reason,
    submitted: false,
    ...extra,
  };
}

async function executeBooking({ candidate, user, slotPreference, deps = {} } = {}) {
  const route = candidate?.reservation_route || null;
  if (route === "email") {
    // §9.5 allows email booking; 11c does not implement it yet. Saying so beats pretending the route
    // does not exist, and beats opening a browser at a mailto: URL.
    return failure(candidate, "email_route_not_implemented", "この店舗はメール予約のみで、メール予約は私がまだ実装できていません");
  }
  if (route !== "web" || !candidate?.reservation_url) {
    return failure(candidate, "route_not_web", "この店舗にはネット予約の入口がありません（§9.5 により電話はかけません）");
  }

  const cdp = deps.cdp;
  if (!cdp) return failure(candidate, "browser_unavailable", "予約用のブラウザに接続できませんでした");

  const values = {
    name: user?.name ? formatU8Identification(user.name) : null,
    phone: user?.phone || null,
    email: user?.email || null,
    slotParts: slotParts(slotPreference?.startIso),
  };

  let session = null;
  let submitted = false;
  let result = null;
  try {
    session = await cdp.createSession();
    await cdp.navigate(session.id, candidate.reservation_url);
    const form = await cdp.readForm(session.id);
    const plan = planFormPlan(form, values);
    if (plan.status !== "mappable") {
      result = failure(candidate, plan.reason_code, plan.reason, { unresolved_fields: plan.unresolved });
    } else {
      for (const assignment of plan.assignments) {
        await cdp.fill(session.id, assignment.selector, assignment.value);
      }
      // ── the one and only submit ──────────────────────────────────────────────────────────────
      try {
        submitted = true;
        await cdp.submit(session.id, form.submitSelector);
      } catch (error) {
        result = {
          schema_version: SCHEMA_VERSION,
          outcome: "possibly_booked",
          provider_id: candidate.provider_id,
          reservation_url: candidate.reservation_url,
          booked_slot: slotPreference?.startIso || null,
          reason_code: "submit_outcome_unknown",
          reason: `送信の結果を確認できませんでした（${String((error && error.message) || error)}）。二重予約を避けるため送り直していません`,
          submitted: true,
        };
      }
      if (!result) {
        let readback = null;
        try {
          readback = await cdp.readConfirmation(session.id);
        } catch (error) {
          result = {
            schema_version: SCHEMA_VERSION,
            outcome: "possibly_booked",
            provider_id: candidate.provider_id,
            reservation_url: candidate.reservation_url,
            booked_slot: slotPreference?.startIso || null,
            reason_code: "readback_unavailable",
            reason: `送信後の画面を読めませんでした（${String((error && error.message) || error)}）。二重予約を避けるため送り直していません`,
            submitted: true,
          };
        }
        if (!result) {
          const signal = readConfirmationSignal(readback);
          result = signal.confirmed
            ? {
              schema_version: SCHEMA_VERSION,
              outcome: "booked",
              provider_id: candidate.provider_id,
              reservation_url: candidate.reservation_url,
              booked_slot: slotPreference?.startIso || null,
              confirmation: { number: signal.number, booking_id: signal.booking_id, text: signal.text },
              submitted: true,
              unfilled_optional_fields: plan.unfilledOptional,
            }
            : {
              schema_version: SCHEMA_VERSION,
              outcome: "possibly_booked",
              provider_id: candidate.provider_id,
              reservation_url: candidate.reservation_url,
              booked_slot: slotPreference?.startIso || null,
              reason_code: "no_confirmation_signal",
              reason: "送信はしましたが、予約完了の表示を確認できませんでした。二重予約を避けるため送り直していません",
              submitted: true,
            };
        }
      }
    }
  } catch (error) {
    // A throw BEFORE the submit is an honest failure; a throw after it is already handled above, so
    // reaching here post-submit still must not claim the booking did not happen.
    const message = String((error && error.message) || error);
    result = submitted
      ? {
        schema_version: SCHEMA_VERSION,
        outcome: "possibly_booked",
        provider_id: candidate.provider_id,
        reservation_url: candidate.reservation_url,
        booked_slot: slotPreference?.startIso || null,
        reason_code: "submit_outcome_unknown",
        reason: `送信の結果を確認できませんでした（${message}）。二重予約を避けるため送り直していません`,
        submitted: true,
      }
      : failure(candidate, "browser_unavailable", `予約サイトを操作できませんでした（${message}）`);
  } finally {
    // The OSS steel build allows ONE concurrent session (§10.0-12): a leaked session blocks every
    // later booking for every user, so release is unconditional and its own failure is reported
    // rather than allowed to overwrite the booking outcome.
    if (session && session.id) {
      try {
        await cdp.releaseSession(session.id);
      } catch {
        if (result) result.session_release_failed = true;
      }
    }
  }
  if (session && session.id && result) result.session_id = session.id;
  return result;
}

module.exports = {
  executeBooking,
  formatU8Identification,
  matchFieldKind,
  planFormPlan,
  readConfirmationSignal,
  FILLABLE_TYPES,
};
