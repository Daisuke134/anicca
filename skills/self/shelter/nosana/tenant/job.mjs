// job.mjs (Mac-side ONLY) — builds the Nosana job definition that runs the bundled
// tenant/entrypoint.bundle.mjs inside a job container. Deliberately does NOT reuse
// ../job-definition.mjs's buildServiceJobDefinition: that function requires an exposePort and
// always shapes a long-running SERVICE (see its own file header's incident note — the
// exposed-HTTP-endpoint path has never once worked across two different nodes). This job needs no
// exposed port at all: it is a one-shot task that boots, restores state, proves itself, and
// exits — its evidence channel is stdout, read back via the jobs API's `jobResult.opStates[0]`
// diagnostics (verified live 2026-07-25; see tenant/README.md).
//
// SECOND PASS (zero-secret redesign): the job definition carries NO secret of any kind.
// tenant/README.md's "A finding that changes the design" section documents why this changed —
// job definitions (this ENTIRE object, verbatim) are published PERMANENTLY to public IPFS the
// moment a non-confidential job posts, not merely readable by the node operator. The only env var
// this job carries now is NOSANA_TREASURY_ADDRESS — a public Solana address, not a secret; only a
// private key would need protecting, and none is present anywhere here.
//
// buildTenantJobDefinition's OUTPUT is still checked against ../job-definition.mjs's
// validateJobDefinition (imported unchanged, zero edits to that file).
//
// Deploys use "docker.io/library/node:20-alpine" (a public, standard, tiny base image) plus a
// fetched script, per the task's own preference: "prefer NOT publishing a custom image if a
// public base plus a fetched script gets there." The "fetched script" is now exactly ONE file —
// tenant/entrypoint.bundle.mjs, an esbuild-bundled artifact (tenant/build-bundle.mjs) that
// inlines @solana/web3.js, bs58, and tweetnacl, plus this repo's own ./proof.mjs,
// ./public-job-state.mjs, ../renew/survival-drive.mjs, and ../market.mjs — so the container needs
// no `npm install` at all (this repo has never verified npm-registry egress from a Nosana node;
// the ONLY network calls the container makes are the ones this feature already needs regardless:
// one fetch for its own code, then Solana RPC + the Nosana jobs API). Retrieved via plain `fetch`
// from a PINNED commit on the public life-manager repo (raw.githubusercontent.com serves it
// unauthenticated — verified live 2026-07-25 that github.com/Daisuke134/life-manager is public) —
// never "latest", so the job always runs exactly the code that was reviewed and pushed.

import { validateJobDefinition } from "../job-definition.mjs";

export const DEFAULT_TENANT_IMAGE = "docker.io/library/node:20-alpine";
export const DEFAULT_CODE_REPO = "Daisuke134/life-manager";
export const DEFAULT_RAW_HOST = "https://raw.githubusercontent.com";

// The single bundled artifact the container fetches and runs. See tenant/build-bundle.mjs.
export const TENANT_BUNDLE_FILE = "tenant/entrypoint.bundle.mjs";

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
 * Pure: the raw URL for the bundled entrypoint artifact at a given base URL.
 * @param {{rawBaseUrl: string}} opts
 * @returns {string}
 */
export function buildBundleUrl({ rawBaseUrl }) {
  if (typeof rawBaseUrl !== "string" || rawBaseUrl.length === 0) {
    throw new Error("buildBundleUrl: rawBaseUrl is required");
  }
  return `${rawBaseUrl}/${TENANT_BUNDLE_FILE}`;
}

/**
 * Pure: the fixed bootstrap shell script every tenant job runs as its container/run `cmd`. Reads
 * NOSANA_CODE_BUNDLE_URL from its own environment (set as a job env var by
 * buildTenantJobDefinition below) rather than having the URL baked into the script text itself, so
 * this string is a deterministic constant independent of which commit/repo it is pointed at —
 * easy to review once, byte-for-byte, and to unit-test as a fixed value.
 *
 * Fetches exactly ONE file and runs it — no directory structure, no `npm install`, no dependency
 * list. Uses Node's global `fetch` (stable in Node 20, the base image's runtime).
 *
 * @returns {string}
 */
export function buildTenantBootstrapScript() {
  return [
    "set -e",
    "node --input-type=module -e '",
    'const url = process.env.NOSANA_CODE_BUNDLE_URL;',
    'if (!url) { throw new Error("NOSANA_CODE_BUNDLE_URL is not set"); }',
    "const res = await fetch(url);",
    'if (!res.ok) { throw new Error("fetch failed: " + url + " " + res.status); }',
    "const text = await res.text();",
    'const fs = await import("node:fs");',
    'fs.writeFileSync("/tmp/entrypoint.bundle.mjs", text);',
    'console.log("bootstrap: fetched entrypoint bundle from " + url);',
    "'",
    "node /tmp/entrypoint.bundle.mjs",
  ].join("\n");
}

/**
 * Pure: build the tenant job definition — a single container/run op, no exposed port, NO SECRET
 * of any kind (only NOSANA_TREASURY_ADDRESS, a public key). Throws on missing required params
 * (mirrors ../job-definition.mjs's own style); does NOT itself call validateJobDefinition —
 * callers (bin/citizen-tenant-up) do that, exactly like deploy.mjs already does for its own job
 * definitions, so there is one place that decides structural validity for every job definition
 * this skill ever posts.
 *
 * @param {{image?: string, rawBaseUrl: string, treasuryAddress: string,
 *          extraEnv?: Record<string,string>, gpu?: boolean}} opts
 * @returns {object} job definition
 */
export function buildTenantJobDefinition({
  image = DEFAULT_TENANT_IMAGE,
  rawBaseUrl,
  treasuryAddress,
  extraEnv = {},
  gpu = true,
} = {}) {
  for (const [key, value] of Object.entries({ rawBaseUrl, treasuryAddress })) {
    if (typeof value !== "string" || value.length === 0) {
      throw new Error(`buildTenantJobDefinition: ${key} is required (non-empty string)`);
    }
  }
  const env = {
    NOSANA_CODE_BUNDLE_URL: buildBundleUrl({ rawBaseUrl }),
    NOSANA_TREASURY_ADDRESS: treasuryAddress,
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
