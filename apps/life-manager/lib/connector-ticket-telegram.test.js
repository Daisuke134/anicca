"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const test = require("node:test");

const {
  buildConnectorTicketCaption,
  deliverConnectorTicket,
  sendOpenClawMedia,
} = require("./connector-ticket-telegram.js");

const ARTIFACT_REF = `object://sha256/${"5".repeat(64)}`;

function input(overrides = {}) {
  return {
    tenantId: "dais-local",
    artifactRef: ARTIFACT_REF,
    telegramTarget: "123456789",
    eventTitle: "Engineer BAR",
    startsAt: "2026-08-15T18:00:00+09:00",
    endsAt: "2026-08-15T23:00:00+09:00",
    venue: "Bar Layover（東京・新宿）",
    registrationIdentity: "Dais",
    selectionReason: "東京でエンジニアと直接会え、既存予定と移動時間が重ならないためです。",
    eventUrl: "https://luma.com/a879ax7k",
    calendarUrl: "https://www.google.com/calendar/event?eid=fixture",
    ...overrides,
  };
}

function png() {
  const bytes = Buffer.alloc(5000, 0x61);
  Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]).copy(bytes);
  return bytes;
}

test("非技術者が理解でき、eventとCalendarへ直接tapできる日本語captionを作る", () => {
  const caption = buildConnectorTicketCaption(input());
  assert.match(caption, /^🎟️ イベント参加の申込みが完了しました。/);
  assert.match(caption, /イベント: Engineer BAR/);
  assert.match(caption, /日時: 2026年8月15日（土）18:00〜23:00/);
  assert.match(caption, /場所: Bar Layover（東京・新宿）/);
  assert.match(caption, /Lumaの確認メールを受信済み/);
  assert.match(caption, /当日の公式QRを添付しました/);
  assert.match(caption, /https:\/\/luma\.com\/a879ax7k/);
  assert.match(caption, /https:\/\/www\.google\.com\/calendar\/event\?eid=fixture/);
  assert.doesNotMatch(caption, /runner|job[_ ]?id|sha256|guest.?key|\{\{|\[.+\]\(.+\)/i);
  assert.ok(caption.length <= 1024);
});

test("placeholder、非Luma URL、非Google Calendar URL、壊れた時刻を拒否する", () => {
  assert.throws(() => buildConnectorTicketCaption(input({ eventTitle: "{{event_name}}" })), /placeholder/i);
  assert.throws(() => buildConnectorTicketCaption(input({ eventUrl: "https://evil.example/a879ax7k" })), /event URL/i);
  assert.throws(() => buildConnectorTicketCaption(input({ calendarUrl: "https://evil.example/calendar" })), /Calendar URL/i);
  assert.throws(() => buildConnectorTicketCaption(input({ endsAt: "2026-08-15T17:00:00+09:00" })), /time/i);
});

test("verified artifactを一度だけ送りpositive message IDだけをreceiptにする", async () => {
  const sends = [];
  const receipt = await deliverConnectorTicket(input(), {
    readArtifact: async (tenant, ref) => {
      assert.equal(tenant, "dais-local");
      assert.equal(ref, ARTIFACT_REF);
      return png();
    },
    sendMedia: async (target, bytes, caption) => {
      sends.push({ target, bytes, caption });
      return { messageId: "7007" };
    },
    observedAt: () => "2026-08-01T15:30:00.000Z",
  });

  assert.equal(sends.length, 1);
  assert.equal(sends[0].target, "123456789");
  assert.deepEqual(sends[0].bytes, png());
  assert.deepEqual(receipt, {
    kind: "telegram_delivery",
    provider_id: "7007",
    observed_at: "2026-08-01T15:30:00.000Z",
    tenant_id: "dais-local",
    chat_id_sha256: "15e2b0d3c33891ebb0f1ef609ec419420c20e320ce94c65fbc8c3312448eb225",
    artifact_ref: ARTIFACT_REF,
    event_url: "https://luma.com/a879ax7k",
  });
  assert.doesNotMatch(JSON.stringify(receipt), /123456789|Engineer BAR|Bar Layover/);
});

test("message ID欠落と壊れたPNGは成功にしない", async () => {
  await assert.rejects(deliverConnectorTicket(input(), {
    readArtifact: async () => png(),
    sendMedia: async () => ({ ok: true }),
  }), /positive message ID/i);
  await assert.rejects(deliverConnectorTicket(input(), {
    readArtifact: async () => Buffer.alloc(5000),
    sendMedia: async () => { throw new Error("must not send"); },
  }), /PNG/i);
});

test("OpenClaw media transportは0600 temporary PNGを使い送信後に削除する", async () => {
  let temporary;
  const result = await sendOpenClawMedia("123456789", png(), "caption", {
    spawnSync(command, args) {
      assert.equal(command, "openclaw");
      const mediaIndex = args.indexOf("--media");
      temporary = args[mediaIndex + 1];
      assert.equal(fs.statSync(temporary).mode & 0o777, 0o600);
      assert.deepEqual(fs.readFileSync(temporary), png());
      return { status: 0, stdout: JSON.stringify({ messageId: "8008" }), stderr: "" };
    },
  });
  assert.deepEqual(result, { messageId: "8008" });
  assert.equal(fs.existsSync(temporary), false);
});
