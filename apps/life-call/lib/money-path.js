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

const STRIPE_RE = /https:\/\/buy\.stripe\.com\/[A-Za-z0-9_]+/;

function extractStripeLink(chunk) {
  const m = String(chunk || "").match(STRIPE_RE);
  return m ? m[0] : null;
}

// assertMoneyPath({ chunk }, registry) → { ok, reason }
function assertMoneyPath(bundle, registry) {
  const link = extractStripeLink(bundle && bundle.chunk);
  if (!link) return { ok: false, reason: "no stripe link found in /lm chunk" };
  if (link !== registry.stripe_lm_url)
    return { ok: false, reason: `stripe link mismatch: live=${link} expected=${registry.stripe_lm_url}` };
  return { ok: true, reason: "ok" };
}

// Stateful gate across checks.
class RollbackController {
  constructor({ debounce = 2 } = {}) {
    this.debounce = debounce;
    this.consecutiveFail = 0;
    this.incidentOpen = false; // true once we've alerted for the current incident
  }
  // onResult(pass, { lastGoodPasses }) → { rollback, escalate, notify }
  onResult(pass, { lastGoodPasses = true } = {}) {
    if (pass) {
      this.consecutiveFail = 0;
      this.incidentOpen = false; // recovery re-arms alerting
      return { rollback: false, escalate: false, notify: false };
    }
    this.consecutiveFail += 1;
    if (this.consecutiveFail < this.debounce) {
      return { rollback: false, escalate: false, notify: false }; // still debouncing
    }
    const notify = !this.incidentOpen; // one alert per incident
    if (notify) this.incidentOpen = true;
    if (lastGoodPasses) {
      return { rollback: true, escalate: false, notify };
    }
    // flap guard: the rollback target is also bad → don't flap, escalate to a human
    return { rollback: false, escalate: true, notify };
  }
}

module.exports = { extractStripeLink, assertMoneyPath, RollbackController, STRIPE_RE };
