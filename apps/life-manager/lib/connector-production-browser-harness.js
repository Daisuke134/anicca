"use strict";

const path = require("node:path");

const { createBrowserHarnessAdapter } = require("./connector-browser-harness-adapter.js");
const { runLocalAgentRunner } = require("./connector-luna-judgment.js");

const CONTROL = /^[a-z][a-z0-9_-]{1,63}$/;
const KINDS = new Set(["input", "textarea", "select", "checkbox", "radio", "button", "link"]);
const FILL = new Set(["ax_fill", "dom_fill", "ax_select", "ax_check"]);
const ACTIONS = { input: ["fill", "ax_fill"], textarea: ["fill", "ax_fill"], select: ["fill", "ax_select"], checkbox: ["fill", "ax_check"], radio: ["fill", "ax_check"], button: ["submit", "ax_click"], link: ["submit", "ax_click"] };
const ACTIONABLE_KINDS = new Set(["input", "textarea", "select", "checkbox", "radio"]);
const MUTATING_METHODS = new Set(["ax_fill", "dom_fill", "ax_select", "ax_check", "ax_click", "coordinate_click", "keyboard_submit"]);
const PROVIDERS = new Set(["luma", "connpass", "peatix"]); const LABEL = { name: /^(?:name|full name|attendee name|氏名|名前|お名前)$/, email: /^(?:email|e-mail|email address|account email|メール|メールアドレス)$/, family: /^(?:family name kana|last name kana|surname kana|lastname_edit|姓（カナ）)$/, given: /^(?:given name kana|first name kana|firstname_edit|名（カナ）)$/, phone: /^(?:phone(?: number)?|telephone|mobile|電話(?:番号)?|携帯)$/, privacy: /^(?:organizer privacy(?: confirmation)?|主催者のプライバシー確認|主催者のプライバシーポリシーに同意する)$/ };
const PEATIX_FORM_SUBMIT_LABEL = "確認画面へ進む";
const PEATIX_CONFIRM_LABEL = "チケットを申し込む";
const PEATIX_FORM_URL = /^https:\/\/peatix\.com\/sales\/event\/([1-9][0-9]*)\/form$/;
const PEATIX_CONFIRM_URL = /^https:\/\/peatix\.com\/sales\/event\/([1-9][0-9]*)\/confirm$/;
const CONNPASS_FINAL_LABEL = "申し込みを確定する";
const CONNPASS_REFERRAL_QUESTION = "このイベントは何を見て知りましたか？";
const CONNPASS_ONLINE_LABEL = /^オンライン視聴枠（YouTube） 無料(?: 参加者数 \d+人)?$/i;
const FINAL_EFFECT_TIMEOUT_MS = 30_000;
const FINAL_EFFECT_POLL_MS = 25;

function invalid() {
  throw new Error("Connector production Browser Harness invalid");
}
function safePageState(page) { try { const url = new URL(String(page && typeof page.url === "function" ? page.url() : "")); return url.origin !== "null" && url.pathname ? `${url.origin}${url.pathname}` : "unavailable"; } catch { return "unavailable"; } }
function candidatePeatixEventId(candidate) {
  const match = /^peatix-event:\/\/event\/([1-9][0-9]*)$/.exec(String(candidate && candidate.event_ref || ""));
  return match ? match[1] : "";
}

function startPeatixConfirmWait(page, provider, control) {
  if (
    provider !== "peatix" || !control || control.kind !== "button" || control.submittable !== true
    || control.label !== PEATIX_FORM_SUBMIT_LABEL
  ) return null;
  let currentHref = "";
  try { currentHref = String(typeof page.url === "function" ? page.url() : ""); } catch { currentHref = ""; }
  const formMatch = PEATIX_FORM_URL.exec(currentHref);
  if (!formMatch) return null;
  if (typeof page.waitForURL !== "function") return { unavailable: true, promise: Promise.resolve(false) };
  let wait;
  try {
    wait = page.waitForURL((url) => {
      const match = PEATIX_CONFIRM_URL.exec(String(url || ""));
      return Boolean(match && match[1] === formMatch[1]);
    }, { waitUntil: "domcontentloaded", timeout: 30_000 });
  } catch {
    return { unavailable: true, promise: Promise.resolve(false) };
  }
  return {
    promise: Promise.resolve(wait).then((settled) => {
      if (settled === false) return false;
      try {
        const match = PEATIX_CONFIRM_URL.exec(String(typeof page.url === "function" ? page.url() : ""));
        return Boolean(match && match[1] === formMatch[1]);
      } catch {
        return false;
      }
    }, () => false),
  };
}

function readPeatixStateWithinDeadline(page, candidate, readProviderState, deadline) {
  const remaining = deadline - Date.now();
  if (remaining <= 0) return Promise.resolve({ expired: true });
  return new Promise((resolve) => {
    let timer;
    let settled = false;
    const finish = (value) => {
      if (settled) return;
      settled = true;
      if (timer !== undefined) clearTimeout(timer);
      resolve(value);
    };
    try { timer = setTimeout(() => finish({ expired: true }), remaining); }
    catch { finish({ expired: true }); return; }
    Promise.resolve()
      .then(() => readProviderState({ page, candidate }))
      .then((state) => finish({ state }), () => finish({ error: true }));
  });
}

function startPeatixFinalEffectWait(page, provider, control, candidate, readProviderState) {
  if (provider !== "peatix" || !control || control.kind !== "button" || control.submittable !== true || control.label !== PEATIX_CONFIRM_LABEL) return null;
  const eventId = candidatePeatixEventId(candidate);
  let href = "";
  try { href = String(typeof page.url === "function" ? page.url() : ""); } catch { href = ""; }
  const confirmMatch = PEATIX_CONFIRM_URL.exec(href);
  if (!eventId || !confirmMatch || confirmMatch[1] !== eventId || typeof readProviderState !== "function") return { unavailable: true, promise: Promise.resolve({ status: "unknown" }) };
  let releaseClick;
  let cancelled = false;
  const clickStarted = new Promise((resolve) => { releaseClick = resolve; });
  const promise = (async () => {
    await clickStarted;
    const deadline = Date.now() + FINAL_EFFECT_TIMEOUT_MS;
    while (!cancelled) {
      const readback = await readPeatixStateWithinDeadline(page, candidate, readProviderState, deadline);
      if (readback.expired) return { status: "unknown" };
      if (readback.state && ["registered", "pending"].includes(readback.state.status)) {
        return { status: readback.state.status, providerState: readback.state };
      }
      const remaining = deadline - Date.now();
      if (remaining <= 0) break;
      await new Promise((resolve) => setTimeout(resolve, Math.min(FINAL_EFFECT_POLL_MS, remaining)));
    }
    return { status: cancelled ? "cancelled" : "unknown" };
  })();
  return { markClicked: releaseClick, cancel() { cancelled = true; releaseClick(); }, promise };
}

async function settlePeatixFinalEffect(wait) {
  let settled = null;
  try { settled = await wait.promise; } catch { settled = null; }
  if (!settled || !["registered", "pending"].includes(settled.status)) {
    return Object.freeze({ status: "failed", safe_reason: "effect_unknown" });
  }
  const providerState = settled.providerState && typeof settled.providerState === "object" && !Array.isArray(settled.providerState)
    ? Object.freeze({ ...settled.providerState }) : null;
  return Object.freeze({ status: "success", ...(providerState ? { provider_state: providerState } : {}) });
}

function safeControl(input) {
  if (!input || typeof input !== "object" || Array.isArray(input)) invalid();
  const control = String(input.control || "");
  const kind = String(input.kind || "");
  const label = String(input.label || "").replace(/\s+/g, " ").trim();
  const question = String(input.question || "").replace(/\s+/g, " ").trim();
  const completed = input.completed == null ? false : input.completed;
  const submittable = input.submittable == null ? false : input.submittable;
  if (
    !CONTROL.test(control) || !KINDS.has(kind) || !label || label.length > 300
    || /[\x00-\x1f\x7f]/.test(label) || question.length > 300
    || /[\x00-\x1f\x7f]/.test(question) || (question && !["checkbox", "radio"].includes(kind))
    || typeof input.required !== "boolean" || typeof completed !== "boolean"
    || typeof submittable !== "boolean" || (submittable && kind !== "button")
  ) invalid();
  return Object.freeze({ control, kind, label, required: input.required, completed, submittable, ...(question ? { question } : {}) });
}

function actionForControl(control) { const action = ACTIONS[control.kind]; return action ? Object.freeze({ purpose: action[0], method: action[1], control: control.control }) : null; }

async function inspectPageControls(input = {}) {
  const page = input.page;
  if (!page || typeof page.locator !== "function") invalid();
  let locator;
  try { locator = page.locator("input, textarea, select, button, a[role=button], a#confirm-button"); } catch { locator = null; }
  if (!locator || typeof locator.evaluateAll !== "function") invalid();
  const provider = String(input.provider || "");
  const href = (() => { try { return String(typeof page.url === "function" ? page.url() : ""); } catch { return ""; } })();
  const eventId = String(input.event_id || "");
  const observed = await locator.evaluateAll((elements, context) => {
    const visibleElements = elements.slice(0, 100);
    const connpassJoin = Boolean(context && context.provider === "connpass" && /^https:\/\/(?:[a-z0-9-]+\.)?connpass\.com\/event\/[1-9][0-9]*\/join\/$/.test(String(context.href || "")));
    const kindOf = (element) => {
      const tag = String(element.tagName || "").toLowerCase();
      const type = String(element.type || "").toLowerCase();
      return tag === "input" && ["checkbox", "radio"].includes(type)
        ? type : tag === "input" && ["button", "submit", "reset", "image"].includes(type) ? "button" : tag === "a" ? "link" : tag;
    };
    const submitTypeOf = (element) => {
      const tag = String(element.tagName || "").toLowerCase(); const type = String(element.type || "").toLowerCase();
      return tag === "button" ? !type || type === "submit" : ["submit", "image"].includes(type);
    };
    const groupOf = (element) => {
      if (typeof element.closest !== "function") return null;
      if (connpassJoin) return element.closest(".question_list") || element.closest("fieldset, dl.field, [role='group'], .field");
      return element.closest("fieldset, dl.field, [role='group'], .field");
    };
    const radioNameOf = (element) => String((element.getAttribute && element.getAttribute("name")) || element.name || "");
    const requiredOf = (element) => {
      const group = groupOf(element);
      const radioName = radioNameOf(element);
      return connpassJoin && String(element.type || "").toLowerCase() === "radio" && radioName === "participation_type"
        || element.required === true || String((element.getAttribute && element.getAttribute("aria-required")) || "").toLowerCase() === "true" || Boolean(group && (((group.classList && typeof group.classList.contains === "function") && group.classList.contains("required")) || /(?:^|\s)required(?:\s|$)/.test(String(group.className || "")) || String((group.getAttribute && group.getAttribute("aria-required")) || "").toLowerCase() === "true"));
    };
    const labelOf = (element, allowKnownValue = false) => {
      const tag = String(element.tagName || "").toLowerCase(); const type = String(element.type || "").toLowerCase();
      const labels = Array.from(element.labels || []).map((label) => label.innerText || label.textContent || "");
      return [
        ...labels,
        element.getAttribute && element.getAttribute("aria-label"),
        element.getAttribute && element.getAttribute("placeholder"),
        element.getAttribute && element.getAttribute("name"),
        element.innerText,
        tag === "input" && (["submit", "image"].includes(type) || allowKnownValue) ? element.value : null,
      ].map((value) => String(value || "").replace(/\s+/g, " ").trim()).find(Boolean) || "";
    };
    const visibleOf = (element) => {
      const view = element.ownerDocument && element.ownerDocument.defaultView;
      const hiddenStyle = (style) => Boolean(style && (
        [style.display, style.visibility, style.contentVisibility].some((value) => ["none", "hidden", "collapse"].includes(String(value || "").toLowerCase()))
        || String(style.opacity || "") === "0"
      ));
      let current = element;
      while (current) {
        if (current.hidden === true || current.isConnected === false || (typeof current.hasAttribute === "function" && current.hasAttribute("hidden"))) return false;
        if (String((current.getAttribute && current.getAttribute("aria-hidden")) || "").toLowerCase() === "true") return false;
        if (hiddenStyle(current.style || {})) return false;
        let computed = null;
        try { computed = view && typeof view.getComputedStyle === "function" ? view.getComputedStyle(current) : null; } catch { computed = null; }
        if (hiddenStyle(computed)) return false;
        current = current.parentElement || null;
      }
      if (typeof element.getBoundingClientRect !== "function") return false;
      let rect;
      try { rect = element.getBoundingClientRect(); } catch { return false; }
      return Boolean(rect && Number(rect.width) > 0 && Number(rect.height) > 0);
    };
    const answerKinds = ["input", "textarea", "select", "checkbox", "radio"];
    const requiredAnswers = visibleElements.filter((element) => String(element.type || "").toLowerCase() !== "hidden" && element.disabled !== true && answerKinds.includes(kindOf(element)) && requiredOf(element));
    const requiredAnswersRepresentable = requiredAnswers.every((element) => !!labelOf(element));
    const completedOf = (element) => {
      const kind = kindOf(element);
      const radioName = radioNameOf(element);
      return ["input", "textarea", "select"].includes(kind) ? Boolean(String(element.value || "").trim()) : kind === "checkbox" ? element.checked === true : kind === "radio" ? radioName.trim() ? elements.some((candidate) => String(candidate.type || "").toLowerCase() === "radio" && String((candidate.getAttribute && candidate.getAttribute("name")) || candidate.name || "") === radioName && candidate.checked === true) : element.checked === true : false;
    };
    const requiredAnswersComplete = requiredAnswers.every(completedOf);
    const answerForms = new Set(requiredAnswers.map((element) => element.form).filter(Boolean));
    const registrationForm = answerForms.size === 1 ? answerForms.values().next().value : null;
    const requiredAnswerFormUnique = answerForms.size <= 1;
    const requiredAnswersBound = Boolean(registrationForm && requiredAnswers.every((element) => element.form === registrationForm));
    const idOf = (element) => String(element.id || (element.getAttribute && element.getAttribute("id")) || "");
    const knownSubmitCount = visibleElements.filter((element) => idOf(element) === "form-submit-button").length;
    const formPageMatch = /^https:\/\/peatix\.com\/sales\/event\/([1-9][0-9]*)\/form$/.exec(String(context && context.href || ""));
    const knownPage = Boolean(context && context.provider === "peatix" && formPageMatch && (!context.eventId || formPageMatch[1] === String(context.eventId)));
    const confirmPageMatch = /^https:\/\/peatix\.com\/sales\/event\/([1-9][0-9]*)\/confirm$/.exec(String(context && context.href || ""));
    const knownConfirmPage = Boolean(context && context.provider === "peatix" && context.eventId && confirmPageMatch && confirmPageMatch[1] === String(context.eventId));
    const knownConfirmCount = visibleElements.filter((element) => idOf(element) === "confirm-button").length;
    const submitCounts = new Map();
    for (const element of visibleElements) {
      const kind = kindOf(element);
      if (kind === "button" && element.disabled !== true && !!element.form && element.form === registrationForm && submitTypeOf(element)) submitCounts.set(element.form, (submitCounts.get(element.form) || 0) + 1);
    }
    return visibleElements.flatMap((element, index) => {
      const tag = String(element.tagName || "").toLowerCase();
      const type = String(element.type || "").toLowerCase();
      if (type === "hidden" || element.disabled === true) return [];
      const knownPeatixConfirm = knownConfirmPage && requiredAnswersRepresentable && requiredAnswersComplete && requiredAnswerFormUnique && requiredAnswersBound && !element.form && visibleOf(element) && tag === "a" && idOf(element) === "confirm-button" && knownConfirmCount === 1 && element.disabled !== true && labelOf(element) === "チケットを申し込む";
      const kind = knownPeatixConfirm ? "button" : kindOf(element);
      if (!["input", "textarea", "select", "checkbox", "radio", "button", "link"].includes(kind)) return [];
      const knownPeatixSubmit = knownPage && requiredAnswersRepresentable && tag === "input" && type === "button" && idOf(element) === "form-submit-button" && element.disabled !== true && !!registrationForm && knownSubmitCount === 1 && labelOf(element, true) === "確認画面へ進む";
      const label = labelOf(element, knownPeatixSubmit);
      if (!label) return [];
      const control = `control_${index + 1}`;
      element.dataset.lmConnectorControl = control;
      const group = groupOf(element);
      const radioName = radioNameOf(element);
      const questionElement = connpassJoin && group && typeof group.querySelector === "function" ? group.querySelector(":scope > .question") : null;
      const question = ["checkbox", "radio"].includes(kind) && connpassJoin
        ? kind === "radio" && radioName === "participation_type"
          ? "参加枠"
          : String(questionElement?.textContent || questionElement?.innerText || "").replace(/\s+/g, " ").trim().replace(/^(?:必須|任意)\s*/, "").trim()
        : ["checkbox", "radio"].includes(kind) && group && typeof group.querySelector === "function"
          ? String(group.querySelector("legend,dt,[data-question]")?.textContent || "").replace(/\s+/g, " ").trim()
          : "";
      const completed = completedOf(element);
      const required = requiredOf(element);
      const submittable = requiredAnswersRepresentable && (knownPeatixSubmit || knownPeatixConfirm || kind === "button" && !!element.form && element.form === registrationForm && submitTypeOf(element) && submitCounts.get(element.form) === 1);
      return [{ control, kind, label, required, completed, submittable, ...(question ? { question } : {}) }];
    });
  }, { provider, href, eventId });
  if (!Array.isArray(observed)) invalid();
  return Object.freeze(observed.map(safeControl));
}

async function operatePageControl(input = {}) {
  if (!input.page || typeof input.page.locator !== "function" || !input.control || !input.action) invalid();
  const token = String(input.control.control || "");
  if (!CONTROL.test(token) || input.action.control !== token) invalid();
  const locator = input.page.locator(`[data-lm-connector-control="${token}"]`);
  if (!locator || typeof locator.count !== "function" || await locator.count() !== 1) {
    return Object.freeze({ status: "failed" });
  }
  switch (input.action.method) {
    case "ax_fill":
    case "dom_fill":
      if (typeof input.value !== "string" || typeof locator.fill !== "function") return Object.freeze({ status: "failed" });
      await locator.fill(input.value);
      break;
    case "ax_check":
      if (typeof locator.check !== "function") return Object.freeze({ status: "failed" });
      await locator.check();
      break;
    case "ax_select":
      if (typeof locator.selectOption !== "function") return Object.freeze({ status: "failed" });
      await locator.selectOption(input.value);
      break;
    case "ax_click":
    case "coordinate_click":
      if (typeof locator.click !== "function") return Object.freeze({ status: "failed" });
      await locator.click();
      break;
    case "keyboard_submit":
      if (!input.page.keyboard || typeof input.page.keyboard.press !== "function") return Object.freeze({ status: "failed" });
      await input.page.keyboard.press("Enter");
      break;
    case "ax_inspect":
    case "dom_inspect":
    case "parent_readback":
      break;
    default:
      return Object.freeze({ status: "failed" });
  }
  return Object.freeze({ status: "success" });
}

function normalizedLabel(value) {
  return String(value || "").replace(/\s+/g, " ").trim().toLowerCase();
}
function connpassSafeRadioCategory(control) {
  if (!control || control.kind !== "radio") return null;
  const label = normalizedLabel(control.label);
  const question = normalizedLabel(control.question);
  if (CONNPASS_ONLINE_LABEL.test(label)) return question === normalizedLabel("参加枠") ? "online" : null;
  return label === "connpass" && question === normalizedLabel(CONNPASS_REFERRAL_QUESTION) ? "referral" : null;
}

function nativeConnpassControl(provider, controls) {
  if (provider !== "connpass") return null;
  const pending = controls.filter((control) => ACTIONABLE_KINDS.has(control.kind) && control.required && !control.completed);
  if (pending.length > 0) {
    for (const category of ["online", "referral"]) {
      const matches = pending.filter((control) => connpassSafeRadioCategory(control) === category);
      if (matches.length > 0) return matches.length === 1 ? matches[0].control : null;
    }
    return null;
  }
  const submits = controls.filter((control) => control.kind === "button" && control.submittable === true && normalizedLabel(control.label) === normalizedLabel(CONNPASS_FINAL_LABEL));
  return submits.length === 1 ? submits[0].control : null;
}

async function safeProfile(read) { try { const value = await read(); return value && typeof value === "object" && !Array.isArray(value) ? value : null; } catch { return null; } } function answerFor(profile, label) { const answers = profile && profile.form_answers; const value = answers && typeof answers === "object" && !Array.isArray(answers) ? Object.entries(answers).find(([key]) => normalizedLabel(key) === label)?.[1] : null; return typeof value === "string" || Array.isArray(value) ? value : null; }
function approvedOption(profile, question, label) { const answers = profile && profile.form_answers; const exactQuestion = normalizedLabel(question); if (!exactQuestion) return false; const value = answers && typeof answers === "object" && !Array.isArray(answers) && Object.entries(answers).find(([key]) => normalizedLabel(key) === exactQuestion)?.[1]; return typeof value === "string" ? normalizedLabel(value) === label : Array.isArray(value) && value.some((item) => typeof item === "string" && normalizedLabel(item) === label); }

function createLumaPrivateValueResolver(options = {}) {
  const readProfile = options.readProfile;
  if (typeof readProfile !== "function") invalid();
  return async function resolveValue(input = {}) {
    const control = safeControl(input.control);
    const profile = await readProfile();
    if (!profile || typeof profile !== "object" || Array.isArray(profile)) invalid();
    const label = normalizedLabel(control.label);
    if (/\b(phone|telephone|mobile|電話|携帯)\b/i.test(label)) {
      return typeof profile.phone === "string" ? profile.phone : null;
    }
    const answers = profile.form_answers;
    if (!answers || typeof answers !== "object" || Array.isArray(answers)) return null;
    const match = Object.entries(answers).find(([key]) => normalizedLabel(key) === label);
    return match ? match[1] : null;
  };
}

function createPrivateValueResolver(options = {}) {
  const readPeatixProfile = options.readPeatixProfile || (() => null);
  const readFormProfile = options.readFormProfile || (() => null);
  if (typeof readPeatixProfile !== "function" || typeof readFormProfile !== "function") invalid();
  return async function resolveValue(input = {}) {
    const control = safeControl(input.control); const label = normalizedLabel(control.label); const question = normalizedLabel(control.question);
    if (["checkbox", "radio"].includes(control.kind)) {
      if (input.provider === "connpass") return connpassSafeRadioCategory(control) ? true : null;
      const profile = await safeProfile(readPeatixProfile);
      const knownPrivacyOption = label === normalizedLabel("確認し同意する。") && /^.+のプライバシーポリシーを読んだ・確認した$/.test(question);
      if ((LABEL.privacy.test(label) || knownPrivacyOption) && profile && profile.accept_organizer_privacy === true) return true;
      return approvedOption(await safeProfile(readFormProfile), question, label) ? true : null;
    }
    const key = label === normalizedLabel("お名前（漢字）") ? "name_kanji" : label === normalizedLabel("お名前（ひらがな）") ? "name_hiragana" : LABEL.name.test(label) ? "name" : LABEL.email.test(label) ? "email" : LABEL.family.test(label) ? "family_name_kana" : LABEL.given.test(label) ? "given_name_kana" : null;
    if (key) { const profile = await safeProfile(readPeatixProfile); return profile && typeof profile[key] === "string" ? profile[key] : null; }
    const profile = await safeProfile(readFormProfile);
    return LABEL.phone.test(label) ? profile && typeof profile.phone === "string" ? profile.phone : null : answerFor(profile, label);
  };
}

function absoluteDirectory(value) {
  const directory = path.resolve(String(value || ""));
  if (!path.isAbsolute(directory) || directory === path.parse(directory).root) invalid();
  return directory;
}

function createBoundedActionProposer(options = {}) {
  const repoRoot = absoluteDirectory(options.repoRoot);
  const evidenceDir = absoluteDirectory(options.evidenceDir);
  const runAgentRunner = options.runAgentRunner || runLocalAgentRunner;
  if (typeof runAgentRunner !== "function") invalid();
  const fallbackSequences = new Map();
  return async function proposeAction(input = {}) {
    const targetId = String(input.target_id || "");
    const step = Number(input.step);
    if (
      !PROVIDERS.has(input.provider) || !/^[A-Za-z0-9._-]{3,128}$/.test(targetId)
      || input.expected_state !== "registered_or_pending"
      || !Number.isInteger(step) || step < 1 || step > 10
      || !input.observation || !Array.isArray(input.observation.controls)
    ) invalid();
    const controls = input.observation.controls.map(safeControl);
    const nativeControl = nativeConnpassControl(input.provider, controls);
    if (nativeControl) return Object.freeze({ control: nativeControl });
    const pendingAnswers = controls.filter((control) => ACTIONABLE_KINDS.has(control.kind) && control.required && !control.completed);
    const actionableControls = pendingAnswers.length ? pendingAnswers : controls.filter((control) => control.kind === "button" && control.submittable === true);
    if (!actionableControls.length) return null;
    const sequence = step === 1 ? (fallbackSequences.get(targetId) || 0) + 1 : (fallbackSequences.get(targetId) || 1);
    fallbackSequences.set(targetId, sequence);
    const state = "registration_page";
    const result = await runAgentRunner({
      prompt: [
        `Choose exactly one browser action for the current ${input.provider} registration page.`,
        "Return only one control token from the supplied list.",
        "Choose only an incomplete required answer field, or after all required answers are complete, a submittable form button. Never invent answers, navigate, open or close pages, run commands, or edit code.",
        "The parent process owns all private values, executes the action, and verifies registered or pending state.",
        `Step: ${step} of 10`,
        `Page state: ${state}`,
        `Controls: ${JSON.stringify(controls)}`,
      ].join("\n"),
      schema: {
        type: "object",
        additionalProperties: false,
        required: ["control"],
        properties: {
          control: { type: "string", enum: actionableControls.map((control) => control.control) },
        },
      },
      taskClass: "browser-lane-agent",
      timeoutMs: 30_000,
      evidenceDir: path.join(evidenceDir, `target-${targetId}`, `fallback-${sequence}`, `step-${step}`),
      repoRoot,
    });
    if (
      !result || !result.summary || result.summary.status !== "success"
      || result.summary.selected_provider !== "codex" || result.summary.selected_model !== "gpt-5.6-terra"
      || !result.value || typeof result.value !== "object" || Array.isArray(result.value)
    ) invalid();
    const control = String(result.value.control || "");
    if (!actionableControls.some((item) => item.control === control)) return null;
    return Object.freeze({ control });
  };
}

function createProductionBrowserHarness(options = {}) {
  const lumaWorkflow = options.lumaWorkflow;
  const connpassWorkflow = options.connpassWorkflow;
  const peatixWorkflow = options.peatixWorkflow;
  const inspectControls = options.inspectControls;
  const proposeAction = options.proposeAction;
  const operateControl = options.operateControl;
  const resolveValue = options.resolveValue;
  if (
    !lumaWorkflow || typeof lumaWorkflow.readProviderState !== "function"
    || (connpassWorkflow != null && typeof connpassWorkflow.readProviderState !== "function")
    || (peatixWorkflow != null && typeof peatixWorkflow.readProviderState !== "function")
    || typeof inspectControls !== "function" || typeof proposeAction !== "function"
    || typeof operateControl !== "function" || typeof resolveValue !== "function"
  ) invalid();
  const registry = new WeakMap();

  async function observed(page, provider, candidate = null) {
    const eventId = candidatePeatixEventId(candidate);
    const values = await inspectControls({ page, provider, event_id: eventId || undefined });
    if (!Array.isArray(values) || values.length < 1 || values.length > 100) invalid();
    const controls = values.map(safeControl);
    if (new Set(controls.map((item) => item.control)).size !== controls.length) invalid();
    const observation = Object.freeze({
      state: "registration_page",
      controls: Object.freeze(controls),
    });
    registry.set(page, { provider, eventId, observation });
    return observation;
  }

  async function performAction(input = {}) {
    if (!input.page || !input.action || !CONTROL.test(String(input.action.control || ""))) invalid();
    const provider = input.provider == null ? "luma" : String(input.provider);
    if (!PROVIDERS.has(provider)) invalid();
    const eventId = candidatePeatixEventId(input.candidate) || String(input.event_id || "");
    const cached = registry.get(input.page);
    const observation = cached && cached.provider === provider && cached.eventId === eventId ? cached.observation : await observed(input.page, provider, input.candidate);
    const control = observation.controls.find((item) => item.control === input.action.control);
    if (!control) return Object.freeze({ status: "failed" });
    const pendingRequiredAnswer = observation.controls.some((item) => ACTIONABLE_KINDS.has(item.kind) && item.required && !item.completed);
    if (control.kind === "button" && pendingRequiredAnswer) return Object.freeze({ status: "failed" });
    if (ACTIONABLE_KINDS.has(control.kind) && (!control.required || control.completed)) return Object.freeze({ status: "failed" });
    if (control.kind === "link" || (control.kind === "button" && control.submittable !== true)) return Object.freeze({ status: "failed" });
    const action = actionForControl(control); if (!action) return Object.freeze({ status: "failed" });
    let value = null;
    if (FILL.has(action.method)) {
      value = await resolveValue({ provider, page: input.page, control, action });
      if (
        !(typeof value === "string" || typeof value === "boolean" || Array.isArray(value))
        || (typeof value === "string" && (!value.trim() || value.length > 2_000))
        || (Array.isArray(value) && (value.length < 1 || value.length > 3))
      ) return Object.freeze({ status: "failed" });
    }
    const navigationWait = startPeatixConfirmWait(input.page, provider, control);
    if (navigationWait && navigationWait.unavailable) return Object.freeze({ status: "failed" });
    const finalEffectWait = startPeatixFinalEffectWait(
      input.page,
      provider,
      control,
      input.candidate,
      provider === "peatix" && peatixWorkflow ? peatixWorkflow.readProviderState : null,
    );
    if (finalEffectWait && finalEffectWait.unavailable) return Object.freeze({ status: "failed" });
    if (finalEffectWait) finalEffectWait.markClicked();
    let result;
    try {
      result = await operateControl({
        page: input.page,
        control,
        action,
        value,
      });
    } catch {
      if (finalEffectWait) return settlePeatixFinalEffect(finalEffectWait);
      return Object.freeze({ status: "failed" });
    }
    if (!result || result.status !== "success") {
      if (finalEffectWait) return settlePeatixFinalEffect(finalEffectWait);
      return Object.freeze({ status: "failed" });
    }
    if (navigationWait && !(await navigationWait.promise)) return Object.freeze({ status: "failed" });
    if (finalEffectWait) return settlePeatixFinalEffect(finalEffectWait);
    return Object.freeze({ status: "success" });
  }

  async function runFallback(input = {}) {
    if (!PROVIDERS.has(input.provider) || !input.candidate) invalid();
    const workflow = { luma: lumaWorkflow, connpass: connpassWorkflow, peatix: peatixWorkflow }[input.provider];
    if (!workflow || typeof workflow.readProviderState !== "function") invalid();
    const seenMutations = new Set();
    let connpassSubmitAttempted = false;
    let ambiguousEffect = false;
    let finalEffectProviderState = null;
    const adapter = createBrowserHarnessAdapter({
      observePage: ({ page }) => observed(page, input.provider, input.candidate),
      async proposeAction(input) { const proposal = await proposeAction(input); const token = String(proposal && typeof proposal === "object" ? proposal.control || "" : ""); const control = input.observation.controls.find((item) => item.control === token); return CONTROL.test(token) && control ? actionForControl(control) : null; },
      async performAction(action) {
        const selected = action.action || action; const effect = ["ax_click", "coordinate_click", "keyboard_submit"].includes(selected.method) ? "activate" : ["ax_fill", "dom_fill"].includes(selected.method) ? "fill" : selected.method; const signature = MUTATING_METHODS.has(selected.method) ? selected.purpose === "submit" ? `${safePageState(action.page)}:submit:form-submit` : `${safePageState(action.page)}:${selected.purpose}:${effect}:${selected.control}` : null;
        if (input.provider === "connpass" && selected.purpose === "submit") {
          if (connpassSubmitAttempted) {
            ambiguousEffect = true;
            return Object.freeze({ status: "failed", safe_reason: "effect_unknown" });
          }
          connpassSubmitAttempted = true;
        }
        if (signature && seenMutations.has(signature)) return Object.freeze({ status: "failed" });
        const result = await performAction({ ...action, provider: input.provider, candidate: input.candidate });
        if (result && result.safe_reason === "effect_unknown") ambiguousEffect = true;
        if (result && result.status === "success" && result.provider_state && ["registered", "pending"].includes(result.provider_state.status)) {
          finalEffectProviderState = result.provider_state;
        }
        if (signature && result && result.status === "success") seenMutations.add(signature);
        return result;
      },
      readExpectedState: ({ page }) => finalEffectProviderState
        ? finalEffectProviderState
        : workflow.readProviderState({
          page,
          candidate: input.candidate,
        }),
    });
    const result = await adapter.runFallback(input);
    return ambiguousEffect && result && result.status === "failed"
      ? Object.freeze({ ...result, safe_reason: "effect_unknown" })
      : result;
  }

  return Object.freeze({ performAction, runFallback });
}

module.exports = {
  createBoundedActionProposer,
  createPrivateValueResolver,
  createLumaPrivateValueResolver,
  createProductionBrowserHarness,
  inspectPageControls,
  operatePageControl,
};
