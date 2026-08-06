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
      "Use Playwright only as the controller for the existing CloakBrowser daily-driver at CDP http://127.0.0.1:9222. Attach with chromium.connectOverCDP(), select the already-open exact event tab, and use user-facing role/label locators with Playwright auto-wait.",
      "Never launch another browser or profile. Never use desktop-wide Cmd-Tab, AppleScript, cliclick, screen coordinates, or a different Chrome window. Never assign DOM values with Runtime.evaluate or mutate the DOM; use real locator fill/click/check/selectOption/press actions on CloakBrowser.",
      "Click the registration/request-to-join action, complete every required form field, submit it, and keep working until the page visibly shows the registered, going, ticket, or pending-approval state.",
      "For identity/contact fields use only the supplied profile. For ordinary subjective questions, answer truthfully and generally: building Life Manager and AI agents, meeting founders/engineers/users, learning, and making useful connections. Choose a reasonable visible option for required choices. Leave optional social handles blank if unknown.",
      "A novel ordinary question is not a blocker: answer it truthfully from the supplied profile or the general purpose above and continue. Do not abandon this event merely because its wording or control was not seen before.",
      "Treat this as one uninterrupted transaction. Inspect and complete every visible required input, choice, and consent before clicking the final submit control.",
      "If the application form or its final submit control is still visible, you are NOT registered and must keep working. Never return registered while a form is open.",
      "After final submit, wait for the form to disappear, then re-read the live event page. Return JSON only when an explicit registered, going, ticket, or pending-approval control is visibly present on that final page. Attendee-count text such as 'people going' is not proof.",
      `Private profile for this one action: ${JSON.stringify(profile)}`,
    ].join("\n"),
    schema: {
      type: "object", additionalProperties: false,
      required: ["status", "observed_url", "form_visible", "submit_control_visible", "observed_marker"],
      properties: {
        status: { type: "string", const: "registered" },
        observed_url: { type: "string", pattern: "^https://luma\\.com/" },
        form_visible: { type: "boolean", const: false },
        submit_control_visible: { type: "boolean", const: false },
        observed_marker: { type: "string", minLength: 2, maxLength: 120 },
      },
    },
    taskClass: "browser-lane-agent",
    timeoutMs: 900_000,
    evidenceDir: path.join(String(input.evidenceDir), "agentic-registration"),
    repoRoot: input.repoRoot,
    runnerPath: input.runnerPath,
  });
  if (!result || !result.summary || result.summary.selected_model !== "gpt-5.6-terra"
    || !result.value || result.value.status !== "registered") unavailable();
  return Object.freeze(result.value);
}

module.exports = { runConnectorAgenticRegistration };
