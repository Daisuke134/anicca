"use strict";
// 11b PHY-b — candidate selection (§9.1 PHYSICAL organ).
// A candidate is only a candidate when three separate facts are proven from
// public pages the user could have read themselves: the provider publicly
// offers the exact care category 11a detected, the provider sits inside the
// user's own living area (home or work), and a non-phone booking route exists.
// Nothing here is inferred from proximity alone — that shortcut is what let an
// earlier pass answer a generic "clinic" signal with three internal-medicine
// clinics. A care category with no public service vocabulary fails closed.

// Public reservation systems whose presence is itself the evidence: reaching
// one of these hosts means a real web booking flow exists, whether the shop
// runs it from its own domain or lives entirely inside the platform.
const BOOKING_HOSTS = Object.freeze([
  "beauty.hotpepper.jp", "reservia.jp", "airrsv.net", "coubic.com",
  "select-type.com", "stora.jp", "reserva.be", "reserve.ne.jp",
  "qr.digikar-smart.jp",
]);

function isBookingHost(url) {
  try {
    return BOOKING_HOSTS.includes(new URL(url).host.toLowerCase());
  } catch {
    return false;
  }
}

function hrefs(html, pageUrl) {
  return [...String(html).matchAll(/href=["']([^"']+)["']/gi)].map((match) => {
    const raw = match[1].replace(/&amp;/g, "&");
    if (!pageUrl || /^[a-z][a-z0-9+.-]*:/i.test(raw)) return raw;
    try {
      return new URL(raw, pageUrl).toString();
    } catch {
      return raw;
    }
  });
}

function reservationJudgment(html, pageUrl) {
  const text = String(html);
  // A page served by a reservation platform is the reservation route.
  if (pageUrl && isBookingHost(pageUrl)) return { route: "web", url: pageUrl };
  const links = hrefs(text, pageUrl);
  const mail = links.find((url) => /^mailto:/i.test(url));
  const hosted = links.find((url) => isBookingHost(url));
  if (hosted) return { route: "web", url: hosted };
  const web = links.find((url) =>
    /^https:\/\//i.test(url)
    && /(reserv|reserve|booking|digikar|yoyaku)/i.test(url));
  if (web && /(Web|ネット|オンライン).{0,20}予約|予約.{0,20}(Web|ネット|オンライン)/is.test(text)) {
    return { route: "web", url: web };
  }
  if (mail && /メール.{0,20}予約|予約.{0,20}メール/is.test(text)) {
    return { route: "email", url: mail };
  }
  if (/予約不要/is.test(text)) return { route: "walk_in", url: null };
  if (/電話.{0,20}予約|予約.{0,20}電話/is.test(text)) return { route: "phone_only", url: null };
  // A published telephone number with no other route is a known route we are
  // forbidden to take (§9.5), which is a different fact from not knowing.
  if (links.some((url) => /^tel:/i.test(url))) return { route: "phone_only", url: null };
  return { route: "unavailable", url: null };
}

async function evaluateCareCandidates(definitions, fetchImpl = fetch) {
  if (!Array.isArray(definitions) || definitions.length !== 3) {
    throw new Error("exactly three candidates are required");
  }
  const candidates = [];
  for (const definition of definitions) {
    let response = null;
    try {
      response = await fetchImpl(definition.officialUrl, {
        signal: AbortSignal.timeout(15_000),
      });
    } catch {}
    const html = response && response.ok ? await response.text() : "";
    const judgment = response && response.ok
      ? reservationJudgment(html)
      : { route: "unavailable", url: null };
    candidates.push({
      provider_id: definition.providerId,
      public_name: definition.publicName,
      official_url: definition.officialUrl,
      proximity_rank: definition.proximityRank,
      usual_provider: definition.usualProvider === true,
      reservation_route: judgment.route,
      reservation_url: judgment.url,
    });
  }

  const eligible = candidates.filter((candidate) =>
    candidate.reservation_route === "web" || candidate.reservation_route === "email");
  eligible.sort((a, b) =>
    Number(b.usual_provider) - Number(a.usual_provider)
    || a.proximity_rank - b.proximity_rank
    || a.provider_id.localeCompare(b.provider_id));
  return {
    schema_version: 1,
    candidates,
    selected_provider_id: eligible[0]?.provider_id || null,
  };
}

// The public service vocabulary each care category has to prove on its own
// site. A category absent from this table has no defensible way to be matched
// to a provider, so it is refused rather than approximated.
const CARE_SERVICE_TERMS = Object.freeze({
  haircut: Object.freeze([
    "ヘアサロン", "美容室", "美容院", "理容室", "理容", "床屋",
    "ヘアカット", "カット", "hair salon", "haircut", "barber",
  ]),
  dental: Object.freeze([
    "歯科", "歯医者", "デンタルクリニック", "dental", "dentist",
  ]),
  health_check: Object.freeze([
    "健康診断", "人間ドック", "健診", "定期健診", "health checkup", "medical checkup",
  ]),
});

const AREA_SUFFIX_GRANULARITY = Object.freeze({
  区: "ward", 市: "city", 郡: "district", 町: "town", 村: "village",
});

function normalizeText(value) {
  return String(value == null ? "" : value).normalize("NFKC").toLowerCase();
}

function normalizeName(value) {
  return normalizeText(value).replace(/\s+/g, " ").trim();
}

function normalizeCareCategory(value) {
  return normalizeText(value).trim().replace(/[\s-]+/g, "_");
}

function nonEmptyString(value) {
  return typeof value === "string" && value.trim().length > 0;
}

// Reduces a private street address to the coarse public area used for ranking.
// The exact address is never returned, logged, or written to a receipt.
function livingAreaFromAddress(homeAddress) {
  if (!nonEmptyString(homeAddress)) {
    throw new Error("living area cannot be derived from a missing address");
  }
  const withoutPrefecture = String(homeAddress).normalize("NFKC")
    .replace(/^\s*.{2,3}[都道府県]/u, "");
  const match = /[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}A-Za-z0-9ー]{1,10}?([区市郡町村])/u
    .exec(withoutPrefecture);
  if (!match) throw new Error("living area cannot be derived from this address");
  return { area: match[0], granularity: AREA_SUFFIX_GRANULARITY[match[1]] };
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

// A history shop name only claims a candidate when it appears as a whole token,
// so "Rein" cannot silently annex an unrelated "Near Salon".
function nameMatches(publicName, historyName) {
  const candidate = normalizeName(publicName);
  const known = normalizeName(historyName);
  if (!candidate || known.length < 2) return false;
  if (candidate === known) return true;
  if (/^[\x20-\x7e]+$/.test(known)) {
    return new RegExp(`(^|[^a-z0-9])${escapeRegExp(known)}([^a-z0-9]|$)`).test(candidate);
  }
  return candidate.includes(known);
}

function livingAreaJudgment(publicArea, livingArea) {
  const area = normalizeText(publicArea);
  if (nonEmptyString(livingArea.homeArea) && area.includes(normalizeText(livingArea.homeArea))) {
    return { match: "home", rank: 1 };
  }
  if (nonEmptyString(livingArea.workArea) && area.includes(normalizeText(livingArea.workArea))) {
    return { match: "work", rank: 2 };
  }
  return { match: "outside", rank: 3 };
}

function careNeedEvidence(html, careCategory) {
  const text = normalizeText(html);
  for (const term of CARE_SERVICE_TERMS[careCategory]) {
    if (text.includes(normalizeText(term))) return term;
  }
  return null;
}

// How many times the user's own history shows this provider for this exact
// care category. Zero means the candidate is a stranger and stays one.
function usualProviderVisits(history, careCategory, publicName) {
  if (!Array.isArray(history)) return 0;
  return history.filter((visit) =>
    visit
    && normalizeCareCategory(visit.careType) === careCategory
    && nonEmptyString(visit.providerName)
    && nameMatches(publicName, visit.providerName)).length;
}

async function selectCareCandidates(input, fetchImpl = fetch) {
  if (!input || typeof input !== "object") throw new Error("input must be an object");
  const careCategory = normalizeCareCategory(input.careCategory);
  if (!careCategory || !Object.prototype.hasOwnProperty.call(CARE_SERVICE_TERMS, careCategory)) {
    throw new Error(`unsupported care category: no public service vocabulary for "${input.careCategory}"`);
  }
  const livingArea = input.livingArea;
  if (!livingArea || typeof livingArea !== "object" || !nonEmptyString(livingArea.homeArea)) {
    throw new Error("living area is required: a home area must be known before ranking candidates");
  }
  const definitions = input.candidates;
  if (!Array.isArray(definitions) || definitions.length !== 3) {
    throw new Error("exactly three candidates are required");
  }
  for (const definition of definitions) {
    if (!definition || typeof definition !== "object") throw new Error("candidate must be an object");
    if (!nonEmptyString(definition.providerId)) throw new Error("candidate provider id is required");
    if (!nonEmptyString(definition.publicName)) throw new Error("candidate public name is required");
    if (!nonEmptyString(definition.officialUrl)) throw new Error("candidate official url is required");
    if (!nonEmptyString(definition.publicArea)) throw new Error("candidate public area is required");
  }

  const candidates = [];
  for (const definition of definitions) {
    let response = null;
    try {
      response = await fetchImpl(definition.officialUrl, { signal: AbortSignal.timeout(15_000) });
    } catch {}
    const reachable = Boolean(response && response.ok);
    const html = reachable ? await response.text() : "";
    const evidence = reachable ? careNeedEvidence(html, careCategory) : null;
    const judgment = reachable
      ? reservationJudgment(html, definition.officialUrl)
      : { route: "unavailable", url: null };
    const area = livingAreaJudgment(definition.publicArea, livingArea);
    const visits = usualProviderVisits(input.history, careCategory, definition.publicName);
    candidates.push({
      provider_id: definition.providerId,
      public_name: definition.publicName,
      official_url: definition.officialUrl,
      care_need_match: evidence !== null,
      care_need_evidence: evidence,
      living_area_match: area.match,
      living_area_rank: area.rank,
      usual_provider: visits > 0,
      usual_provider_visits: visits,
      reservation_route: judgment.route,
      reservation_url: judgment.url,
      web_bookable: judgment.route === "web",
    });
  }

  const eligible = candidates.filter((candidate) =>
    candidate.care_need_match
    && candidate.living_area_match !== "outside"
    && (candidate.reservation_route === "web" || candidate.reservation_route === "email"));
  eligible.sort((a, b) =>
    Number(b.usual_provider) - Number(a.usual_provider)
    || b.usual_provider_visits - a.usual_provider_visits
    || a.living_area_rank - b.living_area_rank
    || Number(b.web_bookable) - Number(a.web_bookable)
    || a.provider_id.localeCompare(b.provider_id));
  const selected = eligible[0] || null;
  return {
    schema_version: 1,
    care_category: careCategory,
    candidates,
    selected_provider_id: selected ? selected.provider_id : null,
    selection_basis: selected ? (selected.usual_provider ? "usual-provider" : "living-area-rank") : null,
  };
}

module.exports = {
  evaluateCareCandidates,
  livingAreaFromAddress,
  selectCareCandidates,
  CARE_SERVICE_TERMS,
};
