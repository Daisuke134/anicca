"use strict";

const crypto = require("crypto");

function httpBase(value) {
  return String(value || "https://aniccaai.com").replace(/^wss:/, "https:").replace(/^ws:/, "http:").replace(/\/ws\/?$/, "").replace(/\/$/, "");
}

function signUid(uid, secret) {
  if (!uid || !secret) return "";
  return crypto.createHmac("sha256", secret).update(uid).digest("base64url");
}

function signedGmailConnectUrl(uid, base, secret) {
  const root = httpBase(base);
  const sig = signUid(uid, secret);
  if (!uid || !sig) return "";
  return `${root}/gmail-connect?uid=${encodeURIComponent(uid)}&sig=${encodeURIComponent(sig)}`;
}

async function createHostedGmailLink(uid, opts = {}) {
  const { dsn, token, notifySecret } = opts;
  if (!uid || !dsn || !token || !notifySecret) return null;
  const fetchImpl = opts.fetchImpl || fetch;
  const publicBase = httpBase(opts.publicBase || "https://aniccaai.com");
  try {
    const expiresOn = new Date((opts.nowMs == null ? Date.now() : opts.nowMs) + 60 * 60 * 1000).toISOString();
    const response = await fetchImpl(`https://${dsn}/api/v1/hosted/accounts/link`, {
      method: "POST",
      headers: { "X-API-KEY": token, "Content-Type": "application/json" },
      body: JSON.stringify({
        type: "create", providers: ["GOOGLE"], api_url: `https://${dsn}`, expiresOn, name: uid,
        notify_url: `${publicBase}/.netlify/functions/unipile-notify?s=${encodeURIComponent(notifySecret)}`,
        success_redirect_url: `${publicBase}/lm?gmail=connected`,
        failure_redirect_url: `${publicBase}/lm?gmail=error`,
      }),
    });
    if (!response.ok) return null;
    const json = await response.json().catch(() => ({}));
    return json.url || json.link || null;
  } catch {
    return null;
  }
}

module.exports = { httpBase, signUid, signedGmailConnectUrl, createHostedGmailLink };
