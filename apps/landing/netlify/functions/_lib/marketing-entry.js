const { randomUUID } = require("node:crypto");
const { PLACEMENT, isAffiliatePlacement } = require("./affiliate-placement");


function makeSupabasePersist({ url, serviceKey, fetchImpl = fetch }) {
  const endpoint = `${url.replace(/\/$/, "")}/rest/v1/marketing_click_receipts`;
  return async (receipt) => {
    const response = await fetchImpl(endpoint, {
      method: "POST", headers: { "Content-Type": "application/json", apikey: serviceKey,
        Authorization: `Bearer ${serviceKey}`, Prefer: "return=minimal" },
      body: JSON.stringify(receipt),
    });
    if (!response.ok) throw new Error(`entry receipt storage failed: HTTP ${response.status}`);
  };
}

function makeEntryHandler({ persist, now = () => new Date().toISOString(), receiptId = randomUUID }) {
  return async (event) => {
    if (event.httpMethod !== "POST") return { statusCode: 405, headers: { allow: "POST" }, body: "" };
    let body;
    try { body = JSON.parse(event.body || "{}"); } catch { return { statusCode: 400, body: "" }; }
    if (!isAffiliatePlacement(body.placement_id) || body.source !== "X")
      return { statusCode: 400, body: "" };
    const receipt = { schema_version: 1, receipt_id: receiptId(), campaign_token: "entry_x",
      product_id: `entry:${body.placement_id}`, clicked_at: now() };
    try { await persist(receipt); } catch { return { statusCode: 503, body: "" }; }
    return { statusCode: 204, headers: { "cache-control": "no-store" }, body: "" };
  };
}

module.exports = { PLACEMENT, makeEntryHandler, makeSupabasePersist };
// AFFILIATE_ENTRY_V1
