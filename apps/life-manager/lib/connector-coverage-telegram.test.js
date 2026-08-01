"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { createHash } = require("node:crypto");

const { buildRollingEventCoverage } = require("./rolling-event-coverage.js");
const { collectLumaInventory } = require("./luma-discovery.js");
const { normalizeLumaEventDetail } = require("./luma-event-detail.js");
const { buildLumaDateInventory } = require("./luma-date-inventory.js");
const { validateEventPreferenceRanking } = require("./event-preference-ranking.js");
const { validateEventGoalSerendipity } = require("./event-goal-serendipity.js");
const { inspectGoogleCalendarBusyInventory } = require("./google-calendar-busy-inventory.js");
const { evaluateCalendarCandidateGate } = require("./calendar-candidate-gate.js");
const { verifyOutboundEvidence } = require("./outbound-evidence.js");
const { buildVerifiedOutboundReceipt } = require("./outbound-success.js");
const { syncVerifiedRegistrationToGoogleCalendar } = require("./connector-calendar-sync.js");
const {
  buildConnectorCoverageTelegramMessage,
  deliverConnectorCoverageTelegram,
} = require("./connector-coverage-telegram.js");

function openCoverage() {
  return buildRollingEventCoverage({
    tenantId: "dais-local", timeZone: "Asia/Tokyo",
    now: "2026-08-01T16:00:00.000Z", resolvedDays: [],
  });
}

async function verifiedNewEventReportInput() {
  const baseCoverage = openCoverage();
  let round = 0;
  const discovered = await collectLumaInventory({
    readSnapshot: async () => (++round === 1 ? [{
      href: "https://luma.com/founder-night", title: "Founder Night",
      cardText: "Founder Night", timelineText: "Aug 5",
    }] : []),
    advance: async () => ({ atEnd: true, scrollHeight: 100 }), stableEndRounds: 1,
  });
  const detail = normalizeLumaEventDetail({
    canonicalUrl: "https://luma.com/founder-night",
    jsonLd: [{
      "@type": "Event", name: "Founder Night", description: "Founders share product lessons",
      startDate: "2026-08-05T19:00:00+09:00", endDate: "2026-08-05T21:00:00+09:00",
      eventAttendanceMode: "https://schema.org/OfflineEventAttendanceMode",
      eventStatus: "https://schema.org/EventScheduled",
      location: { name: "Shibuya Hall", address: "Shibuya, Tokyo" },
      offers: { price: 0, priceCurrency: "JPY", availability: "https://schema.org/InStock" },
    }], controls: ["Register"],
  });
  const dateInventory = buildLumaDateInventory({
    coverage: baseCoverage, inventory: discovered, details: [detail], now: "2026-08-02T01:00:00.000Z",
  });
  const preferenceRanking = validateEventPreferenceRanking({ ranked_events: [{
    event_ref: detail.event_ref, preference_fit: "strong", preference_reason: "founderとの接点に合います",
  }] }, { dateInventory, date: "2026-08-05", preferences: "founderと会い事業を前進させる" });
  const factor = (name, source, assessment) => ({
    factor: name, status: source ? "used" : "unavailable",
    evidence_excerpt: source || null, assessment,
  });
  const goalDecision = validateEventGoalSerendipity({ ranked_events: [{
    event_ref: detail.event_ref, goal_alignment: "strong", serendipity_potential: "high",
    goal_reason: "Life Managerをfounderへ見せ、事業の協力者と出会う目的に合います",
    serendipity_reason: "公開された対面交流から新しい接点が生まれる可能性があります",
    factor_assessments: [
      factor("description", detail.description, "公開説明を確認しました"),
      factor("organizers", null, "公開情報がありません"),
      factor("participants", null, "公開情報がありません"),
      factor("place", "Shibuya Hall", "東京の対面会場です"),
      factor("time", detail.starts_at, "対象日の開催です"),
    ],
  }] }, { dateInventory, preferenceRanking, goals: "毎日人に会いLife Managerを前進させる" });
  const busyInventory = await inspectGoogleCalendarBusyInventory({
    calendar: { async listCalendarsRaw() { return [{ id: "primary" }]; }, async listAllEventsRaw() { return []; } },
    timeMin: "2026-08-02T00:00:00+09:00", timeMax: "2026-08-23T00:00:00+09:00",
    timeZone: "Asia/Tokyo", now: "2026-08-02T01:00:00.000Z",
  });
  const calendarGate = await evaluateCalendarCandidateGate({
    dateInventory, busyInventory, date: "2026-08-05", homeLocation: "Tokyo", routeMinutes: async () => 10,
  });
  const bytes = Buffer.alloc(5_000, 0x61);
  Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]).copy(bytes);
  const artifactHash = createHash("sha256").update(bytes).digest("hex");
  const job = { tenant_id: "dais-local", job_id: `outbound-event:${"d".repeat(64)}`, attempt: 1 };
  const evidence = await verifyOutboundEvidence({
    tenantId: "dais-local", attemptRef: `runtime-attempt://dais-local/${job.job_id}/1`,
    externalReceiptRef: "provider-receipt://luma/fixture", artifactRef: `object://sha256/${artifactHash}`,
    canonicalUrl: detail.canonical_url,
  }, {
    readExternalReceipt: async () => ({ kind: "provider_response", provider_id: "fixture", observed_at: "2026-08-02T01:00:00.000Z" }),
    readArtifact: async () => bytes, fetchImpl: async () => ({ status: 200 }),
  });
  const receipt = buildVerifiedOutboundReceipt({
    tenantId: "dais-local", jobId: job.job_id, attempt: 1, verifiedAt: "2026-08-02T01:00:01.000Z",
  }, evidence);
  const calendarSync = await syncVerifiedRegistrationToGoogleCalendar({
    calendar: {
      async findConnectorEvents() { return []; },
      async createConnectorEvent() { return { id: "private-id", htmlLink: "https://calendar.google.com/calendar/event?eid=opaque" }; },
    },
    calendarId: "primary", dateInventory, calendarGate, eventRef: detail.event_ref,
    registrationReceipt: receipt, registrationJob: job,
  });
  const coverage = buildRollingEventCoverage({
    tenantId: "dais-local", timeZone: "Asia/Tokyo", now: "2026-08-01T16:00:00.000Z",
    resolvedDays: [{
      date: "2026-08-05", status: "covered_new",
      evidence_refs: [calendarSync.registration_receipt_ref, calendarSync.calendar_event_ref],
    }],
  });
  return {
    coverage,
    newEvents: [{ eventRef: detail.event_ref, dateInventory, goalDecision, calendarSync }],
    calendarCoverageUrl: "https://calendar.google.com/calendar/u/0/r",
  };
}

test("未処理日がある報告は失敗終了にせず、21日と継続中の予約作業を人間の言葉で示す", () => {
  const message = buildConnectorCoverageTelegramMessage({
    coverage: openCoverage(), newEvents: [],
    calendarCoverageUrl: "https://calendar.google.com/calendar/u/0/r/customday?start=2026-08-02&end=2026-08-23",
  });
  assert.match(message, /確認期間: 2026年8月2日〜2026年8月22日/);
  assert.match(message, /未処理の空き: 21日/);
  assert.match(message, /予約が成立するまで探索と申込みを続けています/);
  assert.match(message, /空いている日: 8\/2、8\/3/);
  assert.match(message, /3週間のCalendarを開く:\nhttps:\/\/calendar\.google\.com\/calendar\/u\/0\/r\/customday\?start=2026-08-02&end=2026-08-23/);
  assert.doesNotMatch(message, /runner|bounded|none:|候補が見つからなかった|失敗\s*[:：]/i);
});

test("openが0なら新規0件でも、全日が既存予定か固定予定で解決済みだと説明できる", () => {
  const resolvedDays = Array.from({ length: 21 }, (_, index) => {
    const date = new Date(Date.UTC(2026, 7, 2 + index)).toISOString().slice(0, 10);
    return {
      date,
      status: index < 10 ? "covered_existing" : "unavailable",
      evidence_refs: [`calendar-evidence://google/event/${String(index).padStart(64, "a")}`],
    };
  });
  const coverage = buildRollingEventCoverage({
    tenantId: "dais-local", timeZone: "Asia/Tokyo",
    now: "2026-08-01T16:00:00.000Z", resolvedDays,
  });
  const message = buildConnectorCoverageTelegramMessage({
    coverage, newEvents: [], calendarCoverageUrl: "https://calendar.google.com/calendar/u/0/r",
  });
  assert.match(message, /未処理の空き: 0日/);
  assert.match(message, /予約できる空き枠が残っていないため、二重予約を作りませんでした/);
  assert.doesNotMatch(message, /予約作業中|見つからなかった/);
});

test("verified新規予約は名前・時刻・場所・選定理由とevent/Calendarの直接URLを同じ行に出す", async () => {
  const message = buildConnectorCoverageTelegramMessage(await verifiedNewEventReportInput());
  assert.match(message, /Founder Night/);
  assert.match(message, /19:00〜21:00 \/ Shibuya Hall/);
  assert.match(message, /理由: Life Managerをfounderへ見せ/);
  assert.match(message, /イベントページ:\n   https:\/\/luma\.com\/founder-night/);
  assert.match(message, /Calendar:\n   https:\/\/calendar\.google\.com\/calendar\/event\?eid=opaque/);
  assert.match(message, /未処理の空き: 20日/);
});

test("clone coverage、不正Calendar URL、Telegram message ID欠落を成功にしない", async () => {
  assert.throws(() => buildConnectorCoverageTelegramMessage({
    coverage: structuredClone(openCoverage()), newEvents: [],
    calendarCoverageUrl: "https://example.com/calendar",
  }), /Connector coverage Telegram invalid/i);
  assert.throws(() => buildConnectorCoverageTelegramMessage({
    coverage: openCoverage(), newEvents: [], calendarCoverageUrl: "https://example.com/calendar",
  }), /Connector coverage Telegram invalid/i);
  await assert.rejects(deliverConnectorCoverageTelegram({
    tenantId: "dais-local", telegramTarget: "fixture-target", coverage: openCoverage(), newEvents: [],
    calendarCoverageUrl: "https://calendar.google.com/calendar/u/0/r",
  }, { send: async () => ({ ok: true }) }), /positive message ID/i);
});

test("verified reportは一通だけ送り、targetを返さずopaque delivery receiptにする", async () => {
  const sent = [];
  const receipt = await deliverConnectorCoverageTelegram({
    tenantId: "dais-local", telegramTarget: "fixture-target", coverage: openCoverage(), newEvents: [],
    calendarCoverageUrl: "https://calendar.google.com/calendar/u/0/r",
  }, {
    send: async (message, options) => { sent.push([message, options]); return { messageId: "321" }; },
    observedAt: () => "2026-08-02T01:00:00.000Z",
  });
  assert.equal(sent.length, 1);
  assert.equal(sent[0][1].telegramTarget, "fixture-target");
  assert.deepEqual(receipt, {
    kind: "connector_coverage_telegram_delivery", provider_id: "321",
    observed_at: "2026-08-02T01:00:00.000Z", tenant_id: "dais-local",
    chat_id_sha256: "37da4c800042eb1a27e8081315efc08f7d546c5be1e47d2d026be17417a090b3",
    coverage_snapshot_id: openCoverage().coverage_snapshot_id,
  });
  assert.doesNotMatch(JSON.stringify(receipt), /fixture-target/);
});
