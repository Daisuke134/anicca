// lib/providers/luma.js — Luma provider (spec TODO #7 fills this in).
//
// v1 discovers and RSVPs on Luma ONLY (decision D1). The Luma account is contact@aniccaai.com,
// which Anicca owns, so a ban lands on Anicca and not on Dais. The Luma API is organiser-side and
// gated behind Luma Plus, so the attendee-side RSVP has to go through the CloakBrowser
// daily-driver persistent profile.
//
// Every function here refuses. A stub that returned a plausible object would show up in the trace
// ledger as indistinguishable from real work.
"use strict";

const refuse = (name) => async () => {
  throw new Error(`NOT_IMPLEMENTED: luma.${name}`);
};

module.exports = {
  // DISCOVER: -> {ok, candidates: [{id, name, url, starts_at, body}]}
  discoverEvents: refuse("discoverEvents"),
  // ACT: RSVP through the daily-driver profile -> {ok, receipt}
  rsvp: refuse("rsvp"),
  // EVIDENCE E3: the durable event URL, never the /join/complete/ one-shot result URL.
  canonicalEventUrl: refuse("canonicalEventUrl"),
  // EVIDENCE E3: the caller observes HEAD here; the gate only judges the number it reports.
  headStatus: refuse("headStatus"),
};
