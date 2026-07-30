// lib/providers/cloakbrowser.js — browser I/O for ACT and for the E2 artifact.
//
// Browser work runs on the CloakBrowser daily-driver persistent profile, which is already logged
// into the services Anicca needs. That context is long-lived and shared: this provider attaches to
// it and must never kill it.
//
// Every function refuses until the real adapter lands.
"use strict";

const refuse = (name) => async () => {
  throw new Error(`NOT_IMPLEMENTED: cloakbrowser.${name}`);
};

module.exports = {
  // -> a page handle inside the existing persistent context.
  openPage: refuse("openPage"),
  // EVIDENCE E2: -> a PNG Buffer of the confirmation screen (magic number + >= 5000 bytes).
  screenshotPng: refuse("screenshotPng"),
  // ACT: -> {ok, status} from the real form submission.
  submitForm: refuse("submitForm"),
  // Closes THIS page only. It never tears down the shared persistent context.
  close: refuse("close"),
};
