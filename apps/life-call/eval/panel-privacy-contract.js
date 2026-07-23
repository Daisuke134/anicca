"use strict";

const SAFE_TIMELINE_SENTENCE = "予定の詳細を安全に表示できず、次はカレンダーで開始時刻を確認してください。";
const BROWSER_LOAD_ERROR_COPY = "いま情報を読み込めませんでした。少し時間をおいて、もう一度開いてください。";

const RECIPE_BUILDERS = Object.freeze({
  "github-classic-token": () => ["gh", "p_", "a".repeat(36)].join(""),
  "github-fine-grained-token": () => ["github", "_pat_", "11", "_", "A".repeat(74)].join(""),
  "gitlab-personal-token": () => ["gl", "pat-", "A".repeat(20)].join(""),
  "slack-bot-token": () => ["xo", "xb-", "111111111111", "-", "222222222222", "-", "A".repeat(24)].join(""),
  "slack-user-token": () => ["xo", "xp-", "111111111111", "-", "222222222222", "-", "A".repeat(24)].join(""),
  "npm-access-token": () => ["np", "m_", "A".repeat(36)].join(""),
  "aws-access-key-id": () => ["AK", "IA", "A".repeat(16)].join(""),
  "stripe-secret-key": () => ["sk", "_live_", "A".repeat(24)].join(""),
  "google-api-key": () => ["AI", "za", "A".repeat(35)].join(""),
  "openai-project-key": () => ["sk", "-proj-", "A".repeat(48)].join(""),
  "resend-api-key": () => ["re", "_", "A".repeat(32)].join(""),
  "telnyx-api-key": () => ["KE", "Y", "A".repeat(32)].join(""),
  "telegram-bot-token": () => ["123456789", ":", "A".repeat(35)].join(""),
  "stripe-webhook-secret": () => ["wh", "sec_", "A".repeat(32)].join(""),
  "stripe-restricted-key": () => ["rk", "_live_", "A".repeat(24)].join(""),
  "pem-private-key-header": () => [
    "-".repeat(5), "BEGIN", " PRIVATE", " KEY", "-".repeat(5),
    "\n", "A".repeat(64), "\n",
    "-".repeat(5), "END", " PRIVATE", " KEY", "-".repeat(5),
  ].join(""),
  "postgres-credential-uri": () => ["post", "gresql", "://", "panel_user", ":", "panel_pass", "@", "db.invalid", "/", "life"].join(""),
  "redis-credential-uri": () => ["red", "is", "://", "default", ":", "panel_pass", "@", "cache.invalid", ":", "6379", "/", "0"].join(""),
  "mongodb-srv-credential-uri": () => ["mongo", "db+srv", "://", "panel_user", ":", "panel_pass", "@", "cluster.invalid", "/", "life"].join(""),
});

const RECIPE_IDS = Object.freeze(Object.keys(RECIPE_BUILDERS));

const API_ORACLES = Object.freeze({
  "safe-timeline-sentence": Object.freeze({
    status: 200,
    path: Object.freeze(["items", 0, "sentence"]),
    equals: SAFE_TIMELINE_SENTENCE,
  }),
  "null-ledger-link": Object.freeze({
    status: 200,
    path: Object.freeze(["financial", "items", 0, "link"]),
    equals: null,
  }),
  "settings-unavailable": Object.freeze({
    status: 422,
    body: Object.freeze({ error: "section_unavailable", section: "settings" }),
  }),
  "control-center-unavailable": Object.freeze({
    status: 422,
    body: Object.freeze({ error: "section_unavailable", section: "control-center" }),
  }),
  "generic-control-center-identity": Object.freeze({
    status: 200,
    path: Object.freeze(["identity", "name"]),
    equals: "Life Manager user",
  }),
});

const BROWSER_ORACLES = Object.freeze({
  "safe-timeline-visible": Object.freeze({
    state: "loaded",
    includes: SAFE_TIMELINE_SENTENCE,
  }),
  "no-ledger-anchor": Object.freeze({
    state: "loaded",
    excludes: "class=\"ledger-link\"",
  }),
  "generic-identity-visible": Object.freeze({
    state: "loaded",
    includes: "Life Manager user",
  }),
});

const CHANNELS = Object.freeze([
  Object.freeze({ id: "api-timeline-text", section: "timeline", source: "timeline-text", apiOracle: "safe-timeline-sentence" }),
  Object.freeze({ id: "api-ledger-href", section: "ledger", source: "ledger-href", apiOracle: "null-ledger-link" }),
  Object.freeze({ id: "api-settings-call-language", section: "settings", source: "settings-call-language", apiOracle: "settings-unavailable" }),
  Object.freeze({ id: "api-settings-wake-policy", section: "settings", source: "settings-wake-policy", apiOracle: "settings-unavailable" }),
  Object.freeze({ id: "api-control-center-call-language", section: "control-center", source: "control-center-call-language", apiOracle: "control-center-unavailable" }),
  Object.freeze({ id: "api-control-center-wake-policy", section: "control-center", source: "control-center-wake-policy", apiOracle: "control-center-unavailable" }),
  Object.freeze({ id: "browser-timeline-text", section: "timeline", source: "timeline-text", apiOracle: "safe-timeline-sentence", browserOracle: "safe-timeline-visible" }),
  Object.freeze({ id: "browser-ledger-href", section: "ledger", source: "ledger-href", apiOracle: "null-ledger-link", browserOracle: "no-ledger-anchor" }),
  Object.freeze({ id: "browser-control-center-identity", section: "control-center", source: "control-center-identity", apiOracle: "generic-control-center-identity", browserOracle: "generic-identity-visible" }),
]);

const POSITIVE_CASES = Object.freeze([
  Object.freeze({
    id: "settings-null-call-language",
    section: "settings",
    source: "settings-null-call-language",
    browserIncludes: "未設定",
  }),
  Object.freeze({
    id: "control-center-null-call-language",
    section: "control-center",
    source: "control-center-null-call-language",
    browserIncludes: '<option value="" selected disabled>Not configured</option>',
  }),
]);

const MALFORMED_CASES = Object.freeze([
  Object.freeze({ id: "malformed-scores", section: "scores" }),
  Object.freeze({ id: "malformed-gates", section: "gates" }),
  Object.freeze({ id: "malformed-settings", section: "settings" }),
  Object.freeze({ id: "malformed-control-center", section: "control-center" }),
]);

const EXPECTED_COUNTS = Object.freeze({
  api: RECIPE_IDS.length * CHANNELS.length + POSITIVE_CASES.length + MALFORMED_CASES.length,
  browser: RECIPE_IDS.length * CHANNELS.filter((channel) => channel.browserOracle).length
    + POSITIVE_CASES.length
    + MALFORMED_CASES.length,
});

function buildRecipes() {
  return RECIPE_IDS.map((id) => Object.freeze({ id, value: RECIPE_BUILDERS[id]() }));
}

module.exports = {
  API_ORACLES,
  BROWSER_LOAD_ERROR_COPY,
  BROWSER_ORACLES,
  CHANNELS,
  EXPECTED_COUNTS,
  MALFORMED_CASES,
  POSITIVE_CASES,
  RECIPE_IDS,
  SAFE_TIMELINE_SENTENCE,
  buildRecipes,
};
