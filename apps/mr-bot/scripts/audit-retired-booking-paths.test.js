"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const repo = path.resolve(__dirname, "../../..");
const skill = path.join(repo, "skills/anicca-booking/SKILL.md");
const runner = path.join(repo, "skills/anicca-booking/scripts/run.sh");
const proposer = path.join(repo, "skills/anicca-booking/scripts/propose.py");

test("retired booking runner fails closed before reading credentials or using network", () => {
  const result = spawnSync("bash", [runner], {
    cwd: "/",
    env: { PATH: process.env.PATH || "/usr/bin:/bin" },
    encoding: "utf8",
  });
  assert.equal(result.status, 78);
  assert.match(result.stderr, /retired/i);
  assert.doesNotMatch(`${result.stdout}\n${result.stderr}`, /token|password|api.?key/i);
});

test("retired skill contains no executable connpass browser or crawl recipe", () => {
  const text = fs.readFileSync(skill, "utf8");
  assert.match(text, /廃止済み/);
  assert.doesNotMatch(text, /connpass\.com\/event|camofox|firecrawl/i);
  assert.doesNotMatch(fs.readFileSync(proposer, "utf8"), /connpass\.com/i);
});
