"use strict";

// The mobile marketing packs that were measured before the quarantine are
// Larry and ReelClaw families.  A Life Manager wake/demo render is a separate
// artifact and must never silently become a mobile product creative.
const MOBILE_PACK_FORMATS = Object.freeze({
  "honne-ai": new Set(["reelclaw"]),
  anicca: new Set(["larry", "reelclaw", "reelclaw-card", "reelclaw-widget", "watercolor"]),
  "anicca-ios": new Set(["larry", "reelclaw", "reelclaw-card", "reelclaw-widget", "watercolor"]),
});

function assertMarketingProductFormat(productId, formatId) {
  const product = String(productId || "");
  const format = String(formatId || "");
  const allowed = MOBILE_PACK_FORMATS[product];
  if (allowed && !allowed.has(format)) {
    throw new Error(`marketing product ${product} cannot use format ${format}`);
  }
  return { productId: product, formatId: format };
}

function isApprovedMarketingProductFormat(productId, formatId) {
  const product = String(productId || "");
  const format = String(formatId || "");
  const allowed = MOBILE_PACK_FORMATS[product];
  return !allowed || allowed.has(format);
}

module.exports = {
  MOBILE_PACK_FORMATS,
  assertMarketingProductFormat,
  isApprovedMarketingProductFormat,
};
