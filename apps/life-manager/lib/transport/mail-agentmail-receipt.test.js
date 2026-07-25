"use strict";
// CORE-8e: the late notice is only proven when the RECIPIENT mailbox shows it. Resend's response id is a
// queue-accept receipt, not delivery. These tests pin the AgentMail-backed sibling of makeGogMail.findReceipt:
// same fail-closed contract, same safe metadata, plus the real RFC Message-ID the spec's done condition needs.
const assert = require("node:assert/strict");
const test = require("node:test");

const { makeAgentMailReceipt } = require("./mail-agentmail-receipt.js");

const NONCE = "a1b2c3d4e5f60718";
const INBOX = "core8e@agentmail.to";

function messagesResponse(messages) {
  return {
    ok: true,
    status: 200,
    json: async () => ({ count: messages.length, limit: 20, messages }),
  };
}

function fetchReturning(response, calls) {
  return async (url, init) => {
    if (calls) calls.push({ url: String(url), init });
    return response;
  };
}

test("ready() is false until both an api key and an inbox are present", () => {
  assert.equal(makeAgentMailReceipt({ apiKey: "", inbox: INBOX }).ready(), false);
  assert.equal(makeAgentMailReceipt({ apiKey: "k", inbox: "" }).ready(), false);
  assert.equal(makeAgentMailReceipt({ apiKey: "k", inbox: INBOX }).ready(), true);
  assert.equal(makeAgentMailReceipt({ apiKey: "k", inbox: INBOX }).kind, "agentmail");
});

test("a malformed nonce fails closed before any network call", async () => {
  const calls = [];
  const receipt = makeAgentMailReceipt({
    apiKey: "k", inbox: INBOX, fetchImpl: fetchReturning(messagesResponse([]), calls),
  });
  for (const bad of ["", "short", "../etc/passwd", "zzzzzzzzzzzzzzzz", NONCE + "!"]) {
    assert.equal(await receipt.findReceipt({ nonce: bad, afterMs: 0 }), null);
  }
  assert.equal(calls.length, 0);
});

test("an unconfigured receipt reader fails closed without calling the api", async () => {
  const calls = [];
  const receipt = makeAgentMailReceipt({
    apiKey: "", inbox: INBOX, fetchImpl: fetchReturning(messagesResponse([]), calls),
  });
  assert.equal(await receipt.findReceipt({ nonce: NONCE, afterMs: 0 }), null);
  assert.equal(calls.length, 0);
});

test("no matching nonce returns null", async () => {
  const receipt = makeAgentMailReceipt({
    apiKey: "k",
    inbox: INBOX,
    fetchImpl: fetchReturning(messagesResponse([
      { smtp_id: "m1", message_id: "<x@mail>", subject: "Running late: standup", timestamp: "2026-07-25T02:00:00.000Z" },
    ])),
  });
  assert.equal(await receipt.findReceipt({ nonce: NONCE, afterMs: 0 }), null);
});

test("a nonce match that predates afterMs is stale and fails closed", async () => {
  const receipt = makeAgentMailReceipt({
    apiKey: "k",
    inbox: INBOX,
    fetchImpl: fetchReturning(messagesResponse([
      {
        smtp_id: "m1", message_id: "<old@mail>",
        subject: `Running late: LM-CORE-8E ${NONCE}`,
        timestamp: "2026-07-25T02:00:00.000Z",
      },
    ])),
  });
  const afterMs = Date.parse("2026-07-25T03:00:00.000Z");
  assert.equal(await receipt.findReceipt({ nonce: NONCE, afterMs }), null);
});

test("a fresh nonce match returns the real RFC Message-ID and only safe metadata", async () => {
  const receipt = makeAgentMailReceipt({
    apiKey: "k",
    inbox: INBOX,
    fetchImpl: fetchReturning(messagesResponse([
      {
        smtp_id: "msg_2001",
        message_id: "<0100019a@resend.example>",
        subject: `Running late: LM-CORE-8E ${NONCE}`,
        preview: "Hi — Dais is running about 15 minutes late",
        from: "Life Manager <hello@aniccaai.com>",
        to: [INBOX],
        timestamp: "2026-07-25T03:05:00.000Z",
      },
    ])),
  });
  const afterMs = Date.parse("2026-07-25T03:00:00.000Z");
  const found = await receipt.findReceipt({ nonce: NONCE, afterMs });

  assert.ok(found, "expected a receipt");
  assert.equal(found.id, "msg_2001");
  assert.equal(found.rfcMessageId, "<0100019a@resend.example>");
  assert.equal(found.matchedNonce, NONCE);
  assert.equal(found.receivedAtLowerMs, Date.parse("2026-07-25T03:05:00.000Z"));
  assert.equal(found.receivedAtUpperMs, Date.parse("2026-07-25T03:05:00.000Z"));
  // Safe metadata only: no body/preview, no addresses, no subject text.
  assert.deepEqual(
    Object.keys(found).sort(),
    ["id", "matchedNonce", "receivedAtLowerMs", "receivedAtUpperMs", "rfcMessageId"],
  );
});

test("a match without an RFC Message-ID fails closed because the done condition needs one", async () => {
  const receipt = makeAgentMailReceipt({
    apiKey: "k",
    inbox: INBOX,
    fetchImpl: fetchReturning(messagesResponse([
      {
        smtp_id: "msg_2002", message_id: "",
        subject: `Running late: LM-CORE-8E ${NONCE}`,
        timestamp: "2026-07-25T03:05:00.000Z",
      },
    ])),
  });
  const afterMs = Date.parse("2026-07-25T03:00:00.000Z");
  assert.equal(await receipt.findReceipt({ nonce: NONCE, afterMs }), null);
});

// Measured against the live API on 2026-07-25: `message_id` carries the RFC id (`<...@host>`) and
// `smtp_id` is AgentMail's own 40-char handle. An id that is not RFC-shaped is not a Message-ID.
test("an id that is not RFC-shaped is not accepted as a Message-ID", async () => {
  const receipt = makeAgentMailReceipt({
    apiKey: "k",
    inbox: INBOX,
    fetchImpl: fetchReturning(messagesResponse([
      {
        smtp_id: "1f8a0c2b4d6e8091a2b3c4d5e6f708192a3b4c5d",
        message_id: "1f8a0c2b4d6e8091a2b3c4d5e6f708192a3b4c5d",
        subject: `Running late: LM-CORE-8E ${NONCE}`,
        timestamp: "2026-07-25T03:05:00.000Z",
      },
    ])),
  });
  const afterMs = Date.parse("2026-07-25T03:00:00.000Z");
  assert.equal(await receipt.findReceipt({ nonce: NONCE, afterMs }), null);
});

test("an unparseable timestamp fails closed rather than being treated as now", async () => {
  const receipt = makeAgentMailReceipt({
    apiKey: "k",
    inbox: INBOX,
    fetchImpl: fetchReturning(messagesResponse([
      {
        smtp_id: "msg_2003", message_id: "<a@b>",
        subject: `Running late: LM-CORE-8E ${NONCE}`,
        timestamp: "not-a-date",
      },
    ])),
  });
  assert.equal(await receipt.findReceipt({ nonce: NONCE, afterMs: 0 }), null);
});

test("the nonce is matched in the preview body too, not only the subject", async () => {
  const receipt = makeAgentMailReceipt({
    apiKey: "k",
    inbox: INBOX,
    fetchImpl: fetchReturning(messagesResponse([
      {
        smtp_id: "msg_2004", message_id: "<c@d>",
        subject: "Running late: standup",
        preview: `ref ${NONCE} — running about 15 minutes late`,
        timestamp: "2026-07-25T03:05:00.000Z",
      },
    ])),
  });
  const found = await receipt.findReceipt({ nonce: NONCE, afterMs: Date.parse("2026-07-25T03:00:00.000Z") });
  assert.ok(found);
  assert.equal(found.rfcMessageId, "<c@d>");
});

test("an http failure and a thrown network error both fail closed without throwing", async () => {
  const failing = makeAgentMailReceipt({
    apiKey: "k", inbox: INBOX,
    fetchImpl: async () => ({ ok: false, status: 502, json: async () => ({}) }),
  });
  assert.equal(await failing.findReceipt({ nonce: NONCE, afterMs: 0 }), null);

  const throwing = makeAgentMailReceipt({
    apiKey: "k", inbox: INBOX,
    fetchImpl: async () => { throw new Error("socket hang up"); },
  });
  assert.equal(await throwing.findReceipt({ nonce: NONCE, afterMs: 0 }), null);
});

test("the request authenticates with the key and scopes the read to the configured inbox", async () => {
  const calls = [];
  const receipt = makeAgentMailReceipt({
    apiKey: "secret-key", inbox: INBOX, fetchImpl: fetchReturning(messagesResponse([]), calls),
  });
  await receipt.findReceipt({ nonce: NONCE, afterMs: 0 });

  assert.equal(calls.length, 1);
  assert.ok(calls[0].url.includes(encodeURIComponent(INBOX)), "inbox must be url-encoded into the path");
  assert.equal(calls[0].init.headers.Authorization, "Bearer secret-key");
});

// Measured 2026-07-25: adding the receipt inbox as a calendar attendee makes Google send it an
// invitation whose subject also carries the nonce. Matching on the nonce alone would report that
// invitation as delivery proof for a notice we never sent, so callers can pin sender and subject.
test("a nonce match from the wrong sender is not accepted when a sender is required", async () => {
  const receipt = makeAgentMailReceipt({
    apiKey: "k",
    inbox: INBOX,
    fetchImpl: fetchReturning(messagesResponse([
      {
        smtp_id: "invite", message_id: "<calendar-1@google.com>",
        subject: `Invitation: LM-CORE-8E ${NONCE}`,
        from: "Google Calendar <calendar-notification@google.com>",
        timestamp: "2026-07-25T03:05:00.000Z",
      },
    ])),
  });
  assert.equal(await receipt.findReceipt({ nonce: NONCE, afterMs: 0, fromIncludes: "aniccaai.com" }), null);
});

test("a nonce match with the wrong subject is not accepted when a subject is required", async () => {
  const receipt = makeAgentMailReceipt({
    apiKey: "k",
    inbox: INBOX,
    fetchImpl: fetchReturning(messagesResponse([
      {
        smtp_id: "invite", message_id: "<calendar-2@google.com>",
        subject: `Invitation: LM-CORE-8E ${NONCE}`,
        timestamp: "2026-07-25T03:05:00.000Z",
      },
    ])),
  });
  assert.equal(await receipt.findReceipt({ nonce: NONCE, afterMs: 0, subjectIncludes: "Running late:" }), null);
});

test("the right notice still matches when both sender and subject are pinned", async () => {
  const receipt = makeAgentMailReceipt({
    apiKey: "k",
    inbox: INBOX,
    fetchImpl: fetchReturning(messagesResponse([
      {
        smtp_id: "invite", message_id: "<calendar-3@google.com>",
        subject: `Invitation: LM-CORE-8E ${NONCE}`,
        from: "Google Calendar <calendar-notification@google.com>",
        timestamp: "2026-07-25T03:05:00.000Z",
      },
      {
        smtp_id: "notice", message_id: "<real@ap-northeast-1.amazonses.com>",
        subject: `Running late: LM-CORE-8E ${NONCE}`,
        from: "Life Manager <hello@aniccaai.com>",
        timestamp: "2026-07-25T03:06:00.000Z",
      },
    ])),
  });
  const found = await receipt.findReceipt({
    nonce: NONCE, afterMs: 0, fromIncludes: "aniccaai.com", subjectIncludes: "Running late:",
  });
  assert.ok(found);
  assert.equal(found.rfcMessageId, "<real@ap-northeast-1.amazonses.com>");
});
