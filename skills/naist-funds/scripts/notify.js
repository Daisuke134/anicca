const { loadCache, saveCache } = require("./utils/storage");
const { sendMessage } = require("./utils/slack");

function isUrgent(deadline) {
  if (!deadline) return false;
  const d = new Date(deadline);
  const now = new Date();
  const diffDays = (d - now) / (1000 * 60 * 60 * 24);
  return diffDays >= 0 && diffDays <= 30;
}

function formatGrant(grant) {
  const urgent = isUrgent(grant.deadline);
  const prefix = urgent ? "⚠️ *[締切間近] " : "*";
  const suffix = urgent ? "*" : "*";
  const deadline = grant.deadline ? `📅 締切: ${grant.deadline}` : "📅 締切: 不明";
  const amount = grant.amount ? `💰 ${grant.amount}` : "";
  const parts = [`${prefix}${grant.name}${suffix}`];
  const meta = [`🏢 ${grant.organization}`, deadline, amount].filter(Boolean).join(" | ");
  parts.push(meta);
  if (grant.summary) parts.push(grant.summary);
  parts.push(`🔗 ${grant.url || "URL不明"}`);
  return parts.join("\n");
}

function notifyGrants(grants) {
  const cache = loadCache();
  const notifiedIds = new Set(cache.notified.map((n) => n.id));

  const newGrants = grants.filter((g) => !notifiedIds.has(g.id));
  if (newGrants.length === 0) {
    console.log("[naist-funds] 新着なし（全件スキップ）");
    return { posted: 0, skipped: grants.length };
  }

  const lines = [
    `📢 *助成金・奨学金 新着情報* (${new Date().toISOString().slice(0, 10)})`,
    ""
  ];
  for (const g of newGrants) {
    lines.push(formatGrant(g));
    lines.push("");
  }
  lines.push(`---\n新着: ${newGrants.length}件 | スキップ（既通知）: ${grants.length - newGrants.length}件`);

  sendMessage(lines.join("\n"));

  const now = new Date().toISOString();
  const updated = [
    ...cache.notified,
    ...newGrants.map((g) => ({ id: g.id, notifiedAt: now }))
  ].slice(-100);
  saveCache({ ...cache, notified: updated, lastFetchedAt: now });

  return { posted: newGrants.length, skipped: grants.length - newGrants.length };
}

module.exports = { notifyGrants, formatGrant, isUrgent };
