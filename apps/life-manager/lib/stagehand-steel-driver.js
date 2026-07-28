"use strict";

const { z } = require("zod");
const { makeSteelCdpClient, STEEL_BASE_URL } = require("./steel-cdp-client.js");

const MODEL = "google/gemini-2.5-flash";
const AGENT_MODEL = "google/gemini-2.5-computer-use-preview-10-2025";
const AGENT_SYSTEM_PROMPT = "Operate the remote cloud browser carefully. Use only truthful supplied identity data, never invent personal data, and stop at login, CAPTCHA, 2FA, KYC, or payment.";
const SEARCH_URL = "https://www.google.com/";
const PRIVATE_STEEL = /^http:\/\/steel-browser\.railway\.internal:8080\/?$/;
const PRIVATE_CDP = /^ws:\/\/steel-browser\.railway\.internal:8080(?:\/|$)/;

const selectionSchema = z.object({
  selectedSiteName: z.string(),
  selectionReason: z.string(),
  isSpecificActionPage: z.boolean(),
});

const actionSchema = z.object({
  actionSummary: z.string(),
});

const receiptSchema = z.object({
  confirmed: z.boolean(),
  status: z.string(),
  confirmationId: z.string().nullable(),
  providerText: z.string(),
});

function pageUrl(page) {
  if (!page) return "";
  if (typeof page.url === "function") return String(page.url());
  return String(page.url || "");
}

function replaceIdentity(value, agentEmail) {
  const text = String(value || "");
  if (!agentEmail) return text;
  return text.split(agentEmail).join("the agent-owned email");
}

function publicPageUrl(page, agentEmail) {
  const raw = replaceIdentity(pageUrl(page), agentEmail);
  try {
    const parsed = new URL(raw);
    parsed.username = "";
    parsed.password = "";
    parsed.search = "";
    parsed.hash = "";
    return parsed.toString();
  } catch {
    return "";
  }
}

function isSpecificActionUrl(value) {
  try {
    const url = new URL(value);
    if (/^(?:www\.)?(?:google|bing)\./i.test(url.hostname)) return false;
    if (/^\/(?:d\/|search(?:\/|$)|discover(?:\/|$)|events?\/?$)/i.test(url.pathname)) return false;
    return url.pathname.split("/").filter(Boolean).length >= 1;
  } catch {
    return false;
  }
}

function explicitPublicHttpsUrl(goal) {
  const match = String(goal || "").match(/https?:\/\/[^\s<>"']+/i);
  if (!match) return null;
  const raw = match[0].replace(/[),.;!?]+$/, "");
  let url;
  try {
    url = new URL(raw);
  } catch {
    throw new Error("runtime target must be a public HTTPS URL");
  }
  const host = url.hostname.toLowerCase();
  const octets = host.split(".").map(Number);
  const privateIpv4 = octets.length === 4 && octets.every(Number.isInteger) && (
    octets[0] === 10 ||
    octets[0] === 127 ||
    (octets[0] === 169 && octets[1] === 254) ||
    (octets[0] === 172 && octets[1] >= 16 && octets[1] <= 31) ||
    (octets[0] === 192 && octets[1] === 168)
  );
  if (
    url.protocol !== "https:" ||
    !host ||
    host === "localhost" ||
    host === "::1" ||
    host.endsWith(".local") ||
    host.endsWith(".internal") ||
    privateIpv4
  ) {
    throw new Error("runtime target must be a public HTTPS URL");
  }
  url.username = "";
  url.password = "";
  url.hash = "";
  return url.toString();
}

function privateSession(session) {
  if (!session || !session.id || !PRIVATE_CDP.test(String(session.websocketUrl || ""))) {
    throw new Error("Stagehand requires a Railway-private Steel CDP session");
  }
  return session;
}

function makeStagehandSteelDriver(options = {}) {
  const steelClient = options.steelClient || makeSteelCdpClient();
  if (!PRIVATE_STEEL.test(String(steelClient.baseUrl || STEEL_BASE_URL))) {
    throw new Error("Stagehand driver requires Railway-private Steel");
  }
  const Stagehand = options.Stagehand || require("@browserbasehq/stagehand").Stagehand;
  const apiKey = String(options.apiKey || process.env.GEMINI_API_KEY || "").trim();
  const agentEmail = String(options.agentEmail || process.env.LM_AGENT_BROWSER_EMAIL || "").trim();
  const agentName = String(options.agentName || process.env.LM_AGENT_BROWSER_NAME || "").trim();
  if (!apiKey) throw new Error("Stagehand Gemini API key unavailable");
  const sessions = new Map();

  return {
    async openSession() {
      return privateSession(await steelClient.createRawSession({
        blockAds: true,
      }));
    },

    async discoverAndAct(sessionInput, context = {}) {
      const session = privateSession(sessionInput);
      const goal = String(context.goal || "").trim();
      if (!goal) throw new Error("generic browser goal unavailable");
      const stagehand = new Stagehand({
        env: "LOCAL",
        disablePino: true,
        verbose: 0,
        localBrowserLaunchOptions: {
          cdpUrl: session.websocketUrl,
          cdpHeaders: { Host: "localhost:8080" },
        },
        model: {
          modelName: MODEL,
          apiKey,
        },
      });
      await stagehand.init();
      const page = await stagehand.context.awaitActivePage();
      sessions.set(String(session.id), { stagehand, page });
      await page.goto(SEARCH_URL);
      const explicitUrl = explicitPublicHttpsUrl(goal);

      const discoveryTask = [
        "Search the live web for websites that can satisfy this delegated goal:",
        goal,
        "Compare at least two relevant live websites before selecting one.",
        "The selected website must come from this run's web discovery; do not assume a preconfigured site.",
        "Navigate to the best matching provider page, but do not perform or submit the requested action yet.",
      ].join("\n");
      let executionStarted = false;
      try {
        const discoveryAgent = explicitUrl ? null : stagehand.agent({
            model: MODEL,
            executionModel: MODEL,
          });
        const actionAgent = explicitUrl ? null : stagehand.agent({
            mode: "cua",
            model: AGENT_MODEL,
            systemPrompt: AGENT_SYSTEM_PROMPT,
          });
        if (explicitUrl) await page.goto(explicitUrl);
        else await discoveryAgent.execute(discoveryTask);
        let selection;
        let selectedUrl;
        for (let attempt = 0; attempt < 3; attempt += 1) {
          selection = await stagehand.extract(
            "From the current page and browsing path, identify the selected site and explain why it matched the delegated goal. Set isSpecificActionPage=true only if this is one specific event/provider detail page where the requested action can be started; search results, directories, category pages, maps, and home pages are false.",
            selectionSchema,
          );
          selectedUrl = publicPageUrl(page, agentEmail);
          if (selection.isSpecificActionPage === true && isSpecificActionUrl(selectedUrl)) break;
          if (explicitUrl || attempt === 2) {
            throw new Error("browser discovery did not reach a specific action page");
          }
          await discoveryAgent.execute([
            "You are still on a search, directory, category, or listing page.",
            "Open one specific candidate's provider detail/action page now.",
            "Do not submit, register, purchase, or perform the requested external action yet.",
          ].join("\n"));
        }
        const parsed = new URL(selectedUrl);
        const selected = {
          selectedUrl,
          selectedOrigin: parsed.origin,
          selectionReason: replaceIdentity(selection.selectionReason, agentEmail).slice(0, 500),
        };
        if (typeof context.onSelected === "function") await context.onSelected(selected);

        const actionTask = [
          "On the currently selected provider page, perform exactly one reversible, zero-cost external action explicitly inside this delegated goal:",
          goal,
          "Do not search for or switch to another provider.",
          "Do not spend money, accept paid terms, perform KYC, bypass a login/challenge/CAPTCHA/2FA,",
          "or invent any personal value. Stop honestly if any of those are required.",
          "After the action, remain on the provider page that displays its result.",
          agentEmail
            ? `When the goal refers to the agent-owned email, use this exact runtime-only address: ${agentEmail}`
            : "If the goal requires an email address, stop because no agent-owned address is available.",
          agentName
            ? `When a name is required for the agent-owned identity, use this exact runtime-only name: ${agentName}`
            : "If the goal requires a name, stop because no agent-owned name is available.",
          agentName
            ? `When a required company or organization field refers to the agent-owned identity, use: ${agentName}`
            : "If a company or organization is required, stop because none is available.",
          "When a required role or job title refers to the agent-owned identity, use: AI agent",
          "Leave optional social-profile fields blank.",
          "Decline optional marketing or data-sharing consent. If the form requires consent and offers no decline/no choice, stop honestly.",
        ].join("\n");
        executionStarted = true;
        if (typeof context.onActionStarted === "function") {
          await context.onActionStarted({ action: "one delegated zero-cost browser action" });
        }
        if (explicitUrl) {
          const atomicActs = [
            ["Open the zero-cost registration form on this current event page. Do not navigate to a related or organizer website."],
            ["Fill the required name field with %agentName%.", { variables: { agentName } }],
            ["Fill the required email field with %agentEmail%.", { variables: { agentEmail } }],
            ["Fill the required company or organization field with %agentCompany%.", { variables: { agentCompany: agentName } }],
            ["Fill the required role or job title field with %agentRole%.", { variables: { agentRole: "AI agent" } }],
            ["In the required dropdown labeled 'Which best describes you?', select 'AI Researcher'."],
            ["In the required consent dropdown directly above the Register button, select the option meaning No / I do not consent. Fail if no decline option exists."],
            ["Submit this free registration now and remain on the provider result page."],
          ];
          for (let index = 0; index < atomicActs.length; index += 1) {
            const [instruction, actOptions] = atomicActs[index];
            try {
              const acted = await stagehand.act(instruction, actOptions);
              if (!acted || acted.success !== true) {
                throw new Error(String((acted && acted.message) || "unsuccessful result"));
              }
            } catch (error) {
              throw new Error(
                `browser atomic action ${index + 1}/${atomicActs.length} failed: ${String(error && error.message || error).slice(0, 300)}`,
              );
            }
          }
          await page.waitForTimeout(15_000);
        } else {
          await actionAgent.execute(actionTask);
        }
        const observation = await stagehand.extract(
          "Summarize the single delegated action attempted on the current provider page. Do not claim it succeeded.",
          actionSchema,
        );
        return {
          ...selected,
          action: replaceIdentity(observation.actionSummary, agentEmail).slice(0, 500),
          sideEffectStarted: true,
        };
      } catch (error) {
        const failure = error instanceof Error ? error : new Error(String(error));
        failure.sideEffectStarted = executionStarted;
        throw failure;
      }
    },

    async readProviderReceipt(sessionInput) {
      const session = privateSession(sessionInput);
      const open = sessions.get(String(session.id));
      if (!open) throw new Error("Stagehand session unavailable for provider readback");
      const extracted = await open.stagehand.extract(
        "Read only the current provider-authored result page. Report confirmed=true only when the page explicitly says the requested action succeeded. A pending, check-email, error, login, challenge, or ambiguous page is not confirmed. Return its status, confirmation identifier if present, and a short provider status phrase.",
        receiptSchema,
      );
      const status = replaceIdentity(extracted.status || "unknown", agentEmail).slice(0, 100);
      const providerText = replaceIdentity(extracted.providerText, agentEmail).slice(0, 500);
      const negated = /\b(?:failed|error|pending|verify|check email|not confirmed)\b|失敗|未完了|確認してください/i.test(
        `${status} ${providerText}`,
      );
      const handoffText = `${status} ${providerText}`;
      const handoffReason = /\b(?:captcha|challenge)\b/i.test(handoffText)
        ? "challenge"
        : /\b(?:2fa|two-factor|one-time password|otp)\b/i.test(handoffText)
          ? "2fa"
          : /\bkyc\b|identity verification/i.test(handoffText)
            ? "kyc"
            : /\b(?:login|log in|sign in)\b/i.test(handoffText)
              ? "login"
              : null;
      return {
        confirmed: extracted.confirmed === true && !negated && providerText.length > 0,
        status,
        confirmationId: extracted.confirmationId ? String(extracted.confirmationId).slice(0, 200) : null,
        currentUrl: publicPageUrl(open.page, agentEmail),
        handoffRequired: handoffReason != null,
        handoffReason,
      };
    },

    async captureEvidence(sessionInput) {
      const session = privateSession(sessionInput);
      const open = sessions.get(String(session.id));
      if (!open) throw new Error("Stagehand session unavailable for evidence capture");
      return {
        mimeType: "image/png",
        bytes: await open.page.screenshot({ type: "png", fullPage: false }),
      };
    },

    async releaseSession(sessionId) {
      const id = String(sessionId || "");
      const open = sessions.get(id);
      sessions.delete(id);
      if (open && open.stagehand && typeof open.stagehand.close === "function") {
        try { await open.stagehand.close(); } catch { /* Steel release below owns the real slot */ }
      }
      const released = await steelClient.releaseSession(id);
      return { released: released === true };
    },
  };
}

module.exports = {
  makeStagehandSteelDriver,
  MODEL,
  AGENT_MODEL,
  SEARCH_URL,
};
