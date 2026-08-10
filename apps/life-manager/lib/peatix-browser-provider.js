"use strict";

const REF = /^peatix-event:\/\/event\/([1-9][0-9]*)$/;
const ID = /^[1-9][0-9]*$/;
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const KANA = /^[\u30A1-\u30FA\u30FC]+$/u;
const STEP = /^\/sales\/event\/([1-9][0-9]*)\/(tickets|form|confirm)\/?$/;
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
async function waitForStep(page, id, step) {
  if (!page || typeof page.waitForURL !== "function") return false;
  try {
    await page.waitForURL((url) => stepUrl(String(url), id, step), { waitUntil: "domcontentloaded", timeout: 30_000 });
    return stepUrl(pageHref(page), id, step);
  } catch { return false; }
}
function eventPageUrl(href, id) { let u; try { u = new URL(href); } catch { return false; } const m = /^\/event\/([1-9][0-9]*)\/?$/.exec(u.pathname); return u.protocol === "https:" && u.hostname === "peatix.com" && !u.port && !u.username && !u.password && !u.search && !u.hash && !!m && m[1] === id; }
async function canonicalStart(page, id) { if (!eventPageUrl(pageHref(page), id)) return false; const x = await evaluate(page, () => ({ auth: /\/(?:login|signin|signup)(?:\/|$)/i.test(location.pathname), markers: document.querySelectorAll('[data-registration-status="registered"],[data-registration-complete="true"],#registration-complete,[data-peatix-registration="registered"]').length }), { mode: "canonical", event_id: id }); return !!x && x.auth !== true && (x.markers === 0 || (Array.isArray(x.markers) && x.markers.length === 0)); }
async function control(page, selector) {
  if (!page || typeof page.locator !== "function") return null;
  try { const x = page.locator(selector); return await x.count() === 1 && await x.isVisible() ? x : null; } catch { return null; }
}
async function evaluate(page, fn, payload) {
  try { const x = await page.evaluate(fn, payload); return x && typeof x === "object" && !Array.isArray(x) ? x : null; } catch { return null; }
}

async function readPeatixRegistrationStateOnPage(page, raw) {
  const c = candidate(raw); if (!c || !page || typeof page.evaluate !== "function") return out("unavailable", "invalid_input");
  const observed = await evaluate(page, (p) => {
    const clean = (x) => String(x || "").replace(/\s+/g, " ").trim();
    const markers = [...document.querySelectorAll('[data-registration-status="registered"],[data-registration-complete="true"],#registration-complete,[data-peatix-registration="registered"]')].map((n) => {
      const ref = /^peatix-event:\/\/event\/([1-9][0-9]*)$/.exec(clean(n.getAttribute("data-event-ref")));
      return { event_id: clean(n.getAttribute("data-event-id") || n.getAttribute("data-peatix-event-id") || (ref && ref[1])), ticket_id: clean(n.getAttribute("data-ticket-id") || n.getAttribute("data-peatix-ticket-id")) };
    });
    const path = String(location.pathname || "");
    const eventPage = new RegExp(`^/event/${p.event_id}/?$`).test(path);
    return { href: String(location.href || ""), auth: /\/(?:login|signin|signup)(?:\/|$)/i.test(path), checkout: !!((/^\/sales\/event\/[1-9][0-9]*\/(?:tickets|form|confirm)\/?$/.test(path) || eventPage) && document.querySelector('input[name^="number_of_tickets_"],#next-button,#form-submit-button,#confirm-button')), markers };
  }, { mode: "readback", event_id: c.id, ticket_id: c.ticket });
  if (!observed) return out("unavailable", "readback_unavailable");
  if (observed.status === "registered") return String(observed.event_id) === c.id && String(observed.ticket_id) === c.ticket ? out("registered") : out("unavailable", "readback_unavailable");
  if (observed.status === "absent") return out("absent");
  if (observed.auth === true) return out("unavailable", "readback_unavailable");
  if (Array.isArray(observed.markers) && observed.markers.length) return observed.markers.length === 1 && String(observed.markers[0].event_id) === c.id && String(observed.markers[0].ticket_id) === c.ticket ? out("registered") : out("unavailable", "readback_unavailable");
  return observed.checkout === true && (stepUrl(observed.href, c.id, "tickets") || stepUrl(observed.href, c.id, "form") || stepUrl(observed.href, c.id, "confirm") || eventPageUrl(observed.href, c.id)) ? out("absent") : out("unavailable", "readback_unavailable");
}

async function submitPeatixOnPage(page, rawCandidate, rawProfile) {
  if (rawCandidate && rawCandidate.candidate) { rawProfile = rawProfile || rawCandidate.profile || rawCandidate.attendee_profile; rawCandidate = rawCandidate.candidate; }
  if (rawProfile && rawProfile.profile) rawProfile = rawProfile.profile;
  const c = candidate(rawCandidate); const p = profile(rawProfile); if (!c || !p || !page) return out("unavailable", "invalid_input");
  let clicked = false;
  try {
    const before = await readPeatixRegistrationStateOnPage(page, c); if (before.status === "registered") return before; if (before.status !== "absent" && !await canonicalStart(page, c.id)) return before;
    const base = `https://peatix.com/sales/event/${c.id}`;
    if (typeof page.goto !== "function" || !await page.goto(`${base}/tickets`, { waitUntil: "domcontentloaded", timeout: 30000 }).then(() => true, () => false) || !stepUrl(pageHref(page), c.id, "tickets")) return out("unavailable", "tickets_navigation_failed");
    const ticket = await control(page, `input[name=number_of_tickets_${c.ticket}]`); if (!ticket || typeof ticket.fill !== "function") return out("unavailable", "ticket_control_unavailable"); await ticket.fill("1");
    const next = await control(page, "#next-button"); if (!next || typeof next.click !== "function") return out("unavailable", "next_control_unavailable"); if (typeof page.waitForURL !== "function") return out("unavailable", "form_navigation_failed"); const formNavigation = waitForStep(page, c.id, "form"); await next.click();
    if (!await formNavigation) return out("unavailable", "form_navigation_failed");
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
    const confirm = await evaluate(page, () => { const b = document.querySelector("#confirm-button"); return { text: b && String(b.innerText || b.value || "").replace(/\s+/g, " ").trim(), visible: !!(b && !b.hidden) }; }, { mode: "confirm", event_id: c.id });
    if (!confirm || confirm.text !== TEXT || confirm.visible !== true) return out("unavailable", "confirm_control_unavailable");
    const family = await control(page, '#confirm-form [name="lastname_edit"]'); const given = await control(page, '#confirm-form [name="firstname_edit"]');
    if (!family || !given || typeof family.fill !== "function" || typeof given.fill !== "function") return out("unavailable", "kana_control_unavailable");
    await family.fill(p.family_name_kana); await given.fill(p.given_name_kana);
    const validation = await evaluate(page, () => {
      const form = document.querySelector("#confirm-form"); const $ = window.jQuery;
      if (!$ || !form || typeof $(form).valid !== "function") return { valid: false };
      try { return { valid: Boolean($(form).valid()) }; } catch { return { valid: false }; }
    }, { mode: "confirm_validation" });
    if (!validation || validation.valid !== true) return out("unavailable", "confirm_validation_failed");
    const final = await control(page, "#confirm-button"); if (!final || typeof final.click !== "function") return out("unavailable", "confirm_control_unavailable"); clicked = true; await final.click();
    const after = await readPeatixRegistrationStateOnPage(page, c); return after.status === "registered" || after.status === "absent" ? after : out("unavailable", "readback_unavailable");
  } catch { return out("unavailable", clicked ? "readback_unavailable" : "browser_action_failed"); }
}

module.exports = { readPeatixRegistrationStateOnPage, submitPeatixOnPage };
