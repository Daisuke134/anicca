// node:test — pure builder for the Composio GMAIL_SEND_EMAIL execute payload (offline, no I/O).
import { test } from "node:test";
import assert from "node:assert/strict";
import { buildGmailSend } from "../composio-gmail.mjs";

test("buildGmailSend produces the GMAIL_SEND_EMAIL execute payload with user_id + arguments", () => {
  const { slug, body } = buildGmailSend({
    to: "person@example.com",
    subject: "Anicca wake net $0",
    body: "NET WORTH $0\nREVENUE $0",
    userId: "genesis",
  });
  assert.equal(slug, "GMAIL_SEND_EMAIL");
  assert.equal(body.user_id, "genesis");
  assert.equal(body.arguments.recipient_email, "person@example.com");
  assert.equal(body.arguments.subject, "Anicca wake net $0");
  assert.equal(body.arguments.body, "NET WORTH $0\nREVENUE $0");
  assert.equal(body.arguments.is_html, false);
  assert.ok(!("connected_account_id" in body), "no connected_account_id unless provided");
});

test("buildGmailSend includes connected_account_id when given, and is_html when true", () => {
  const { body } = buildGmailSend({
    to: "user@example.com",
    subject: "S",
    body: "<b>hi</b>",
    userId: "u1",
    connectedAccountId: "ca_123",
    isHtml: true,
  });
  assert.equal(body.connected_account_id, "ca_123");
  assert.equal(body.arguments.is_html, true);
});

test("buildGmailSend trims the recipient", () => {
  const { body } = buildGmailSend({ to: "  a@b.co  ", subject: "S", body: "B", userId: "u" });
  assert.equal(body.arguments.recipient_email, "a@b.co");
});

test("buildGmailSend rejects an invalid recipient", () => {
  assert.throws(() => buildGmailSend({ to: "not-an-email", subject: "S", body: "B", userId: "u" }), /invalid recipient/);
  assert.throws(() => buildGmailSend({ to: "", subject: "S", body: "B", userId: "u" }), /invalid recipient/);
});

test("buildGmailSend requires subject, body, and userId", () => {
  assert.throws(() => buildGmailSend({ to: "a@b.co", subject: "", body: "B", userId: "u" }), /subject required/);
  assert.throws(() => buildGmailSend({ to: "a@b.co", subject: "S", body: "", userId: "u" }), /body required/);
  assert.throws(() => buildGmailSend({ to: "a@b.co", subject: "S", body: "B", userId: "" }), /userId required/);
});
