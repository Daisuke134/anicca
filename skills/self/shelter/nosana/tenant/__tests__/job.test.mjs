// node:test — job.mjs: the tenant job definition builder + bootstrap script + raw URL builder
// (S7, zero-secret redesign — a single bundled artifact, no secrets, no npm install).
import { test } from "node:test";
import assert from "node:assert/strict";

import {
  buildRawBaseUrl,
  buildBundleUrl,
  buildTenantBootstrapScript,
  buildTenantJobDefinition,
  validateJobDefinition,
  TENANT_BUNDLE_FILE,
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

test("buildBundleUrl: appends the single bundle file path to the base URL", () => {
  const url = buildBundleUrl({ rawBaseUrl: "https://raw.githubusercontent.com/o/r/sha/skills/self/shelter/nosana" });
  assert.equal(url, `https://raw.githubusercontent.com/o/r/sha/skills/self/shelter/nosana/${TENANT_BUNDLE_FILE}`);
});

test("buildBundleUrl: requires rawBaseUrl", () => {
  assert.throws(() => buildBundleUrl({}), /rawBaseUrl is required/);
});

test("buildTenantBootstrapScript: deterministic constant, fetches exactly the ONE bundle URL via NOSANA_CODE_BUNDLE_URL, runs it, no npm install", () => {
  const script = buildTenantBootstrapScript();
  assert.equal(script, buildTenantBootstrapScript(), "must be a pure, deterministic constant");
  assert.ok(script.includes("NOSANA_CODE_BUNDLE_URL"), "must read the bundle URL from its own env, not a baked-in value");
  assert.ok(script.includes("node /tmp/entrypoint.bundle.mjs"), "must actually run the fetched bundle");
  assert.ok(!script.includes("npm install"), "the bundle is dependency-free — no npm install needed at runtime");
  assert.ok(!script.includes("curl"), "uses Node's global fetch, not curl — the base image needs no extra packages");
});

test("buildTenantBootstrapScript: never embeds a secret-shaped string (defense in depth — it is a fixed constant with zero interpolation of runtime values)", () => {
  const script = buildTenantBootstrapScript();
  assert.ok(!script.includes("NOSANA_TENANT_SECRET_KEY"), "the zero-secret redesign carries no tenant secret at all");
  assert.ok(!script.includes("NOSANA_STATE_GITHUB_TOKEN"), "the zero-secret redesign carries no github token at all");
});

test("buildTenantJobDefinition: produces a structurally valid job definition per ../job-definition.mjs's own validator", () => {
  const def = buildTenantJobDefinition({
    rawBaseUrl: "https://raw.githubusercontent.com/Daisuke134/life-manager/abc1234/skills/self/shelter/nosana",
    treasuryAddress: "F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T",
  });
  const validation = validateJobDefinition(def);
  assert.deepEqual(validation.errors, []);
  assert.equal(validation.valid, true);
});

test("buildTenantJobDefinition: has NO exposed port (a one-shot task, not a service) — see job.mjs's header for why", () => {
  const def = buildTenantJobDefinition({ rawBaseUrl: "https://raw.githubusercontent.com/o/r/sha/path", treasuryAddress: "TREASURY" });
  assert.equal(def.ops[0].args.expose, undefined);
});

test("buildTenantJobDefinition: injects ONLY NOSANA_CODE_BUNDLE_URL and NOSANA_TREASURY_ADDRESS — no secret env var of any kind", () => {
  const def = buildTenantJobDefinition({ rawBaseUrl: "https://raw.example/base", treasuryAddress: "TREASURY_ADDR" });
  const args = def.ops[0].args;
  assert.equal(args.image, DEFAULT_TENANT_IMAGE);
  assert.deepEqual(Object.keys(args.env).sort(), ["NOSANA_CODE_BUNDLE_URL", "NOSANA_TREASURY_ADDRESS"]);
  assert.equal(args.env.NOSANA_CODE_BUNDLE_URL, `https://raw.example/base/${TENANT_BUNDLE_FILE}`);
  assert.equal(args.env.NOSANA_TREASURY_ADDRESS, "TREASURY_ADDR");
});

test("buildTenantJobDefinition: fails closed on any missing required param", () => {
  assert.throws(() => buildTenantJobDefinition({ treasuryAddress: "T" }), /rawBaseUrl is required/);
  assert.throws(() => buildTenantJobDefinition({ rawBaseUrl: "u" }), /treasuryAddress is required/);
});

test("buildTenantJobDefinition: cmd is [sh, -c, script] — a single argv element, avoiding outer-shell quoting issues", () => {
  const def = buildTenantJobDefinition({ rawBaseUrl: "https://raw.example/base", treasuryAddress: "T" });
  const cmd = def.ops[0].args.cmd;
  assert.deepEqual(cmd.slice(0, 2), ["sh", "-c"]);
  assert.equal(cmd.length, 3);
  assert.equal(cmd[2], buildTenantBootstrapScript());
});
