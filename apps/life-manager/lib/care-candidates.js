"use strict";

function hrefs(html) {
  return [...String(html).matchAll(/href=["']([^"']+)["']/gi)].map((match) => match[1]);
}

function reservationJudgment(html) {
  const text = String(html);
  const links = hrefs(text);
  const mail = links.find((url) => /^mailto:/i.test(url));
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
  return { route: "unavailable", url: null };
}

async function evaluateCareCandidates(definitions, fetchImpl = fetch) {
  // 11b: anchored discovery can honestly find fewer than three real providers in the user's
  // life sphere; forcing exactly three would force fabrication. One to three are accepted.
  if (!Array.isArray(definitions) || definitions.length < 1 || definitions.length > 3) {
    throw new Error("one to three candidates are required");
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

module.exports = { evaluateCareCandidates };
