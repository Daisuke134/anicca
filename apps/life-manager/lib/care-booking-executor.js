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
//      impersonate the person it works for, in this or any other free-text field. A field that cannot
//      CARRY that identification — a maxlength shorter than it, a カナ/フリガナ box, a 姓/名 split —
//      ends the attempt too: a truncated or halved disclosure discloses nothing.
//   5. It never submits a form it would put NOTHING into, and never acts on a requested slot with no
//      timezone offset ("2026-08-08T11:00" is a wall clock, not an instant).
//
// ─── WHAT COMES BACK OUT ────────────────────────────────────────────────────────────────────────
// The outcome carries identifiers, never provider page text: the readback is up to 4000 characters of
// a confirmation screen that echoes the name, phone and email just typed in, and the caller writes
// what it gets here into an append-only log. Any provider-authored fragment that DOES ride out (a
// field label inside a `reason`) is truncated, stripped of URLs and newlines, and quoted in 「」 —
// untrusted text on its way to the user's Telegram is visibly somebody else's words or it is nothing.
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
// A submit happens AT MOST ONCE. After it, any uncertainty at all — the submit threw, the post-submit
// page never loaded, the readback threw, the page shows no confirmation signal — resolves to
// {outcome:"possibly_booked"}, which is reported to the user and NEVER retried. Re-submitting to find
// out whether the first one worked is how you double-book a clinic; not knowing and saying so is the
// honest outcome. The mirror image matters just as much: `submitted` flips only after the click was
// actually DISPATCHED, so a provably-zero-submits failure is reported as the clean failure it is
// rather than as an uncertainty that would block the honest retry forever.
//
// ─── WHAT COUNTS AS A CONFIRMATION ──────────────────────────────────────────────────────────────
// An id the provider handed back through the protocol, or its own "we received your booking" sentence
// with NO negation beside it. 「予約が完了できませんでした」 contains 「予約が完了」, and a 予約番号
// scraped off a login panel is not evidence about the submit we just made — see readConfirmationSignal.
//
// ─── THE DEADLINE ───────────────────────────────────────────────────────────────────────────────
// The whole attempt is raced against its own deadline (75s), under the scheduler's 90s per-tenant
// abandon. An abandoned tick does not stop this function, so without one a hung provider page would
// hold the single OSS steel session after nobody is waiting for it any more.

const { formatU8Identification } = require("./care-identity.js");

const SCHEMA_VERSION = 1;

// A slot we are willing to act on has to name an INSTANT — "…+09:00" or "…Z". "2026-08-08T11:00" is a
// wall clock with no timezone, and every consumer downstream would resolve it differently.
const OFFSET_BEARING_ISO = /T\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})$/i;

// The page-side submit helper throws this BEFORE it dispatches a click. It is the one submit error we
// can read as "provably zero submits"; every other error leaves the outcome genuinely unknown.
const SUBMIT_NEVER_DISPATCHED = /submit control not found/i;

// Under the scheduler's per-tenant abandon (LIFE_USER_TICK_TIMEOUT_MS, 90s) with room to release the
// session before the tick is dropped.
const DEFAULT_DEADLINE_MS = 75_000;
const DEFAULT_LOAD_WAIT_MS = 15_000;

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

// ─── page text is UNTRUSTED INPUT on its way to the user's Telegram ─────────────────────────────
// Every `reason` below quotes a label the PROVIDER's page wrote. A 4000-character label, an embedded
// URL, or a newline that fakes a new paragraph would each be the provider composing part of a message
// the user reads as ours. It rides as a short, single-line, URL-free fragment inside 「」 — visibly
// somebody else's words — or it does not ride at all.
const QUOTE_MAX_CHARS = 40;
function quoted(raw) {
  const cleaned = String(raw || "")
    .replace(/[\u0000-\u001f\u007f]+/g, " ")
    .replace(/(?:https?:\/\/|www\.)\S+/gi, "")
    .replace(/[「」]/g, "")
    .replace(/\s+/g, " ")
    .trim();
  const clipped = cleaned.length > QUOTE_MAX_CHARS ? `${cleaned.slice(0, QUOTE_MAX_CHARS)}…` : cleaned;
  return `「${clipped || "無題の項目"}」`;
}

// A CDP error message can itself carry page-authored text (a page-side exception's description), and
// honest_failure reasons are rendered straight into the user's Telegram. Same rule as `quoted`, one
// size bigger, because these are mostly our own strings.
const ERROR_MAX_CHARS = 80;
function safeError(error) {
  const raw = String((error && error.message) || error || "")
    .replace(/[\u0000-\u001f\u007f]+/g, " ")
    .replace(/(?:https?:\/\/|www\.)\S+/gi, "")
    .replace(/\s+/g, " ")
    .trim();
  return raw.length > ERROR_MAX_CHARS ? `${raw.slice(0, ERROR_MAX_CHARS)}…` : raw;
}

// §10.1 U8 says the name typed into a form is the AI's OWN identification. Three shapes of name field
// cannot carry it, and each one ends the attempt rather than being approximated:
//   - a カナ/フリガナ field: the identification is not a reading of a Japanese name, and inventing one
//     would put the USER's name (in kana) where our own identification belongs.
//   - a 姓/名 split: there is no honest way to cut 「Life Manager（AI secretary, acting for X）」 in two.
//   - a maxlength shorter than the identification: a truncation silently turns the disclosure into
//     something else, and 「Life Manager（AI sec」 is not a disclosure of anything.
const KANA_FIELD = /カナ|かな|フリガナ|ふりがな|ｶﾅ|kana|furigana/i;
const SPLIT_NAME_FIELD = /(?<!姓)姓(?!名)|名字|苗字|\blast[\s_-]*name\b|\bfirst[\s_-]*name\b|\bfamily[\s_-]*name\b|\bgiven[\s_-]*name\b|\b(?:sei|mei)\b/i;
const fieldHaystack = (field) => `${field?.label || ""} ${field?.name || ""}`;

function fieldMaxLength(field) {
  const raw = field?.maxLength ?? field?.maxlength;
  const max = Number(raw);
  return Number.isFinite(max) && max > 0 ? max : null;
}

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
      reason: `この予約経路はログイン（${quoted(label(password))}）が必要で、私はアカウントを持っていません`,
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

    // U8 shape checks run for any field we would TYPE THE IDENTIFICATION INTO (kind "name"), and for
    // any REQUIRED field at all — an optional kana box we leave blank is honest; one we fill is not.
    if (kind === "name" || required) {
      const haystack = fieldHaystack(field);
      if (KANA_FIELD.test(haystack)) {
        return {
          status: "unmappable",
          reason_code: "name_kana_unsupported",
          reason: `予約フォームのふりがな欄（${quoted(label(field))}）に、代理で予約していることを正しく書けません`,
          unresolved: [descriptor],
        };
      }
      if (SPLIT_NAME_FIELD.test(haystack)) {
        return {
          status: "unmappable",
          reason_code: "name_split_unsupported",
          reason: `予約フォームが姓と名を分けて求めており（${quoted(label(field))}）、代理人としての名乗りを分割できません`,
          unresolved: [descriptor],
        };
      }
    }

    if (!kind) {
      if (required) {
        unresolved.push(descriptor);
        return {
          status: "unmappable",
          reason_code: "unmappable_required_field",
          reason: `予約フォームに私が埋められない必須項目があります: ${quoted(label(field))}`,
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
          reason: `予約フォームが希望日時（${quoted(label(field))}）を求めていますが、希望枠が指定されていません`,
          unresolved: [descriptor],
        };
      }
      return {
        status: "unmappable",
        reason_code: "missing_user_field",
        reason: `予約フォームが必須にしている${quoted(label(field))}を、私はまだ預かっていません`,
        unresolved: [descriptor],
      };
    }

    // U8 again: a name box shorter than the identification is refused, never truncated.
    if (kind === "name") {
      const max = fieldMaxLength(field);
      if (max !== null && String(value).length > max) {
        return {
          status: "unmappable",
          reason_code: "identity_too_long_for_field",
          reason: `予約フォームの名前欄（${quoted(label(field))}）が${max}文字までで、代理人としての名乗りが入りきりません`,
          unresolved: [descriptor],
        };
      }
    }
    assignments.push({ selector: field.selector, kind, value });
  }
  // A form we would fill NOTHING into is not this form filler's form. Submitting it would post an
  // empty request to a real provider — an action we could not describe afterwards, let alone report.
  if (assignments.length === 0) {
    return {
      status: "unmappable",
      reason_code: "no_mappable_field",
      reason: "予約フォームの項目を1つも読み取れませんでした",
      unresolved: fields.map((field) => ({ label: label(field), name: field?.name || null, type: field?.type || null, required: field?.required === true })),
    };
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

// 「予約が完了できませんでした」 CONTAINS 「予約が完了」. A substring match on an affirmative phrase is
// therefore not evidence of anything — the sentence that most often carries it is the one saying the
// booking did NOT happen. An affirmative phrase counts only when nothing near it negates it.
const NEGATION_NEAR = /でき(?:ませ|なかっ|ず|かね)|して(?:い)?ませ|されて(?:い)?ませ|受け付けられ|失敗|未完了|エラー|不可|無効|見つかりま|not\s+(?:confirmed|complete|received)|(?:was|were)\s+not|fail(?:ed|ure)|unable|could\s?n[o']?t/i;
const NEGATION_WINDOW_CHARS = 24;

// An affirmative confirmation is a phrase from the bank with no negation in its immediate neighbour-
// hood. Exported through readConfirmationSignal only — the window, not the phrase, is the safety.
function hasAffirmativeConfirmation(text) {
  for (const pattern of CONFIRMED_TEXT) {
    const match = pattern.exec(text);
    if (!match) continue;
    const from = Math.max(0, match.index - NEGATION_WINDOW_CHARS);
    const to = match.index + match[0].length + NEGATION_WINDOW_CHARS;
    if (NEGATION_NEAR.test(text.slice(from, to))) continue;
    return true;
  }
  return false;
}

// A readback is a confirmation ONLY on an explicit signal: an id the provider handed back through the
// PROTOCOL (bookingId / confirmationNumber — structured fields nobody scraped), or its own
// un-negated "received your booking" sentence. Silence is not yes, and neither is a negated yes.
//
// A number SCRAPED out of the page body is different in kind: 「予約番号をお持ちの方はこちら」 sits on
// login panels and lookup forms all day long, and it says nothing about the submit we just made. It is
// therefore accepted only alongside an affirmative sentence, and never on its own.
//
// `text` is deliberately NOT returned: it is up to 4000 characters of the provider's page, which on a
// confirmation screen echoes the name, phone and email that were just typed in. Callers persist this
// object to an append-only log, so what they cannot get here they cannot leak.
function readConfirmationSignal(readback) {
  const text = String(readback?.text || "");
  const bookingId = readback?.bookingId || readback?.booking_id || null;
  const handedBackNumber = readback?.confirmationNumber || readback?.confirmation_number || null;
  const affirmative = hasAffirmativeConfirmation(text);

  let scrapedNumber = null;
  if (!handedBackNumber && affirmative) {
    for (const pattern of NUMBER_PATTERNS) {
      const match = pattern.exec(text);
      if (match) { scrapedNumber = match[1]; break; }
    }
  }
  const number = handedBackNumber || scrapedNumber || null;
  const confirmed = Boolean(bookingId) || Boolean(handedBackNumber) || affirmative;
  return { confirmed, matched_signal: confirmed, number, booking_id: bookingId || null };
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
  // A requested slot with no UTC offset ("2026-08-08T11:00") is not a moment in time: the form value,
  // the reported sentence and the calendar entry would each resolve it in a different timezone. The
  // form flow has to hand over an offset-bearing instant, and until it does this is a clean refusal
  // with zero side effects — not a booking made at a guessed hour.
  if (slotPreference?.startIso && !OFFSET_BEARING_ISO.test(String(slotPreference.startIso))) {
    return failure(candidate, "slot_timezone_missing", "希望日時にタイムゾーンが付いておらず、何時の予約か確定できませんでした");
  }

  const cdp = deps.cdp;
  if (!cdp) return failure(candidate, "browser_unavailable", "予約用のブラウザに接続できませんでした");

  const values = {
    name: user?.name ? formatU8Identification(user.name) : null,
    phone: user?.phone || null,
    email: user?.email || null,
    slotParts: slotParts(slotPreference?.startIso),
  };

  const deadlineMs = Number.isFinite(deps.deadlineMs) ? deps.deadlineMs : DEFAULT_DEADLINE_MS;
  const loadWaitMs = Number.isFinite(deps.loadWaitMs) ? deps.loadWaitMs : DEFAULT_LOAD_WAIT_MS;

  let session = null;
  let sessionId = null;
  let submitted = false;
  let result = null;

  const possibly = (reasonCode, reason) => ({
    schema_version: SCHEMA_VERSION,
    outcome: "possibly_booked",
    provider_id: candidate.provider_id,
    reservation_url: candidate.reservation_url,
    booked_slot: slotPreference?.startIso || null,
    reason_code: reasonCode,
    reason,
    submitted: true,
  });

  // The whole attempt, so the deadline below can race it as one unit.
  const attempt = async () => {
    session = await cdp.createSession();
    sessionId = (session && session.id) || null;
    await cdp.navigate(sessionId, candidate.reservation_url);
    const form = await cdp.readForm(sessionId);
    const plan = planFormPlan(form, values);
    if (plan.status !== "mappable") {
      result = failure(candidate, plan.reason_code, plan.reason, { unresolved_fields: plan.unresolved });
      return;
    }
    for (const assignment of plan.assignments) {
      await cdp.fill(sessionId, assignment.selector, assignment.value);
    }

    // ── the one and only submit ────────────────────────────────────────────────────────────────
    // `submitted` flips only AFTER the click was dispatched. Setting it beforehand made every
    // deterministic "there is no such control" throw look like an ambiguous half-booking: it locked
    // the user out of the honest retry to protect against a submit that provably never happened.
    try {
      await cdp.submit(sessionId, form.submitSelector);
      submitted = true;
    } catch (error) {
      const message = safeError(error);
      if (SUBMIT_NEVER_DISPATCHED.test(message)) {
        result = failure(candidate, "submit_control_missing", "送信ボタンを押せませんでした（フォームの送信操作が見つかりません）");
        return;
      }
      submitted = true;
      result = possibly("submit_outcome_unknown", `送信の結果を確認できませんでした（${message}）。二重予約を避けるため送り直していません`);
      return;
    }

    // A submit usually navigates. Reading the DOM straight after the click reads the PRE-submit page,
    // which is either the form again (→ a false "no confirmation") or a stale banner (→ a false
    // booking). waitForLoad returns early when nothing navigated at all (an in-page/AJAX submit), so
    // this costs nothing on the forms that do not reload.
    if (typeof cdp.waitForLoad === "function") {
      try {
        await cdp.waitForLoad(sessionId, loadWaitMs);
      } catch (error) {
        result = possibly(
          "load_wait_timeout",
          `送信後のページが開き終わりませんでした（${safeError(error)}）。二重予約を避けるため送り直していません`,
        );
        return;
      }
    }

    let readback = null;
    try {
      readback = await cdp.readConfirmation(sessionId);
    } catch (error) {
      result = possibly("readback_unavailable", `送信後の画面を読めませんでした（${safeError(error)}）。二重予約を避けるため送り直していません`);
      return;
    }

    const signal = readConfirmationSignal(readback);
    result = signal.confirmed
      ? {
        schema_version: SCHEMA_VERSION,
        outcome: "booked",
        provider_id: candidate.provider_id,
        reservation_url: candidate.reservation_url,
        booked_slot: slotPreference?.startIso || null,
        // Identifiers only. The page text they came from is never carried out of this function.
        confirmation: { number: signal.number, booking_id: signal.booking_id, matched_signal: true },
        submitted: true,
        unfilled_optional_fields: plan.unfilledOptional,
      }
      : possibly("no_confirmation_signal", "送信はしましたが、予約完了の表示を確認できませんでした。二重予約を避けるため送り直していません");
  };

  // The scheduler abandons a tenant tick at ~90s (LIFE_USER_TICK_TIMEOUT_MS). An abandoned tick does
  // not stop this function, so without a SHORTER deadline of its own a hung provider page keeps the
  // single OSS steel session (§10.0-12) held after the tick is gone — blocking every later booking
  // for every user. Hitting the deadline is an outcome like any other: possibly_booked if the click
  // went out, honest_failure if it did not, and the session released either way by the finally below.
  let deadlineTimer = null;
  const deadline = new Promise((_, reject) => {
    deadlineTimer = setTimeout(() => {
      const error = new Error(`booking deadline exceeded (${deadlineMs}ms)`);
      error.bookingDeadline = true;
      reject(error);
    }, deadlineMs);
    if (typeof deadlineTimer.unref === "function") deadlineTimer.unref();
  });

  try {
    await Promise.race([attempt(), deadline]);
  } catch (error) {
    // A throw BEFORE the submit is an honest failure; a throw after it is already handled above, so
    // reaching here post-submit still must not claim the booking did not happen.
    const message = safeError(error);
    // A createSession that threw after the remote session already existed hands its id back on the
    // error, so the finally can release what would otherwise be an invisible leak.
    if (!sessionId && error && error.sessionId && error.sessionReleased !== true) sessionId = error.sessionId;
    const deadlineHit = Boolean(error && error.bookingDeadline);
    if (submitted) {
      result = possibly(
        deadlineHit ? "booking_deadline_exceeded" : "submit_outcome_unknown",
        `送信の結果を確認できませんでした（${message}）。二重予約を避けるため送り直していません`,
      );
    } else if (deadlineHit) {
      result = failure(candidate, "booking_deadline_exceeded", `予約サイトの応答が時間内に返りませんでした（${message}）`);
    } else {
      result = failure(candidate, "browser_unavailable", `予約サイトを操作できませんでした（${message}）`);
    }
  } finally {
    clearTimeout(deadlineTimer);
    // The OSS steel build allows ONE concurrent session (§10.0-12): a leaked session blocks every
    // later booking for every user, so release is unconditional and its own failure is reported
    // rather than allowed to overwrite the booking outcome.
    if (sessionId) {
      try {
        await cdp.releaseSession(sessionId);
      } catch {
        if (result) result.session_release_failed = true;
      }
    } else if (typeof cdp.releaseAll === "function") {
      // The deadline can fire while createSession is still in flight: there is no id to release, but
      // a session may well exist on the other side. Release-all is the only honest cleanup left.
      try { await cdp.releaseAll(); } catch { /* nothing else to try */ }
    }
  }
  if (sessionId && result) result.session_id = sessionId;
  return result;
}

module.exports = {
  executeBooking,
  formatU8Identification,
  matchFieldKind,
  planFormPlan,
  readConfirmationSignal,
  SUBMIT_NEVER_DISPATCHED,
  FILLABLE_TYPES,
};
