// job-definition.mjs — pure builder + validator for a Nosana schema-0.1 "container" job
// definition describing ONE long-running exposed service (the shape verified live 2026-07-25:
// version "0.1", type "container", ops[].type "container/run", args.image/args.cmd/args.expose/
// args.gpu; a job whose op sets `args.expose` becomes reachable at
// https://<node>.node.k8s.prd.nos.ci once a node picks it up).
//
// INCIDENT (2026-07-25): job FHAjMnM1q3p5c5qCeFRjZLYEo12FUBesFPW8zvG5heAC ran
// `{image: nginx:alpine, expose: 80, gpu: true}` — a bare-integer `expose`, no `health_checks`.
// The container itself ran perfectly healthy for the FULL 900s timeout (confirmed via the
// dashboard jobs API's `jobResult.opStates[0].diagnostics`: ExitCode 0, no Error, no OOMKilled,
// stopped only by "flow expired"/jobExpired at the natural timeout — never crashed). Yet the
// public URL served Nosana's own "Service Initializing" 503 placeholder for 28 consecutive polls
// over ~9 minutes and never once proxied real traffic. Root cause per Nosana's own docs
// (https://learn.nosana.com/deployments/jobs/job-definition/health-checks.html, whose worked
// example is this EXACT image+port: `nginx` on port 80): the service router needs an explicit
// `health_checks` entry to learn a service is ready to receive traffic; a bare-integer `expose`
// gives it no such signal, so the placeholder never flips even though the container is fine.
// (Bare-integer `expose` is still valid schema — Nosana's own production templates, e.g.
// nosana-ci/pipeline-templates' Gaia/OpenClaw/open-webui-ollama, use it successfully — but those
// are slow-loading model servers where "not yet listening" and "not yet health-checked" are
// indistinguishable from the outside; a near-instant static server like nginx exposes the gap.)
// GPU-runtime incompatibility (image has no CUDA payload) and slow image pull were both
// considered and REJECTED by the same diagnostics: the container did not crash on start and
// stayed alive/healthy for the whole duration, so neither `gpu: true` nor pull time explain the
// sustained external 503.
//
// Fix: `buildServiceJobDefinition` now accepts an optional `healthCheck` option that reshapes
// `args.expose` from a bare integer into the documented `ExposedPort[]` object form
// (`[{port, health_checks: [...]}]`), matching Nosana's own nginx health-check example.
//
// Second real finding, from a live `nosana job post` rejection while testing the fix above: the
// docs' own "Health Checks" example (omits `continuous`) does not match the real @nosana/cli
// schema, which rejects a health check with `continuous` missing
// (`health_checks[0].continuous: expected boolean, got undefined`). `continuous` is therefore
// always emitted below (default `true`, matching the docs' "Services" page vLLM example, which
// does include it) — never left optional.
//
// THIRD real finding (2026-07-25, resolved): every one of five prior live attempts — the
// bare-integer one above AND two later `health_checks`-shaped ones (jobs CMZ4B2jvqx63... and
// HaAxki9ZjZ5K...) — exposed port 80 and got 503 "Service Initializing" on every poll. A survey
// of all 58 job-definition*.json files across nosana-ci/pipeline-templates (every official vendor
// template) found the real port set in use is {7860, 8888, 8188, 8000, 9000, 7861, 11434, 8080,
// 9090, 23333, 3000, 18789, 8787} — port 80 is used by ZERO of them. Posting the SAME shape as the
// first failed attempt (bare-integer `expose`, no `health_checks`, `gpu: true`) but changing ONLY
// the port away from 80 — `docker.io/nginxinc/nginx-unprivileged:alpine` (the official,
// same-vendor, same-content nginx image whose only difference from `nginx:alpine` is that it
// listens on 8080 instead of 80, so the image swap is forced by the port change, not an
// independent variable) on port 8080 — produced job CUcMnkzWL8RdNDtGw7pdbqE8xVawuPf2dUigQ3wS5qDs,
// which served a REAL `HTTP/2 200` nginx welcome page (`server: nginx/1.31.3`) on 4 consecutive
// polls. Port 80 is therefore the confirmed differentiator, not `gpu`/`health_checks`/the
// container itself (all previously weakly-rejected, now further corroborated).
//
// This also surfaced a real, previously-undocumented gap: the URL this file's own earlier header
// comment gave (`https://<node>.node.k8s.prd.nos.ci`) is WRONG — that bare node-subdomain hits the
// node operator's own Express status API (confirmed live: it returns `{"...":"<node address>"}`
// JSON, not the job's container), not the job's exposed port. The real, frp-routed URL is a
// per-exposed-port HASH subdomain, reverse-engineered from @nosana/cli's own
// `node_modules/@nosana/sdk/dist/utils/expose.js` (`getExposeIdHash`) and confirmed correct
// because deriving it live is exactly what found the 200 above:
//   exposeId = base58(nacl.hash(utf8Bytes(`${opIndex}:${port}:${jobAddress}`))).slice(0, 44)
//   url      = `https://${exposeId}.node.k8s.prd.nos.ci`
// `computeExposeIdHash`/`computeExposeUrl` below implement this (pure, no I/O) so callers never
// have to re-derive it or guess at the wrong node-subdomain URL again.
//
// No I/O here — deploy.mjs owns writing the built object to a --file for the CLI and posting it
// on-chain. `validateJobDefinition` below is a lightweight structural check covering the fields
// this builder actually emits; it is NOT a reimplementation of @nosana/sdk's full internal zod
// schema (confirmed present only inside the globally-installed @nosana/cli's own node_modules,
// not a dependency of this project) — deploy.mjs additionally shells out to the real
// `nosana job validate` as an authoritative, non-unit-testable second check before any post.

import bs58 from "bs58";
import nacl from "tweetnacl";

// The frp tunnel domain for exposed services on mainnet — same constant @nosana/cli resolves from
// its own `.env.prd`'s `FRP_SERVER_ADDRESS` (devnet's is `node.k8s.dev.nos.ci`, unused here since
// deploy.mjs is mainnet-only).
export const FRP_SERVER_ADDR_MAINNET = "node.k8s.prd.nos.ci";

const KNOWN_RUN_ARGS_KEYS = new Set([
  "image",
  "aliases",
  "cmd",
  "volumes",
  "expose",
  "private",
  "gpu",
  "work_dir",
  "output",
  "entrypoint",
  "env",
  "restart_policy",
  "required_vram",
  "resources",
  "authentication",
  "trusted_execution_env",
]);

function isNonEmptyString(v) {
  return typeof v === "string" && v.length > 0;
}

function isStringOrStringArray(v) {
  return typeof v === "string" || (Array.isArray(v) && v.every((x) => typeof x === "string"));
}

function isValidExposePort(v) {
  return Number.isInteger(v) && v > 0 && v <= 65535;
}

const KNOWN_HEALTH_CHECK_TYPES = new Set(["http"]); // the only type Nosana's docs document

function isValidHealthCheckShape(hc) {
  if (!hc || typeof hc !== "object" || Array.isArray(hc)) return false;
  if (!KNOWN_HEALTH_CHECK_TYPES.has(hc.type)) return false;
  if (!isNonEmptyString(hc.path)) return false;
  if (hc.method !== undefined && !isNonEmptyString(hc.method)) return false;
  if (hc.expected_status !== undefined && !Number.isInteger(hc.expected_status)) return false;
  // `continuous` is REQUIRED by the real @nosana/cli schema, not merely optional as Nosana's own
  // "Health Checks" docs page example implies (that example omits it). Verified live 2026-07-25:
  // `nosana job post` rejected a health check with `continuous` omitted with
  // `$input.ops[0].args.expose[0].health_checks[0].continuous: expected boolean, got undefined`
  // — the docs example is incomplete; the "Services" doc page's own working vLLM template example
  // does include `"continuous": true`, which is the shape this builder now always emits.
  if (typeof hc.continuous !== "boolean") return false;
  return true;
}

/**
 * Pure: build a minimal, valid schema-0.1 "container" job definition running a single
 * `container/run` op that exposes one port (a long-running service job).
 *
 * `healthCheck`, when given, reshapes `args.expose` from a bare port number into the documented
 * `ExposedPort[]` object form (`[{port, health_checks: [...]}]`) — see the file header incident
 * note: without this, Nosana's service router has no signal to flip its "Service Initializing"
 * placeholder to real traffic, even when the container itself is running fine.
 *
 * @param {{image: string, exposePort: number, cmd?: string|string[], env?: Record<string,string>, gpu?: boolean, id?: string, healthCheck?: {path: string, method?: string, expectedStatus?: number, type?: string, continuous?: boolean}}} opts
 * @returns {object} job definition
 */
export function buildServiceJobDefinition({
  image,
  exposePort,
  cmd,
  env,
  gpu = true,
  id = "main",
  healthCheck,
} = {}) {
  if (!isNonEmptyString(image)) {
    throw new Error("buildServiceJobDefinition: image is required (non-empty string)");
  }
  if (!isValidExposePort(exposePort)) {
    throw new Error("buildServiceJobDefinition: exposePort must be an integer in 1..65535");
  }
  if (!isNonEmptyString(id) || id.includes(" ")) {
    throw new Error("buildServiceJobDefinition: id must be a non-empty string with no spaces");
  }
  if (cmd !== undefined && !isStringOrStringArray(cmd)) {
    throw new Error("buildServiceJobDefinition: cmd must be a string or string[]");
  }
  if (
    env !== undefined &&
    (typeof env !== "object" || env === null || Array.isArray(env) || Object.values(env).some((v) => typeof v !== "string"))
  ) {
    throw new Error("buildServiceJobDefinition: env must be a flat object of string values");
  }

  let expose = exposePort;
  if (healthCheck !== undefined) {
    if (!healthCheck || typeof healthCheck !== "object" || Array.isArray(healthCheck)) {
      throw new Error("buildServiceJobDefinition: healthCheck must be an object");
    }
    if (!isNonEmptyString(healthCheck.path)) {
      throw new Error("buildServiceJobDefinition: healthCheck.path is required (non-empty string)");
    }
    const hc = {
      type: healthCheck.type || "http",
      path: healthCheck.path,
      method: healthCheck.method || "GET",
      expected_status: healthCheck.expectedStatus ?? 200,
      // Always present (never omitted) — see isValidHealthCheckShape's comment: the real
      // @nosana/cli schema requires this field, confirmed via a live `nosana job post` rejection.
      continuous: healthCheck.continuous ?? true,
    };
    if (!isValidHealthCheckShape(hc)) {
      throw new Error("buildServiceJobDefinition: healthCheck produced an invalid health check shape");
    }
    expose = [{ port: exposePort, health_checks: [hc] }];
  }

  const args = { image, expose, gpu: Boolean(gpu) };
  if (cmd !== undefined) args.cmd = cmd;
  if (env !== undefined) args.env = env;

  return {
    version: "0.1",
    type: "container",
    ops: [
      {
        type: "container/run",
        id,
        args,
      },
    ],
  };
}

/**
 * Pure: lightweight structural validation of a job definition. Returns {valid, errors} rather
 * than throwing so callers can log every problem found, not just the first.
 */
export function validateJobDefinition(def) {
  const errors = [];

  if (!def || typeof def !== "object" || Array.isArray(def)) {
    return { valid: false, errors: ["job definition must be an object"] };
  }
  if (def.version !== undefined && typeof def.version !== "string") {
    errors.push("version must be a string");
  }
  if (def.type !== "container") {
    errors.push('type must be "container"');
  }
  if (!Array.isArray(def.ops) || def.ops.length === 0) {
    errors.push("ops must be a non-empty array");
    return { valid: errors.length === 0, errors };
  }

  const seenIds = new Set();
  def.ops.forEach((op, index) => {
    const where = `ops[${index}]`;
    if (!op || typeof op !== "object") {
      errors.push(`${where} must be an object`);
      return;
    }
    if (op.type !== "container/run" && op.type !== "container/create-volume") {
      errors.push(`${where}.type must be "container/run" or "container/create-volume"`);
    }
    if (!isNonEmptyString(op.id) || op.id.includes(" ")) {
      errors.push(`${where}.id must be a non-empty string with no spaces`);
    } else if (seenIds.has(op.id)) {
      errors.push(`${where}.id "${op.id}" duplicates an earlier op id (ids must be unique)`);
    } else {
      seenIds.add(op.id);
    }
    if (!op.args || typeof op.args !== "object" || Array.isArray(op.args)) {
      errors.push(`${where}.args must be an object`);
      return;
    }
    if (!isNonEmptyString(op.args.image)) {
      errors.push(`${where}.args.image is required (non-empty string)`);
    }
    if (op.args.cmd !== undefined && !isStringOrStringArray(op.args.cmd)) {
      errors.push(`${where}.args.cmd must be a string or string[]`);
    }
    if (op.args.expose !== undefined) {
      const expose = op.args.expose;
      const validNumber = isValidExposePort(expose);
      const validRangeString = typeof expose === "string" && /^[0-9]+-[0-9]+$/.test(expose);
      const validNumberArray = Array.isArray(expose) && expose.length > 0 && expose.every((p) => isValidExposePort(p));
      const validObjectArray =
        Array.isArray(expose) &&
        expose.length > 0 &&
        expose.every(
          (p) =>
            p &&
            typeof p === "object" &&
            !Array.isArray(p) &&
            isValidExposePort(p.port) &&
            (p.health_checks === undefined ||
              (Array.isArray(p.health_checks) && p.health_checks.length > 0 && p.health_checks.every(isValidHealthCheckShape))),
        );
      if (!validNumber && !validRangeString && !validNumberArray && !validObjectArray) {
        errors.push(
          `${where}.args.expose must be a port number, a "start-end" range string, an array of port numbers, or an array of {port, health_checks} objects`,
        );
      }
    }
    if (op.args.gpu !== undefined && typeof op.args.gpu !== "boolean") {
      errors.push(`${where}.args.gpu must be a boolean`);
    }
    for (const key of Object.keys(op.args)) {
      if (!KNOWN_RUN_ARGS_KEYS.has(key)) {
        errors.push(`${where}.args has unknown key "${key}"`);
      }
    }
  });

  return { valid: errors.length === 0, errors };
}

// Port 80 has zero occurrences across all 58 real job-definition*.json files in every official
// nosana-ci/pipeline-templates template (verified live 2026-07-25 via the GitHub API — the real
// port set in use is {7860, 8888, 8188, 8000, 9000, 7861, 11434, 8080, 9090, 23333, 3000, 18789,
// 8787}), and every one of five real posted jobs that exposed port 80 (bare-integer AND
// health_checks-shaped) got a 503 "Service Initializing" placeholder for the job's entire
// lifetime. This is advisory, not a structural validation error (validateJobDefinition above
// intentionally stays a schema check, not a business-rule gate) — a caller who has independently
// verified a working port-80 configuration should not be structurally blocked from using it.
export function isDiscouragedExposePort(port) {
  return port === 80;
}

/**
 * Pure: scan a job definition's ops for concrete exposed ports, returning `{opIndex, opId, port}`
 * for each one — the exact `(opIndex, port)` pair `computeExposeIdHash` needs. Handles every
 * `args.expose` shape `validateJobDefinition` accepts (bare number, number array, ExposedPort[]
 * object array); a `"start-end"` range string has no single concrete port and is skipped, since
 * there is no one port to compute a hash for.
 *
 * @param {object} jobDefinition
 * @returns {Array<{opIndex: number, opId: string, port: number}>}
 */
export function extractExposedPorts(jobDefinition) {
  if (!jobDefinition || !Array.isArray(jobDefinition.ops)) return [];
  const result = [];
  jobDefinition.ops.forEach((op, opIndex) => {
    const expose = op && op.args && op.args.expose;
    if (expose === undefined) return;
    const opId = (op && op.id) || String(opIndex);
    if (isValidExposePort(expose)) {
      result.push({ opIndex, opId, port: expose });
    } else if (Array.isArray(expose)) {
      for (const entry of expose) {
        if (isValidExposePort(entry)) {
          result.push({ opIndex, opId, port: entry });
        } else if (entry && typeof entry === "object" && isValidExposePort(entry.port)) {
          result.push({ opIndex, opId, port: entry.port });
        }
      }
    }
    // Range strings (e.g. "8000-8010") have no single concrete port — deliberately skipped.
  });
  return result;
}

/**
 * Pure: reverse-engineered from @nosana/cli's own `node_modules/@nosana/sdk/dist/utils/expose.js`
 * (`getExposeIdHash`/`createHash`) — the ONLY correct way to derive the public frp URL for a
 * given exposed port of a posted job. See the file header's THIRD incident note: this file's own
 * earlier header comment claimed the URL was `https://<node>.node.k8s.prd.nos.ci`, which is WRONG
 * (that bare node-subdomain hits the node operator's own status API, not the job's container) —
 * discovering that mistake, and this correct derivation, is what let the 2026-07-25 port-80 test
 * actually observe its real HTTP 200 instead of guessing at the wrong host. Verified against a
 * real posted job (CUcMnkzWL8RdNDtGw7pdbqE8xVawuPf2dUigQ3wS5qDs, opIndex 0, port 8080): this
 * function produces exactly `wpjZ4FQEeQom3y2PdYWTLwYMpWXw7ddmMi5AeNrqy81r`, and
 * `https://wpjZ4FQEeQom3y2PdYWTLwYMpWXw7ddmMi5AeNrqy81r.node.k8s.prd.nos.ci` really did serve the
 * job's nginx container (`HTTP/2 200`, `server: nginx/1.31.3`).
 *
 * @param {{jobAddress: string, opIndex?: number, port: number}} opts
 * @returns {string} the 44-character base58 expose-id hash (the URL's subdomain label)
 */
export function computeExposeIdHash({ jobAddress, opIndex = 0, port }) {
  if (!isNonEmptyString(jobAddress)) {
    throw new Error("computeExposeIdHash: jobAddress is required (non-empty string)");
  }
  if (!Number.isInteger(opIndex) || opIndex < 0) {
    throw new Error("computeExposeIdHash: opIndex must be a non-negative integer");
  }
  if (!isValidExposePort(port)) {
    throw new Error("computeExposeIdHash: port must be an integer in 1..65535");
  }
  // Exact field order/format @nosana/sdk hashes: `${opIndex}:${port}:${jobAddress}`.
  const inputString = `${opIndex}:${port}:${jobAddress}`;
  const hashBytes = nacl.hash(new TextEncoder().encode(inputString));
  return bs58.encode(hashBytes).slice(0, 44);
}

/**
 * Pure: `computeExposeIdHash` plus the frp domain, giving the full public URL a caller can poll
 * to check whether a job's exposed port is actually serving traffic.
 *
 * @param {{jobAddress: string, opIndex?: number, port: number, frpServerAddr?: string}} opts
 * @returns {string} e.g. "https://wpjZ4FQEeQom3y2PdYWTLwYMpWXw7ddmMi5AeNrqy81r.node.k8s.prd.nos.ci"
 */
export function computeExposeUrl({ jobAddress, opIndex = 0, port, frpServerAddr = FRP_SERVER_ADDR_MAINNET }) {
  const exposeId = computeExposeIdHash({ jobAddress, opIndex, port });
  return `https://${exposeId}.${frpServerAddr}`;
}
