#!/usr/bin/env node
"use strict";

const { chromium } = require("playwright-core");
const { createCloakBrowserDailyDriver } = require("../lib/cloakbrowser-daily-driver.js");
const { discoverLumaTokyo } = require("../lib/luma-discovery.js");

async function inspectLumaSemanticSourceReadonly(options = {}) {
  const dailyDriver = (options.createDailyDriver || createCloakBrowserDailyDriver)({
    connectOverCDP: options.connectOverCDP || ((endpoint) => chromium.connectOverCDP(endpoint)),
  });
  const inventory = await (options.discover || discoverLumaTokyo)({ dailyDriver });
  if (!inventory || inventory.complete !== true || !inventory.candidates.length) {
    throw new Error("Luma semantic source inspection unavailable");
  }
  const raw = await dailyDriver.withLumaPage(inventory.candidates[0].canonical_url, (page) => page.evaluate(() => {
    const events = [];
    for (const script of document.querySelectorAll('script[type="application/ld+json"]')) {
      try {
        const parsed = JSON.parse(script.textContent || "null");
        const values = Array.isArray(parsed) ? parsed : parsed && parsed["@graph"] || [parsed];
        for (const value of values) if (value && value["@type"] === "Event") events.push(value);
      } catch {
        // Malformed provider metadata is counted as absent without exposing it.
      }
    }
    const event = events[0] || {};
    const location = event.location && typeof event.location === "object" ? event.location : {};
    const address = location.address && typeof location.address === "object" ? location.address : {};
    const hrefs = [...document.querySelectorAll("a[href]")].map((link) => link.getAttribute("href") || "");
    return {
      eventCount: events.length,
      eventKeys: Object.keys(event).sort(),
      descriptionLength: typeof event.description === "string" ? event.description.length : 0,
      organizerCount: Array.isArray(event.organizer) ? event.organizer.length : event.organizer ? 1 : 0,
      attendeeCount: Array.isArray(event.attendee) ? event.attendee.length : event.attendee ? 1 : 0,
      performerCount: Array.isArray(event.performer) ? event.performer.length : event.performer ? 1 : 0,
      locationKeys: Object.keys(location).sort(),
      addressKeys: Object.keys(address).sort(),
      publicProfileLinkCount: hrefs.filter((href) => /\/(?:user|profile|u)\//i.test(href)).length,
      pageTextLength: (document.body && document.body.innerText || "").length,
    };
  }));
  return Object.freeze({
    inventory_complete: true,
    inventory_rounds: inventory.rounds,
    discovered_candidate_count: inventory.candidates.length,
    json_ld_event_count: raw.eventCount,
    json_ld_event_keys: Object.freeze(raw.eventKeys),
    description_present: raw.descriptionLength > 0,
    description_length: raw.descriptionLength,
    organizer_count: raw.organizerCount,
    attendee_count: raw.attendeeCount,
    performer_count: raw.performerCount,
    location_keys: Object.freeze(raw.locationKeys),
    address_keys: Object.freeze(raw.addressKeys),
    public_profile_link_count: raw.publicProfileLinkCount,
    rendered_page_text_length: raw.pageTextLength,
  });
}

async function main() {
  try {
    const result = await inspectLumaSemanticSourceReadonly();
    process.stdout.write(`${JSON.stringify(result)}\n`, () => process.exit(0));
  } catch {
    process.stderr.write("Luma semantic source inspection unavailable\n", () => process.exit(1));
  }
}

if (require.main === module) main();

module.exports = { inspectLumaSemanticSourceReadonly };
