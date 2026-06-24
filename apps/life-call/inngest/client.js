// inngest/client.js — shared Inngest client for the life-manager app.
// Uses the verified 2-arg createFunction API (triggers inside the first config object).
"use strict";

const { Inngest } = require("inngest");

const inngest = new Inngest({ id: "life-manager" });

module.exports = { inngest };
