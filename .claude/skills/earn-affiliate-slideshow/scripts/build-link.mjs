#!/usr/bin/env node
// Build an Amazon affiliate link from an ASIN + the configured partner tag.
// No PA-API needed: a /dp/<ASIN>?tag=<PARTNER_TAG> link is a valid associate link
// and works during the 180-day qualifying window (3 sales to keep the account).
//
// Usage: node build-link.mjs <ASIN> [--tag aniccaai-22] [--mkt www.amazon.co.jp]
const args = process.argv.slice(2);
const asin = args[0];
const get = (f, d) => { const i = args.indexOf(f); return i >= 0 ? args[i + 1] : d; };
const tag = get("--tag", process.env.AMAZON_PARTNER_TAG);
const mkt = get("--mkt", process.env.AMAZON_ASSOC_MARKETPLACE || "www.amazon.co.jp");

if (!asin || !/^[A-Z0-9]{10}$/.test(asin)) { console.error("ERROR: valid 10-char ASIN required"); process.exit(2); }
if (!tag) { console.error("ERROR: partner tag required (AMAZON_PARTNER_TAG or --tag)"); process.exit(2); }

const url = `https://${mkt}/dp/${asin}?tag=${encodeURIComponent(tag)}&linkCode=ll1&language=ja_JP`;
console.log(url);
