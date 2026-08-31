"use strict";

const crypto = require("node:crypto");
const { persistFeedback } = require("./feedback-intake.js");


const SIGNAL_CLASSES = Object.freeze({
  provider_timeout: "provider-timeout",
  call_failed: "side-effect-failed",
  email_failed: "side-effect-failed",
  post_failed: "side-effect-failed",
  http_5xx: "runtime-regression",
  eval_regression: "runtime-regression",
});

const CLASS_COPY = Object.freeze({
  "provider-timeout": "Provider timeout",
  "side-effect-failed": "Side effect failed",
  "runtime-regression": "Runtime regression",
});

const SAFE_SLUG = /^[a-z][a-z0-9-]{1,63}$/;


function buildErrorIntake({ signal, component, fingerprint, provenanceKey } = {}) {
  const incidentClass = SIGNAL_CLASSES[signal];
  if (
    !incidentClass
    || !SAFE_SLUG.test(String(component || ""))
    || !SAFE_SLUG.test(String(fingerprint || ""))
    || !String(provenanceKey || "")
  ) {
    throw new Error("error_intake_invalid");
  }
  const digest = crypto
    .createHmac("sha256", String(provenanceKey))
    .update(`${incidentClass}:${component}:${fingerprint}`)
    .digest("hex")
    .slice(0, 32);
  return Object.freeze({
    source_ref: `err:sha256:${digest}`,
    summary: `${CLASS_COPY[incidentClass]} in ${component} (${fingerprint}).`,
    labels: Object.freeze(["error", incidentClass]),
  });
}


async function persistErrorIntake(intake, options = {}) {
  const persist = options.persist || persistFeedback;
  return persist(intake, options);
}


module.exports = {
  SIGNAL_CLASSES,
  buildErrorIntake,
  persistErrorIntake,
};
