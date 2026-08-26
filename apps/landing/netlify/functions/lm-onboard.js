// Legacy browser onboarding is retired. Telegram + the authenticated Railway panel own onboarding.
"use strict";

const RETIRED_ACTIONS = new Set(["google-start", "google-callback", "exchange", "save", "telegram-link"]);

function json(statusCode, body) {
  return {
    statusCode,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
    body: JSON.stringify(body),
  };
}

exports.handler = async function handler(event) {
  const action = event && event.queryStringParameters && event.queryStringParameters.action;
  if (RETIRED_ACTIONS.has(action)) return json(410, { error: "legacy_onboarding_retired" });
  return json(400, { error: "unknown_action" });
};
