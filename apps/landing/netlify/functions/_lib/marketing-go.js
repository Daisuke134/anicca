const { randomUUID } = require("node:crypto");
const { isAffiliatePlacement } = require("./affiliate-placement");

const TOKEN = /^(?:(ai|ho|ej|ee)_[a-z2-7]{20}|af_(elevenlabs-discovered-[a-z0-9][a-z0-9-]*-en(?:-experiment-[a-f0-9]{12})?-1))$/; // AFFILIATE_CTA_V1

function destination(product, token, providerToken) {
  if (product.kind === "affiliate") return `https://try.elevenlabs.io/${product.placementId}`;
  if (product.kind === "app") {
    const query = new URLSearchParams({ pt: providerToken, ct: token, mt: "8" });
    return `https://apps.apple.com/app/id${product.appId}?${query}`;
  }
  const query = new URLSearchParams({
    utm_source: "social",
    utm_medium: "owned_redirect",
    utm_campaign: token,
  });
  return `https://aniccaai.com${product.path}?${query}`;
}

function makeSupabasePersist({ url, serviceKey, fetchImpl = fetch }) {
  if (!url || !serviceKey) throw new Error("Supabase receipt storage is not configured");
  const endpoint = `${url.replace(/\/$/, "")}/rest/v1/marketing_click_receipts`;
  return async (_key, receipt) => {
    const response = await fetchImpl(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        apikey: serviceKey,
        Authorization: `Bearer ${serviceKey}`,
        Prefer: "return=minimal",
      },
      body: JSON.stringify(receipt),
    });
    if (!response.ok) throw new Error(`click receipt storage failed: HTTP ${response.status}`);
  };
}

function makeMarketingGoHandler({
  products,
  providerToken,
  persist,
  now = () => new Date().toISOString(),
  receiptId = randomUUID,
}) {
  if (!products || typeof persist !== "function") // AFFILIATE_CTA_V2
    throw new Error("marketing-go dependencies are required");
  return async (event) => {
    if (event.httpMethod !== "GET")
      return { statusCode: 405, headers: { allow: "GET" }, body: "Method Not Allowed" };
    const token = decodeURIComponent(String(event.path || "").split("/").filter(Boolean).at(-1) || "");
    const match = TOKEN.exec(token);
    const product = match && (!match[2] || isAffiliatePlacement(match[2])) && (match[2]
      ? { productId: match[2], kind: "affiliate", placementId: match[2] }
      : products[match[1]]);
    if (!product)
      return { statusCode: 404, headers: { "cache-control": "no-store" }, body: "Not Found" };
    if (product.kind === "app" && !providerToken)
      return { statusCode: 503, headers: { "cache-control": "no-store" }, body: "Attribution unavailable" };
    const id = receiptId();
    const receipt = {
      schema_version: 1,
      receipt_id: id,
      campaign_token: token,
      product_id: product.productId,
      clicked_at: now(),
    };
    try {
      await persist(`clicks/${id}`, receipt);
    } catch {
      return {
        statusCode: 503,
        headers: { "cache-control": "no-store", "retry-after": "60" },
        body: "Click receipt unavailable",
      };
    }
    return {
      statusCode: 302,
      headers: {
        location: destination(product, token, providerToken),
        "cache-control": "no-store",
        "x-click-receipt": id,
      },
      body: "",
    };
  };
}

module.exports = { TOKEN, destination, makeMarketingGoHandler, makeSupabasePersist };
