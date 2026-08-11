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
const PROVIDERS = new Set(["luma", "connpass", "peatix", "meetup", "doorkeeper", "eventbrite"]); const LABEL = { name: /^(?:name|full name|attendee name|氏名|名前|お名前)$/, email: /^(?:email|e-mail|email address|account email|メール|メールアドレス)$/, family: /^(?:family name kana|last name kana|surname kana|lastname_edit|姓（カナ）)$/, given: /^(?:given name kana|first name kana|firstname_edit|名（カナ）)$/, phone: /^(?:phone(?: number)?|telephone|mobile|電話(?:番号)?|携帯)$/, privacy: /^(?:organizer privacy(?: confirmation)?|主催者のプライバシーポリシーに同意する)$/ };
const PEATIX_FORM_SUBMIT_LABEL = "確認画面へ進む";
const PEATIX_CONFIRM_LABEL = "チケットを申し込む";
const PEATIX_FORM_URL = /^https:\/\/peatix\.com\/sales\/event\/([1-9][0-9]*)\/form$/;
const PEATIX_CONFIRM_URL = /^https:\/\/peatix\.com\/sales\/event\/([1-9][0-9]*)\/confirm$/;
const CONNPASS_FINAL_LABEL = "申し込みを確定する";
const CONNPASS_REFERRAL_QUESTION = "このイベントは何を見て知りましたか？";
const CONNPASS_ONLINE_LABEL = /^オンライン視聴枠（YouTube） 無料(?: 参加者数 \d+人)?$/i;
const CONNPASS_JOIN_URL = /^https:\/\/(?:[a-z0-9-]+\.)?connpass\.com\/event\/([1-9][0-9]*)\/join\/$/;
const DOORKEEPER_FINAL_LABEL = "申し込む";
const DOORKEEPER_TRIGGER_CONTROL = /^(?:control_[1-9][0-9]*|(?:doorkeeper_)?(?:modal_)?trigger(?:_[a-z0-9]+)?)$/;
const DOORKEEPER_EVENT_REF = /^doorkeeper-event:\/\/event\/([1-9][0-9]*)$/;
const DOORKEEPER_EVENT_URL = /^https:\/\/([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)\.doorkeeper\.jp\/events\/([1-9][0-9]*)$/;
const EVENTBRITE_EVENT_REF = /^eventbrite-event:\/\/event\/([1-9][0-9]*)$/;
const EVENTBRITE_EVENT_URL = /^https:\/\/www\.eventbrite\.com\/e\/(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)-tickets-([1-9][0-9]*)|([1-9][0-9]*))$/i;
const EVENTBRITE_TRIGGER_CONTROL = /^eventbrite_checkout_([1-9][0-9]*)$/;
const EVENTBRITE_TICKET_REGISTER_CONTROL = /^eventbrite_ticket_register_([1-9][0-9]*)$/;
const EVENTBRITE_CTA_LABELS = new Set(["Get tickets", "Reserve a spot"]);
const EVENTBRITE_FRAME_TIMEOUT_MS = 30_000;
const EVENTBRITE_FRAME_STABILITY_MS = 500;
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
function candidateMeetupEventId(candidate) {
  const match = /^meetup-event:\/\/event\/([1-9][0-9]*)$/.exec(String(candidate && candidate.event_ref || ""));
  return match ? match[1] : "";
}
function candidateConnpassEventId(candidate) { const match = /^connpass-event:\/\/event\/([1-9][0-9]*)$/.exec(String(candidate && candidate.event_ref || "")); return match ? match[1] : ""; }
function candidateDoorkeeperBinding(candidate) {
  const ref = DOORKEEPER_EVENT_REF.exec(String(candidate && candidate.event_ref || ""));
  const url = DOORKEEPER_EVENT_URL.exec(String(candidate && candidate.canonical_url || ""));
  return ref && url && url[1] !== "www" && ref[1] === url[2]
    ? Object.freeze({ eventId: ref[1], canonicalUrl: String(candidate.canonical_url) }) : null;
}
function candidateDoorkeeperEventId(candidate) { return candidateDoorkeeperBinding(candidate)?.eventId || ""; }
function candidateEventbriteBinding(candidate) {
  const ref = EVENTBRITE_EVENT_REF.exec(String(candidate && candidate.event_ref || ""));
  const url = EVENTBRITE_EVENT_URL.exec(String(candidate && candidate.canonical_url || ""));
  const eventId = url && (url[1] || url[2]);
  return ref && eventId && ref[1] === eventId
    ? Object.freeze({ eventId: ref[1], canonicalUrl: String(candidate.canonical_url) }) : null;
}
function isEventbriteTriggerMeaning(control) {
  return Boolean(
    control && control.kind === "button" && typeof control.label === "string" && control.label.trim()
    && control.required === false && control.completed === false && control.submittable === true
  );
}
function isEventbriteTriggerSemantic(control) {
  return isEventbriteTriggerMeaning(control)
    && EVENTBRITE_TRIGGER_CONTROL.test(String(control.control || ""))
    && EVENTBRITE_CTA_LABELS.has(control.label);
}
function isEventbriteCheckoutTrigger({ provider, page, candidate, control, controls = [] } = {}) {
  if (provider !== "eventbrite" || !isEventbriteTriggerSemantic(control)) return false;
  const binding = candidateEventbriteBinding(candidate);
  if (!binding || EVENTBRITE_TRIGGER_CONTROL.exec(control.control)[1] !== binding.eventId) return false;
  let href = "";
  try { href = String(typeof page?.url === "function" ? page.url() : ""); } catch { href = ""; }
  if (href !== binding.canonicalUrl) return false;
  const matching = Array.isArray(controls) ? controls.filter(isEventbriteTriggerMeaning) : [];
  return matching.length === 1 && matching[0].control === control.control;
}
function eventbriteFrameUrl(frame) {
  let href = "";
  try { href = String(frame && typeof frame.url === "function" ? frame.url() : ""); } catch { return null; }
  try {
    const url = new URL(href);
    if (url.protocol !== "https:" || url.hostname !== "www.eventbrite.com" || url.port || url.username || url.password || url.pathname !== "/checkout-external" || url.hash) return null;
    return Object.freeze({ href, url });
  } catch { return null; }
}
function eventbriteFrameMatches(frame, eventId) {
  const parsed = eventbriteFrameUrl(frame);
  if (!parsed) return false;
  const eventIds = parsed.url.searchParams.getAll("eid");
  return eventIds.length === 1 && eventIds[0] === String(eventId);
}
function eventbriteChildFrame(frame) {
  try { return typeof frame?.parentFrame === "function" && frame.parentFrame() !== null; } catch { return false; }
}
function eventbriteCheckoutFrameSet(page, eventId) {
  let frames = [];
  try { frames = typeof page?.frames === "function" ? page.frames() : []; } catch { frames = []; }
  const official = Array.isArray(frames) ? frames.map((frame) => ({ frame, parsed: eventbriteFrameUrl(frame) })).filter(({ frame, parsed }) => parsed && eventbriteChildFrame(frame)) : [];
  return { official, matching: official.filter(({ frame }) => eventbriteFrameMatches(frame, eventId)) };
}
function eventbriteTicketFrame(page, eventId, canonicalUrl) {
  let href = "";
  try { href = String(typeof page?.url === "function" ? page.url() : ""); } catch { return null; }
  if (href !== String(canonicalUrl)) return null;
  const { official, matching } = eventbriteCheckoutFrameSet(page, eventId);
  return official.length === 1 && matching.length === 1 ? matching[0].frame : null;
}
async function inspectEventbriteTicketFrame(frame, eventId) {
  if (!frame || typeof frame.locator !== "function") return null;
  let locator;
  try { locator = frame.locator("[data-testid]"); } catch { return null; }
  if (!locator || typeof locator.evaluateAll !== "function") return null;
  try {
    return await locator.evaluateAll((elements, context) => {
      if (!Array.isArray(elements) || elements.length > 100) return { cardCount: -1, control: null };
      const testIdOf = (element) => String((element.getAttribute && element.getAttribute("data-testid")) || (element.dataset && element.dataset.testid) || "");
      const textOf = (element) => String(element && (element.innerText || element.textContent || element.value) || "").replace(/\s+/g, " ").trim();
      const hiddenStyle = (style) => Boolean(style && (
        [style.display, style.visibility, style.contentVisibility].some((value) => ["none", "hidden", "collapse"].includes(String(value || "").toLowerCase()))
        || String(style.opacity ?? "") === "0"
      ));
      const visibleOf = (element) => {
        const view = element && element.ownerDocument && element.ownerDocument.defaultView;
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
        if (!element || typeof element.getBoundingClientRect !== "function") return false;
        let rect;
        try { rect = element.getBoundingClientRect(); } catch { return false; }
        return Boolean(rect && Number(rect.width) > 0 && Number(rect.height) > 0);
      };
      const descendants = (element) => [element, ...(typeof element.querySelectorAll === "function" ? [...element.querySelectorAll("*")] : [])];
      const cardCandidates = elements.filter((element) => testIdOf(element) === "ticket-display-card-content-full-size");
      const cards = cardCandidates.filter(visibleOf);
      const primaryCandidates = elements.filter((element) => testIdOf(element) === "eds-modal__primary-button");
      const primary = primaryCandidates.filter((element) => {
        const tag = String(element.tagName || "").toLowerCase(); const type = String(element.type || "").toLowerCase();
        return visibleOf(element) && element.disabled !== true && String((element.getAttribute && element.getAttribute("aria-disabled")) || "").toLowerCase() !== "true"
          && tag === "button" && type === "button" && textOf(element) === "Register";
      });
      if (cardCandidates.length !== 1 || cards.length !== 1 || primaryCandidates.length !== 1 || primary.length !== 1) return { cardCount: cards.length, control: null };
      const card = cards[0]; const cardText = textOf(card);
      const stepperCandidates = descendants(card).filter((element) => testIdOf(element) === "eds-stepper");
      const stepper = stepperCandidates.filter(visibleOf);
      const parts = stepper.length === 1 ? descendants(stepper[0]) : [];
      const quantityCandidates = parts.filter((element) => testIdOf(element) === "eds-stepper-quantity");
      const increaseCandidates = parts.filter((element) => testIdOf(element) === "eds-stepper-increase-button");
      const decreaseCandidates = parts.filter((element) => testIdOf(element) === "eds-stepper-decrease-button");
      const prices = descendants(card).filter((element) => testIdOf(element) === "ticket-price__price");
      const quantity = quantityCandidates.filter((element) => visibleOf(element) && textOf(element) === "1");
      const enabledOf = (element) => element.disabled !== true && String((element.getAttribute && element.getAttribute("aria-disabled")) || "").toLowerCase() !== "true";
      const increase = increaseCandidates.filter((element) => visibleOf(element) && String(element.tagName || "").toLowerCase() === "button" && enabledOf(element));
      const decrease = decreaseCandidates.filter((element) => visibleOf(element) && String(element.tagName || "").toLowerCase() === "button");
      const paid = /(?:[$€£¥￥]\s*\d|\b(?:jpy|usd)\s*\d[\d,]*(?:\.\d+)?(?:\b|(?=\s|$))|\b\d[\d,]*(?:\.\d+)?\s*(?:jpy|usd|yen|円)(?![A-Za-z0-9])|\bcash\b|\bpaid\b|\bdoor\s*(?:fee|price)\b|\bat\s+the\s+door\b|\bminimum\s+purchase\b|\bone\s+drink\s+minimum\b|\bpurchase\s+required\b|会場払い|当日払い|有料)/i.test(cardText);
      const free = prices.length === 1 && visibleOf(prices[0]) && textOf(prices[0]) === "Free";
      const valid = stepperCandidates.length === 1 && stepper.length === 1 && quantityCandidates.length === 1 && quantity.length === 1
        && increaseCandidates.length === 1 && increase.length === 1 && decreaseCandidates.length === 1 && decrease.length === 1
        && prices.length === 1 && free && decrease[0].disabled === true && !paid;
      if (valid && primary[0].dataset) primary[0].dataset.lmConnectorControl = `eventbrite_ticket_register_${context.eventId}`;
      return { cardCount: cards.length, control: valid ? `eventbrite_ticket_register_${context.eventId}` : null };
    }, { eventId });
  } catch { return null; }
}
async function inspectEventbriteAttendeeFrame(frame, eventId) {
  if (!frame || typeof frame.locator !== "function") return null;
  let locator;
  try { locator = frame.locator("input, textarea, select, button, [data-testid]"); } catch { return null; }
  if (!locator || typeof locator.evaluateAll !== "function") return null;
  try {
    return await locator.evaluateAll((elements, { eventId: id }) => {
      if (!Array.isArray(elements) || elements.length > 100) return [];
      const hidden = (style) => Boolean(style && [style.display, style.visibility, style.contentVisibility].some((value) => ["none", "hidden", "collapse"].includes(String(value || "").toLowerCase())) || String(style.opacity ?? "") === "0");
      const visibleOf = (element) => {
        const view = element?.ownerDocument?.defaultView;
        for (let current = element; current; current = current.parentElement || null) {
          let computed = null; try { computed = view?.getComputedStyle?.(current); } catch { /* fail closed below */ }
          if (current.hidden === true || current.isConnected === false || (typeof current.hasAttribute === "function" && current.hasAttribute("hidden")) || String(current.getAttribute?.("aria-hidden") || "").toLowerCase() === "true" || hidden(current.style) || hidden(computed)) return false;
        }
        let rect; try { rect = element?.getBoundingClientRect?.(); } catch { return false; }
        return Boolean(rect && Number(rect.width) > 0 && Number(rect.height) > 0);
      };
      const tagOf = (element) => String(element && element.tagName || "").toLowerCase();
      const typeOf = (element) => String(element && element.type || "").toLowerCase();
      const nameOf = (element) => String((element && element.getAttribute && element.getAttribute("name")) || (element && element.name) || "");
      const requiredOf = (element) => element.required === true || element.hasAttribute?.("required") || String(element.getAttribute?.("aria-required") || "").toLowerCase() === "true";
      const enabledOf = (element) => element.disabled !== true && !element.hasAttribute?.("disabled") && String(element.getAttribute?.("aria-disabled") || "").toLowerCase() !== "true";
      const fields = [{ key: "first_name", label: "First name", pattern: /^buyer\.([0-9]+)-first_name$/, type: "text" }, { key: "last_name", label: "Last name", pattern: /^buyer\.([0-9]+)-last_name$/, type: "text" }, { key: "email", label: "Email", pattern: /^buyer\.([0-9]+)-email$/, type: "email" }, { key: "confirm_email", label: "Confirm email", pattern: /^buyer\.confirmEmailAddress$/, type: "email" }];
      const candidates = fields.map((field) => elements.filter((element) => tagOf(element) === "input" && field.pattern.test(nameOf(element)) && typeOf(element) === field.type));
      const required = elements.filter((element) => {
        const tag = tagOf(element); const type = typeOf(element);
        return ["input", "select", "textarea"].includes(tag) && (tag !== "input" || type !== "hidden") && visibleOf(element) && enabledOf(element) && requiredOf(element);
      });
      if (required.length !== 4 || candidates.some((items) => items.length !== 1 || !required.includes(items[0]))) return [];
      const buyerIndexes = candidates.slice(0, 3).map(([element]) => /^buyer\.([0-9]+)-/.exec(nameOf(element))?.[1]);
      if (new Set(buyerIndexes).size !== 1) return [];
      const completedOf = (element) => Boolean(String(element && element.value || "").trim());
      return fields.map((field, index) => ({
        control: `eventbrite_attendee_${field.key}_${id}`,
        kind: "input",
        label: field.label,
        required: true,
        completed: completedOf(candidates[index][0]),
        submittable: false,
      }));
    }, { eventId });
  } catch { return null; }
}
async function waitForEventbriteCheckoutFrame(page, eventId, canonicalUrl) {
  if (!page || typeof page.frames !== "function" || !canonicalUrl) return false;
  const deadline = Date.now() + EVENTBRITE_FRAME_TIMEOUT_MS;
  let stableSignature = null;
  let stableSince = null;
  while (Date.now() <= deadline) {
    let pageHref = "";
    try { pageHref = String(typeof page.url === "function" ? page.url() : ""); } catch { return false; }
    if (pageHref !== String(canonicalUrl)) return false;
    const { official, matching } = eventbriteCheckoutFrameSet(page, eventId);
    if (official.length === 1 && matching.length === 1) {
      const signature = official[0].parsed.href;
      if (stableSignature !== signature) {
        stableSignature = signature;
        stableSince = Date.now();
      } else if (stableSince != null && Date.now() - stableSince >= EVENTBRITE_FRAME_STABILITY_MS) return true;
    } else {
      stableSignature = null;
      stableSince = null;
    }
    const remaining = deadline - Date.now();
    if (remaining <= 0) break;
    await new Promise((resolve) => setTimeout(resolve, Math.min(FINAL_EFFECT_POLL_MS, remaining)));
  }
  return false;
}
function isEventbriteTicketRegister({ provider, page, candidate, control, controls = [] } = {}) {
  if (provider !== "eventbrite" || !control || control.kind !== "button" || control.label !== "Register"
    || control.required !== false || control.completed !== false || control.submittable !== true) return false;
  const binding = candidateEventbriteBinding(candidate);
  if (!binding) return false;
  const match = EVENTBRITE_TICKET_REGISTER_CONTROL.exec(String(control.control || ""));
  let href = "";
  try { href = String(typeof page?.url === "function" ? page.url() : ""); } catch { return false; }
  const semantic = Array.isArray(controls) ? controls.filter((item) => item && item.kind === "button" && item.label === "Register"
    && item.required === false && item.completed === false && item.submittable === true && EVENTBRITE_TICKET_REGISTER_CONTROL.test(String(item.control || ""))) : [];
  return Boolean(match && match[1] === binding.eventId && href === binding.canonicalUrl && semantic.length === 1 && semantic[0].control === control.control);
}
async function waitForEventbriteTicketStep(page, eventId, canonicalUrl) {
  const deadline = Date.now() + EVENTBRITE_FRAME_TIMEOUT_MS;
  let stableSince = null;
  while (Date.now() <= deadline) {
    const frame = eventbriteTicketFrame(page, eventId, canonicalUrl);
    const state = frame ? await inspectEventbriteTicketFrame(frame, eventId) : null;
    if (state && state.cardCount === 0) {
      if (stableSince == null) stableSince = Date.now();
      if (Date.now() - stableSince >= EVENTBRITE_FRAME_STABILITY_MS) return true;
    } else stableSince = null;
    const remaining = deadline - Date.now();
    if (remaining <= 0) break;
    await new Promise((resolve) => setTimeout(resolve, Math.min(FINAL_EFFECT_POLL_MS, remaining)));
  }
  return false;
}
function isConnpassJoin(provider, href) {
  return provider === "connpass" && CONNPASS_JOIN_URL.test(String(href || ""));
}
function isDoorkeeperTriggerSemantic(control) {
  return Boolean(
    control && control.kind === "link" && control.label === DOORKEEPER_FINAL_LABEL
    && control.required === false && control.completed === false && control.submittable === false
  );
}
function isDoorkeeperTriggerControl(control) {
  return isDoorkeeperTriggerSemantic(control) && DOORKEEPER_TRIGGER_CONTROL.test(String(control.control || ""));
}
function isDoorkeeperModalTrigger({ provider, page, candidate, control, controls = [] } = {}) {
  if (provider !== "doorkeeper" || !isDoorkeeperTriggerControl(control)) return false;
  const binding = candidateDoorkeeperBinding(candidate);
  if (!binding) return false;
  let href = "";
  try { href = String(typeof page?.url === "function" ? page.url() : ""); } catch { href = ""; }
  if (href !== binding.canonicalUrl) return false;
  const matching = Array.isArray(controls)
    ? controls.filter(isDoorkeeperTriggerSemantic)
    : [];
  return matching.length === 1 && matching[0].control === control.control;
}
function isDoorkeeperFinalSubmit({ provider, page, candidate, control, controls = [] } = {}) {
  if (provider !== "doorkeeper" || !control || control.kind !== "button" || control.submittable !== true || control.label !== DOORKEEPER_FINAL_LABEL) return false;
  const binding = candidateDoorkeeperBinding(candidate);
  if (!binding) return false;
  let href = "";
  try { href = String(typeof page?.url === "function" ? page.url() : ""); } catch { href = ""; }
  if (href !== binding.canonicalUrl) return false;
  const matching = Array.isArray(controls)
    ? controls.filter((item) => item && item.kind === "button" && item.submittable === true && item.label === DOORKEEPER_FINAL_LABEL)
    : [];
  return matching.length === 1 && matching[0].control === control.control;
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

function readStateWithinDeadline(page, candidate, readProviderState, deadline) {
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

function startFinalEffectWait(page, provider, control, candidate, readProviderState, controls = [], acceptedStatuses) {
  if (!control || control.kind !== "button" || control.submittable !== true) return null;
  const peatixFinal = provider === "peatix" && control.label === PEATIX_CONFIRM_LABEL;
  const connpassFinal = provider === "connpass" && control.label === CONNPASS_FINAL_LABEL;
  const doorkeeperFinal = provider === "doorkeeper" && control.label === DOORKEEPER_FINAL_LABEL;
  if (!peatixFinal && !connpassFinal && !doorkeeperFinal) return null;
  let href = "";
  try { href = String(typeof page.url === "function" ? page.url() : ""); } catch { href = ""; }
  if (peatixFinal) {
    const eventId = candidatePeatixEventId(candidate);
    const confirmMatch = PEATIX_CONFIRM_URL.exec(href);
    if (!eventId || !confirmMatch || confirmMatch[1] !== eventId || typeof readProviderState !== "function") return { unavailable: true, promise: Promise.resolve({ status: "unknown" }) };
  } else if (connpassFinal) {
    const eventId = candidateConnpassEventId(candidate);
    const joinMatch = CONNPASS_JOIN_URL.exec(href);
    const matchingControls = Array.isArray(controls) ? controls.filter((item) => item && item.kind === "button" && item.submittable === true && item.label === CONNPASS_FINAL_LABEL) : [];
    if (!eventId || !joinMatch || joinMatch[1] !== eventId || matchingControls.length !== 1 || matchingControls[0].control !== control.control || typeof readProviderState !== "function") return { unavailable: true, promise: Promise.resolve({ status: "unknown" }) };
  } else {
    if (!isDoorkeeperFinalSubmit({ provider, page, candidate, control, controls }) || typeof readProviderState !== "function") return { unavailable: true, promise: Promise.resolve({ status: "unknown" }) };
  }
  const statuses = Array.isArray(acceptedStatuses) && acceptedStatuses.length ? acceptedStatuses : ["registered", "pending"];
  let releaseClick;
  let cancelled = false;
  const clickStarted = new Promise((resolve) => { releaseClick = resolve; });
  const promise = (async () => {
    await clickStarted;
    const deadline = Date.now() + FINAL_EFFECT_TIMEOUT_MS;
    while (!cancelled) {
      const readback = await readStateWithinDeadline(page, candidate, readProviderState, deadline);
      if (readback.expired) return { status: "unknown" };
      if (readback.state && statuses.includes(readback.state.status)) {
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

async function settleFinalEffect(wait, acceptedStatuses) {
  let settled = null;
  try { settled = await wait.promise; } catch { settled = null; }
  const statuses = Array.isArray(acceptedStatuses) && acceptedStatuses.length ? acceptedStatuses : ["registered", "pending"];
  if (!settled || !statuses.includes(settled.status)) {
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
  const provider = String(input.provider || "");
  const selector = provider === "eventbrite"
    ? '[data-testid="conversion-bar-checkout-button"]'
    : provider === "doorkeeper"
    ? "input, textarea, select, button, a[role=button], a#confirm-button, a[href=\"#new_registration_modal\"]"
    : "input, textarea, select, button, a[role=button], a#confirm-button";
  let locator;
  try { locator = page.locator(selector); } catch { locator = null; }
  if (!locator || typeof locator.evaluateAll !== "function") invalid();
  const href = (() => { try { return String(typeof page.url === "function" ? page.url() : ""); } catch { return ""; } })();
  const eventId = String(input.event_id || "");
  const canonicalUrl = String(input.canonical_url || input.candidate_url || "");
  const connpassJoin = isConnpassJoin(provider, href);
  const eventbriteUrl = EVENTBRITE_EVENT_URL.exec(canonicalUrl);
  const eventbriteEventId = eventbriteUrl && (eventbriteUrl[1] || eventbriteUrl[2]);
  if (provider === "eventbrite" && (!eventbriteEventId || eventbriteEventId !== eventId)) return Object.freeze([]);
  if (provider === "eventbrite") {
    const { official, matching } = eventbriteCheckoutFrameSet(page, eventId);
    if (official.length > 0) {
      if (href !== canonicalUrl || official.length !== 1 || matching.length !== 1) return Object.freeze([]);
      const ticket = await inspectEventbriteTicketFrame(matching[0].frame, eventId);
      if (!ticket) return Object.freeze([]);
      if (ticket.control) return Object.freeze([{ control: ticket.control, kind: "button", label: "Register", required: false, completed: false, submittable: true }]);
      if (ticket.cardCount !== 0) return Object.freeze([]);
      const attendee = await inspectEventbriteAttendeeFrame(matching[0].frame, eventId);
      if (!Array.isArray(attendee)) return Object.freeze([]);
      return Object.freeze(attendee.map(safeControl));
    }
  }
  const observed = await locator.evaluateAll((elements, context) => {
    if (context && context.provider === "eventbrite" && Array.isArray(elements) && elements.length > 100) return [];
    const visibleElements = elements.slice(0, 100);
    const connpassJoin = Boolean(context && context.connpassJoin === true);
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
      if (connpassJoin) return element.closest(".question_list");
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
    const doorkeeperFormIdOf = (form) => String(form && (form.id || (form.getAttribute && form.getAttribute("id")) || ""));
    const doorkeeperHrefOf = (element) => String((element.getAttribute && element.getAttribute("href")) || element.href || "");
    const doorkeeperTextOf = (element) => String(element.innerText || element.textContent || "").replace(/\s+/g, " ").trim();
    const doorkeeperTriggerOf = (element) => String(element.tagName || "").toLowerCase() === "a" && doorkeeperHrefOf(element) === "#new_registration_modal" && doorkeeperTextOf(element) === "申し込む";
    const doorkeeperVisibleOf = (element) => {
      if (!visibleOf(element)) return false;
      let ancestor = element.parentElement || null;
      while (ancestor) {
        if (typeof ancestor.getBoundingClientRect === "function") {
          let rect;
          try { rect = ancestor.getBoundingClientRect(); } catch { return false; }
          if (!rect || Number(rect.width) <= 0 || Number(rect.height) <= 0) return false;
        }
        ancestor = ancestor.parentElement || null;
      }
      return true;
    };
    const doorkeeperVisibleElements = visibleElements.filter(doorkeeperVisibleOf);
    if (context && context.provider === "eventbrite") {
      if (!context.eventId || !context.canonicalUrl || String(context.href || "") !== String(context.canonicalUrl)) return [];
      const testIdOf = (element) => String((element.getAttribute && element.getAttribute("data-testid")) || (element.dataset && element.dataset.testid) || "");
      const visibleEventbriteCtas = visibleElements.filter((element) => testIdOf(element) === "conversion-bar-checkout-button" && visibleOf(element));
      if (visibleEventbriteCtas.length !== 1) return [];
      const [element] = visibleEventbriteCtas;
      const eventbriteCta = [element].filter((element) => {
        const tag = String(element.tagName || "").toLowerCase();
        const type = String(element.type || "").toLowerCase();
        const ariaDisabled = String((element.getAttribute && element.getAttribute("aria-disabled")) || "").toLowerCase() === "true";
        return tag === "button" && type === "button" && testIdOf(element) === "conversion-bar-checkout-button"
          && new Set(["Get tickets", "Reserve a spot"]).has(String(element.innerText || element.textContent || "").replace(/\s+/g, " ").trim())
          && element.disabled !== true && !ariaDisabled;
      });
      if (eventbriteCta.length !== 1) return [];
      const control = `eventbrite_checkout_${context.eventId}`;
      if (element.dataset) element.dataset.lmConnectorControl = control;
      return [{ control, kind: "button", label: String(element.innerText || element.textContent || "").replace(/\s+/g, " ").trim(), required: false, completed: false, submittable: true }];
    }
    const doorkeeperPageMatch = /^https:\/\/([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)\.doorkeeper\.jp\/events\/([1-9][0-9]*)$/.exec(String(context && context.href || ""));
    const knownDoorkeeperPage = Boolean(context && context.provider === "doorkeeper" && context.eventId && doorkeeperPageMatch && doorkeeperPageMatch[1] !== "www" && doorkeeperPageMatch[2] === String(context.eventId));
    if (context && context.provider === "doorkeeper") {
      if (!knownDoorkeeperPage) return [];
      const idOf = (element) => String(element.id || (element.getAttribute && element.getAttribute("id")) || "");
      const nameOf = (element) => String((element.getAttribute && element.getAttribute("name")) || element.name || "");
      const requiredEmailOf = (element) => String(element.tagName || "").toLowerCase() === "input"
        && String(element.type || "").toLowerCase() === "email"
        && idOf(element) === "event_registration_email"
        && nameOf(element) === "event_registration[email]"
        && element.required === true
        && doorkeeperFormIdOf(element.form) === "new_event_registration";
      const submitOf = (element) => String(element.tagName || "").toLowerCase() === "input"
        && String(element.type || "").toLowerCase() === "submit"
        && nameOf(element) === "commit"
        && String(element.value || "") === "申し込む";
      const triggerCandidates = doorkeeperVisibleElements.filter(doorkeeperTriggerOf);
      const emailCandidates = doorkeeperVisibleElements.filter(requiredEmailOf);
      const requiredAnswers = doorkeeperVisibleElements.filter((element) => element.disabled !== true && ["input", "textarea", "select", "checkbox", "radio"].includes(kindOf(element)) && requiredOf(element));
      const answerForms = new Set(requiredAnswers.map((element) => element.form).filter(Boolean));
      const registrationForm = answerForms.size === 1 ? answerForms.values().next().value : null;
      const requiredAnswersComplete = requiredAnswers.length === 1 && requiredAnswers.every(completedOf);
      const requiredAnswersRepresentable = requiredAnswers.length === 1 && emailCandidates.length === 1 && requiredAnswers[0] === emailCandidates[0];
      const requiredAnswersBound = Boolean(registrationForm && requiredAnswers.every((element) => element.form === registrationForm) && doorkeeperFormIdOf(registrationForm) === "new_event_registration");
      const submitCandidates = doorkeeperVisibleElements.filter(submitOf);
      const submitReady = requiredAnswersRepresentable && requiredAnswersComplete && requiredAnswersBound && submitCandidates.length === 1 && submitCandidates[0].form === registrationForm;
      const publicControl = (element, kind, label, required, completed, submittable) => {
        const index = visibleElements.indexOf(element);
        const control = `control_${index + 1}`;
        if (element.dataset) element.dataset.lmConnectorControl = control;
        return { control, kind, label, required, completed, submittable };
      };
      if (triggerCandidates.length !== 1) return [];
      const controls = [];
      controls.push(publicControl(triggerCandidates[0], "link", "申し込む", false, false, false));
      for (const email of emailCandidates) controls.push(publicControl(email, "input", "Email", true, completedOf(email), false));
      for (const submit of submitCandidates) controls.push(publicControl(submit, "button", "申し込む", false, false, submitReady && submit === submitCandidates[0]));
      return controls;
    }
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
  }, { provider, href, eventId, canonicalUrl, connpassJoin });
  if (!Array.isArray(observed)) invalid();
  return Object.freeze(observed.map(safeControl));
}

async function operatePageControl(input = {}) {
  const target = input.frame || input.page;
  if (!input.page || !target || typeof target.locator !== "function" || !input.control || !input.action) invalid();
  const token = String(input.control.control || "");
  if (!CONTROL.test(token) || input.action.control !== token) invalid();
  const locator = target.locator(`[data-lm-connector-control="${token}"]`);
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

function nativeConnpassControl(provider, state, controls) {
  if (provider !== "connpass" || state !== "connpass_join") return null;
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
function nativeDoorkeeperTrigger(provider, controls) {
  if (provider !== "doorkeeper") return null;
  if (controls.some((control) => ACTIONABLE_KINDS.has(control.kind) && control.required && !control.completed)) return null;
  if (controls.some((control) => control.kind === "button" && control.submittable === true)) return null;
  const triggers = controls.filter(isDoorkeeperTriggerControl);
  const semanticTriggers = controls.filter(isDoorkeeperTriggerSemantic);
  return triggers.length === 1 && semanticTriggers.length === 1 ? triggers[0].control : null;
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
    if (input.provider === "eventbrite") {
      if (control.kind !== "input" || control.required !== true || control.completed !== false || control.submittable !== false) return null;
      const key = control.label === "First name" ? "given_name" : control.label === "Last name" ? "family_name" : ["Email", "Confirm email"].includes(control.label) ? "email" : null;
      if (!key) return null;
      const profile = await safeProfile(readPeatixProfile); const value = profile && profile[key];
      return typeof value === "string" && value.length > 0 && value.length <= 2_000 && value === value.trim() ? value : null;
    }
    if (["checkbox", "radio"].includes(control.kind)) {
      if (input.provider === "connpass") return input.state === "connpass_join" && connpassSafeRadioCategory(control) ? true : null;
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
    const observationState = String(input.observation.state || "");
    const nativeControl = nativeConnpassControl(input.provider, observationState, controls);
    if (nativeControl) return Object.freeze({ control: nativeControl });
    const nativeTrigger = nativeDoorkeeperTrigger(input.provider, controls);
    if (nativeTrigger) return Object.freeze({ control: nativeTrigger });
    const pendingAnswers = controls.filter((control) => ACTIONABLE_KINDS.has(control.kind) && control.required && !control.completed);
    const actionableControls = pendingAnswers.length ? pendingAnswers : controls.filter((control) => control.kind === "button" && control.submittable === true);
    if (!actionableControls.length) return null;
    const sequence = step === 1 ? (fallbackSequences.get(targetId) || 0) + 1 : (fallbackSequences.get(targetId) || 1);
    fallbackSequences.set(targetId, sequence);
    const state = observationState === "connpass_join" ? "connpass_join" : "registration_page";
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
  const meetupWorkflow = options.meetupWorkflow;
  const doorkeeperWorkflow = options.doorkeeperWorkflow;
  const inspectControls = options.inspectControls;
  const proposeAction = options.proposeAction;
  const operateControl = options.operateControl;
  const resolveValue = options.resolveValue;
  if (
    !lumaWorkflow || typeof lumaWorkflow.readProviderState !== "function"
    || (connpassWorkflow != null && typeof connpassWorkflow.readProviderState !== "function")
    || (peatixWorkflow != null && typeof peatixWorkflow.readProviderState !== "function")
    || (meetupWorkflow != null && typeof meetupWorkflow.readProviderState !== "function")
    || (doorkeeperWorkflow != null && typeof doorkeeperWorkflow.readProviderState !== "function")
    || typeof inspectControls !== "function" || typeof proposeAction !== "function"
    || typeof operateControl !== "function" || typeof resolveValue !== "function"
  ) invalid();
  const registry = new WeakMap();

  async function observed(page, provider, candidate = null) {
    const eventbriteBinding = provider === "eventbrite" ? candidateEventbriteBinding(candidate) : null;
    const eventId = candidatePeatixEventId(candidate) || candidateMeetupEventId(candidate) || candidateDoorkeeperEventId(candidate) || eventbriteBinding?.eventId || "";
    const href = (() => { try { return String(typeof page.url === "function" ? page.url() : ""); } catch { return ""; } })();
    const connpassJoin = isConnpassJoin(provider, href);
    const values = await inspectControls({ page, provider, event_id: eventId || undefined, canonical_url: eventbriteBinding?.canonicalUrl, connpass_join: connpassJoin });
    if (!Array.isArray(values) || values.length < 1 || values.length > 100) invalid();
    const controls = values.map(safeControl);
    if (new Set(controls.map((item) => item.control)).size !== controls.length) invalid();
    const eventbriteTicket = provider === "eventbrite" && controls.some((item) => EVENTBRITE_TICKET_REGISTER_CONTROL.test(item.control));
    const observation = Object.freeze({
      state: eventbriteTicket ? "eventbrite_ticket_step" : connpassJoin ? "connpass_join" : "registration_page",
      controls: Object.freeze(controls),
    });
    registry.set(page, { provider, eventId, observation });
    return observation;
  }

  async function performAction(input = {}) {
    if (!input.page || !input.action || !CONTROL.test(String(input.action.control || ""))) invalid();
    const provider = input.provider == null ? "luma" : String(input.provider);
    if (!PROVIDERS.has(provider)) invalid();
    const doorkeeperBinding = provider === "doorkeeper" ? candidateDoorkeeperBinding(input.candidate) : null;
    if (provider === "doorkeeper" && !doorkeeperBinding) return Object.freeze({ status: "failed" });
    const eventbriteBinding = provider === "eventbrite" ? candidateEventbriteBinding(input.candidate) : null;
    if (provider === "eventbrite" && !eventbriteBinding) return Object.freeze({ status: "failed" });
    const eventId = candidatePeatixEventId(input.candidate) || candidateMeetupEventId(input.candidate) || candidateDoorkeeperEventId(input.candidate) || eventbriteBinding?.eventId || String(input.event_id || "");
    const cached = registry.get(input.page);
    const observation = provider === "eventbrite" || !cached || cached.provider !== provider || cached.eventId !== eventId
      ? await observed(input.page, provider, input.candidate) : cached.observation;
    const currentHref = (() => { try { return String(typeof input.page.url === "function" ? input.page.url() : ""); } catch { return ""; } })();
    const state = observation.state === "connpass_join" && isConnpassJoin(provider, currentHref) ? "connpass_join" : observation.state === "connpass_join" ? "registration_page" : observation.state;
    const control = observation.controls.find((item) => item.control === input.action.control);
    if (!control) return Object.freeze({ status: "failed" });
    if (provider !== "eventbrite" && EVENTBRITE_TRIGGER_CONTROL.test(control.control)) return Object.freeze({ status: "failed" });
    const doorkeeperModalTrigger = isDoorkeeperModalTrigger({ provider, page: input.page, candidate: input.candidate, control, controls: observation.controls });
    const eventbriteTrigger = isEventbriteCheckoutTrigger({ provider, page: input.page, candidate: input.candidate, control, controls: observation.controls });
    const eventbriteTicket = isEventbriteTicketRegister({ provider, page: input.page, candidate: input.candidate, control, controls: observation.controls });
    const ticketFrame = eventbriteTicket ? eventbriteTicketFrame(input.page, eventbriteBinding.eventId, eventbriteBinding.canonicalUrl) : null;
    if (provider === "eventbrite" && !eventbriteTrigger && !eventbriteTicket) return Object.freeze({ status: "failed" });
    if (eventbriteTicket && !ticketFrame) return Object.freeze({ status: "failed" });
    const pendingRequiredAnswer = observation.controls.some((item) => ACTIONABLE_KINDS.has(item.kind) && item.required && !item.completed);
    if (control.kind === "button" && pendingRequiredAnswer) return Object.freeze({ status: "failed" });
    if (ACTIONABLE_KINDS.has(control.kind) && (!control.required || control.completed)) return Object.freeze({ status: "failed" });
    if ((control.kind === "link" && !doorkeeperModalTrigger) || (control.kind === "button" && control.submittable !== true)) return Object.freeze({ status: "failed" });
    if (doorkeeperModalTrigger && (input.action.purpose !== "submit" || input.action.method !== "ax_click")) return Object.freeze({ status: "failed" });
    if (eventbriteTrigger && (input.action.purpose !== "submit" || input.action.method !== "ax_click")) return Object.freeze({ status: "failed" });
    if (eventbriteTicket && (input.action.purpose !== "submit" || input.action.method !== "ax_click")) return Object.freeze({ status: "failed" });
    if (provider === "connpass" && state === "connpass_join" && control.kind === "button" && control.label !== CONNPASS_FINAL_LABEL) return Object.freeze({ status: "failed" });
    if (provider === "doorkeeper" && control.kind === "button" && control.label !== DOORKEEPER_FINAL_LABEL) return Object.freeze({ status: "failed" });
    const action = actionForControl(control); if (!action) return Object.freeze({ status: "failed" });
    let value = null;
    if (FILL.has(action.method)) {
      value = await resolveValue({ provider, page: input.page, control, action, state });
      if (
        !(typeof value === "string" || typeof value === "boolean" || Array.isArray(value))
        || (typeof value === "string" && (!value.trim() || value.length > 2_000))
        || (Array.isArray(value) && (value.length < 1 || value.length > 3))
      ) return Object.freeze({ status: "failed" });
    }
    const navigationWait = startPeatixConfirmWait(input.page, provider, control);
    if (navigationWait && navigationWait.unavailable) return Object.freeze({ status: "failed" });
    const finalEffectStatuses = provider === "doorkeeper" ? ["registered"] : undefined;
    const finalEffectWait = startFinalEffectWait(
      input.page,
      provider,
      control,
      input.candidate,
      provider === "connpass" && connpassWorkflow ? connpassWorkflow.readProviderState
        : provider === "peatix" && peatixWorkflow ? peatixWorkflow.readProviderState
          : provider === "doorkeeper" && doorkeeperWorkflow ? doorkeeperWorkflow.readProviderState : null,
      observation.controls,
      finalEffectStatuses,
    );
    if (finalEffectWait && finalEffectWait.unavailable) return Object.freeze({ status: "failed" });
    if (finalEffectWait) finalEffectWait.markClicked();
    let result;
    if (eventbriteTicket) {
      const ticket = await inspectEventbriteTicketFrame(ticketFrame, eventbriteBinding.eventId);
      if (!ticket || ticket.control !== control.control) return Object.freeze({ status: "failed" });
      if (eventbriteTicketFrame(input.page, eventbriteBinding.eventId, eventbriteBinding.canonicalUrl) !== ticketFrame) return Object.freeze({ status: "failed" });
    }
    try {
      result = await operateControl({
        page: input.page,
        ...(ticketFrame ? { frame: ticketFrame } : {}),
        control,
        action,
        value,
      });
    } catch {
      if (finalEffectWait) return settleFinalEffect(finalEffectWait, finalEffectStatuses);
      return Object.freeze({ status: "failed" });
    }
    if (!result || result.status !== "success") {
      if (finalEffectWait) return settleFinalEffect(finalEffectWait, finalEffectStatuses);
      return Object.freeze({ status: "failed" });
    }
    if (eventbriteTicket) return Object.freeze({ status: await waitForEventbriteTicketStep(input.page, eventbriteBinding.eventId, eventbriteBinding.canonicalUrl) ? "success" : "failed" });
    if (eventbriteTrigger) return Object.freeze({ status: await waitForEventbriteCheckoutFrame(input.page, eventbriteBinding.eventId, eventbriteBinding.canonicalUrl) ? "success" : "failed" });
    if (navigationWait && !(await navigationWait.promise)) return Object.freeze({ status: "failed" });
    if (finalEffectWait) return settleFinalEffect(finalEffectWait, finalEffectStatuses);
    return Object.freeze({ status: "success" });
  }

  async function runFallback(input = {}) {
    if (!PROVIDERS.has(input.provider) || !input.candidate) invalid();
    const workflow = { luma: lumaWorkflow, connpass: connpassWorkflow, peatix: peatixWorkflow, meetup: meetupWorkflow, doorkeeper: doorkeeperWorkflow }[input.provider];
    if (!workflow || typeof workflow.readProviderState !== "function") {
      if (input.provider === "doorkeeper") return Object.freeze({ status: "failed", safe_reason: "agent_action_failed", repaired_actions: Object.freeze([]) });
      invalid();
    }
    const seenMutations = new Set();
    let connpassSubmitAttempted = false;
    let doorkeeperSubmitAttempted = false;
    let doorkeeperTriggerAttempted = false;
    let ambiguousEffect = false;
    let finalEffectProviderState = null;
    const adapter = createBrowserHarnessAdapter({
      observePage: ({ page }) => observed(page, input.provider, input.candidate),
      async proposeAction(input) { const proposal = await proposeAction(input); const token = String(proposal && typeof proposal === "object" ? proposal.control || "" : ""); const control = input.observation.controls.find((item) => item.control === token); return CONTROL.test(token) && control ? actionForControl(control) : null; },
      async performAction(action) {
        const selected = action.action || action;
        const cached = registry.get(action.page);
        const selectedControl = cached && cached.provider === input.provider ? cached.observation.controls.find((item) => item.control === selected.control) : null;
        const doorkeeperTrigger = isDoorkeeperModalTrigger({ provider: input.provider, page: action.page, candidate: input.candidate, control: selectedControl, controls: cached?.observation.controls });
        const doorkeeperFinal = isDoorkeeperFinalSubmit({ provider: input.provider, page: action.page, candidate: input.candidate, control: selectedControl, controls: cached?.observation.controls });
        const effect = ["ax_click", "coordinate_click", "keyboard_submit"].includes(selected.method) ? "activate" : ["ax_fill", "dom_fill"].includes(selected.method) ? "fill" : selected.method;
        const signature = MUTATING_METHODS.has(selected.method)
          ? doorkeeperTrigger ? `${safePageState(action.page)}:doorkeeper:modal-trigger`
            : selected.purpose === "submit" ? `${safePageState(action.page)}:submit:form-submit` : `${safePageState(action.page)}:${selected.purpose}:${effect}:${selected.control}`
          : null;
        if (doorkeeperTrigger && doorkeeperTriggerAttempted) return Object.freeze({ status: "success" });
        if (input.provider === "connpass" && selected.purpose === "submit") {
          if (connpassSubmitAttempted) {
            ambiguousEffect = true;
            return Object.freeze({ status: "failed", safe_reason: "effect_unknown" });
          }
          connpassSubmitAttempted = true;
        }
        if (input.provider === "doorkeeper" && doorkeeperFinal) {
          if (doorkeeperSubmitAttempted) {
            ambiguousEffect = true;
            return Object.freeze({ status: "failed", safe_reason: "effect_unknown" });
          }
          doorkeeperSubmitAttempted = true;
        }
        if (signature && seenMutations.has(signature)) return Object.freeze({ status: "failed" });
        const result = await performAction({ ...action, provider: input.provider, candidate: input.candidate });
        if (result && result.safe_reason === "effect_unknown") ambiguousEffect = true;
        if (result && result.status === "success" && result.provider_state && ["registered", "pending"].includes(result.provider_state.status)) {
          finalEffectProviderState = result.provider_state;
        }
        if (signature && result && result.status === "success") {
          if (doorkeeperTrigger) doorkeeperTriggerAttempted = true;
          else seenMutations.add(signature);
        }
        return result;
      },
      async readExpectedState({ page }) {
        const state = finalEffectProviderState || await workflow.readProviderState({
          page,
          candidate: input.candidate,
        });
        if (input.provider === "doorkeeper") {
          return state && typeof state === "object" && !Array.isArray(state) && state.status === "registered"
            ? state : Object.freeze({ status: "unavailable" });
        }
        return input.provider === "meetup" && (!state || state.status !== "registered")
          ? Object.freeze({ status: "unavailable" }) : state;
      },
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
