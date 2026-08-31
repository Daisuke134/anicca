"use strict";
// Short, unguessable, opaque token for the Reply-To local-part (mailbox-hash / plus-addressing pattern,
// Postmark/SendGrid style). The (token → uid, eventId) mapping lives server-side in lm_ask_log.reply_token;
// the inbound webhook looks it up. 128 bits of entropy = unforgeable, and short enough that
// reply+<token>@reply.aniccaai.com stays under the RFC-5321 64-char local-part limit (a self-contained
// signed token embedding a 39-char uid blew past 64 → Resend 422'd it).
const crypto = require("crypto");

// 16 random bytes → 22 base64url chars. local part "reply+" + 22 = 28 chars (well under 64).
function newReplyToken() {
  return crypto.randomBytes(16).toString("base64url");
}

// Shape guard so the inbound webhook can reject obvious garbage before a DB lookup.
const REPLY_TOKEN_RE = /^[A-Za-z0-9_-]{16,64}$/;
function isReplyToken(t) {
  return typeof t === "string" && REPLY_TOKEN_RE.test(t);
}

module.exports = { newReplyToken, isReplyToken };
