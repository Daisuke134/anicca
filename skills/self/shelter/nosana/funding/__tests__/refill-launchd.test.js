import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../../../..");
const runnerPath = path.join(repoRoot, "bin", "citizen-refill-launchd");
const installerPath = path.join(repoRoot, "bin", "install-citizen-refill-launchd");
const templatePath = path.join(repoRoot, "launchd", "ai.anicca.citizen-refill.plist.template");

test("the scheduled refill runner loads the managed environment and executes the real live rail", () => {
  const runner = fs.readFileSync(runnerPath, "utf8");
  assert.match(runner, /source "\$HOME\/\.openclaw\/\.env"/);
  assert.match(runner, /ANICCA_HOME=.*\.blockrun/);
  assert.match(runner, /exec \/opt\/homebrew\/bin\/node "\$REPO_ROOT\/bin\/citizen-refill" --live/);
  assert.doesNotMatch(runner, /--dry/);
});

test("the launchd template runs hourly, at login, with bounded logs", () => {
  const template = fs.readFileSync(templatePath, "utf8");
  assert.match(template, /<string>ai\.anicca\.citizen-refill<\/string>/);
  assert.match(template, /<key>RunAtLoad<\/key>\s*<true\/>/);
  assert.match(template, /<key>StartInterval<\/key>\s*<integer>3600<\/integer>/);
  assert.match(template, /__REPO_ROOT__\/bin\/citizen-refill-launchd/);
  assert.match(template, /__HOME__\/\.anicca\/logs\/citizen-refill\.out\.log/);
  assert.match(template, /__HOME__\/\.anicca\/logs\/citizen-refill\.err\.log/);
});

test("the installer renders absolute paths and loads the exact launchd label", () => {
  const installer = fs.readFileSync(installerPath, "utf8");
  assert.match(installer, /replaceAll\("__HOME__"/);
  assert.match(installer, /replaceAll\("__REPO_ROOT__"/);
  assert.match(installer, /launchctl", \["bootstrap", `gui\/\$\{uid\}`/);
  assert.match(installer, /launchctl", \["kickstart", "-k", `gui\/\$\{uid\}\/\$\{LABEL\}`/);
});
