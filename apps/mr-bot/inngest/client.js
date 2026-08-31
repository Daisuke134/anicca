// inngest/client.js — shared Inngest client for the mr-bot app.
// Uses the verified 2-arg createFunction API (triggers inside the first config object).
"use strict";

const { Inngest } = require("inngest");

const inngest = new Inngest({ id: "mr-bot" });

module.exports = { inngest };
