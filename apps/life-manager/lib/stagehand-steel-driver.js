"use strict";

const { z } = require("zod");
const { makeSteelCdpClient, STEEL_BASE_URL } = require("./steel-cdp-client.js");

const MODEL = "google/gemini-2.5-flash";
const SEARCH_URL = "https://www.google.com/";
const PRIVATE_STEEL = /^http:\/\/steel-browser\.railway\.internal:8080\/?$/;
const PRIVATE_CDP = /^ws:\/\/steel-browser\.railway\.internal:8080(?:\/|$)/;

const selectionSchema = z.object({
  selectedSiteName: z.string(),
  selectionReason: z.string(),
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

      const task = [
        "Search the live web for websites that can satisfy this delegated goal:",
        goal,
        "Compare at least two relevant live websites before selecting one.",
        "The selected website must come from this run's web discovery; do not assume a preconfigured site.",
        "Perform exactly one reversible, zero-cost external action that is explicitly inside the goal.",
        "Do not spend money, accept paid terms, perform KYC, bypass a login/challenge/CAPTCHA/2FA,",
        "or invent any personal value. Stop honestly if any of those are required.",
        "After the action, remain on the provider page that displays its result.",
        agentEmail
          ? `When the goal refers to the agent-owned email, use this exact runtime-only address: ${agentEmail}`
          : "If the goal requires an email address, stop because no agent-owned address is available.",
      ].join("\n");
      let executionStarted = false;
      try {
        executionStarted = true;
        const agent = stagehand.agent({
          model: MODEL,
          executionModel: MODEL,
        });
        await agent.execute(task);
        const selection = await stagehand.extract(
          "From the current provider page and the just-completed browsing path, identify the selected site, explain why it matched the delegated goal, and summarize the single action attempted.",
          selectionSchema,
        );
        const selectedUrl = publicPageUrl(page, agentEmail);
        const parsed = new URL(selectedUrl);
        return {
          selectedUrl,
          selectedOrigin: parsed.origin,
          selectionReason: replaceIdentity(selection.selectionReason, agentEmail).slice(0, 500),
          action: replaceIdentity(selection.actionSummary, agentEmail).slice(0, 500),
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
      return {
        confirmed: extracted.confirmed === true && !negated && providerText.length > 0,
        status,
        confirmationId: extracted.confirmationId ? String(extracted.confirmationId).slice(0, 200) : null,
        currentUrl: publicPageUrl(open.page, agentEmail),
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
  SEARCH_URL,
};
