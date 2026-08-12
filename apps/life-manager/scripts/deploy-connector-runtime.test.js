"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const test = require("node:test");

test("deploy entrypoint sources the owner-only token and requires both Connector capabilities", () => {
  const source = fs.readFileSync(path.join(__dirname, "deploy-connector-runtime.sh"), "utf8");
  assert.match(source, /connector-host-bridge\/token/);
  assert.match(source, /\.openclaw\/\.env/);
  assert.match(source, /GEMINI_API_KEY/);
  assert.match(source, /LM_CONNECTOR_PROFILE_PATH/);
  assert.match(source, /LM_LUMA_FORM_PROFILE_HOST_PATH/);
  assert.match(source, /job-search\/profile\.json/);
  assert.match(source, /compose\.connector\.yaml/);
  assert.match(source, /outbound\.event\.apply/);
  assert.match(source, /connector\.coverage\.refresh/);
  assert.match(source, /build["']? worker/);
  assert.match(source, /--force-recreate/);
  assert.match(source, /--wait/);
  assert.doesNotMatch(source, /[0-9a-f]{64}|GOG_KEYRING_PASSWORD|GOOGLE_API_KEY_DIRECTIONS|LIFE_HOME_ADDRESS/);
});

test("deploy entrypoint passes a token to compose without printing it", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "lm-connector-deploy-"));
  const home = path.join(root, "home");
  const bin = path.join(root, "bin");
  const tokenDir = path.join(home, ".local/state/life-manager/connector-host-bridge");
  const envDir = path.join(home, ".openclaw");
  const identityDir = path.join(home, ".config/anicca/job-search");
  fs.mkdirSync(tokenDir, { recursive: true, mode: 0o700 });
  fs.mkdirSync(envDir, { recursive: true, mode: 0o700 });
  fs.mkdirSync(identityDir, { recursive: true, mode: 0o700 });
  fs.mkdirSync(bin, { recursive: true });
  const token = "d".repeat(64);
  const tokenPath = path.join(tokenDir, "token");
  fs.writeFileSync(tokenPath, `${token}\n`, { mode: 0o600 });
  fs.chmodSync(tokenPath, 0o600);
  const gemini = "fixture-gemini-secret";
  fs.writeFileSync(path.join(envDir, ".env"), `GEMINI_API_KEY=${gemini}\n`, { mode: 0o600 });
  fs.writeFileSync(path.join(identityDir, "profile.json"), JSON.stringify({
    candidate: { phone: "+81 90 0000 0000" },
  }), { mode: 0o600 });
  const fakeDocker = path.join(bin, "docker");
  fs.writeFileSync(fakeDocker, `#!/bin/bash\nset -e\nif [[ -z "\${LM_CONNECTOR_BRIDGE_TOKEN:-}" || -z "\${GEMINI_API_KEY:-}" || -z "\${LM_CONNECTOR_PROFILE_PATH:-}" || ! -f "\${LM_LUMA_FORM_PROFILE_HOST_PATH:-}" ]]; then exit 9; fi\nif [[ "$*" == *"exec -T worker node"* ]]; then printf '{"ok":true,"capabilities":["runtime.noop","outbound.event.apply","connector.coverage.refresh"]}'; fi\n`, { mode: 0o700 });
  const result = spawnSync("/bin/bash", [path.join(__dirname, "deploy-connector-runtime.sh")], {
    cwd: path.resolve(__dirname, ".."),
    env: {
      ...process.env,
      HOME: home,
      LM_CONNECTOR_BRIDGE_TOKEN_FILE: tokenPath,
      LM_DOCKER_BIN: fakeDocker,
    },
    encoding: "utf8",
  });
  assert.equal(result.status, 0, result.stderr);
  assert.doesNotMatch(`${result.stdout}${result.stderr}`, new RegExp(token));
  assert.doesNotMatch(`${result.stdout}${result.stderr}`, new RegExp(gemini));
  assert.match(result.stdout, /Connector runtime deployed/);
  const formProfile = JSON.parse(fs.readFileSync(
    path.join(home, ".local/state/life-manager/private/connector-luma-form-profile.json"), "utf8",
  ));
  assert.equal(formProfile.phone, "+81 90 0000 0000");
  assert.deepEqual(formProfile.form_answers, {});
  assert.equal(fs.statSync(
    path.join(home, ".local/state/life-manager/private/connector-luma-form-profile.json"),
  ).mode & 0o777, 0o600);
});
