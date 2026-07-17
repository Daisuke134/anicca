// lib/money-path.js — C5/C6 (VCSDD life-manager-cost-connect-reliability). Continuous money-path check
// so the ¥700k-wrong-link / site-down class (2026-07-03) can never silently survive again.
// SRE: black-box + CONTENT assertion (200 is not enough — assert the actual Stripe link VALUE). The
// known-good value is the single registry SSOT (also the GHA build source). Rollback is gated:
//   - debounce: >=2 consecutive FAIL (no single-transient rollback)
//   - flap guard: never roll back into a last-good that itself fails → escalate instead
//   - dedup: ONE Telegram per incident, re-armed after a recovery
// Pure logic; the HTTP fetch + Netlify restore + Telegram send live in the caller (a GitHub Actions cron,
// independent of Railway/Netlify so the monitor never dies with the monitored).
"use strict";

const STRIPE_RE = /https:\/\/buy\.stripe\.com\/[A-Za-z0-9_]+/g;

// All DISTINCT buy.stripe.com links in a chunk (order-preserving). The monitor must not trust the FIRST
// match — a rogue second link (exactly the ¥700k class) must be caught.
function extractAllStripeLinks(chunk) {
  return [...new Set(String(chunk || "").match(STRIPE_RE) || [])];
}

function extractStripeLink(chunk) {
  const all = extractAllStripeLinks(chunk);
  return all.length ? all[0] : null;
}

// assertMoneyPath({ chunk }, registry) → { ok, reason }
// FAIL if: no link, the (single) link != registry, OR any OTHER distinct stripe link is present
// (ambiguous bundle = a rogue link snuck in). Only an exact single-match to the registry passes.
function assertMoneyPath(bundle, registry) {
  const links = extractAllStripeLinks(bundle && bundle.chunk);
  if (links.length === 0) return { ok: false, reason: "no stripe link found in /lm chunk" };
  const rogue = links.filter((l) => l !== registry.stripe_lm_url);
  if (rogue.length > 0)
    return { ok: false, reason: `stripe link mismatch/ambiguous: unexpected=${rogue.join(",")} expected=${registry.stripe_lm_url}` };
  return { ok: true, reason: "ok" };
}

// Stateful gate across checks.
class RollbackController {
  constructor({ debounce = 2 } = {}) {
    this.debounce = debounce;
    this.consecutiveFail = 0;
    this.incidentOpen = false; // true once we've alerted/acted for the current incident
    this.rollbackFired = false; // one restore per incident — never re-fire real Netlify restores each cycle
  }
  // onResult(pass, { lastGoodPasses }) → { rollback, escalate, notify }
  onResult(pass, { lastGoodPasses = true } = {}) {
    if (pass) {
      this.consecutiveFail = 0;
      this.incidentOpen = false; // recovery re-arms alerting
      this.rollbackFired = false; // ...and re-arms rollback for a future incident
      return { rollback: false, escalate: false, notify: false };
    }
    this.consecutiveFail += 1;
    if (this.consecutiveFail < this.debounce) {
      return { rollback: false, escalate: false, notify: false }; // still debouncing
    }
    const notify = !this.incidentOpen; // one alert per incident
    if (notify) this.incidentOpen = true;
    if (lastGoodPasses) {
      const rollback = !this.rollbackFired; // one restore per incident
      if (rollback) this.rollbackFired = true;
      return { rollback, escalate: false, notify };
    }
    // flap guard: the rollback target is also bad → don't flap, escalate to a human
    return { rollback: false, escalate: true, notify };
  }
}

module.exports = { extractStripeLink, assertMoneyPath, RollbackController, STRIPE_RE };
