// lib/outbound-events-stages.js — the events pack's six stages, built over the Luma provider.
//
// The pipeline (runtime/loop/outbound/pipeline.mjs) owns ordering and the result shape. This file
// owns which provider call each stage makes, and — the part that matters — WHERE THE VERDICT LIVES.
//
//   ACT      calls luma.rsvp and returns ok=true when the attempt COMPLETED. "Completed" is not
//            "succeeded": rsvp deliberately returns raw material and refuses to grade itself.
//   EVIDENCE re-reads the screenshot off disk, observes a real HEAD on the canonical URL, and hands
//            the bundle to runtime/loop/outbound/evidence.mjs. That module, and only that module,
//            decides. Nothing here may shortcut it.
//
// AUTO-RSVP IS OFF BY DEFAULT (`auto_rsvp: false` in the pack config). The deterministic screen can
// prove an event is free, in-person, in-region and open — it cannot judge whether the event is
// worth Dais's evening. That judgment is the model's (spec §3.1: QUALIFY is LLM, regex forbidden)
// and lands with TODO #10. Until then the daily pass discovers, screens and reports, and a human-
// initiated run (scripts/outbound-luma-rsvp.js) is what actually registers.
"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { pathToFileURL } = require("node:url");

const { resolveDataRoot } = require("./runtime-paths.js");

const ENGINE_DIR = path.join(__dirname, "..", "..", "..", "runtime", "loop", "outbound");
const loadEvidence = () => import(pathToFileURL(path.join(ENGINE_DIR, "evidence.mjs")).href);

/** Where E2 artifacts land: under the canonical portable data root, never inside the repo. */
function artifactDir(env = {}) {
  return path.join(resolveDataRoot(env), "outbound", "evidence", "events");
}

/**
 * Read the RSVP identity from the environment. It is NOT stored in the pack config: a config file
 * is committed, and a name / mailbox / phone number are the operator's personal data.
 */
function readIdentity(env = {}) {
  const name = String(env.LM_OUTBOUND_NAME || "").trim();
  const email = String(env.LM_OUTBOUND_EMAIL || "").trim();
  const phone = String(env.LM_OUTBOUND_PHONE || "").trim();
  const localName = String(env.LM_OUTBOUND_NAME_JA || "").trim();
  return { name, email, ...(phone ? { phone } : {}), ...(localName ? { localName } : {}) };
}

/** A Japanese-locale event wants the Japanese form of the name when one is configured. */
function nameFor(event, identity) {
  const jp = identity.localName;
  if (!jp) return identity.name;
  return String((event && event.timezone) || "") === "Asia/Tokyo" ? jp : identity.name;
}

function discoverOptions(config = {}) {
  return {
    city: config.city || "tokyo",
    ...(config.categories ? { categories: config.categories } : {}),
    ...(Array.isArray(config.regions) ? { regions: [...config.regions] } : {}),
    ...(Number.isInteger(config.hydrate_limit) ? { hydrateLimit: config.hydrate_limit } : {}),
    ...(Number.isInteger(config.polite_delay_ms) ? { politeDelayMs: config.polite_delay_ms } : {}),
  };
}

function buildStages(deps = {}) {
  const luma = deps.luma || require("./providers/luma.js");
  const env = deps.env || process.env;
  const identity = deps.identity || readIdentity(env);
  const readFile = deps.readFile || ((p) => fs.readFileSync(p));
  const evidenceDir = deps.artifactDir || artifactDir(env);
  const cdpUrl = deps.cdpUrl || String(env.LM_BROWSER_CDP_URL || "");

  return {
    async discover({ config }) {
      const result = await luma.discoverEvents(discoverOptions(config));
      if (!result.ok) return { ok: false, reason: result.reason || "luma_discover_failed" };
      return { ok: true, candidates: [...result.candidates], data: { rejected: result.rejected } };
    },

    async qualify({ config, target }) {
      // Re-screen rather than trusting DISCOVER's word: the two run minutes apart and an event can
      // sell out in between.
      const verdict = luma.screenEvent(target, {
        ...discoverOptions(config),
        ...(target && target.ticket ? { ticketApiId: target.ticket.apiId } : {}),
      });
      if (!verdict.ok) {
        return { ok: false, reason: `screened_out:${verdict.rejections.map((r) => r.code).join(",")}` };
      }
      if (config.auto_rsvp !== true) {
        // Honest stop, not a failure to hide: the model has not been asked yet (TODO #10).
        return { ok: false, reason: "auto_rsvp_disabled_pending_model_qualify" };
      }
      return { ok: true, data: { ticket: verdict.ticket } };
    },

    async act({ target, prior }) {
      if (!cdpUrl) return { ok: false, reason: "no_leased_cdp_url (browser-guard.sh acquire)" };
      if (!identity.name || !identity.email) return { ok: false, reason: "no_rsvp_identity_in_env" };
      const ticket = (prior.qualify && prior.qualify.ticket) || target.ticket || null;
      const receipt = await luma.rsvp(target.url, { ...identity, name: nameFor(target, identity) }, {
        cdpUrl,
        artifactDir: evidenceDir,
        ...(ticket && ticket.name ? { ticketName: ticket.name } : {}),
      });
      // ok=true means the attempt ran to completion. EVIDENCE decides whether it worked.
      return { ok: true, data: { receipt } };
    },

    async evidence({ prior }) {
      const receipt = prior.act && prior.act.receipt;
      if (!receipt) return { ok: false, reason: "no_rsvp_receipt" };
      const { verifyEvidence } = await loadEvidence();

      let artifactBytes = null;
      try {
        artifactBytes = readFile(receipt.artifactPath);
      } catch {
        artifactBytes = null; // absence of evidence, which the gate turns into E2_ABSENT
      }

      let head = null;
      try {
        head = await luma.headStatus(receipt.canonicalUrl);
      } catch {
        head = null; // recorded as "no observed HEAD status", which the gate rejects
      }

      const bundle = luma.buildEvidence(receipt, {
        ...(artifactBytes ? { artifactBytes } : {}),
        headStatus: head,
      });
      const verdict = verifyEvidence(bundle);
      // The ledger stores the artifact PATH, not its bytes: the verifier re-reads the file.
      const recorded = { ...bundle, e2: { ...bundle.e2, bytes: undefined } };
      delete recorded.e2.bytes;
      if (!verdict.ok) {
        return {
          ok: false,
          reason: `evidence_gate:${verdict.failures.map((f) => f.code).join(",")}`,
          evidence: recorded,
        };
      }
      return { ok: true, evidence: recorded, data: { guest_key: receipt.guestKey, venue: receipt.venue } };
    },

    // TRACK reads replies and outcomes out of the real mailbox (TODO #16); LEARN rewrites templates
    // from the trace ledger (TODO #21). Neither is built, and neither pretends to be.
    async track() {
      return { ok: false, reason: "track_not_wired_for_events" };
    },
    async learn() {
      return { ok: false, reason: "learn_not_wired_for_events" };
    },
  };
}

module.exports = { buildStages, readIdentity, nameFor, artifactDir, discoverOptions };
