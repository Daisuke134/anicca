// job.mjs (Mac-side ONLY) — builds the Nosana job definition that runs tenant/entrypoint.mjs
// inside a job container. Deliberately does NOT reuse ../job-definition.mjs's
// buildServiceJobDefinition: that function requires an exposePort and always shapes a
// long-running SERVICE (see its own file header's incident note — the exposed-HTTP-endpoint path
// has never once worked across two different nodes). This job needs no exposed port at all: it is
// a one-shot task that boots, restores state, proves itself, snapshots state, and exits — its
// evidence channel is stdout, read back via the jobs API's `jobResult.opStates[0]` diagnostics
// (verified live 2026-07-25; see tenant/README.md).
//
// buildTenantJobDefinition's OUTPUT is still checked against ../job-definition.mjs's
// validateJobDefinition (imported unchanged, zero edits to that file) — that function's structural
// checks (image required, op.args keys must be from its known-keys allowlist, etc.) are generic
// enough to apply to any container/run op, not just service ones.
//
// Deploys use "docker.io/library/node:20-alpine" (a public, standard, tiny base image) plus a
// fetched script, per the task's own preference: "prefer NOT publishing a custom image if a
// public base plus a fetched script gets there." The "fetched script" is TENANT_BUNDLE_RELATIVE_FILES
// below, retrieved via plain `fetch` from a PINNED commit on the public life-manager repo
// (raw.githubusercontent.com serves it unauthenticated — verified live 2026-07-25 that
// github.com/Daisuke134/life-manager is a public repo) — never "latest", so the job always runs
// exactly the code that was reviewed and pushed, never a moving target.

import { validateJobDefinition } from "../job-definition.mjs";

export const DEFAULT_TENANT_IMAGE = "docker.io/library/node:20-alpine";
export const DEFAULT_CODE_REPO = "Daisuke134/life-manager";
export const DEFAULT_RAW_HOST = "https://raw.githubusercontent.com";

// The fixed, small, self-contained file set tenant/entrypoint.mjs actually needs at runtime — see
// derive-address.mjs's header for why this list is deliberately short and why nothing outside
// tenant/ is on it.
export const TENANT_BUNDLE_RELATIVE_FILES = [
  "tenant/derive-address.mjs",
  "tenant/github-contents-store.mjs",
  "tenant/report-ledger.mjs",
  "tenant/proof.mjs",
  "tenant/entrypoint.mjs",
];

// Pinned exactly to this repo's own package.json versions (checked live 2026-07-25) so the
// in-job npm install reproduces the same dependency code this feature was tested against.
export const TENANT_NPM_DEPS = ["@solana/web3.js@1.98.4", "bs58@5.0.0", "tweetnacl@1.0.3"];

/**
 * Pure: the raw-content base URL for one commit of this repo's nosana skill directory.
 * @param {{repo?: string, commitSha: string, rawHost?: string}} opts
 * @returns {string}
 */
export function buildRawBaseUrl({ repo = DEFAULT_CODE_REPO, commitSha, rawHost = DEFAULT_RAW_HOST } = {}) {
  if (typeof commitSha !== "string" || !/^[0-9a-f]{7,40}$/i.test(commitSha)) {
    throw new Error(`buildRawBaseUrl: commitSha must be a hex git commit SHA, got ${JSON.stringify(commitSha)}`);
  }
  return `${rawHost}/${repo}/${commitSha}/skills/self/shelter/nosana`;
}

/**
 * Pure: the fixed bootstrap shell script every tenant job runs as its container/run `cmd`. Reads
 * NOSANA_CODE_RAW_BASE_URL from its own environment (set as a job env var by
 * buildTenantJobDefinition below) rather than having the URL baked into the script text itself, so
 * this string is a deterministic constant independent of which commit/repo it is pointed at —
 * easy to review once, byte-for-byte, and to unit-test as a fixed value.
 *
 * Uses Node's global `fetch` (stable in Node 20, the base image's runtime) instead of `curl` so
 * the base image needs no extra packages installed at all — just node+npm, which
 * docker.io/library/node:20-alpine already ships.
 *
 * @returns {string}
 */
export function buildTenantBootstrapScript() {
  const filesLiteral = JSON.stringify(TENANT_BUNDLE_RELATIVE_FILES);
  const depsArgs = TENANT_NPM_DEPS.join(" ");
  return [
    "set -e",
    "mkdir -p /tmp/app/tenant",
    "node --input-type=module -e '",
    `const files = ${filesLiteral};`,
    'const base = process.env.NOSANA_CODE_RAW_BASE_URL;',
    'if (!base) { throw new Error("NOSANA_CODE_RAW_BASE_URL is not set"); }',
    'const fs = await import("node:fs");',
    "for (const f of files) {",
    "  const res = await fetch(base + \"/\" + f);",
    '  if (!res.ok) { throw new Error("fetch failed: " + f + " " + res.status); }',
    "  const text = await res.text();",
    '  fs.writeFileSync("/tmp/app/" + f, text);',
    "}",
    'console.log("bootstrap: fetched " + files.length + " files from " + base);',
    "'",
    "cd /tmp/app",
    `npm install --no-audit --no-fund --silent ${depsArgs}`,
    "node tenant/entrypoint.mjs",
  ].join("\n");
}

/**
 * Pure: build the tenant job definition — a single container/run op, no exposed port, running
 * buildTenantBootstrapScript()'s cmd with the tenant secret + state-store token injected as env
 * vars. Throws on missing required params (mirrors ../job-definition.mjs's own style); does NOT
 * itself call validateJobDefinition — callers (bin/citizen-tenant-up) do that, exactly like
 * deploy.mjs already does for its own job definitions, so there is one place that decides
 * structural validity for every job definition this skill ever posts.
 *
 * @param {{image?: string, rawBaseUrl: string, tenantSecretBase58: string, githubToken: string,
 *          stateRepo?: string, extraEnv?: Record<string,string>, gpu?: boolean}} opts
 * @returns {object} job definition
 */
export function buildTenantJobDefinition({
  image = DEFAULT_TENANT_IMAGE,
  rawBaseUrl,
  tenantSecretBase58,
  githubToken,
  stateRepo,
  extraEnv = {},
  gpu = true,
} = {}) {
  for (const [key, value] of Object.entries({ rawBaseUrl, tenantSecretBase58, githubToken })) {
    if (typeof value !== "string" || value.length === 0) {
      throw new Error(`buildTenantJobDefinition: ${key} is required (non-empty string)`);
    }
  }
  const env = {
    NOSANA_CODE_RAW_BASE_URL: rawBaseUrl,
    NOSANA_TENANT_SECRET_KEY: tenantSecretBase58,
    NOSANA_STATE_GITHUB_TOKEN: githubToken,
    ...(stateRepo ? { NOSANA_STATE_REPO: stateRepo } : {}),
    ...extraEnv,
  };
  return {
    version: "0.1",
    type: "container",
    ops: [
      {
        type: "container/run",
        id: "main",
        args: {
          image,
          cmd: ["sh", "-c", buildTenantBootstrapScript()],
          env,
          gpu: Boolean(gpu),
        },
      },
    ],
  };
}

export { validateJobDefinition };
