#!/usr/bin/env node
// ~/anicca/skills/life/ask.js — B-ask skill top-level entrypoint (spec27 WF-B B-ask).
//
// This file provides the rubric-named flat path: ~/anicca/skills/life/ask.js
// It re-exports the full implementation from the canonical location:
//   ~/anicca/skills/life/ask/ask.js
//
// Usage is identical to the canonical module:
//   node ~/anicca/skills/life/ask.js --action question
//   node ~/anicca/skills/life/ask.js --action reply --body '<json>'
//
// The canonical source (ask/ask.js) is the HTTP wrapper that POSTs to:
//   https://aniccaai.com/.netlify/functions/life-ask?action=<action>
// which is the Netlify function handling GCal scanning + AgentMail sends.

"use strict";

// Delegate entirely to the canonical implementation.
// This ensures the flat shim and the subdirectory implementation stay in sync.
module.exports = require("./ask/ask");

// Run as CLI entrypoint: forward to ask/ask.js main()
if (require.main === module) {
  require("./ask/ask");
}
