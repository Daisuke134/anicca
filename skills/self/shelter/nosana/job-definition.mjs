// job-definition.mjs — pure builder + validator for a Nosana schema-0.1 "container" job
// definition describing ONE long-running exposed service (the shape verified live 2026-07-25:
// version "0.1", type "container", ops[].type "container/run", args.image/args.cmd/args.expose/
// args.gpu; a job whose op sets `args.expose` becomes reachable at
// https://<node>.node.k8s.prd.nos.ci once a node picks it up).
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

/**
 * Pure: build a minimal, valid schema-0.1 "container" job definition running a single
 * `container/run` op that exposes one port (a long-running service job).
 *
 * @param {{image: string, exposePort: number, cmd?: string|string[], env?: Record<string,string>, gpu?: boolean, id?: string}} opts
 * @returns {object} job definition
 */
export function buildServiceJobDefinition({
  image,
  exposePort,
  cmd,
  env,
  gpu = true,
  id = "main",
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

  const args = { image, expose: exposePort, gpu: Boolean(gpu) };
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
      if (!validNumber && !validRangeString) {
        errors.push(`${where}.args.expose must be a valid port number or "start-end" range string`);
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
