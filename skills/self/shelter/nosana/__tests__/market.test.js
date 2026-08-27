// node:test — market: pure Nosana market selection + cost math, fetchers with fetchImpl injected
// so nothing here touches the real network.
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  isGpuMarketName,
  normalizeMarkets,
  selectCheapestMarket,
  estimateJobCost,
  fetchMarkets,
  fetchNosUsdPriceLive,
} from "../market.mjs";

test("isGpuMarketName matches NVIDIA-named markets, rejects generic names", () => {
  assert.equal(isGpuMarketName("NVIDIA 3060"), true);
  assert.equal(isGpuMarketName("zephyr-skyline NVIDIA 4090"), true);
  assert.equal(isGpuMarketName("Generic CPU box"), false);
  assert.equal(isGpuMarketName(undefined), false);
  assert.equal(isGpuMarketName(""), false);
});

test("normalizeMarkets maps the live API shape into {address,name,usdPerHour,gpu}", () => {
  const raw = [
    { address: "A1", name: "NVIDIA 3060", usd_reward_per_hour: 0.04796 },
    { address: "A2", name: "NVIDIA 4090", usd_reward_per_hour: 0.31999 },
  ];
  const markets = normalizeMarkets(raw);
  assert.equal(markets.length, 2);
  assert.deepEqual(markets[0], { address: "A1", name: "NVIDIA 3060", usdPerHour: 0.04796, gpu: true });
});

test("normalizeMarkets throws on a non-array payload (fail closed, never an empty-but-ok list)", () => {
  assert.throws(() => normalizeMarkets({ not: "an array" }), /expected an array/);
  assert.throws(() => normalizeMarkets(null), /expected an array/);
});

test("normalizeMarkets filters out entries missing address/name or with a non-positive price", () => {
  const raw = [
    { address: "A1", name: "NVIDIA 3060", usd_reward_per_hour: 0.05 },
    { address: "A2", name: "NVIDIA 4090", usd_reward_per_hour: 0 },
    { address: null, name: "NVIDIA 4080", usd_reward_per_hour: 0.1 },
    { address: "A4", name: "NVIDIA 5080", usd_reward_per_hour: "not-a-number" },
  ];
  const markets = normalizeMarkets(raw);
  assert.equal(markets.length, 1);
  assert.equal(markets[0].address, "A1");
});

test("selectCheapestMarket picks the lowest usdPerHour among GPU markets by default", () => {
  const markets = [
    { address: "A1", name: "NVIDIA 4090", usdPerHour: 0.32, gpu: true },
    { address: "A2", name: "NVIDIA 3060", usdPerHour: 0.048, gpu: true },
    { address: "A3", name: "cheap-non-gpu", usdPerHour: 0.001, gpu: false },
  ];
  const chosen = selectCheapestMarket(markets);
  assert.equal(chosen.address, "A2");
});

test("selectCheapestMarket with requireGpu:false considers non-GPU markets too", () => {
  const markets = [
    { address: "A1", name: "NVIDIA 3060", usdPerHour: 0.048, gpu: true },
    { address: "A2", name: "cheap-non-gpu", usdPerHour: 0.001, gpu: false },
  ];
  const chosen = selectCheapestMarket(markets, { requireGpu: false });
  assert.equal(chosen.address, "A2");
});

test("selectCheapestMarket returns null (never throws) when nothing is eligible", () => {
  assert.equal(selectCheapestMarket([], { requireGpu: true }), null);
  assert.equal(selectCheapestMarket([{ address: "A1", usdPerHour: 1, gpu: false }], { requireGpu: true }), null);
});

test("selectCheapestMarket breaks equal-price ties deterministically by lowest address", () => {
  const markets = [
    { address: "Bzzz", name: "NVIDIA X", usdPerHour: 0.1, gpu: true },
    { address: "Aaaa", name: "NVIDIA Y", usdPerHour: 0.1, gpu: true },
  ];
  assert.equal(selectCheapestMarket(markets).address, "Aaaa");
});

test("estimateJobCost computes usd = usdPerHour*hours and nos = usd/nosUsdPrice", () => {
  const { usd, nos } = estimateJobCost({ usdPerHour: 0.04796, hours: 0.25, nosUsdPrice: 0.2541681138496177 });
  assert.ok(Math.abs(usd - 0.01199) < 1e-4);
  assert.ok(Math.abs(nos - usd / 0.2541681138496177) < 1e-9);
});

test("estimateJobCost fails closed on non-positive/non-finite inputs (never treats unknown as free)", () => {
  assert.throws(() => estimateJobCost({ usdPerHour: 0, hours: 1, nosUsdPrice: 1 }), /usdPerHour/);
  assert.throws(() => estimateJobCost({ usdPerHour: 1, hours: 0, nosUsdPrice: 1 }), /hours/);
  assert.throws(() => estimateJobCost({ usdPerHour: 1, hours: 1, nosUsdPrice: 0 }), /nosUsdPrice/);
  assert.throws(() => estimateJobCost({ usdPerHour: 1, hours: 1, nosUsdPrice: NaN }), /nosUsdPrice/);
  assert.throws(() => estimateJobCost({ usdPerHour: -1, hours: 1, nosUsdPrice: 1 }), /usdPerHour/);
});

test("fetchMarkets normalizes a successful injected response", async () => {
  const fetchImpl = async (url) => {
    assert.equal(url, "https://dashboard.k8s.prd.nos.ci/api/markets/prices");
    return {
      ok: true,
      json: async () => [{ address: "A1", name: "NVIDIA 3060", usd_reward_per_hour: 0.048 }],
    };
  };
  const markets = await fetchMarkets({ fetchImpl });
  assert.equal(markets.length, 1);
  assert.equal(markets[0].address, "A1");
});

test("fetchMarkets throws on a non-ok HTTP response (fail closed)", async () => {
  const fetchImpl = async () => ({ ok: false, status: 503 });
  await assert.rejects(() => fetchMarkets({ fetchImpl }), /HTTP 503/);
});

test("fetchNosUsdPriceLive returns a valid injected price", async () => {
  const fetchImpl = async () => ({ json: async () => ({ price: 0.25 }) });
  const price = await fetchNosUsdPriceLive({ fetchImpl });
  assert.equal(price, 0.25);
});

test("fetchNosUsdPriceLive throws (fail closed) when the underlying fetch yields no valid price", async () => {
  const fetchImpl = async () => ({ json: async () => ({}) });
  await assert.rejects(() => fetchNosUsdPriceLive({ fetchImpl }), /could not obtain a valid NOS\/USD price/);
});

test("fetchNosUsdPriceLive throws (fail closed) when the underlying fetchImpl throws", async () => {
  const fetchImpl = async () => {
    throw new Error("network down");
  };
  await assert.rejects(() => fetchNosUsdPriceLive({ fetchImpl }), /could not obtain a valid NOS\/USD price/);
});
