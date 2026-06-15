// gcal-token.js — obtain a fresh Google Calendar access token.
//
// Strategy (in priority order):
//   1. GOOGLE_CALENDAR_TOKEN env var (pre-fetched short-lived token)
//   2. GOOGLE_REFRESH_TOKEN + GOOGLE_CLIENT_ID + GOOGLE_CLIENT_SECRET
//      → calls Google OAuth2 token endpoint to mint a fresh access token
//
// The Netlify function calls getAccessToken() before every GCal API call.
// This makes the function work even when the static access token has expired.

"use strict";

const TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token";

/**
 * Returns a valid Google OAuth2 access token.
 *
 * @returns {Promise<string>} access token
 * @throws if neither strategy succeeds
 */
async function getAccessToken() {
  // Strategy 1 — pre-provided static token
  if (process.env.GOOGLE_CALENDAR_TOKEN) {
    return process.env.GOOGLE_CALENDAR_TOKEN;
  }

  // Strategy 2 — refresh via OAuth2
  const refreshToken = process.env.GOOGLE_REFRESH_TOKEN;
  const clientId = process.env.GOOGLE_CLIENT_ID;
  const clientSecret = process.env.GOOGLE_CLIENT_SECRET;

  if (!refreshToken || !clientId || !clientSecret) {
    throw new Error(
      "missing GOOGLE_CALENDAR_TOKEN (or GOOGLE_REFRESH_TOKEN + GOOGLE_CLIENT_ID + GOOGLE_CLIENT_SECRET)"
    );
  }

  const body = new URLSearchParams({
    grant_type: "refresh_token",
    refresh_token: refreshToken,
    client_id: clientId,
    client_secret: clientSecret,
  });

  const r = await fetch(TOKEN_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: body.toString(),
  });

  if (!r.ok) {
    const text = await r.text();
    throw new Error(`OAuth2 token refresh failed ${r.status}: ${text.slice(0, 200)}`);
  }

  const data = await r.json();
  if (!data.access_token) {
    throw new Error("OAuth2 token response missing access_token");
  }

  return data.access_token;
}

module.exports = { getAccessToken };
