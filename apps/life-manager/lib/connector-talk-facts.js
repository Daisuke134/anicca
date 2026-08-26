"use strict";

const fs = require("node:fs");
const path = require("node:path");

const REF = /^evidence:\/\/connector\/source\/[a-z0-9._-]{2,100}$/;
const UNSAFE = /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|\b(?:password|cookie|api[_ -]?key|secret|token)\b|\{\{|\}\}/i;

function unavailable() { throw new Error("connector talk facts unavailable"); }

function readConnectorTalkFacts(file) {
  const target = path.resolve(String(file || ""));
  if (!path.isAbsolute(target) || target === path.parse(target).root) unavailable();
  let value;
  try {
    const stat = fs.statSync(target);
    if (!stat.isFile() || stat.size < 2 || stat.size > 16_384) unavailable();
    value = JSON.parse(fs.readFileSync(target, "utf8"));
  } catch { unavailable(); }
  if (!value || typeof value !== "object" || Array.isArray(value)
    || Object.keys(value).sort().join(",") !== "facts,schema_version" || value.schema_version !== 1
    || !Array.isArray(value.facts) || value.facts.length < 1 || value.facts.length > 20) unavailable();
  const facts = value.facts.map((row) => {
    if (!row || typeof row !== "object" || Array.isArray(row)
      || Object.keys(row).sort().join(",") !== "evidence_ref,fact"
      || !REF.test(String(row.evidence_ref || ""))) unavailable();
    const fact = String(row.fact || "").replace(/\s+/g, " ").trim();
    if (!fact || fact.length > 500 || UNSAFE.test(fact)) unavailable();
    return Object.freeze({ evidence_ref: row.evidence_ref, fact });
  });
  if (new Set(facts.map((row) => row.evidence_ref)).size !== facts.length) unavailable();
  return Object.freeze(facts);
}

module.exports = { readConnectorTalkFacts };
