"use strict";

const path = require("node:path");
const { runLocalAgentRunner } = require("./connector-luna-judgment.js");

function unavailable() { throw new Error("Connector agentic registration unavailable"); }

async function runConnectorAgenticRegistration(input = {}, deps = {}) {
  const canonicalUrl = String(input.canonicalUrl || "").trim();
  if (!/^https:\/\/luma\.com\/[A-Za-z0-9_-]+(?:[/?#].*)?$/.test(canonicalUrl)) unavailable();
  const profile = input.profile && typeof input.profile === "object" ? input.profile : {};
  const result = await (deps.runAgentRunner || runLocalAgentRunner)({
    prompt: [
      "You are the Connector loop's browser executor. Execute the event registration now; do not edit code and do not ask the human.",
      `Use the already-open tab for this exact event in the local CloakBrowser daily-driver session at CDP http://127.0.0.1:9222: ${canonicalUrl}`,
      "Do not create another tab, navigate away, or close the event tab. The parent loop deliberately keeps this tab alive until you return.",
      "Use the existing authenticated browser account. Visually inspect and operate the live UI as a capable browser agent; do not depend on hardcoded site selectors.",
      "Click the registration/request-to-join action, complete every required form field, submit it, and keep working until the page visibly shows the registered, going, ticket, or pending-approval state.",
      "For identity/contact fields use only the supplied profile. For ordinary subjective questions, answer truthfully and generally: building Life Manager and AI agents, meeting founders/engineers/users, learning, and making useful connections. Choose a reasonable visible option for required choices. Leave optional social handles blank if unknown.",
      "Do not return immediately after loading the page or after a click. Wait for each UI change, inspect the buttons and form, and re-read the final live page. Return the required JSON only after the registered state is visibly observed.",
      `Private profile for this one action: ${JSON.stringify(profile)}`,
    ].join("\n"),
    schema: {
      type: "object", additionalProperties: false,
      required: ["status", "observed_url"],
      properties: {
        status: { type: "string", const: "registered" },
        observed_url: { type: "string", pattern: "^https://luma\\.com/" },
      },
    },
    timeoutMs: 600_000,
    evidenceDir: path.join(String(input.evidenceDir), "agentic-registration"),
    repoRoot: input.repoRoot,
    runnerPath: input.runnerPath,
  });
  if (!result || !result.summary || result.summary.selected_model !== "gpt-5.6-terra"
    || !result.value || result.value.status !== "registered") unavailable();
  return Object.freeze(result.value);
}

module.exports = { runConnectorAgenticRegistration };
