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
// No I/O here — deploy.mjs owns writing the built object to a --file for the CLI and posting it
// on-chain. `validateJobDefinition` below is a lightweight structural check covering the fields
// this builder actually emits; it is NOT a reimplementation of @nosana/sdk's full internal zod
// schema (confirmed present only inside the globally-installed @nosana/cli's own node_modules,
// not a dependency of this project) — deploy.mjs additionally shells out to the real
// `nosana job validate` as an authoritative, non-unit-testable second check before any post.

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
