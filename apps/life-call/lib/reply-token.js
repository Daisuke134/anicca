"use strict";
// Per-message HMAC-signed token embedded in the Reply-To local-part so ONE catch-all inbound domain
// (reply.aniccaai.com) can route every user's reply to the right user+event — no per-user mailbox.
// Pattern: mailbox-hash / plus-addressing / VERP (Postmark MailboxHash, SendGrid Inbound Parse, Rails
// Action Mailbox). The token MUST be signed: the address travels an untrusted channel, so a bare
// reply+<uid> would let a stranger inject into someone else's calendar (Django signing rule).
const crypto = require("crypto");

const SECRET = process.env.LM_REPLY_SECRET || "";
const DEFAULT_MAX_AGE_MS = 30 * 24 * 3600 * 1000; // replies older than 30 days are rejected

function b64url(s) { return Buffer.from(s).toString("base64url"); }
function sign(payload) {
  // 128-bit truncated HMAC tag — plenty against forgery, short enough for an email local-part.
  return crypto.createHmac("sha256", SECRET).update(payload).digest("base64url").slice(0, 22);
}

// makeReplyToken("lm_abc","evt_1") -> "<base64url(uid|eventId|ts)>.<sig>"
function makeReplyToken(uid, eventId, nowMs = Date.now()) {
  if (!SECRET) throw new Error("LM_REPLY_SECRET not set");
  if (!uid || !eventId) throw new Error("uid and eventId required");
  const payload = b64url(`${uid}|${eventId}|${nowMs}`);
  return `${payload}.${sign(payload)}`;
}

// verifyReplyToken(token) -> { uid, eventId } | null  (null = forged / tampered / expired / malformed)
function verifyReplyToken(token, nowMs = Date.now(), maxAgeMs = DEFAULT_MAX_AGE_MS) {
  if (!SECRET || typeof token !== "string") return null;
  const dot = token.lastIndexOf(".");
  if (dot <= 0) return null;
  const payload = token.slice(0, dot);
  const sig = token.slice(dot + 1);
  const expected = sign(payload);
  const a = Buffer.from(sig), b = Buffer.from(expected);
  if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return null; // forged/tampered
  let decoded;
  try { decoded = Buffer.from(payload, "base64url").toString("utf8"); } catch { return null; }
  const parts = decoded.split("|");
  if (parts.length !== 3) return null;
  const [uid, eventId, tsStr] = parts;
  const ts = Number(tsStr);
  if (!Number.isFinite(ts)) return null;
  if (nowMs - ts > maxAgeMs) return null;   // expired
  if (ts - nowMs > 60_000) return null;      // future-dated (clock-skew tolerance 60s)
  if (!uid || !eventId) return null;
  return { uid, eventId };
}

module.exports = { makeReplyToken, verifyReplyToken, DEFAULT_MAX_AGE_MS };
