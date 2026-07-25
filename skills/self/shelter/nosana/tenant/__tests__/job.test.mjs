// node:test — job.mjs: the tenant job definition builder + bootstrap script + raw URL builder.
import { test } from "node:test";
import assert from "node:assert/strict";

import {
  buildRawBaseUrl,
  buildTenantBootstrapScript,
  buildTenantJobDefinition,
  validateJobDefinition,
  TENANT_BUNDLE_RELATIVE_FILES,
  TENANT_NPM_DEPS,
  DEFAULT_TENANT_IMAGE,
} from "../job.mjs";

test("buildRawBaseUrl: builds the expected raw.githubusercontent.com URL for a commit", () => {
  const url = buildRawBaseUrl({ repo: "Daisuke134/life-manager", commitSha: "abc1234" });
  assert.equal(url, "https://raw.githubusercontent.com/Daisuke134/life-manager/abc1234/skills/self/shelter/nosana");
});

test("buildRawBaseUrl: rejects a non-hex/malformed commit SHA (never silently builds a bad URL)", () => {
  assert.throws(() => buildRawBaseUrl({ commitSha: "not a sha" }), /commitSha must be a hex git commit SHA/);
  assert.throws(() => buildRawBaseUrl({ commitSha: "" }), /commitSha must be a hex git commit SHA/);
  assert.throws(() => buildRawBaseUrl({ commitSha: undefined }), /commitSha must be a hex git commit SHA/);
});

test("buildRawBaseUrl: accepts both short and full 40-char SHAs", () => {
  assert.doesNotThrow(() => buildRawBaseUrl({ commitSha: "abc1234" }));
  assert.doesNotThrow(() => buildRawBaseUrl({ commitSha: "0123456789abcdef0123456789abcdef01234567" }));
});

test("buildTenantBootstrapScript: deterministic constant, fetches every TENANT_BUNDLE_RELATIVE_FILES entry, installs every TENANT_NPM_DEPS entry, runs the entrypoint", () => {
  const script = buildTenantBootstrapScript();
  assert.equal(script, buildTenantBootstrapScript(), "must be a pure, deterministic constant");
  for (const file of TENANT_BUNDLE_RELATIVE_FILES) {
    assert.ok(script.includes(file), `bootstrap script must reference ${file}`);
  }
  for (const dep of TENANT_NPM_DEPS) {
    assert.ok(script.includes(dep), `bootstrap script must npm-install ${dep}`);
  }
  assert.ok(script.includes("node tenant/entrypoint.mjs"), "must actually run the entrypoint after fetching+installing");
  assert.ok(script.includes("NOSANA_CODE_RAW_BASE_URL"), "must read the raw base URL from its own env, not a baked-in value");
  assert.ok(!script.includes("curl"), "uses Node's global fetch, not curl — the base image needs no extra packages");
});

test("buildTenantBootstrapScript: never embeds a secret-shaped string (defense in depth — it is a fixed constant with zero interpolation of runtime values)", () => {
  const script = buildTenantBootstrapScript();
  assert.ok(!script.includes("NOSANA_TENANT_SECRET_KEY="), "must reference the env var NAME only, never bake in a value");
  assert.ok(!script.includes("NOSANA_STATE_GITHUB_TOKEN="));
});

test("buildTenantJobDefinition: produces a structurally valid job definition per ../job-definition.mjs's own validator", () => {
  const def = buildTenantJobDefinition({
    rawBaseUrl: "https://raw.githubusercontent.com/Daisuke134/life-manager/abc1234/skills/self/shelter/nosana",
    tenantSecretBase58: "TENANT_SECRET",
    githubToken: "GH_TOKEN",
  });
  const validation = validateJobDefinition(def);
  assert.deepEqual(validation.errors, []);
  assert.equal(validation.valid, true);
});

test("buildTenantJobDefinition: has NO exposed port (a one-shot task, not a service) — see job.mjs's header for why", () => {
  const def = buildTenantJobDefinition({
    rawBaseUrl: "https://raw.githubusercontent.com/o/r/sha/path",
    tenantSecretBase58: "S",
    githubToken: "T",
  });
  assert.equal(def.ops[0].args.expose, undefined);
});

test("buildTenantJobDefinition: injects exactly the expected env vars, defaults image to node:20-alpine", () => {
  const def = buildTenantJobDefinition({
    rawBaseUrl: "https://raw.example/base",
    tenantSecretBase58: "TENANT_SECRET_VALUE",
    githubToken: "GH_TOKEN_VALUE",
    stateRepo: "owner/state-repo",
  });
  const args = def.ops[0].args;
  assert.equal(args.image, DEFAULT_TENANT_IMAGE);
  assert.equal(args.env.NOSANA_CODE_RAW_BASE_URL, "https://raw.example/base");
  assert.equal(args.env.NOSANA_TENANT_SECRET_KEY, "TENANT_SECRET_VALUE");
  assert.equal(args.env.NOSANA_STATE_GITHUB_TOKEN, "GH_TOKEN_VALUE");
  assert.equal(args.env.NOSANA_STATE_REPO, "owner/state-repo");
});

test("buildTenantJobDefinition: omits NOSANA_STATE_REPO entirely when not given (lets the tenant fall back to its own default)", () => {
  const def = buildTenantJobDefinition({ rawBaseUrl: "https://raw.example/base", tenantSecretBase58: "S", githubToken: "T" });
  assert.ok(!("NOSANA_STATE_REPO" in def.ops[0].args.env));
});

test("buildTenantJobDefinition: fails closed on any missing required param", () => {
  assert.throws(() => buildTenantJobDefinition({ tenantSecretBase58: "S", githubToken: "T" }), /rawBaseUrl is required/);
  assert.throws(() => buildTenantJobDefinition({ rawBaseUrl: "u", githubToken: "T" }), /tenantSecretBase58 is required/);
  assert.throws(() => buildTenantJobDefinition({ rawBaseUrl: "u", tenantSecretBase58: "S" }), /githubToken is required/);
});

test("buildTenantJobDefinition: cmd is [sh, -c, script] — a single argv element, avoiding outer-shell quoting issues", () => {
  const def = buildTenantJobDefinition({ rawBaseUrl: "https://raw.example/base", tenantSecretBase58: "S", githubToken: "T" });
  const cmd = def.ops[0].args.cmd;
  assert.deepEqual(cmd.slice(0, 2), ["sh", "-c"]);
  assert.equal(cmd.length, 3);
  assert.equal(cmd[2], buildTenantBootstrapScript());
});
