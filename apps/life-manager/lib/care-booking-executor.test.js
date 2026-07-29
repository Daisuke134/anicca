"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const {
  executeBooking,
  formatU8Identification,
  matchFieldKind,
  readConfirmationSignal,
} = require("./care-booking-executor.js");

const USER = Object.freeze({ uid: "u1", name: "山田太郎", phone: "+810000000000", email: "y@example.com" });
const WEB_CANDIDATE = Object.freeze({
  provider_id: "places/ChIJexample",
  public_name: "丸の内内科クリニック",
  reservation_route: "web",
  reservation_url: "https://mrweb-yoyaku.example.jp/reserve",
});
const SLOT = Object.freeze({ startIso: "2026-08-06T18:00:00+09:00" });

// A CDP client the executor drives. Every call is recorded so a test can prove what did NOT happen
// (zero submits, session released) — the negative assertions are the point of this atomic.
function fakeCdp(overrides = {}) {
  const calls = [];
  const client = {
    calls,
    async createSession() {
      calls.push(["createSession"]);
      return { id: "sess-1", websocketUrl: "ws://steel-browser.railway.internal:8080/" };
    },
    async navigate(sessionId, url) { calls.push(["navigate", sessionId, url]); },
    async readForm(sessionId) {
      calls.push(["readForm", sessionId]);
      return {
        submitSelector: "#submit",
        fields: [
          { selector: "#n", label: "お名前", name: "name", type: "text", required: true },
          { selector: "#t", label: "電話番号", name: "tel", type: "tel", required: true },
          { selector: "#e", label: "メールアドレス", name: "email", type: "email", required: true },
          { selector: "#d", label: "ご希望日時", name: "datetime", type: "datetime-local", required: true },
        ],
      };
    },
    async fill(sessionId, selector, value) { calls.push(["fill", sessionId, selector, value]); },
    async submit(sessionId, selector) { calls.push(["submit", sessionId, selector]); },
    async readConfirmation(sessionId) {
      calls.push(["readConfirmation", sessionId]);
      return { text: "ご予約を受け付けました。予約番号: A1B2C3", url: "https://mrweb-yoyaku.example.jp/done" };
    },
    async releaseSession(sessionId) { calls.push(["releaseSession", sessionId]); },
  };
  return Object.assign(client, overrides);
}

const kinds = (calls, kind) => calls.filter((call) => call[0] === kind);

test("U8: the identification never impersonates the user", () => {
  assert.equal(
    formatU8Identification("山田太郎"),
    "Life Manager（AI secretary, acting for 山田太郎）",
  );
});

test("label matching is deterministic over the documented vocabulary only", () => {
  assert.equal(matchFieldKind({ label: "お名前", name: "name", type: "text" }), "name");
  assert.equal(matchFieldKind({ label: "氏名", name: "kanji", type: "text" }), "name");
  assert.equal(matchFieldKind({ label: "電話番号", name: "tel", type: "tel" }), "phone");
  assert.equal(matchFieldKind({ label: "メールアドレス", name: "mail", type: "email" }), "email");
  assert.equal(matchFieldKind({ label: "ご希望日時", name: "dt", type: "datetime-local" }), "datetime");
  assert.equal(matchFieldKind({ label: "第一希望日", name: "d1", type: "date" }), "datetime");
  assert.equal(matchFieldKind({ label: "保険証番号", name: "insurance", type: "text" }), null);
});

test("happy path: fills U8 name, submits once, reads the confirmation back, releases the session", async () => {
  const cdp = fakeCdp();
  const result = await executeBooking({
    candidate: WEB_CANDIDATE, user: USER, slotPreference: SLOT, deps: { cdp },
  });

  assert.equal(result.outcome, "booked");
  assert.equal(result.provider_id, WEB_CANDIDATE.provider_id);
  assert.equal(result.confirmation.number, "A1B2C3");
  assert.equal(result.booked_slot, SLOT.startIso);
  assert.equal(result.submitted, true);

  assert.equal(kinds(cdp.calls, "submit").length, 1, "exactly one submit");
  assert.equal(kinds(cdp.calls, "releaseSession").length, 1, "session released");
  assert.deepEqual(kinds(cdp.calls, "navigate")[0], ["navigate", "sess-1", WEB_CANDIDATE.reservation_url]);

  const filled = kinds(cdp.calls, "fill").map(([, , selector, value]) => [selector, value]);
  assert.deepEqual(filled, [
    ["#n", "Life Manager（AI secretary, acting for 山田太郎）"],
    ["#t", "+810000000000"],
    ["#e", "y@example.com"],
    ["#d", "2026-08-06T18:00"],
  ]);
});

test("a field it cannot map and cannot leave empty is an honest failure with ZERO submits", async () => {
  const cdp = fakeCdp({
    async readForm(sessionId) {
      this.calls.push(["readForm", sessionId]);
      return {
        submitSelector: "#submit",
        fields: [
          { selector: "#n", label: "お名前", name: "name", type: "text", required: true },
          { selector: "#i", label: "保険証番号", name: "insurance", type: "text", required: true },
        ],
      };
    },
  });
  const result = await executeBooking({
    candidate: WEB_CANDIDATE, user: USER, slotPreference: SLOT, deps: { cdp },
  });

  assert.equal(result.outcome, "honest_failure");
  assert.equal(result.reason_code, "unmappable_required_field");
  assert.match(result.reason, /保険証番号/);
  assert.equal(result.submitted, false);
  assert.equal(kinds(cdp.calls, "submit").length, 0, "never submits a form it cannot fully map");
  assert.equal(kinds(cdp.calls, "fill").length, 0, "no partial fill of a doomed form");
  assert.equal(kinds(cdp.calls, "releaseSession").length, 1);
});

test("a password field means the route needs a login this atomic does not own", async () => {
  const cdp = fakeCdp({
    async readForm(sessionId) {
      this.calls.push(["readForm", sessionId]);
      return {
        submitSelector: "#login",
        fields: [
          { selector: "#u", label: "ID", name: "userid", type: "text", required: true },
          { selector: "#p", label: "パスワード", name: "password", type: "password", required: true },
        ],
      };
    },
  });
  const result = await executeBooking({
    candidate: WEB_CANDIDATE, user: USER, slotPreference: SLOT, deps: { cdp },
  });
  assert.equal(result.outcome, "honest_failure");
  assert.equal(result.reason_code, "login_required");
  assert.equal(kinds(cdp.calls, "submit").length, 0);
});

test("a required field whose value the user profile lacks is an honest failure, never a guess", async () => {
  const cdp = fakeCdp();
  const result = await executeBooking({
    candidate: WEB_CANDIDATE,
    user: { ...USER, phone: null },
    slotPreference: SLOT,
    deps: { cdp },
  });
  assert.equal(result.outcome, "honest_failure");
  assert.equal(result.reason_code, "missing_user_field");
  assert.match(result.reason, /電話番号/);
  assert.equal(kinds(cdp.calls, "submit").length, 0);
  assert.equal(kinds(cdp.calls, "fill").length, 0);
});

test("no requested slot: the executor does not invent a datetime", async () => {
  const cdp = fakeCdp();
  const result = await executeBooking({
    candidate: WEB_CANDIDATE, user: USER, slotPreference: null, deps: { cdp },
  });
  assert.equal(result.outcome, "honest_failure");
  assert.equal(result.reason_code, "missing_slot_preference");
  assert.equal(kinds(cdp.calls, "submit").length, 0);
});

test("a select/radio slot picker is a judgment call this deterministic filler refuses", async () => {
  const cdp = fakeCdp({
    async readForm(sessionId) {
      this.calls.push(["readForm", sessionId]);
      return {
        submitSelector: "#submit",
        fields: [
          { selector: "#n", label: "お名前", name: "name", type: "text", required: true },
          { selector: "#s", label: "ご希望日時", name: "slot", type: "select", required: true },
        ],
      };
    },
  });
  const result = await executeBooking({
    candidate: WEB_CANDIDATE, user: USER, slotPreference: SLOT, deps: { cdp },
  });
  assert.equal(result.outcome, "honest_failure");
  assert.equal(result.reason_code, "unmappable_required_field");
  assert.equal(kinds(cdp.calls, "submit").length, 0);
});

test("a form with no submit control never gets filled", async () => {
  const cdp = fakeCdp({
    async readForm(sessionId) {
      this.calls.push(["readForm", sessionId]);
      return { submitSelector: null, fields: [{ selector: "#n", label: "お名前", name: "name", type: "text", required: true }] };
    },
  });
  const result = await executeBooking({
    candidate: WEB_CANDIDATE, user: USER, slotPreference: SLOT, deps: { cdp },
  });
  assert.equal(result.outcome, "honest_failure");
  assert.equal(result.reason_code, "no_submit_control");
  assert.equal(kinds(cdp.calls, "fill").length, 0);
});

test("optional fields it cannot map are left empty and reported, not guessed", async () => {
  const cdp = fakeCdp({
    async readForm(sessionId) {
      this.calls.push(["readForm", sessionId]);
      return {
        submitSelector: "#submit",
        fields: [
          { selector: "#n", label: "お名前", name: "name", type: "text", required: true },
          { selector: "#m", label: "ご相談内容", name: "memo", type: "textarea", required: false },
        ],
      };
    },
  });
  const result = await executeBooking({
    candidate: WEB_CANDIDATE, user: USER, slotPreference: SLOT, deps: { cdp },
  });
  assert.equal(result.outcome, "booked");
  assert.deepEqual(result.unfilled_optional_fields, ["ご相談内容"]);
  assert.deepEqual(
    kinds(cdp.calls, "fill").map(([, , selector]) => selector),
    ["#n"],
    "the unmapped optional field is left empty",
  );
});

test("a submit that throws is possibly-booked — it is NEVER retried", async () => {
  let submits = 0;
  const cdp = fakeCdp({
    async submit(sessionId, selector) {
      submits += 1;
      this.calls.push(["submit", sessionId, selector]);
      throw new Error("socket hang up");
    },
  });
  const result = await executeBooking({
    candidate: WEB_CANDIDATE, user: USER, slotPreference: SLOT, deps: { cdp },
  });
  assert.equal(result.outcome, "possibly_booked");
  assert.equal(result.reason_code, "submit_outcome_unknown");
  assert.equal(result.submitted, true);
  assert.equal(submits, 1, "one attempt, never a second");
  assert.equal(kinds(cdp.calls, "releaseSession").length, 1);
});

test("a submit with no confirmation signal is possibly-booked, not booked and not retried", async () => {
  const cdp = fakeCdp({
    async readConfirmation(sessionId) {
      this.calls.push(["readConfirmation", sessionId]);
      return { text: "送信中です…", url: "https://mrweb-yoyaku.example.jp/reserve" };
    },
  });
  const result = await executeBooking({
    candidate: WEB_CANDIDATE, user: USER, slotPreference: SLOT, deps: { cdp },
  });
  assert.equal(result.outcome, "possibly_booked");
  assert.equal(result.reason_code, "no_confirmation_signal");
  assert.equal(kinds(cdp.calls, "submit").length, 1);
});

test("a readback that throws is possibly-booked, not a failure", async () => {
  const cdp = fakeCdp({
    async readConfirmation(sessionId) {
      this.calls.push(["readConfirmation", sessionId]);
      throw new Error("navigation timeout");
    },
  });
  const result = await executeBooking({
    candidate: WEB_CANDIDATE, user: USER, slotPreference: SLOT, deps: { cdp },
  });
  assert.equal(result.outcome, "possibly_booked");
  assert.equal(result.reason_code, "readback_unavailable");
  assert.equal(kinds(cdp.calls, "submit").length, 1);
});

test("the OSS single-session rail is released even when the page work throws", async () => {
  const cdp = fakeCdp({
    async readForm(sessionId) {
      this.calls.push(["readForm", sessionId]);
      throw new Error("CDP target crashed");
    },
  });
  const result = await executeBooking({
    candidate: WEB_CANDIDATE, user: USER, slotPreference: SLOT, deps: { cdp },
  });
  assert.equal(result.outcome, "honest_failure");
  assert.equal(result.reason_code, "browser_unavailable");
  assert.equal(kinds(cdp.calls, "releaseSession").length, 1, "finally releases the one OSS session");
});

test("a release that throws never masks the booking outcome", async () => {
  const cdp = fakeCdp({
    async releaseSession(sessionId) {
      this.calls.push(["releaseSession", sessionId]);
      throw new Error("503");
    },
  });
  const result = await executeBooking({
    candidate: WEB_CANDIDATE, user: USER, slotPreference: SLOT, deps: { cdp },
  });
  assert.equal(result.outcome, "booked");
  assert.equal(result.session_release_failed, true);
});

test("a non-web route is refused before any browser session is created", async () => {
  const cdp = fakeCdp();
  const result = await executeBooking({
    candidate: { ...WEB_CANDIDATE, reservation_route: "phone_only", reservation_url: null },
    user: USER,
    slotPreference: SLOT,
    deps: { cdp },
  });
  assert.equal(result.outcome, "honest_failure");
  assert.equal(result.reason_code, "route_not_web");
  assert.equal(cdp.calls.length, 0, "no steel session for a route we cannot drive");
});

test("the email route is honestly declared unimplemented, not silently attempted", async () => {
  const cdp = fakeCdp();
  const result = await executeBooking({
    candidate: { ...WEB_CANDIDATE, reservation_route: "email", reservation_url: "mailto:a@b.jp" },
    user: USER,
    slotPreference: SLOT,
    deps: { cdp },
  });
  assert.equal(result.outcome, "honest_failure");
  assert.equal(result.reason_code, "email_route_not_implemented");
  assert.equal(cdp.calls.length, 0);
});

test("a booking id handed back by the provider counts as confirmation", async () => {
  const cdp = fakeCdp({
    async readConfirmation(sessionId) {
      this.calls.push(["readConfirmation", sessionId]);
      return { text: "完了", bookingId: "BK-77" };
    },
  });
  const result = await executeBooking({
    candidate: WEB_CANDIDATE, user: USER, slotPreference: SLOT, deps: { cdp },
  });
  assert.equal(result.outcome, "booked");
  assert.equal(result.confirmation.booking_id, "BK-77");
});

// ─── review findings ────────────────────────────────────────────────────────────────────────────

// 🔴 Finding 2: "2026-08-08T11:00" is not a moment in time — everything downstream (the form value,
// the report sentence, the calendar entry) would each pick a different timezone for it.
test("a requested slot with no timezone offset is refused before any browser session", async () => {
  const cdp = fakeCdp();
  const result = await executeBooking({
    candidate: WEB_CANDIDATE, user: USER, slotPreference: { startIso: "2026-08-08T11:00" }, deps: { cdp },
  });
  assert.equal(result.outcome, "honest_failure");
  assert.equal(result.reason_code, "slot_timezone_missing");
  assert.equal(result.submitted, false);
  assert.equal(cdp.calls.length, 0, "no steel session for a slot we cannot pin to a real instant");
});

// 🔴 Finding 3: the readback text is up to 4000 chars of the provider's page — it echoes the name,
// phone and email that were just typed in. The outcome keeps the identifiers, never the page.
test("the confirmation keeps identifiers and drops the provider page text entirely", async () => {
  const cdp = fakeCdp();
  const result = await executeBooking({
    candidate: WEB_CANDIDATE, user: USER, slotPreference: SLOT, deps: { cdp },
  });
  assert.deepEqual(result.confirmation, { number: "A1B2C3", booking_id: null, matched_signal: true });
  assert.ok(!JSON.stringify(result).includes("ご予約を受け付けました"), "no page text anywhere in the outcome");
});

// 🔴 Finding 4: 「予約が完了できませんでした」 contains 「予約が完了」. An affirmative phrase with a
// negation beside it is a REFUSAL, and reading it as a booking is the exact fabricated success 11d bans.
test("a negated confirmation sentence is not a confirmation", () => {
  assert.equal(readConfirmationSignal({ text: "予約が完了できませんでした。時間をおいてお試しください。" }).confirmed, false);
  assert.equal(readConfirmationSignal({ text: "エラー：ご予約を受け付けませんでした" }).confirmed, false);
  assert.equal(readConfirmationSignal({ text: "予約の確定に失敗しました。予約が完了していません。" }).confirmed, false);
  assert.equal(readConfirmationSignal({ text: "ご予約を受け付けました。" }).confirmed, true);
  assert.equal(readConfirmationSignal({ text: "reservation confirmed" }).confirmed, true);
  assert.equal(readConfirmationSignal({ text: "booking could not be confirmed" }).confirmed, false);
});

test("a page that says the booking FAILED is possibly_booked, never booked", async () => {
  const cdp = fakeCdp({
    async readConfirmation(sessionId) {
      this.calls.push(["readConfirmation", sessionId]);
      return { text: "予約が完了できませんでした。お手数ですが再度お試しください。" };
    },
  });
  const result = await executeBooking({ candidate: WEB_CANDIDATE, user: USER, slotPreference: SLOT, deps: { cdp } });
  assert.equal(result.outcome, "possibly_booked");
  assert.equal(result.reason_code, "no_confirmation_signal");
});

// 🟡 Finding 10: a 予約番号 scraped off a login panel is not evidence that THIS submit booked anything.
test("a 予約番号 scraped without any affirmative confirmation is not a booking", async () => {
  const cdp = fakeCdp({
    async readConfirmation(sessionId) {
      this.calls.push(["readConfirmation", sessionId]);
      return { text: "ログイン\n予約番号: A1B2C3 をお持ちの方はこちらから照会できます" };
    },
  });
  const result = await executeBooking({ candidate: WEB_CANDIDATE, user: USER, slotPreference: SLOT, deps: { cdp } });
  assert.equal(result.outcome, "possibly_booked");
  assert.equal(result.reason_code, "no_confirmation_signal");
});

test("a confirmation number the provider handed back structurally still counts", async () => {
  const cdp = fakeCdp({
    async readConfirmation(sessionId) {
      this.calls.push(["readConfirmation", sessionId]);
      return { text: "", confirmationNumber: "R-9" };
    },
  });
  const result = await executeBooking({ candidate: WEB_CANDIDATE, user: USER, slotPreference: SLOT, deps: { cdp } });
  assert.equal(result.outcome, "booked");
  assert.equal(result.confirmation.number, "R-9");
});

// 🔴 Finding 6: a submit control that was never clicked is ZERO submits — reporting it as
// possibly_booked invents an uncertainty that does not exist and blocks the honest retry forever.
test("a submit control that could not be clicked is an honest failure with zero submits", async () => {
  const cdp = fakeCdp({
    async submit(sessionId, selector) {
      this.calls.push(["submit", sessionId, selector]);
      throw new Error("page evaluate failed: Error: submit control not found");
    },
  });
  const result = await executeBooking({ candidate: WEB_CANDIDATE, user: USER, slotPreference: SLOT, deps: { cdp } });
  assert.equal(result.outcome, "honest_failure");
  assert.equal(result.reason_code, "submit_control_missing");
  assert.equal(result.submitted, false, "the click was never dispatched");
  assert.equal(kinds(cdp.calls, "releaseSession").length, 1);
});

// 🔴 Finding 7: without a load wait the readback reads the PRE-submit page — a stale form that shows
// no confirmation, or worse a stale success banner from an earlier step.
test("the confirmation is read only after the post-submit load has been awaited", async () => {
  const order = [];
  const cdp = fakeCdp({
    async submit(sessionId, selector) { this.calls.push(["submit", sessionId, selector]); order.push("submit"); },
    async waitForLoad(sessionId, timeoutMs) {
      this.calls.push(["waitForLoad", sessionId, timeoutMs]);
      order.push("waitForLoad");
      return { loaded: true };
    },
    async readConfirmation(sessionId) {
      this.calls.push(["readConfirmation", sessionId]);
      order.push("readConfirmation");
      return { text: "ご予約を受け付けました。予約番号: A1B2C3" };
    },
  });
  const result = await executeBooking({ candidate: WEB_CANDIDATE, user: USER, slotPreference: SLOT, deps: { cdp } });
  assert.deepEqual(order, ["submit", "waitForLoad", "readConfirmation"]);
  assert.equal(result.outcome, "booked");
  const [, , timeoutMs] = kinds(cdp.calls, "waitForLoad")[0];
  assert.ok(Number.isFinite(timeoutMs) && timeoutMs > 0, "the load wait is bounded");
});

test("a post-submit load that never lands is possibly_booked, and the stale page is never read", async () => {
  const cdp = fakeCdp({
    async waitForLoad(sessionId) {
      this.calls.push(["waitForLoad", sessionId]);
      throw new Error("CDP timeout: page load (15000ms)");
    },
  });
  const result = await executeBooking({ candidate: WEB_CANDIDATE, user: USER, slotPreference: SLOT, deps: { cdp } });
  assert.equal(result.outcome, "possibly_booked");
  assert.equal(result.reason_code, "load_wait_timeout");
  assert.equal(result.submitted, true);
  assert.equal(kinds(cdp.calls, "readConfirmation").length, 0, "a stale page is never read as a confirmation");
});

// 🟡 Finding 11: the label text comes from the provider's page — untrusted input on its way to the
// user's Telegram. It rides as a QUOTED, truncated, single-line fragment or not at all.
test("untrusted page label text is quoted, truncated and stripped before it reaches the report", async () => {
  const nasty = `保険証番号\nhttps://evil.example/steal?u=1 ${"あ".repeat(120)}`;
  const cdp = fakeCdp({
    async readForm(sessionId) {
      this.calls.push(["readForm", sessionId]);
      return {
        submitSelector: "#submit",
        fields: [
          { selector: "#n", label: "お名前", name: "name", type: "text", required: true },
          { selector: "#i", label: nasty, name: "insurance", type: "text", required: true },
        ],
      };
    },
  });
  const result = await executeBooking({ candidate: WEB_CANDIDATE, user: USER, slotPreference: SLOT, deps: { cdp } });
  assert.equal(result.outcome, "honest_failure");
  assert.doesNotMatch(result.reason, /https?:\/\//, "no URL survives into the message");
  assert.doesNotMatch(result.reason, /\n/, "no newline survives into the message");
  assert.match(result.reason, /「[^」]{1,41}」/, "the page's words are quoted as foreign text");
  assert.ok(result.reason.length < 120, `the reason stays short, got ${result.reason.length}`);
});

// 🟡 Finding 12: U8 says the typed name is the AI's own identification. A field too short to hold it,
// a カナ field, or a 姓/名 split cannot carry that identification — and truncating it would be an
// impersonation of the user by omission.
test("a name field too short for the U8 identification is an honest failure, never a truncation", async () => {
  const cdp = fakeCdp({
    async readForm(sessionId) {
      this.calls.push(["readForm", sessionId]);
      return {
        submitSelector: "#submit",
        fields: [{ selector: "#n", label: "お名前", name: "name", type: "text", required: true, maxLength: 10 }],
      };
    },
  });
  const result = await executeBooking({ candidate: WEB_CANDIDATE, user: USER, slotPreference: SLOT, deps: { cdp } });
  assert.equal(result.outcome, "honest_failure");
  assert.equal(result.reason_code, "identity_too_long_for_field");
  assert.equal(kinds(cdp.calls, "fill").length, 0);
  assert.equal(kinds(cdp.calls, "submit").length, 0);
});

test("a カナ name field cannot carry the delegation identification", async () => {
  const cdp = fakeCdp({
    async readForm(sessionId) {
      this.calls.push(["readForm", sessionId]);
      return {
        submitSelector: "#submit",
        fields: [{ selector: "#k", label: "お名前（フリガナ）", name: "name_kana", type: "text", required: true }],
      };
    },
  });
  const result = await executeBooking({ candidate: WEB_CANDIDATE, user: USER, slotPreference: SLOT, deps: { cdp } });
  assert.equal(result.outcome, "honest_failure");
  assert.equal(result.reason_code, "name_kana_unsupported");
  assert.equal(kinds(cdp.calls, "submit").length, 0);
});

test("a 姓/名 split name field is refused rather than half-filled", async () => {
  const cdp = fakeCdp({
    async readForm(sessionId) {
      this.calls.push(["readForm", sessionId]);
      return {
        submitSelector: "#submit",
        fields: [
          { selector: "#s", label: "お名前（姓）", name: "sei", type: "text", required: true },
          { selector: "#m", label: "お名前（名）", name: "mei", type: "text", required: true },
        ],
      };
    },
  });
  const result = await executeBooking({ candidate: WEB_CANDIDATE, user: USER, slotPreference: SLOT, deps: { cdp } });
  assert.equal(result.outcome, "honest_failure");
  assert.equal(result.reason_code, "name_split_unsupported");
  assert.equal(kinds(cdp.calls, "fill").length, 0);
});

// 🟡 Finding 16 (executor half): a form the vocabulary maps NOTHING in must never be submitted —
// an empty POST to a provider is a request we cannot describe, let alone report honestly.
test("a form nothing maps into is never submitted", async () => {
  const cdp = fakeCdp({
    async readForm(sessionId) {
      this.calls.push(["readForm", sessionId]);
      return {
        submitSelector: "#submit",
        fields: [{ selector: "#q", label: "サイト内検索", name: "q", type: "search", required: false }],
      };
    },
  });
  const result = await executeBooking({ candidate: WEB_CANDIDATE, user: USER, slotPreference: SLOT, deps: { cdp } });
  assert.equal(result.outcome, "honest_failure");
  assert.equal(result.reason_code, "no_mappable_field");
  assert.equal(kinds(cdp.calls, "submit").length, 0);
});

// 🟡 Finding 13: the scheduler abandons a tenant tick at 90s. Without its own shorter deadline the
// booking can hold the single OSS steel session past that abandon and block every later booking.
test("a hung page hits the executor's own deadline and the session is still released", async () => {
  const cdp = fakeCdp({
    async readForm(sessionId) {
      this.calls.push(["readForm", sessionId]);
      await new Promise((resolve) => setTimeout(resolve, 300));
      return { submitSelector: "#submit", fields: [] };
    },
  });
  const result = await executeBooking({
    candidate: WEB_CANDIDATE, user: USER, slotPreference: SLOT, deps: { cdp, deadlineMs: 25 },
  });
  assert.equal(result.outcome, "honest_failure");
  assert.equal(result.reason_code, "booking_deadline_exceeded");
  assert.equal(result.submitted, false);
  assert.equal(kinds(cdp.calls, "releaseSession").length, 1, "the deadline still frees the single OSS session");
});

test("a deadline hit AFTER the submit is possibly_booked, never a clean failure", async () => {
  const cdp = fakeCdp({
    async readConfirmation(sessionId) {
      this.calls.push(["readConfirmation", sessionId]);
      await new Promise((resolve) => setTimeout(resolve, 300));
      return { text: "" };
    },
  });
  const result = await executeBooking({
    candidate: WEB_CANDIDATE, user: USER, slotPreference: SLOT, deps: { cdp, deadlineMs: 25 },
  });
  assert.equal(result.outcome, "possibly_booked");
  assert.equal(result.reason_code, "booking_deadline_exceeded");
  assert.equal(result.submitted, true);
  assert.equal(kinds(cdp.calls, "releaseSession").length, 1);
});

// 🔴 Finding 5 (executor half): a createSession that threw AFTER the remote session existed hands the
// id back on the error. The one OSS session must be released by that id, not leaked.
test("a session created but never connected is still released by id", async () => {
  const released = [];
  const cdp = fakeCdp({
    async createSession() {
      this.calls.push(["createSession"]);
      const error = new Error("connect ECONNREFUSED");
      error.sessionId = "sess-orphan";
      throw error;
    },
    async releaseSession(sessionId) { this.calls.push(["releaseSession", sessionId]); released.push(sessionId); },
  });
  const result = await executeBooking({ candidate: WEB_CANDIDATE, user: USER, slotPreference: SLOT, deps: { cdp } });
  assert.equal(result.outcome, "honest_failure");
  assert.deepEqual(released, ["sess-orphan"], "the orphaned session is released by the id the error carried");
});

test("a session the client already released itself is not released twice", async () => {
  const released = [];
  const cdp = fakeCdp({
    async createSession() {
      this.calls.push(["createSession"]);
      const error = new Error("connect ECONNREFUSED");
      error.sessionId = "sess-orphan";
      error.sessionReleased = true;
      throw error;
    },
    async releaseSession(sessionId) { this.calls.push(["releaseSession", sessionId]); released.push(sessionId); },
  });
  await executeBooking({ candidate: WEB_CANDIDATE, user: USER, slotPreference: SLOT, deps: { cdp } });
  assert.deepEqual(released, []);
});
