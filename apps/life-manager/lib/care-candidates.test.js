"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const { evaluateCareCandidates } = require("./care-candidates");

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
