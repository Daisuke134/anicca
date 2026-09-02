"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const {
  evaluateCareCandidates,
  livingAreaFromAddress,
  selectCareCandidates,
} = require("./care-candidates");

const definitions = [
  {
    providerId: "sora",
    publicName: "Sora Clinic",
    officialUrl: "https://sora.example/",
    proximityRank: 1,
    usualProvider: false,
  },
  {
    providerId: "walkin",
    publicName: "Walk-in Clinic",
    officialUrl: "https://walkin.example/",
    proximityRank: 2,
    usualProvider: false,
  },
  {
    providerId: "usual",
    publicName: "Usual Clinic",
    officialUrl: "https://usual.example/",
    proximityRank: 7,
    usualProvider: true,
  },
];

function fakeFetch(url) {
  const bodies = {
    "https://sora.example/": '<a href="https://booking.example/reserve">Web予約</a>',
    "https://walkin.example/": "<p>一般診療は予約不要です</p>",
    "https://usual.example/": '<a href="mailto:care@usual.example">メール予約</a>',
  };
  return Promise.resolve({
    ok: true,
    url,
    text: async () => bodies[url],
  });
}

test("three live candidates get closed reservation-route judgments and usual provider wins", async () => {
  const receipt = await evaluateCareCandidates(definitions, fakeFetch);
  assert.equal(receipt.candidates.length, 3);
  assert.deepEqual(receipt.candidates.map((candidate) => candidate.reservation_route), [
    "web", "walk_in", "email",
  ]);
  assert.equal(receipt.selected_provider_id, "usual");
  for (const candidate of receipt.candidates) {
    assert.deepEqual(Object.keys(candidate).sort(), [
      "official_url",
      "provider_id",
      "proximity_rank",
      "public_name",
      "reservation_route",
      "reservation_url",
      "usual_provider",
    ]);
  }
});

test("phone-only or unverifiable paths are judged but never selected for autonomous booking", async () => {
  const receipt = await evaluateCareCandidates([
    { ...definitions[0], providerId: "phone", officialUrl: "https://phone.example/" },
    { ...definitions[1], providerId: "missing", officialUrl: "https://missing.example/" },
    { ...definitions[2], providerId: "web", usualProvider: false, officialUrl: "https://web.example/" },
  ], async (url) => ({
    ok: url !== "https://missing.example/",
    url,
    text: async () => ({
      "https://phone.example/": "<p>電話予約のみ</p>",
      "https://web.example/": '<a href="https://reserve.example/">オンライン予約</a>',
    })[url] || "",
  }));
  assert.deepEqual(receipt.candidates.map((candidate) => candidate.reservation_route), [
    "phone_only", "unavailable", "web",
  ]);
  assert.equal(receipt.selected_provider_id, "web");
});

test("anything other than exactly three candidates fails closed", async () => {
  await assert.rejects(() => evaluateCareCandidates(definitions.slice(0, 2), fakeFetch), /exactly three/);
});

// ---------------------------------------------------------------------------
// 11b PHY-b — candidate selection bound to the exact care category from 11a,
// ranked by the user's living area, preferring the shop history already shows.
// ---------------------------------------------------------------------------

const HAIRCUT_HISTORY = [
  { careType: "haircut", startMs: Date.parse("2025-02-26T00:00:00Z"), providerName: null },
  { careType: "haircut", startMs: Date.parse("2025-10-18T00:00:00Z"), providerName: null },
  { careType: "haircut", startMs: Date.parse("2026-06-21T00:00:00Z"), providerName: "Rein" },
  { careType: "dental", startMs: Date.parse("2026-06-13T00:00:00Z"), providerName: "四谷歯科" },
];

const SALON_PAGES = {
  "https://near.example/": '<p>美容室のカット</p><a href="https://beauty.hotpepper.jp/slnH000/">ネット予約</a>',
  "https://rein.example/": '<p>ヘアサロン Rein のカット</p><a href="https://beauty.hotpepper.jp/slnH999/">ネット予約</a>',
  "https://work.example/": '<p>美容院でカットいたします</p><a href="mailto:hi@work.example">メール予約</a>',
};

function salonFetch(url) {
  return Promise.resolve({ ok: url in SALON_PAGES, url, text: async () => SALON_PAGES[url] || "" });
}

const SALONS = [
  {
    providerId: "near", publicName: "Near Salon",
    officialUrl: "https://near.example/", publicArea: "東京都新宿区西新宿1-1-1",
  },
  {
    providerId: "rein", publicName: "ヘアサロン Rein",
    officialUrl: "https://rein.example/", publicArea: "東京都新宿区高田馬場2-2-2",
  },
  {
    providerId: "work", publicName: "Work Salon",
    officialUrl: "https://work.example/", publicArea: "東京都渋谷区渋谷3-3-3",
  },
];

const LIVING_AREA = { homeArea: "新宿区", workArea: "渋谷区" };

test("the living area is derived as a coarse public area and never carries the exact address", () => {
  const area = livingAreaFromAddress("東京都新宿区西新宿2-8-1 都庁ビル1203号室");
  assert.equal(area.area, "新宿区");
  assert.equal(area.granularity, "ward");
  assert.ok(!JSON.stringify(area).includes("2-8-1"));
  assert.ok(!JSON.stringify(area).includes("1203"));
});

test("an address that cannot be reduced to an area fails closed instead of guessing", () => {
  assert.throws(() => livingAreaFromAddress(""), /living area/);
  assert.throws(() => livingAreaFromAddress(null), /living area/);
  assert.throws(() => livingAreaFromAddress("somewhere over there"), /living area/);
});

test("a care category with no known service vocabulary fails closed rather than picking a specialty", async () => {
  await assert.rejects(() => selectCareCandidates({
    careCategory: "clinic",
    livingArea: LIVING_AREA,
    history: HAIRCUT_HISTORY,
    candidates: SALONS,
  }, salonFetch), /care category/);
});

test("three real salons are bound to the haircut need, ranked by living area, and the usual shop wins", async () => {
  const receipt = await selectCareCandidates({
    careCategory: "haircut",
    livingArea: LIVING_AREA,
    history: HAIRCUT_HISTORY,
    candidates: SALONS,
  }, salonFetch);

  assert.equal(receipt.care_category, "haircut");
  assert.equal(receipt.candidates.length, 3);
  const byId = Object.fromEntries(receipt.candidates.map((c) => [c.provider_id, c]));

  // every candidate provides the same care need, proven from its own public page
  assert.deepEqual(receipt.candidates.map((c) => c.care_need_match), [true, true, true]);
  assert.equal(byId.near.care_need_evidence, "美容室");
  assert.equal(byId.rein.care_need_evidence, "ヘアサロン");

  // living-area check: home ranks above work, and the rank is derived, not supplied
  assert.deepEqual(
    receipt.candidates.map((c) => [c.provider_id, c.living_area_match, c.living_area_rank]),
    [["near", "home", 1], ["rein", "home", 1], ["work", "work", 2]],
  );

  // web booking possibility is stated per candidate
  assert.deepEqual(receipt.candidates.map((c) => c.web_bookable), [true, true, false]);
  assert.equal(byId.work.reservation_route, "email");
  assert.equal(byId.near.reservation_url, "https://beauty.hotpepper.jp/slnH000/");

  // the shop the user already used wins over an equally close stranger
  assert.deepEqual(receipt.candidates.map((c) => c.usual_provider), [false, true, false]);
  assert.equal(byId.rein.usual_provider_visits, 1);
  assert.equal(receipt.selected_provider_id, "rein");
  assert.equal(receipt.selection_basis, "usual-provider");
});

test("a candidate outside the living area is judged, ranked last, and never selected", async () => {
  const receipt = await selectCareCandidates({
    careCategory: "haircut",
    livingArea: { homeArea: "新宿区", workArea: null },
    history: [],
    candidates: SALONS,
  }, salonFetch);
  const outside = receipt.candidates.find((c) => c.provider_id === "work");
  assert.equal(outside.living_area_match, "outside");
  assert.equal(outside.living_area_rank, 3);
  assert.deepEqual(receipt.candidates.map((c) => c.usual_provider), [false, false, false]);
  assert.equal(receipt.selected_provider_id, "near");
  assert.equal(receipt.selection_basis, "living-area-rank");
});

test("a page that does not publicly offer the care need is never selected for that need", async () => {
  const receipt = await selectCareCandidates({
    careCategory: "dental",
    livingArea: LIVING_AREA,
    history: HAIRCUT_HISTORY,
    candidates: SALONS,
  }, salonFetch);
  assert.deepEqual(receipt.candidates.map((c) => c.care_need_match), [false, false, false]);
  assert.deepEqual(receipt.candidates.map((c) => c.care_need_evidence), [null, null, null]);
  assert.equal(receipt.selected_provider_id, null);
  assert.equal(receipt.selection_basis, null);
});

test("an unreachable official page is reported honestly and cannot become a candidate", async () => {
  const receipt = await selectCareCandidates({
    careCategory: "haircut",
    livingArea: LIVING_AREA,
    history: HAIRCUT_HISTORY,
    candidates: [
      SALONS[0],
      { ...SALONS[1], officialUrl: "https://gone.example/" },
      SALONS[2],
    ],
  }, salonFetch);
  const gone = receipt.candidates.find((c) => c.provider_id === "rein");
  assert.equal(gone.care_need_match, false);
  assert.equal(gone.reservation_route, "unavailable");
  assert.equal(gone.web_bookable, false);
  assert.equal(receipt.selected_provider_id, "near");
});

test("missing living area, missing provider area, and the wrong candidate count all fail closed", async () => {
  const base = { careCategory: "haircut", history: HAIRCUT_HISTORY, candidates: SALONS };
  await assert.rejects(
    () => selectCareCandidates({ ...base, livingArea: null }, salonFetch), /living area/);
  await assert.rejects(
    () => selectCareCandidates({ ...base, livingArea: { homeArea: "", workArea: null } }, salonFetch),
    /living area/);
  await assert.rejects(() => selectCareCandidates({
    ...base,
    livingArea: LIVING_AREA,
    candidates: [SALONS[0], { ...SALONS[1], publicArea: "" }, SALONS[2]],
  }, salonFetch), /public area/);
  await assert.rejects(() => selectCareCandidates({
    ...base, livingArea: LIVING_AREA, candidates: SALONS.slice(0, 2),
  }, salonFetch), /exactly three/);
  await assert.rejects(() => selectCareCandidates({
    ...base,
    livingArea: LIVING_AREA,
    candidates: [SALONS[0], { ...SALONS[1], officialUrl: "" }, SALONS[2]],
  }, salonFetch), /official url/);
});

test("the candidate receipt stays a closed schema", async () => {
  const receipt = await selectCareCandidates({
    careCategory: "haircut",
    livingArea: LIVING_AREA,
    history: HAIRCUT_HISTORY,
    candidates: SALONS,
  }, salonFetch);
  assert.deepEqual(Object.keys(receipt).sort(), [
    "candidates", "care_category", "schema_version", "selected_provider_id", "selection_basis",
  ]);
  for (const candidate of receipt.candidates) {
    assert.deepEqual(Object.keys(candidate).sort(), [
      "care_need_evidence",
      "care_need_match",
      "living_area_match",
      "living_area_rank",
      "official_url",
      "provider_id",
      "public_name",
      "reservation_route",
      "reservation_url",
      "usual_provider",
      "usual_provider_visits",
      "web_bookable",
    ]);
  }
});

test("a provider whose public page is itself a booking system is web bookable at that page", async () => {
  const receipt = await selectCareCandidates({
    careCategory: "haircut",
    livingArea: { homeArea: "新宿区", workArea: null },
    history: [],
    candidates: [
      { providerId: "reservia", publicName: "Reservia Salon", publicArea: "東京都新宿区四谷1-4",
        officialUrl: "https://reservia.jp/shop/reserve/abc123" },
      SALONS[0],
      SALONS[2],
    ],
  }, (url) => Promise.resolve({
    ok: true,
    url,
    text: async () => url.startsWith("https://reservia.jp/")
      ? '<p>カット 2,900円</p><a href="/reserve/menu/abc123?is_guest=1">スタッフを選ぶ</a>'
      : SALON_PAGES[url] || "",
  }));
  const hosted = receipt.candidates.find((c) => c.provider_id === "reservia");
  assert.equal(hosted.care_need_match, true);
  assert.equal(hosted.reservation_route, "web");
  assert.equal(hosted.web_bookable, true);
  assert.equal(hosted.reservation_url, "https://reservia.jp/shop/reserve/abc123");
});

test("a relative booking link on an official page becomes an absolute reservation url", async () => {
  const receipt = await selectCareCandidates({
    careCategory: "haircut",
    livingArea: { homeArea: "新宿区", workArea: null },
    history: [],
    candidates: [
      { providerId: "own", publicName: "Own Site Salon", publicArea: "東京都新宿区四谷1-20",
        officialUrl: "https://own.example/index.html" },
      SALONS[0],
      SALONS[2],
    ],
  }, (url) => Promise.resolve({
    ok: true,
    url,
    text: async () => url.startsWith("https://own.example/")
      ? '<p>美容室のカット</p><a href="/reserve/">ネット予約はこちら</a>'
      : SALON_PAGES[url] || "",
  }));
  const own = receipt.candidates.find((c) => c.provider_id === "own");
  assert.equal(own.reservation_route, "web");
  assert.equal(own.reservation_url, "https://own.example/reserve/");
});

test("a page that publishes only a telephone number is judged phone_only, not unknown", async () => {
  const receipt = await selectCareCandidates({
    careCategory: "haircut",
    livingArea: { homeArea: "新宿区", workArea: null },
    history: [],
    candidates: [
      { providerId: "tel", publicName: "Tel Only Salon", publicArea: "東京都新宿区四谷1-20",
        officialUrl: "https://tel.example/" },
      SALONS[0],
      SALONS[2],
    ],
  }, (url) => Promise.resolve({
    ok: true,
    url,
    text: async () => url === "https://tel.example/"
      ? '<p>美容室 予約優先制</p><a href="tel:03-0000-0000">電話する</a>'
      : SALON_PAGES[url] || "",
  }));
  const telOnly = receipt.candidates.find((c) => c.provider_id === "tel");
  assert.equal(telOnly.reservation_route, "phone_only");
  assert.equal(telOnly.reservation_url, null);
  assert.equal(telOnly.web_bookable, false);
  assert.notEqual(receipt.selected_provider_id, "tel");
});
