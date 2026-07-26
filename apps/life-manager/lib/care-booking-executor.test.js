"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const {
  executeBooking,
  formatU8Identification,
  matchFieldKind,
} = require("./care-booking-executor.js");

const USER = Object.freeze({ uid: "u1", name: "山田太郎", phone: "+819012345678", email: "y@example.com" });
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
      return { id: "sess-1", websocketUrl: "ws://steel-browser.railway.internal:3000/" };
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
    ["#t", "+819012345678"],
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
