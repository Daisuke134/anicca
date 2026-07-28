"use strict";

const { z } = require("zod");
const { makeSteelCdpClient, STEEL_BASE_URL } = require("./steel-cdp-client.js");
const {
  scopeSessionContextToOrigin,
  readBrowserAuthSession: defaultReadBrowserAuthSession,
  upsertBrowserAuthSession: defaultUpsertBrowserAuthSession,
  invalidateBrowserAuthSession: defaultInvalidateBrowserAuthSession,
} = require("./browser-auth-session-store.js");

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
  activeRegistrationForm: z.boolean().optional(),
  activeAuthenticationForm: z.boolean().optional(),
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
  const readBrowserAuthSession = options.readBrowserAuthSession || defaultReadBrowserAuthSession;
  const upsertBrowserAuthSession = options.upsertBrowserAuthSession || defaultUpsertBrowserAuthSession;
  const invalidateBrowserAuthSession =
    options.invalidateBrowserAuthSession || defaultInvalidateBrowserAuthSession;
  const sessions = new Map();
  const authSessions = new Map();

  return {
    async openSession(input = {}) {
      let auth = null;
      let context;
      if (input && input.requiresLogin === true) {
        const explicitUrl = explicitPublicHttpsUrl(input.goal);
        if (explicitUrl) {
          const identity = {
            uid: input.uid,
            origin: new URL(explicitUrl).origin,
            principalKind: input.principalKind,
          };
          const record = await readBrowserAuthSession(identity);
          auth = { ...identity, loaded: Boolean(record) };
          if (record) context = scopeSessionContextToOrigin(record.context, identity.origin);
        }
      }
      const createOptions = { blockAds: true };
      if (context !== undefined) createOptions.sessionContext = context;
      const created = await steelClient.createRawSession(createOptions);
      let session;
      try {
        session = privateSession(created);
      } catch (error) {
        if (created && created.id) {
          try { await steelClient.releaseSession(String(created.id)); } catch { /* preserve validation */ }
        }
        throw error;
      }
      if (auth) authSessions.set(String(session.id), auth);
      return session;
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
      const readOnlyAuth = Boolean(
        explicitUrl && context.actionKind === "browser_auth_continuity_readback",
      );

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
        const actionAgent = readOnlyAuth ? null : stagehand.agent({
            mode: "cua",
            model: AGENT_MODEL,
            systemPrompt: AGENT_SYSTEM_PROMPT,
          });
        if (explicitUrl) await page.goto(explicitUrl);
        else await discoveryAgent.execute(discoveryTask);
        let selection;
        let selectedUrl;
        if (readOnlyAuth) {
          selectedUrl = publicPageUrl(page, agentEmail);
          if (!selectedUrl) throw new Error("browser auth readback carried no public page");
          selection = {
            selectionReason: "Explicit authenticated provider readback URL.",
          };
        } else {
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
        }
        const parsed = new URL(selectedUrl);
        const selected = {
          selectedUrl,
          selectedOrigin: parsed.origin,
          selectionReason: replaceIdentity(selection.selectionReason, agentEmail).slice(0, 500),
        };
        if (typeof context.onSelected === "function") await context.onSelected(selected);
        if (readOnlyAuth) {
          return {
            ...selected,
            action: "Read current authenticated provider page.",
            sideEffectStarted: false,
            readOnlyAuth: true,
          };
        }

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
        await actionAgent.execute(actionTask);
        if (explicitUrl) await page.waitForTimeout(15_000);
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

    async readProviderReceipt(sessionInput, action = {}) {
      const session = privateSession(sessionInput);
      const open = sessions.get(String(session.id));
      if (!open) throw new Error("Stagehand session unavailable for provider readback");
      const readOnlyAuth = action && action.readOnlyAuth === true;
      const extracted = await open.stagehand.extract(
        readOnlyAuth
          ? [
              "Read only the current authenticated provider continuity page.",
              "Report confirmed=true only when provider-authored account or protected content is visible and no login, verification-code, OTP, or 2FA form is active.",
              "Do not require registration, booking, purchase, or other action-success language for this read-only authentication check.",
              "Set activeAuthenticationForm=true when any login or authentication form is active.",
              "Return its authentication status and a short provider-authored content marker.",
            ].join(" ")
          : [
              "Read only the current provider-authored result page.",
              "Report confirmed=true only when the page explicitly says the requested action succeeded.",
              "Set activeRegistrationForm=true only when a visible registration form can still be submitted.",
              "Set activeAuthenticationForm=true only when a visible login, verification-code, OTP, or 2FA form is active.",
              "An Add to Calendar completion control with no active registration/authentication form may coexist with optional email verification used only to manage an already-completed registration.",
              "A pending, check-email, error, login, challenge, payment, active registration form, or active authentication form is otherwise not confirmed.",
              "Return its status, confirmation identifier if present, and a short provider status phrase.",
            ].join(" "),
        receiptSchema,
      );
      const status = replaceIdentity(extracted.status || "unknown", agentEmail).slice(0, 100);
      const providerText = replaceIdentity(extracted.providerText, agentEmail).slice(0, 500);
      const handoffText = `${status} ${providerText}`;
      const activeRegistrationForm = extracted.activeRegistrationForm === true;
      const activeAuthenticationForm = extracted.activeAuthenticationForm === true;
      const explicitSuccess = /\b(?:you(?:'|’)re in|registration confirmed|registered|booking confirmed|rsvp confirmed|success)\b/i.test(
        providerText,
      );
      const managementCompletion = /\badd to calendar\b/i.test(handoffText)
        && /\bverify email\b/i.test(handoffText)
        && !activeRegistrationForm
        && !activeAuthenticationForm;
      const strongCompletion = explicitSuccess || managementCompletion;
      const hardFailure = /\b(?:failed|error|not confirmed)\b|失敗|未完了/i.test(handoffText);
      const pendingWithoutCompletion = /\bpending\b/i.test(handoffText) && !strongCompletion;
      const negated = hardFailure || pendingWithoutCompletion;
      const blockingVerification = !strongCompletion &&
        /\b(?:verify|check email)\b|確認してください/i.test(handoffText);
      const handoffReason = activeAuthenticationForm
        ? /\b(?:2fa|two-factor|one-time password|otp|verification code)\b/i.test(handoffText)
          ? "2fa"
          : "login"
        : /\b(?:captcha|challenge)\b/i.test(handoffText)
        ? "challenge"
        : /\b(?:2fa|two-factor|one-time password|otp)\b/i.test(handoffText)
          ? "2fa"
          : /\bkyc\b|identity verification/i.test(handoffText)
            ? "kyc"
            : /\b(?:payment|purchase|checkout|credit card|card details|billing)\b|支払|決済|購入/i.test(handoffText)
              ? "payment"
              : /\b(?:login|log in|sign in)\b/i.test(handoffText)
                ? "login"
                : null;
      return {
        confirmed: (extracted.confirmed === true || strongCompletion) &&
          !negated &&
          !blockingVerification &&
          !activeRegistrationForm &&
          !activeAuthenticationForm &&
          providerText.length > 0,
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

    async releaseSession(sessionId, releaseOptions = {}) {
      const id = String(sessionId || "");
      const open = sessions.get(id);
      const auth = authSessions.get(id);
      sessions.delete(id);
      authSessions.delete(id);

      let authContextSaved = false;
      let authContextInvalidated = false;
      let contextSha256 = null;
      let keyVersion = null;
      if (auth) {
        const providerReceipt = releaseOptions && releaseOptions.providerReceipt || {};
        const handoffReason = String(
          providerReceipt.handoff_reason || providerReceipt.handoffReason || "",
        ).toLowerCase();
        try {
          if (handoffReason === "login") {
            authContextInvalidated = await invalidateBrowserAuthSession({
              uid: auth.uid,
              origin: auth.origin,
              principalKind: auth.principalKind,
            }) === true;
          } else {
            const context = await steelClient.getSessionContext(id);
            const saved = await upsertBrowserAuthSession({
              uid: auth.uid,
              origin: auth.origin,
              principalKind: auth.principalKind,
              context,
            });
            authContextSaved = true;
            if (saved && /^[a-f0-9]{64}$/.test(String(saved.context_sha256 || ""))) {
              contextSha256 = saved.context_sha256;
            }
            if (saved && Number.isSafeInteger(saved.key_version) && saved.key_version > 0) {
              keyVersion = saved.key_version;
            }
          }
        } catch {
          authContextSaved = false;
          authContextInvalidated = false;
          contextSha256 = null;
          keyVersion = null;
        }
      }

      if (open && open.stagehand && typeof open.stagehand.close === "function") {
        try { await open.stagehand.close(); } catch { /* Steel release below owns the real slot */ }
      }
      const released = await steelClient.releaseSession(id);
      const receipt = { released: released === true };
      if (!auth) return receipt;
      return {
        ...receipt,
        origin: auth.origin,
        principal_kind: auth.principalKind,
        auth_context_loaded: auth.loaded,
        auth_context_saved: authContextSaved,
        auth_context_invalidated: authContextInvalidated,
        context_sha256: contextSha256,
        key_version: keyVersion,
      };
    },
  };
}

module.exports = {
  makeStagehandSteelDriver,
  MODEL,
  AGENT_MODEL,
  SEARCH_URL,
};
