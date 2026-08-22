"use client";

import { useEffect } from "react";

const X_HOSTS = new Set(["x.com", "www.x.com", "twitter.com", "www.twitter.com", "t.co"]);

export default function AffiliateEntryReceipt({ placementId }: { placementId: string }) {
  useEffect(() => {
    let source = "UNKNOWN";
    try { source = X_HOSTS.has(new URL(document.referrer).hostname.toLowerCase()) ? "X" : "UNKNOWN"; } catch {}
    if (source !== "X") return;
    void fetch("/.netlify/functions/marketing-entry", {
      method: "POST", credentials: "omit", cache: "no-store", keepalive: true,
      referrerPolicy: "no-referrer", headers: { "content-type": "application/json" },
      body: JSON.stringify({ placement_id: placementId, source }),
    });
  }, [placementId]);
  return null;
}
// AFFILIATE_ENTRY_V1
