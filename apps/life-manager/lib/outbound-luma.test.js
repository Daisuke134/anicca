// lib/outbound-luma.test.js — the Luma provider's parsing, screening and evidence shaping.
//
// Every fixture under test/fixtures/luma/ is a REAL capture taken on 2026-07-31: the SSR payloads
// are verbatim (only the surrounding page markup was dropped), and the one email fixture has its
// guest key and mailbox redacted because a guest key is a live ticket credential.
//
// Nothing in this file touches the network or a browser. The network-shaped functions are exercised
// through an injected fetch that serves those same fixtures, so a provider change that breaks
// parsing fails here in milliseconds instead of at 07:30 in front of a third party's website.
//
// The load-bearing test is "a page that SAYS 参加確定 is not a registration". That is the exact
// failure being replaced: connpass-lt-discover.py:166 decided success by matching DOM text, matched
// the word キャンセル inside every page's cancellation policy, and reported success forever.
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const luma = require("./providers/luma.js");

const FIXTURES = path.join(__dirname, "..", "test", "fixtures", "luma");
const fixture = (name) => fs.readFileSync(path.join(FIXTURES, name), "utf8");
const fixtureJson = (name) => JSON.parse(fixture(name));

const CITY_PAGE = "city-page-tokyo.html";
const DISCOVER = "discover-tokyo.json";
const SINGLE_FREE = "event-single-free-ticket.html";
const TWO_FREE = "event-two-free-tickets.html";
const PAID = "event-paid.html";
const OUT_OF_REGION = "event-out-of-region.html";
const ONLINE = "event-online-livestream.html";

const event = (name) => luma.parseEventPage(fixture(name));

// A syntactically valid PNG header padded past the 5000-byte artifact floor.
function pngBytes(size = 6000) {
  const buffer = Buffer.alloc(size, 0x20);
  Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]).copy(buffer, 0);
  return buffer;
}

// ───────────────────────────────────────────────────────────────────────────── parsing

test("parseCityPage lifts the discover place id and the server-rendered entries", () => {
  const parsed = luma.parseCityPage(fixture(CITY_PAGE));
  assert.equal(parsed.placeApiId, "discplace-9H7asQEvWiv6DA9");
  assert.equal(parsed.entries.length, 3);
});

test("parseNextData refuses a page that is not a Luma SSR page", () => {
  assert.throws(() => luma.parseNextData("<html><body>Just a moment…</body></html>"), /no __NEXT_DATA__/);
  assert.throws(
    () => luma.parseNextData('<script id="__NEXT_DATA__" type="application/json">{oops</script>'),
    /not valid JSON/,
  );
});

test("parseDiscoverPayload reads the paginated API envelope", () => {
  const page = luma.parseDiscoverPayload(fixtureJson(DISCOVER));
  assert.equal(page.entries.length, 6);
  assert.equal(typeof page.hasMore, "boolean");
});

test("normalizeEvent maps a discover entry and marks it unhydrated", () => {
  const [first] = luma.parseDiscoverPayload(fixtureJson(DISCOVER)).entries;
  const normalized = luma.normalizeEvent(first);
  assert.equal(normalized.slug, "cursor-tokyoai-0731");
  assert.equal(normalized.url, "https://luma.com/cursor-tokyoai-0731");
  assert.equal(normalized.locationType, "offline");
  assert.equal(normalized.region, "Tokyo");
  assert.equal(normalized.hydrated, false);
  assert.equal(normalized.ticketTypes, null);
});

test("parseEventPage hydrates ticket types off the event page", () => {
  const parsed = event(SINGLE_FREE);
  assert.equal(parsed.slug, "a879ax7k");
  assert.equal(parsed.hydrated, true);
  assert.deepEqual(parsed.ticketTypes.map((t) => [t.name, t.type, t.cents]), [["Standard", "free", null]]);
  assert.deepEqual([...parsed.categories], ["Tech"]);
});

// ───────────────────────────────────────────────────────────────────────────── screening

test("a free, in-person, open Tokyo event passes and yields its ticket", () => {
  const verdict = luma.screenEvent(event(SINGLE_FREE));
  assert.equal(verdict.ok, true, JSON.stringify(verdict.rejections));
  assert.equal(verdict.ticket.name, "Standard");
});

test("an online event is REJECTED — it is a defect, never a fallback", () => {
  // Real capture: "Agentic AI Summit 2026 | Free Livestream", location_type "unknown".
  const online = event(ONLINE);
  assert.notEqual(online.locationType, "offline");
  const verdict = luma.screenEvent(online);
  assert.equal(verdict.ok, false);
  assert.ok(
    verdict.rejections.some((r) => r.code === "ONLINE_EVENT"),
    `expected ONLINE_EVENT, got ${JSON.stringify(verdict.rejections)}`,
  );
  assert.equal(verdict.ticket, null);
});

test("a paid event is REJECTED even though its page loads perfectly", () => {
  const paid = event(PAID);
  assert.equal(paid.hydrated, true);
  const verdict = luma.screenEvent(paid);
  assert.equal(verdict.ok, false);
  assert.ok(
    verdict.rejections.some((r) => r.code === "NOT_FREE"),
    `expected NOT_FREE, got ${JSON.stringify(verdict.rejections)}`,
  );
});

test("an event outside the configured region is rejected", () => {
  const verdict = luma.screenEvent(event(OUT_OF_REGION));
  assert.equal(verdict.ok, false);
  assert.ok(verdict.rejections.some((r) => r.code === "REGION_EXCLUDED"));
  // …and the same event passes when the region list says so, proving the rule is config, not bias.
  assert.equal(luma.screenEvent(event(OUT_OF_REGION), { regions: ["Kanagawa"] }).ok, true);
});

test("an unhydrated candidate is PAID UNTIL PROVEN FREE, even when the feed claims is_free", () => {
  const entries = luma.parseDiscoverPayload(fixtureJson(DISCOVER)).entries.map(luma.normalizeEvent);
  const claimsFree = luma.parseDiscoverPayload(fixtureJson(DISCOVER)).entries
    .filter((e) => e.ticket_info && e.ticket_info.is_free === true);
  assert.ok(claimsFree.length > 0, "fixture should contain at least one is_free:true entry");
  for (const candidate of entries) {
    const verdict = luma.screenEvent(candidate);
    assert.equal(verdict.ok, false);
    assert.ok(verdict.rejections.some((r) => r.code === "NOT_HYDRATED"));
  }
});

test("the discover feed's is_free flag is not trusted in either direction", () => {
  // Measured: the feed says is_free=false for this event while its page says every ticket is free.
  const [entry] = luma.parseDiscoverPayload(fixtureJson(DISCOVER)).entries
    .filter((e) => e.event.url === "cursor-tokyoai-0731");
  assert.equal(entry.ticket_info.is_free, false);
  const paidPage = event(PAID);
  assert.ok(paidPage.ticketTypes.every((t) => t.type !== "free"));
});

test("two free tickets on one event force the caller to name one", () => {
  const split = event(TWO_FREE);
  assert.deepEqual(split.ticketTypes.map((t) => t.name), ["会場参加", "オンライン参加"]);
  const undecided = luma.screenEvent(split);
  assert.equal(undecided.ok, false);
  assert.ok(undecided.rejections.some((r) => r.code === "TICKET_CHOICE_REQUIRED"));

  const chosen = luma.screenEvent(split, { ticketName: "会場参加" });
  assert.equal(chosen.ok, true, JSON.stringify(chosen.rejections));
  assert.equal(chosen.ticket.name, "会場参加");

  assert.ok(luma.screenEvent(split, { ticketName: "not a ticket" })
    .rejections.some((r) => r.code === "TICKET_NOT_FOUND"));
});

test("a waitlist or sold-out event is not registrable", () => {
  const open = event(SINGLE_FREE);
  const waitlisted = { ...open, availability: "waitlist" };
  assert.ok(luma.screenEvent(waitlisted).rejections.some((r) => r.code === "NOT_OPEN"));
});

test("approval-gated tickets are held back unless the caller opts in", () => {
  const base = event(SINGLE_FREE);
  const gated = {
    ...base,
    ticketTypes: base.ticketTypes.map((t) => ({ ...t, requireApproval: true })),
  };
  assert.ok(luma.screenEvent(gated).rejections.some((r) => r.code === "APPROVAL_REQUIRED"));
  assert.equal(luma.screenEvent(gated, { allowApproval: true }).ok, true);
});

// ───────────────────────────────────────────────────────────────────────────── ranking

test("topic ranking prefers crypto+AI, then crypto, then AI, then broader tech", () => {
  const make = (slug, categories, startsAt) => ({ slug, categories, startsAt });
  const ordered = luma.rankEvents([
    make("tech", ["Tech"], "2026-08-01T00:00:00.000Z"),
    make("ai", ["AI"], "2026-08-02T00:00:00.000Z"),
    make("crypto-ai", ["Crypto", "AI"], "2026-08-03T00:00:00.000Z"),
    make("crypto", ["Crypto"], "2026-08-04T00:00:00.000Z"),
    make("none", [], "2026-07-01T00:00:00.000Z"),
  ]);
  assert.deepEqual(ordered.map((e) => e.slug), ["crypto-ai", "crypto", "ai", "tech", "none"]);
});

test("ties on topic are broken by the soonest start", () => {
  const ordered = luma.rankEvents([
    { slug: "later", categories: ["AI"], startsAt: "2026-09-01T00:00:00.000Z" },
    { slug: "sooner", categories: ["AI"], startsAt: "2026-08-01T00:00:00.000Z" },
  ]);
  assert.deepEqual(ordered.map((e) => e.slug), ["sooner", "later"]);
});

test("selectEvents keeps the rejections visible instead of silently dropping them", () => {
  const selection = luma.selectEvents([event(SINGLE_FREE), event(PAID), event(ONLINE)]);
  assert.deepEqual(selection.accepted.map((e) => e.slug), ["a879ax7k"]);
  assert.equal(selection.rejected.length, 2);
  assert.ok(selection.rejected.every((r) => r.rejections.length > 0));
});

// ───────────────────────────────────────────────────────────────────────── canonical URL (E3)

test("canonicalEventUrl returns the durable page for a slug or a full URL", () => {
  assert.equal(luma.canonicalEventUrl("8dcgttdv"), "https://luma.com/8dcgttdv");
  assert.equal(luma.canonicalEventUrl("https://luma.com/8dcgttdv"), "https://luma.com/8dcgttdv");
  // The per-guest token is stripped: a canonical URL must be shareable and stable.
  assert.equal(luma.canonicalEventUrl("https://luma.com/8dcgttdv?tk=AbCdEf"), "https://luma.com/8dcgttdv");
});

test("canonicalEventUrl refuses one-shot and per-guest URLs by their path", () => {
  assert.throws(() => luma.canonicalEventUrl("https://luma.com/join/complete/xyz123"), /one-shot/);
  assert.throws(() => luma.canonicalEventUrl("https://luma.com/join/g-abc123"), /one-shot/);
  assert.throws(() => luma.canonicalEventUrl("https://luma.com/e/ticket/evt-abc?pk=g-abc"), /one-shot/);
  assert.throws(() => luma.canonicalEventUrl(""), /needs a slug/);
});

// ─────────────────────────────────────────────────────────────────── guest key + confirmation

test("extractGuestKey pulls the pk= guest key out of a real confirmation body", () => {
  const message = fixtureJson("confirmation-email.json");
  const found = luma.extractGuestKey(message.body);
  assert.equal(found.guestKey, "g-REDACTEDGUESTKEY");
  assert.equal(found.slug, "p9kfepcf");
  assert.equal(found.ticketUrl, "https://luma.com/e/ticket/evt-eXObzZdL57cxXnG?pk=g-REDACTEDGUESTKEY");
});

test("extractGuestKey does not mistake luma.com/ios or /tokyo for an event slug", () => {
  const found = luma.extractGuestKey("https://luma.com/ios?utm_source=email https://luma.com/tokyo");
  assert.equal(found.guestKey, null);
  assert.equal(found.slug, null);
});

test("parseConfirmationEmail keeps the message id, subject and guest key together", () => {
  const parsed = luma.parseConfirmationEmail(fixtureJson("confirmation-email.json"));
  assert.equal(parsed.message_id, "19fb3c3c704429cf");
  assert.equal(parsed.subject, "Codex Meetup Tokyo #2の参加登録が承認されました");
  assert.equal(parsed.from, "AIAU <aiau@calendar.luma-mail.com>");
  assert.equal(parsed.guestKey, "g-REDACTEDGUESTKEY");
});

// ───────────────────────────────────────────────────────────────────── outcome (the load-bearing bit)

test("★ a page that SAYS 参加確定！ is NOT a registration ★", () => {
  // This is connpass-lt-discover.py:166 in miniature. The DOM is as convincing as it gets and the
  // wire is silent, so the answer must be "no".
  const outcome = luma.readRsvpOutcome({
    finalUrl: "https://luma.com/8dcgttdv",
    pageText: "参加確定！ ✅ ご登録ありがとうございます。キャンセルポリシーはこちら。",
    httpEvidence: [{ url: "https://api.lu.ma/event/get-page", method: "GET", status: 200 }],
  });
  assert.equal(outcome.registered, false);
  assert.deepEqual([...outcome.signals], []);
  assert.equal(outcome.acceptedCall, null);
});

test("the ?tk= token Luma writes into the URL counts as a signal", () => {
  const outcome = luma.readRsvpOutcome({ finalUrl: "https://luma.com/8dcgttdv?tk=A1b2C3", httpEvidence: [] });
  assert.equal(outcome.registered, true);
  assert.equal(outcome.tk, "A1b2C3");
  assert.deepEqual([...outcome.signals], ["tk_token"]);
});

test("a 2xx from the registration endpoint counts as a signal", () => {
  const outcome = luma.readRsvpOutcome({
    finalUrl: "https://luma.com/8dcgttdv",
    httpEvidence: [
      { url: "https://api.lu.ma/event/get-page", method: "GET", status: 200 },
      { url: "https://api.lu.ma/event/independent/register", method: "POST", status: 201 },
    ],
  });
  assert.equal(outcome.registered, true);
  assert.deepEqual([...outcome.signals], ["register_2xx"]);
  assert.equal(outcome.acceptedCall.status, 201);
});

test("a rejected registration call is not a registration", () => {
  const outcome = luma.readRsvpOutcome({
    finalUrl: "https://luma.com/8dcgttdv",
    httpEvidence: [{ url: "https://api.lu.ma/event/independent/register", method: "POST", status: 422 }],
  });
  assert.equal(outcome.registered, false);
  assert.equal(outcome.registerCalls.length, 1);
  assert.equal(outcome.acceptedCall, null);
});

// ─────────────────────────────────────────────────────── evidence shaping (provider → gate)

test("buildEvidence hands the gate a bundle it accepts when all three limbs are real", async () => {
  const { verifyEvidence } = await import("../../../runtime/loop/outbound/evidence.mjs");
  const receipt = {
    requestedUrl: "https://luma.com/8dcgttdv",
    canonicalUrl: "https://luma.com/8dcgttdv",
    artifactPath: "/tmp/evidence/luma-8dcgttdv.png",
    httpEvidence: { kind: "http", url: "https://api.lu.ma/event/independent/register", status: 201 },
  };
  const verdict = verifyEvidence(luma.buildEvidence(receipt, { artifactBytes: pngBytes(), headStatus: 200 }));
  assert.equal(verdict.ok, true, JSON.stringify(verdict.failures));
});

test("buildEvidence prefers a real confirmation email over the HTTP receipt for E1", () => {
  const bundle = luma.buildEvidence(
    { canonicalUrl: "https://luma.com/8dcgttdv", httpEvidence: { status: 201 } },
    { confirmation: { message_id: "19fb3c3c704429cf", subject: "Registration confirmed" }, headStatus: 200 },
  );
  assert.equal(bundle.e1.kind, "email");
  assert.equal(bundle.e1.message_id, "19fb3c3c704429cf");
});

test("evidence with no wire receipt at all fails E1", async () => {
  const { verifyEvidence } = await import("../../../runtime/loop/outbound/evidence.mjs");
  const bundle = luma.buildEvidence(
    { canonicalUrl: "https://luma.com/8dcgttdv", artifactPath: "/tmp/x.png", httpEvidence: null },
    { artifactBytes: pngBytes(), headStatus: 200 },
  );
  const verdict = verifyEvidence(bundle);
  assert.equal(verdict.ok, false);
  assert.ok(verdict.failures.some((f) => f.code === "E1_ABSENT"));
});

test("a screenshot under the artifact floor fails E2", async () => {
  const { verifyEvidence } = await import("../../../runtime/loop/outbound/evidence.mjs");
  const verdict = verifyEvidence(luma.buildEvidence(
    { canonicalUrl: "https://luma.com/8dcgttdv", artifactPath: "/tmp/x.png", httpEvidence: { status: 201 } },
    { artifactBytes: pngBytes(120), headStatus: 200 },
  ));
  assert.equal(verdict.ok, false);
  assert.ok(verdict.failures.some((f) => f.code === "E2_TOO_SMALL"));
});

test("a canonical URL that does not answer 200 fails E3", async () => {
  const { verifyEvidence } = await import("../../../runtime/loop/outbound/evidence.mjs");
  const verdict = verifyEvidence(luma.buildEvidence(
    { canonicalUrl: "https://luma.com/8dcgttdv", artifactPath: "/tmp/x.png", httpEvidence: { status: 201 } },
    { artifactBytes: pngBytes(), headStatus: 404 },
  ));
  assert.equal(verdict.ok, false);
  assert.ok(verdict.failures.some((f) => f.code === "E3_HEAD_NOT_200"));
});

// ─────────────────────────────────────────────────────────────── discover, over an injected fetch

function fixtureFetch(log = []) {
  return async (url) => {
    log.push(String(url));
    const respond = (body, json) => ({
      ok: true,
      status: 200,
      text: async () => body,
      json: async () => json,
    });
    if (url === "https://luma.com/tokyo") return respond(fixture(CITY_PAGE), null);
    if (String(url).startsWith(luma.DISCOVER_API)) return respond(null, fixtureJson(DISCOVER));
    if (url === "https://luma.com/a879ax7k") return respond(fixture(SINGLE_FREE), null);
    if (url === "https://luma.com/8dcgttdv") return respond(fixture(TWO_FREE), null);
    if (url === "https://luma.com/s3a5nqdu") return respond(fixture(PAID), null);
    return { ok: false, status: 404, text: async () => "", json: async () => ({}) };
  };
}

test("discoverEvents resolves the place id from the city page and never hardcodes one", async () => {
  const log = [];
  const result = await luma.discoverEvents({ fetchImpl: fixtureFetch(log), politeDelayMs: 0, hydrateLimit: 3 });
  assert.equal(result.ok, true);
  assert.equal(result.place_api_id, "discplace-9H7asQEvWiv6DA9");
  assert.equal(log[0], "https://luma.com/tokyo");
  assert.ok(log[1].includes("discover_place_api_id=discplace-9H7asQEvWiv6DA9"));
});

test("discoverEvents hydrates candidates and reports why the rest were dropped", async () => {
  const result = await luma.discoverEvents({ fetchImpl: fixtureFetch(), politeDelayMs: 0, hydrateLimit: 6 });
  assert.equal(result.ok, true);
  const codes = new Set(result.rejected.flatMap((r) => (r.rejections || []).map((x) => x.code)));
  // The fixture feed is all waitlist/sold-out/paid, so nothing survives — and every drop is named.
  assert.ok(result.rejected.length > 0);
  assert.ok([...codes].length > 0, "every rejection carries a code");
  assert.ok(result.seen >= 6);
});

test("discoverEvents degrades honestly when Luma stops answering", async () => {
  const result = await luma.discoverEvents({
    fetchImpl: async () => ({ ok: false, status: 503, text: async () => "", json: async () => ({}) }),
    politeDelayMs: 0,
  });
  assert.equal(result.ok, false);
  assert.match(result.reason, /^luma_discover_failed: /);
  assert.deepEqual([...result.candidates], []);
});

test("headStatus reports the number it observed, and nothing else", async () => {
  const seen = [];
  const status = await luma.headStatus("https://luma.com/8dcgttdv", {
    fetchImpl: async (url, init) => {
      seen.push([url, init.method, init.headers["user-agent"]]);
      return { ok: true, status: 200 };
    },
  });
  assert.equal(status, 200);
  assert.equal(seen[0][1], "HEAD");
  assert.match(seen[0][2], /Chrome\//);
});

// ─────────────────────────────────────────────────────────────────────── rsvp preconditions

test("rsvp refuses to run without a leased CDP endpoint", async () => {
  await assert.rejects(
    () => luma.rsvp("https://luma.com/8dcgttdv", { name: "N", email: "e@example.com" }, {}),
    /needs a leased cdpUrl/,
  );
});

test("rsvp refuses without an artifact directory or an identity", async () => {
  await assert.rejects(
    () => luma.rsvp("https://luma.com/8dcgttdv", { name: "N", email: "e@example.com" }, { cdpUrl: "http://x" }),
    /needs an artifactDir/,
  );
  await assert.rejects(
    () => luma.rsvp("https://luma.com/8dcgttdv", {}, { cdpUrl: "http://x", artifactDir: "/tmp" }),
    /needs identity/,
  );
});
