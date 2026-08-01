"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { createHash } = require("node:crypto");

const ANSWER_IDS = Object.freeze([
  "q01_what", "q02_why_now", "q03_market", "q04_traction", "q05_team",
  "q06_use_of_funds", "q07_competition", "q08_business_model", "q09_vision", "q10_risks",
]);
const ASSETS = Object.freeze({
  "deck-en": "deck/deck-en.pdf",
  "deck-ja": "deck/deck-ja.pdf",
  "onepager-en": "onepager/onepager-en.png",
  "onepager-ja": "onepager/onepager-ja.png",
  logo: "assets/anicca-icon.png",
  "founder-photo": "assets/dais-profile.jpg",
});
const ANSWER_SOURCE = /^kit:answer\/(q(?:0[1-9]|10)_[a-z0-9_]+)\.(en|ja)$/;
const ASSET_SOURCE = /^kit:asset\/([a-z0-9-]+)$/;
const DASHBOARD_TOKEN = /\{\{dashboard:([a-zA-Z0-9_.]+)\}\}/g;

function createApplicationKitProvider(options = {}) {
  const root = path.resolve(String(options.root || ""));
  const readFile = options.readFile || ((file) => fs.readFileSync(file));
  if (!path.isAbsolute(String(options.root || "")) || root === path.parse(root).root) {
    throw new Error("application-kit root invalid");
  }
  function absolute(relative) {
    const target = path.resolve(root, relative);
    if (!target.startsWith(`${root}${path.sep}`)) throw new Error("application-kit path invalid");
    return target;
  }
  function read(relative, binary = false) {
    try {
      const value = readFile(absolute(relative), binary ? undefined : "utf8");
      const bytes = Buffer.isBuffer(value) ? value : Buffer.from(String(value), "utf8");
      if (bytes.length < 1) throw new Error("empty");
      return binary ? bytes : bytes.toString("utf8");
    } catch {
      throw new Error(`application-kit incomplete: ${relative}`);
    }
  }
  function snapshot() {
    const files = new Map();
    files.set("KIT.md", Buffer.from(read("KIT.md")));
    const manifest = read("MANIFEST.md");
    files.set("MANIFEST.md", Buffer.from(manifest));
    for (const id of ANSWER_IDS) {
      for (const language of ["en", "ja"]) {
        const relative = `answers/${id}.${language}.md`;
        files.set(relative, Buffer.from(read(relative)));
      }
    }
    for (const relative of Object.values(ASSETS)) {
      if (!manifest.includes(relative)) throw new Error(`application-kit incomplete: manifest ${relative}`);
      files.set(relative, read(relative, true));
    }
    const digest = createHash("sha256");
    for (const [relative, bytes] of [...files.entries()].sort(([left], [right]) => left.localeCompare(right))) {
      digest.update(relative).update("\0").update(bytes).update("\0");
    }
    return Object.freeze({
      schema_version: 1,
      root_ref: "application-kit://current",
      company_facts_ref: "application-kit://KIT.md",
      answer_count: ANSWER_IDS.length * 2,
      asset_count: Object.keys(ASSETS).length,
      kit_digest: digest.digest("hex"),
    });
  }
  return Object.freeze({
    snapshot,
    readCompanyFacts: () => read("KIT.md"),
    readAnswer(id, language) {
      if (!ANSWER_IDS.includes(id) || !["en", "ja"].includes(language)) throw new Error("application-kit answer invalid");
      return read(`answers/${id}.${language}.md`);
    },
    assetPath(alias) {
      const relative = ASSETS[alias];
      if (!relative) throw new Error("application-kit asset invalid");
      read(relative, true);
      return absolute(relative);
    },
  });
}

function dashboardValue(dashboard, key) {
  let current = dashboard;
  for (const segment of key.split(".")) {
    if (!current || typeof current !== "object" || Array.isArray(current) || !Object.hasOwn(current, segment)) {
      throw new Error(`application-kit dashboard fact missing: ${key}`);
    }
    current = current[segment];
  }
  if (!["string", "number", "boolean"].includes(typeof current) || (typeof current === "number" && !Number.isFinite(current))) {
    throw new Error(`application-kit dashboard fact invalid: ${key}`);
  }
  return String(current);
}

function injectDashboard(document, dashboard) {
  const resolved = String(document).replace(DASHBOARD_TOKEN, (_token, key) => dashboardValue(dashboard, key));
  if (/\{\{dashboard:[^}]+\}\}/.test(resolved)) throw new Error("application-kit dashboard token unresolved");
  return resolved;
}

function resolveFunderKitFields(input = {}) {
  const provider = input.provider;
  if (!provider || typeof provider.snapshot !== "function" || !Array.isArray(input.fields)) {
    throw new Error("application-kit field resolver invalid");
  }
  const snapshot = provider.snapshot();
  const values = {};
  const sources = {};
  for (const field of input.fields) {
    const name = String(field && field.name || "").trim();
    const source = String(field && field.value_source || "").trim();
    if (!/^[a-z][a-z0-9._-]{0,99}$/i.test(name) || Object.hasOwn(values, name)) {
      throw new Error("application-kit field invalid");
    }
    const answer = ANSWER_SOURCE.exec(source);
    const asset = ASSET_SOURCE.exec(source);
    if (source === "kit:company-facts") {
      values[name] = injectDashboard(provider.readCompanyFacts(), input.dashboard || {});
      sources[name] = "application-kit://KIT.md";
    } else if (answer && ANSWER_IDS.includes(answer[1])) {
      values[name] = injectDashboard(provider.readAnswer(answer[1], answer[2]), input.dashboard || {});
      sources[name] = `application-kit://answers/${answer[1]}.${answer[2]}.md`;
    } else if (asset && Object.hasOwn(ASSETS, asset[1])) {
      values[name] = provider.assetPath(asset[1]);
      sources[name] = `application-kit://${ASSETS[asset[1]]}`;
    } else {
      throw new Error("application-kit value source invalid");
    }
  }
  return Object.freeze({
    schema_version: 1,
    kit_digest: snapshot.kit_digest,
    values: Object.freeze(values),
    sources: Object.freeze(sources),
  });
}

module.exports = { ANSWER_IDS, createApplicationKitProvider, resolveFunderKitFields };
