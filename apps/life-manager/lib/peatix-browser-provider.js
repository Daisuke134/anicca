"use strict";

const REF = /^peatix-event:\/\/event\/([1-9][0-9]*)$/;
const ID = /^[1-9][0-9]*$/;
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const KANA = /^[\u30A1-\u30FA\u30FC]+$/u;
const STEP = /^\/sales\/event\/([1-9][0-9]*)\/(tickets|form|confirm)\/?$/;
const CONFIRMED = /^\/sales\/event\/([1-9][0-9]*)\/confirmed$/;
const TICKET = /^\/event\/([1-9][0-9]*)\/ticket$/;
const TEXT = "チケットを申し込む";
const VERIFIED = Symbol("peatixVerifiedCandidate");

const out = (status, reason) => Object.freeze(reason ? { status, reason } : { status });
function candidate(v) {
  if (v && v[VERIFIED] === true) return v;
  if (!v || typeof v !== "object" || Array.isArray(v) || v.provider !== "peatix") return null;
  const m = REF.exec(String(v.event_ref || ""));
  let u; try { u = new URL(String(v.canonical_url || "")); } catch { return null; }
  const p = /^\/event\/([1-9][0-9]*)\/?$/.exec(u.pathname);
  const ticket = String(v.ticket_id == null ? "" : v.ticket_id);
  if (u.protocol !== "https:" || u.hostname !== "peatix.com" || u.port || u.username || u.password || u.search || u.hash
    || !m || !p || m[1] !== p[1] || !ID.test(ticket) || v.registration_status !== "available"
    || v.ticket_price_status !== "free" || v.ticket_price_minor !== 0) return null;
  return Object.freeze({ id: m[1], ticket, [VERIFIED]: true });
}
function profile(v) {
  if (!v || typeof v !== "object" || Array.isArray(v)) return null;
  const name = String(v.name || "").trim(); const email = String(v.email || "").trim();
  const kana = (value) => typeof value === "string" && value.length >= 1 && value.length <= 100
    && value === value.trim() && KANA.test(value);
  return name && name.length <= 200 && email.length <= 320 && EMAIL.test(email)
    && kana(v.family_name_kana) && kana(v.given_name_kana) && v.accept_organizer_privacy === true
    ? { name, email, family_name_kana: v.family_name_kana, given_name_kana: v.given_name_kana } : null;
}
function pageHref(page) { try { return String(page.url()); } catch { return ""; } }
function stepUrl(href, id, step) {
  let u; try { u = new URL(href); } catch { return false; }
  const m = STEP.exec(u.pathname);
  return u.protocol === "https:" && u.hostname === "peatix.com" && !u.port && !u.username && !u.password
    && !u.search && !u.hash && !!m && m[1] === id && m[2] === step;
}
function confirmedUrl(href, id) {
  let u; try { u = new URL(href); } catch { return false; }
  const m = CONFIRMED.exec(u.pathname);
  return u.protocol === "https:" && u.hostname === "peatix.com" && !u.port && !u.username && !u.password
    && !u.search && !u.hash && !!m && m[1] === id;
}
async function waitForStep(page, id, step) {
  if (!page || typeof page.waitForURL !== "function") return false;
  try {
    await page.waitForURL((url) => stepUrl(String(url), id, step), { waitUntil: "domcontentloaded", timeout: 30_000 });
    return stepUrl(pageHref(page), id, step);
  } catch { return false; }
}
async function waitForFormOrConfirm(page, id) {
  if (!page || typeof page.waitForURL !== "function") return null;
  try {
    await page.waitForURL((url) => {
      const href = String(url);
      return stepUrl(href, id, "form") || stepUrl(href, id, "confirm");
    }, { waitUntil: "domcontentloaded", timeout: 30_000 });
    const href = pageHref(page);
    return stepUrl(href, id, "form") ? "form" : stepUrl(href, id, "confirm") ? "confirm" : null;
  } catch { return null; }
}
async function waitForConfirmed(page, id) {
  if (!page || typeof page.waitForURL !== "function") return false;
  try {
    await page.waitForURL((url) => confirmedUrl(String(url), id), { waitUntil: "domcontentloaded", timeout: 30_000 });
    return confirmedUrl(pageHref(page), id);
  } catch { return false; }
}
async function readTicketProof(page, c) {
  const canonical = `https://peatix.com/event/${c.id}`;
  const ticket = `${canonical}/ticket`;
  if (!page || typeof page.goto !== "function" || !eventPageUrl(pageHref(page), c.id)) return "unavailable";
  const moved = await page.goto(ticket, { waitUntil: "domcontentloaded", timeout: 30_000 }).then(() => true, () => false);
  if (!moved) return "unavailable";
  if (!ticketPageUrl(pageHref(page), c.id)) {
    const restored = await page.goto(canonical, { waitUntil: "domcontentloaded", timeout: 30_000 }).then(() => true, () => false);
    return restored && eventPageUrl(pageHref(page), c.id) ? "unproven" : "unavailable";
  }
  const observed = await readPeatixRegistrationStateOnPage(page, c);
  if (observed.status === "registered") return "registered";
  const restored = await page.goto(canonical, { waitUntil: "domcontentloaded", timeout: 30_000 }).then(() => true, () => false);
  return restored && eventPageUrl(pageHref(page), c.id) ? "unproven" : "unavailable";
}
function eventPageUrl(href, id) { let u; try { u = new URL(href); } catch { return false; } const m = /^\/event\/([1-9][0-9]*)\/?$/.exec(u.pathname); return u.protocol === "https:" && u.hostname === "peatix.com" && !u.port && !u.username && !u.password && !u.search && !u.hash && !!m && m[1] === id; }
function ticketPageUrl(href, id) { let u; try { u = new URL(href); } catch { return false; } const m = TICKET.exec(u.pathname); return u.protocol === "https:" && u.hostname === "peatix.com" && !u.port && !u.username && !u.password && !u.search && !u.hash && !!m && m[1] === id; }
async function canonicalStart(page, id) { if (!eventPageUrl(pageHref(page), id)) return false; const x = await evaluate(page, () => ({ auth: /\/(?:login|signin|signup)(?:\/|$)/i.test(location.pathname), markers: document.querySelectorAll('[data-registration-status="registered"],[data-registration-complete="true"],#registration-complete,[data-peatix-registration="registered"]').length }), { mode: "canonical", event_id: id }); return !!x && x.auth !== true && (x.markers === 0 || (Array.isArray(x.markers) && x.markers.length === 0)); }
async function control(page, selector) {
  if (!page || typeof page.locator !== "function") return null;
  try { const x = page.locator(selector); return await x.count() === 1 && await x.isVisible() ? x : null; } catch { return null; }
}
async function inspectControl(page, selector) {
  if (!page || typeof page.locator !== "function") return null;
  try {
    const locator = page.locator(selector);
    const count = await locator.count();
    if (count !== 1) return Object.freeze({ count, visible: false, enabled: false, editable: false, locator: null });
    const visible = await locator.isVisible();
    if (typeof locator.isEnabled !== "function" || typeof locator.isEditable !== "function") return null;
    const enabled = await locator.isEnabled();
    const editable = await locator.isEditable();
    if (typeof visible !== "boolean" || typeof enabled !== "boolean" || typeof editable !== "boolean") return null;
    return Object.freeze({ count, visible, enabled, editable, locator });
  } catch { return null; }
}
async function evaluate(page, fn, payload) {
  try { const x = await page.evaluate(fn, payload); return x && typeof x === "object" && !Array.isArray(x) ? x : null; } catch { return null; }
}

// Measured live 2026-08-18 (see docs/superpowers/plans/2026-08-16-connector-core-recovery-execution-notes.md,
// "Peatix was logged out too"): a logged-out peatix.com shows both a
// "ログイン" and a "新規登録" control in the page header, on every page —
// including the ticket page this runs on, so no extra navigation is needed.
// Requiring both (not just one) keeps this from firing on an unrelated
// control that merely contains one of the two words.
async function peatixSessionExpired(page) {
  const observed = await evaluate(page, () => {
    const clean = (x) => String(x || "").replace(/\s+/g, " ").trim();
    const texts = new Set([...document.querySelectorAll("a,button")].map((el) => (
      clean(el.innerText || el.value || el.getAttribute("aria-label") || "")
    )));
    return { login: texts.has("ログイン"), signup: texts.has("新規登録") };
  }, { mode: "session_check" });
  return Boolean(observed && observed.login === true && observed.signup === true);
}

async function readPeatixRegistrationStateOnPage(page, raw) {
  const c = candidate(raw); if (!c || !page || typeof page.evaluate !== "function") return out("unavailable", "invalid_input");
  const observed = await evaluate(page, (p) => {
    const clean = (x) => String(x || "").replace(/\s+/g, " ").trim();
    const hiddenStyle = (style) => Boolean(style && ([style.display, style.visibility, style.contentVisibility].some((value) => ["none", "hidden", "collapse"].includes(String(value || "").toLowerCase())) || String(style.opacity == null ? "" : style.opacity) === "0"));
    const visible = (element) => {
      if (!element || element.hidden === true || element.isConnected === false) return false;
      const view = element.ownerDocument && element.ownerDocument.defaultView; let current = element;
      while (current) {
        if (current.hidden === true || current.isConnected === false || (typeof current.hasAttribute === "function" && current.hasAttribute("hidden")) || String((current.getAttribute && current.getAttribute("aria-hidden")) || "").toLowerCase() === "true") return false;
        if (hiddenStyle(current.style || {})) return false;
        let computed = null; try { computed = view && typeof view.getComputedStyle === "function" ? view.getComputedStyle(current) : null; } catch { computed = null; }
        if (hiddenStyle(computed)) return false;
        current = current.parentElement || null;
      }
      if (typeof element.getBoundingClientRect !== "function") return false;
      let rect; try { rect = element.getBoundingClientRect(); } catch { return false; }
      return Boolean(rect && Number(rect.width) > 0 && Number(rect.height) > 0);
    };
    const markers = [...document.querySelectorAll('[data-registration-status="registered"],[data-registration-complete="true"],#registration-complete,[data-peatix-registration="registered"]')].map((n) => {
      const ref = /^peatix-event:\/\/event\/([1-9][0-9]*)$/.exec(clean(n.getAttribute("data-event-ref")));
      return { event_id: clean(n.getAttribute("data-event-id") || n.getAttribute("data-peatix-event-id") || (ref && ref[1])), ticket_id: clean(n.getAttribute("data-ticket-id") || n.getAttribute("data-peatix-ticket-id")) };
    });
    const path = String(location.pathname || "");
    const eventPage = new RegExp(`^/event/${p.event_id}/?$`).test(path);
    const ticketPage = new RegExp(`^/event/${p.event_id}/ticket$`).test(path);
    const auth = /\/(?:login|signin|signup)(?:\/|$)/i.test(path);
    const checkout = !!((/^\/sales\/event\/[1-9][0-9]*\/(?:tickets|form|confirm)\/?$/.test(path) || eventPage) && document.querySelector('input[name^="number_of_tickets_"],#next-button,#form-submit-button,#confirm-button'));
    const ticketEventId = (element) => {
      let href = element && element.getAttribute && element.getAttribute("href");
      if (!href && element) href = element.href;
      try {
        const url = new URL(String(href || ""), location.href);
        const match = /^\/event\/([1-9][0-9]*)\/ticket$/.exec(url.pathname);
        return url.protocol === "https:" && url.hostname === "peatix.com" && !url.port && !url.username && !url.password && !url.search && !url.hash && match ? match[1] : "";
      } catch { return ""; }
    };
    const ticketLinks = eventPage && !auth ? [...document.querySelectorAll("a[href]")].map((element) => ({ event_id: ticketEventId(element), visible: visible(element) })).filter((link) => link.event_id) : [];
    const canonicalTicketLinkCount = ticketLinks.filter((link) => link.event_id === p.event_id && link.visible).length;
    const canonicalTicketLinkTotal = ticketLinks.filter((link) => link.event_id === p.event_id).length;
    const competingTicketLinkCount = ticketLinks.filter((link) => link.event_id !== p.event_id).length;
    const bodies = ticketPage && !auth ? [...document.querySelectorAll("body.webticket")] : [];
    const sections = ticketPage && !auth ? [...document.querySelectorAll("section.ticket")] : [];
    const qrImages = ticketPage && !auth ? [...document.querySelectorAll("#qr-code img.js-qrcode-image")] : [];
    const ticketCovers = ticketPage && !auth ? [...document.querySelectorAll(".ticket_cover")] : [];
    const ticketEvents = ticketPage && !auth ? [...document.querySelectorAll(".ticket_event")] : [];
    const ticketEventNames = ticketPage && !auth ? [...document.querySelectorAll(".ticket_event-name")] : [];
    const ticketSummaries = ticketPage && !auth ? [...document.querySelectorAll(".ticket_summary")] : [];
    const ticketShell = bodies.length === 1 && sections.length === 1 && qrImages.length === 1 && bodies.every(visible) && sections.every(visible) && qrImages.every(visible);
    const swipeShell = bodies.length === 1 && sections.length === 1
      && [ticketCovers, ticketEvents, ticketEventNames, ticketSummaries].every((nodes) => nodes.length === 1 && nodes.every(visible))
      && bodies.every(visible) && sections.every(visible);
    return { href: String(location.href || ""), auth, checkout, markers, canonical_ticket_link_count: canonicalTicketLinkCount, canonical_ticket_link_total: canonicalTicketLinkTotal, competing_ticket_link_count: competingTicketLinkCount, ticket_shell: ticketShell, swipe_shell: swipeShell };
  }, { mode: "readback", event_id: c.id, ticket_id: c.ticket });
  if (!observed) return out("unavailable", "readback_unavailable");
  if (observed.status === "registered") return String(observed.event_id) === c.id && String(observed.ticket_id) === c.ticket ? out("registered") : out("unavailable", "readback_unavailable");
  if (observed.status === "absent") return out("absent");
  if (observed.auth === true) return out("unavailable", "readback_unavailable");
  if (!Array.isArray(observed.markers)) return out("unavailable", "readback_unavailable");
  if (observed.markers.length === 0 && observed.checkout === false
    && (observed.ticket_shell === true || observed.swipe_shell === true) && ticketPageUrl(observed.href, c.id)) return out("registered");
  if (observed.markers.length === 0 && observed.checkout === false
    && observed.canonical_ticket_link_count === 1 && observed.canonical_ticket_link_total === 1
    && observed.competing_ticket_link_count === 0 && eventPageUrl(observed.href, c.id)) return out("registered");
  if (Array.isArray(observed.markers) && observed.markers.length) return observed.markers.length === 1 && String(observed.markers[0].event_id) === c.id && String(observed.markers[0].ticket_id) === c.ticket ? out("registered") : out("unavailable", "readback_unavailable");
  return observed.checkout === true && (stepUrl(observed.href, c.id, "tickets") || stepUrl(observed.href, c.id, "form") || stepUrl(observed.href, c.id, "confirm") || eventPageUrl(observed.href, c.id)) ? out("absent") : out("unavailable", "readback_unavailable");
}

async function submitPeatixOnPage(page, rawCandidate, rawProfile) {
  if (rawCandidate && rawCandidate.candidate) { rawProfile = rawProfile || rawCandidate.profile || rawCandidate.attendee_profile; rawCandidate = rawCandidate.candidate; }
  if (rawProfile && rawProfile.profile) rawProfile = rawProfile.profile;
  const c = candidate(rawCandidate); const p = profile(rawProfile); if (!c || !p || !page) return out("unavailable", "invalid_input");
  let clicked = false;
  try {
    const before = await readPeatixRegistrationStateOnPage(page, c);
    if (before.status === "registered") return before;
    if (before.status !== "absent") {
      if (!await canonicalStart(page, c.id)) return before;
      if (eventPageUrl(pageHref(page), c.id)) {
        const ticketProof = await readTicketProof(page, c);
        if (ticketProof === "registered") return out("registered");
        if (ticketProof === "unavailable") return out("unavailable", "readback_unavailable");
      }
    }
    const base = `https://peatix.com/sales/event/${c.id}`;
    if (typeof page.goto !== "function" || !await page.goto(`${base}/tickets`, { waitUntil: "domcontentloaded", timeout: 30000 }).then(() => true, () => false) || !stepUrl(pageHref(page), c.id, "tickets")) return out("unavailable", "tickets_navigation_failed");
    const ticket = await control(page, `input[name=number_of_tickets_${c.ticket}]`); if (!ticket || typeof ticket.fill !== "function") return out("unavailable", "ticket_control_unavailable"); await ticket.fill("1");
    const next = await control(page, "#next-button"); if (!next || typeof next.click !== "function") return out("unavailable", "next_control_unavailable"); if (typeof page.waitForURL !== "function") return out("unavailable", "form_navigation_failed"); const nextNavigation = waitForFormOrConfirm(page, c.id); await next.click();
    const nextStep = await nextNavigation;
    if (!nextStep) {
      if (await peatixSessionExpired(page)) return out("unavailable", "session_expired");
      return out("unavailable", "form_navigation_failed");
    }
    if (nextStep === "form") {
    const form = await evaluate(page, () => {
      const norm = (x) => String(x || "").normalize("NFKC").replace(/\s+/g, " ").trim().toLowerCase();
      const label = (n) => norm(n.getAttribute("aria-label") || (n.labels && n.labels[0] && n.labels[0].textContent) || n.getAttribute("data-label"));
      const selector = (n) => n.id ? `#${CSS.escape(n.id)}` : `[name="${n.name}"]`;
      const fields = [...document.querySelectorAll("input[required],textarea[required],select[required],[aria-required='true']")].filter((n) => !["hidden","submit","button"].includes(String(n.type || "").toLowerCase())).map((n) => { const l = label(n); const name = norm(n.getAttribute("name")); const kind = ["氏名","名前","お名前","name","attendee name"].includes(l) ? "name" : ["メール","メールアドレス","email","e-mail","email address","account email"].includes(l) ? "email" : ["organizer privacy","organizer privacy confirmation","主催者のプライバシーポリシーに同意する","主催者のプライバシー確認"].includes(l) || ["organizer_privacy"].includes(name) ? "privacy" : "unknown"; return { selector: selector(n), kind, visible: !n.hidden, checked: !!n.checked }; });
      const radioFields = [...document.querySelectorAll("dl.field.required")].flatMap((field) => {
        const prompt = norm((field.querySelector(":scope > dt") || field.querySelector("dt") || {}).textContent);
        const radios = [...field.querySelectorAll("input[type=\"radio\"]")].filter((n) => !n.hidden);
        const privacyPrompt = /^.+のプライバシーポリシーを読んだ・確認した$/.test(prompt);
        if (!radios.length) return privacyPrompt ? [{ kind: "unknown", visible: true }] : [];
        const consent = radios.length === 1 && privacyPrompt && !radios[0].disabled && label(radios[0]) === "確認し同意する。";
        return [{ selector: consent ? selector(radios[0]) : "", kind: consent ? "privacy" : "unknown", visible: true, checked: !!radios[0].checked }];
      });
      return { fields: fields.concat(radioFields), submit: !!document.querySelector("#form-submit-button") };
    }, { mode: "form" });
    if (!form || !Array.isArray(form.fields) || form.fields.some((f) => f.visible !== false && f.kind === "unknown")) return out("needs_fallback", "unknown_required_field");
    const names = form.fields.filter((f) => f.visible !== false && f.kind === "name"); const emails = form.fields.filter((f) => f.visible !== false && f.kind === "email"); const privacy = form.fields.filter((f) => f.visible !== false && f.kind === "privacy");
    if (names.length !== 1 || emails.length !== 1) return out("unavailable", "required_field_unavailable"); if (privacy.length > 1) return out("unavailable", "privacy_control_unavailable");
    for (const [f, value] of [[names[0], p.name], [emails[0], p.email]]) { const x = await control(page, f.selector); if (!x || typeof x.fill !== "function") return out("unavailable", "required_field_unavailable"); await x.fill(value); }
    if (privacy.length === 1) { const consent = await control(page, privacy[0].selector); if (!consent || typeof consent.check !== "function") return out("unavailable", "privacy_control_unavailable"); if (typeof consent.isChecked !== "function" || !await consent.isChecked()) await consent.check(); }
    const formSubmit = await control(page, "#form-submit-button"); if (!formSubmit || typeof formSubmit.click !== "function") return out("unavailable", "form_submit_unavailable"); if (typeof page.waitForURL !== "function") return out("unavailable", "confirm_navigation_failed"); const confirmNavigation = waitForStep(page, c.id, "confirm"); await formSubmit.click();
    if (!await confirmNavigation) { const confirmUrl = pageHref(page); const u = (() => { try { return new URL(confirmUrl); } catch { return null; } })(); const match = u && STEP.exec(u.pathname); return out("unavailable", match && match[2] === "confirm" && match[1] !== c.id ? "confirm_event_mismatch" : "confirm_navigation_failed"); }
    }
    const confirm = await evaluate(page, () => { const b = document.querySelector("#confirm-button"); return { text: b && String(b.innerText || b.value || "").replace(/\s+/g, " ").trim(), visible: !!(b && !b.hidden) }; }, { mode: "confirm", event_id: c.id });
    if (!confirm || confirm.text !== TEXT || confirm.visible !== true) return out("unavailable", "confirm_control_unavailable");
    const family = await inspectControl(page, '#confirm-form [name="lastname_edit"]'); const given = await inspectControl(page, '#confirm-form [name="firstname_edit"]');
    if (!family || !given || family.count !== 1 || given.count !== 1 || family.visible !== given.visible) return out("unavailable", "kana_control_unavailable");
    if (family.visible) {
      if (!family.enabled || !given.enabled || !family.editable || !given.editable) return out("unavailable", "kana_control_unavailable");
      await family.locator.fill(p.family_name_kana); await given.locator.fill(p.given_name_kana);
    }
    const validation = await evaluate(page, () => {
      const form = document.querySelector("#confirm-form"); const $ = window.jQuery;
      if (!$ || !form || typeof $(form).valid !== "function") return { valid: false };
      try { return { valid: Boolean($(form).valid()) }; } catch { return { valid: false }; }
    }, { mode: "confirm_validation" });
    if (!validation || validation.valid !== true) return out("unavailable", "confirm_validation_failed");
    const final = await control(page, "#confirm-button"); if (!final || typeof final.click !== "function") return out("unavailable", "confirm_control_unavailable");
    const confirmedNavigation = waitForConfirmed(page, c.id); clicked = true; await final.click();
    if (!await confirmedNavigation) return out("unavailable", "readback_unavailable");
    const canonical = `https://peatix.com/event/${c.id}`;
    if (typeof page.goto !== "function" || !await page.goto(canonical, { waitUntil: "domcontentloaded", timeout: 30_000 }).then(() => true, () => false) || !eventPageUrl(pageHref(page), c.id)) return out("unavailable", "readback_unavailable");
    let after = await readPeatixRegistrationStateOnPage(page, c);
    if (after.status !== "registered" && after.status !== "absent") {
      const ticketProof = await readTicketProof(page, c);
      if (ticketProof === "registered") return out("registered");
      if (ticketProof === "unavailable") return out("unavailable", "readback_unavailable");
    }
    return after.status === "registered" || after.status === "absent" ? after : out("unavailable", "readback_unavailable");
  } catch { return out("unavailable", clicked ? "readback_unavailable" : "browser_action_failed"); }
}

module.exports = { readPeatixRegistrationStateOnPage, submitPeatixOnPage };
