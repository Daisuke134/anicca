"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const { inferEventGoalSerendipity } = require("./event-goal-serendipity.js");
const { inferEventPreferenceRanking } = require("./event-preference-ranking.js");
const { isVerifiedConnectorProfile } = require("./connector-profile.js");

function unavailable() {
  throw new Error("Connector Luna judgment unavailable");
}

function absoluteDirectory(value) {
  const directory = path.resolve(String(value == null ? "" : value));
  if (!path.isAbsolute(directory) || directory === path.parse(directory).root) unavailable();
  return directory;
}

function containedFile(root, value) {
  const file = path.resolve(String(value == null ? "" : value));
  if (!file.startsWith(`${root}${path.sep}`) || file === root) unavailable();
  let stat;
  try { stat = fs.statSync(file); } catch { unavailable(); }
  if (!stat.isFile() || stat.size < 2 || stat.size > 1_000_000) unavailable();
  return file;
}

function runLocalAgentRunner(input = {}, deps = {}) {
  try {
    const prompt = String(input.prompt == null ? "" : input.prompt);
    const taskClass = input.taskClass == null ? "repeatable-agent" : String(input.taskClass);
    const schema = input.schema;
    const timeoutMs = Number(input.timeoutMs);
    const evidenceDir = absoluteDirectory(input.evidenceDir);
    const repoRoot = absoluteDirectory(input.repoRoot);
    const runnerPath = path.resolve(String(
      input.runnerPath || path.join(repoRoot, "runtime", "agent-runner", "agent_runner.py"),
    ));
    if (
      prompt.trim().length < 100 || prompt.length > 100_000
      || !schema || typeof schema !== "object" || Array.isArray(schema)
      || !["repeatable-agent", "browser-lane-agent"].includes(taskClass)
      || !Number.isSafeInteger(timeoutMs) || timeoutMs < 1_000 || timeoutMs > 900_000
    ) unavailable();
    const isRunnerFile = typeof deps.isRunnerFile === "function"
      ? deps.isRunnerFile
      : (file) => fs.statSync(file).isFile();
    if (!path.isAbsolute(runnerPath) || !isRunnerFile(runnerPath)) unavailable();
    fs.mkdirSync(evidenceDir, { mode: 0o700, recursive: true });
    fs.chmodSync(evidenceDir, 0o700);
    const schemaPath = path.join(evidenceDir, "schema.json");
    fs.writeFileSync(schemaPath, `${JSON.stringify(schema)}\n`, { encoding: "utf8", mode: 0o600, flag: "w" });
    const execute = typeof deps.spawnSync === "function" ? deps.spawnSync : spawnSync;
    const completed = execute("python3", [
      runnerPath,
      "--task-class", taskClass,
      "--prompt-stdin",
      "--schema", schemaPath,
      "--evidence-dir", evidenceDir,
      "--task-label", taskClass === "browser-lane-agent"
        ? "connector-event-application" : "connector-event-judgment",
      "--loop", "connector",
      "--workdir", repoRoot,
    ], {
      input: prompt,
      encoding: "utf8",
      timeout: timeoutMs + 5_000,
      maxBuffer: 1_000_000,
      env: { ...process.env },
    });
    if (!completed || completed.status !== 0) unavailable();
    let summary;
    try { summary = JSON.parse(String(completed.stdout || "").trim()); }
    catch { unavailable(); }
    if (
      !summary || summary.status !== "success"
      || summary.selected_provider !== "codex"
      || summary.selected_model !== "gpt-5.6-terra"
    ) unavailable();
    const resultPath = containedFile(evidenceDir, summary.result_path);
    let value;
    try { value = JSON.parse(fs.readFileSync(resultPath, "utf8")); }
    catch { unavailable(); }
    return Object.freeze({ summary: Object.freeze({
      status: summary.status,
      selected_provider: summary.selected_provider,
      selected_model: summary.selected_model,
    }), value });
  } catch {
    unavailable();
  }
}

async function runConnectorLunaJudgment(input = {}, deps = {}) {
  try {
    if (!input || typeof input !== "object" || Array.isArray(input)) unavailable();
    if (!isVerifiedConnectorProfile(input.profile)) unavailable();
    const runAgentRunner = typeof deps.runAgentRunner === "function"
      ? deps.runAgentRunner
      : (request) => runLocalAgentRunner(request, deps);
    const evidenceRoot = absoluteDirectory(input.evidenceDir);
    if (typeof deps.runAgentRunner !== "function") {
      fs.mkdirSync(evidenceRoot, { mode: 0o700, recursive: true });
      fs.chmodSync(evidenceRoot, 0o700);
    }
    const invokeLuna = async ({ prompt, schema, timeoutMs }, stage) => {
      const result = await runAgentRunner({
        prompt, schema, timeoutMs,
        evidenceDir: path.join(evidenceRoot, stage),
        repoRoot: input.repoRoot,
        runnerPath: input.runnerPath,
      });
      if (
        !result || !result.summary
        || result.summary.status !== "success"
        || result.summary.selected_provider !== "codex"
        || result.summary.selected_model !== "gpt-5.6-terra"
      ) unavailable();
      return result.value;
    };
    const preferenceRanking = input.preferenceRanking || await inferEventPreferenceRanking({
      dateInventory: input.dateInventory,
      date: input.date,
      preferences: input.profile.preferences,
    }, {
      generateDecision: (request) => invokeLuna(request, "preference"),
    });
    return await inferEventGoalSerendipity({
      dateInventory: input.dateInventory,
      preferenceRanking,
      goals: input.profile.goals,
    }, {
      generateDecision: (request) => invokeLuna(request, "goal"),
    });
  } catch {
    unavailable();
  }
}

module.exports = { runConnectorLunaJudgment, runLocalAgentRunner };
