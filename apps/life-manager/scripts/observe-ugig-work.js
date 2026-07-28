#!/usr/bin/env node
"use strict";

const { readFileSync } = require("node:fs");
const { resolve } = require("node:path");
const { observeUgigDeliveries } = require("../lib/ugig-invoice-observer.js");

const MAX_RESPONSE_BYTES = 1_000_000;

function unwrapList(value, keys) {
  if (Array.isArray(value)) return value;
  for (const key of keys) {
    if (Array.isArray(value?.[key])) return value[key];
    if (Array.isArray(value?.data?.[key])) return value.data[key];
  }
  if (Array.isArray(value?.data)) return value.data;
  return [];
}

async function fetchJson(fetchImpl, url, init = {}) {
  const response = await fetchImpl(url, init);
  const text = await response.text();
  if (Buffer.byteLength(text, "utf8") > MAX_RESPONSE_BYTES) {
    throw new Error(`response too large from ${new URL(url).host}`);
  }
  if (!response.ok) throw new Error(`HTTP ${response.status} from ${new URL(url).host}`);
  try {
    return text === "" ? {} : JSON.parse(text);
  } catch {
    throw new Error(`invalid JSON from ${new URL(url).host}`);
  }
}

function githubPullApiUrl(link) {
  const parsed = new URL(link);
  const parts = parsed.pathname.split("/").filter(Boolean);
  if (parsed.protocol !== "https:" || parsed.hostname !== "github.com" ||
      parts.length !== 4 || parts[2] !== "pull" || !/^[1-9][0-9]*$/.test(parts[3])) {
    throw new Error("invalid GitHub pull request URL");
  }
  return `https://api.github.com/repos/${parts[0]}/${parts[1]}/pulls/${parts[3]}`;
}

async function main(deps = {}) {
  const fetchImpl = deps.fetchImpl || globalThis.fetch;
  const apiBase = (deps.apiBase || process.env.UGIG_API_BASE || "https://ugig.net").replace(/\/$/, "");
  const apiKey = deps.apiKey || process.env.UGIG_API_KEY;
  const deliveries = deps.deliveries || JSON.parse(readFileSync(
    resolve(deps.configPath || process.env.UGIG_DELIVERIES_CONFIG ||
      resolve(__dirname, "ugig-deliveries.json")),
    "utf8",
  ));
  const now = deps.now || (() => new Date());
  const writeOutput = deps.writeOutput || ((value) => process.stdout.write(value));

  if (!apiKey) throw new Error("UGIG_API_KEY is required");
  const headers = {
    authorization: `Bearer ${apiKey}`,
    accept: "application/json",
  };
  const applicationBody = await fetchJson(fetchImpl, `${apiBase}/api/applications/my`, { headers });
  const applications = unwrapList(applicationBody, ["applications"]);

  const result = await observeUgigDeliveries({
    deliveries,
    applications,
    listInvoices: async (gigId) => {
      const body = await fetchJson(fetchImpl, `${apiBase}/api/gigs/${gigId}/invoices`, { headers });
      return unwrapList(body, ["invoices"]);
    },
    isPullRequestMerged: async (link) => {
      const body = await fetchJson(fetchImpl, githubPullApiUrl(link), {
        headers: {
          accept: "application/vnd.github+json",
          "x-github-api-version": "2022-11-28",
          "user-agent": "life-manager-ugig-invoice-observer",
        },
      });
      return Boolean(body.merged_at);
    },
    createInvoice: async (gigId, payload) => fetchJson(
      fetchImpl,
      `${apiBase}/api/gigs/${gigId}/invoice`,
      {
        method: "POST",
        headers: { ...headers, "content-type": "application/json" },
        body: JSON.stringify(payload),
      },
    ),
  });

  const output = { observed_at: now().toISOString(), ...result };
  writeOutput(`${JSON.stringify(output)}\n`);
  return result;
}

if (require.main === module) {
  main().catch((error) => {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
  });
}

module.exports = { main, fetchJson, githubPullApiUrl };
