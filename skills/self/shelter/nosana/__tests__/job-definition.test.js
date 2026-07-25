// node:test — job-definition: pure builder + structural validator for a schema-0.1 Nosana
// "container" job definition running one long-running exposed service.
import { test } from "node:test";
import assert from "node:assert/strict";
import { buildServiceJobDefinition, validateJobDefinition } from "../job-definition.mjs";

test("buildServiceJobDefinition produces a minimal valid schema-0.1 container job with expose", () => {
  const def = buildServiceJobDefinition({ image: "docker.io/library/nginx:alpine", exposePort: 80 });
  assert.equal(def.version, "0.1");
  assert.equal(def.type, "container");
  assert.equal(def.ops.length, 1);
  assert.equal(def.ops[0].type, "container/run");
  assert.equal(def.ops[0].id, "main");
  assert.equal(def.ops[0].args.image, "docker.io/library/nginx:alpine");
  assert.equal(def.ops[0].args.expose, 80);
  assert.equal(def.ops[0].args.gpu, true);
});

test("buildServiceJobDefinition honors cmd, env, gpu:false, and a custom id", () => {
  const def = buildServiceJobDefinition({
    image: "myimage:latest",
    exposePort: 8080,
    cmd: ["node", "server.js"],
    env: { PORT: "8080" },
    gpu: false,
    id: "svc",
  });
  assert.deepEqual(def.ops[0].args.cmd, ["node", "server.js"]);
  assert.deepEqual(def.ops[0].args.env, { PORT: "8080" });
  assert.equal(def.ops[0].args.gpu, false);
  assert.equal(def.ops[0].id, "svc");
});

test("buildServiceJobDefinition rejects a missing/empty image", () => {
  assert.throws(() => buildServiceJobDefinition({ exposePort: 80 }), /image is required/);
  assert.throws(() => buildServiceJobDefinition({ image: "", exposePort: 80 }), /image is required/);
});

test("buildServiceJobDefinition rejects an invalid exposePort", () => {
  assert.throws(() => buildServiceJobDefinition({ image: "x", exposePort: 0 }), /exposePort/);
  assert.throws(() => buildServiceJobDefinition({ image: "x", exposePort: 70000 }), /exposePort/);
  assert.throws(() => buildServiceJobDefinition({ image: "x", exposePort: 1.5 }), /exposePort/);
});

test("buildServiceJobDefinition rejects an id containing spaces", () => {
  assert.throws(() => buildServiceJobDefinition({ image: "x", exposePort: 80, id: "has space" }), /id must be/);
});

test("buildServiceJobDefinition rejects a malformed cmd or env", () => {
  assert.throws(() => buildServiceJobDefinition({ image: "x", exposePort: 80, cmd: 123 }), /cmd must be/);
  assert.throws(() => buildServiceJobDefinition({ image: "x", exposePort: 80, env: { a: 1 } }), /env must be/);
  assert.throws(() => buildServiceJobDefinition({ image: "x", exposePort: 80, env: ["a"] }), /env must be/);
});

test("validateJobDefinition accepts a definition built by buildServiceJobDefinition", () => {
  const def = buildServiceJobDefinition({ image: "nginx:alpine", exposePort: 80 });
  const result = validateJobDefinition(def);
  assert.deepEqual(result, { valid: true, errors: [] });
});

test("validateJobDefinition rejects a non-object input", () => {
  assert.equal(validateJobDefinition(null).valid, false);
  assert.equal(validateJobDefinition("nope").valid, false);
  assert.equal(validateJobDefinition([1, 2]).valid, false);
});

test("validateJobDefinition rejects the wrong top-level type", () => {
  const result = validateJobDefinition({ type: "vm", version: "0.1", ops: [] });
  assert.equal(result.valid, false);
  assert.ok(result.errors.some((e) => e.includes('type must be "container"')));
});

test("validateJobDefinition rejects an empty or missing ops array", () => {
  assert.equal(validateJobDefinition({ type: "container", version: "0.1", ops: [] }).valid, false);
  assert.equal(validateJobDefinition({ type: "container", version: "0.1" }).valid, false);
});

test("validateJobDefinition rejects duplicate op ids", () => {
  const def = {
    type: "container",
    version: "0.1",
    ops: [
      { type: "container/run", id: "a", args: { image: "x" } },
      { type: "container/run", id: "a", args: { image: "y" } },
    ],
  };
  const result = validateJobDefinition(def);
  assert.equal(result.valid, false);
  assert.ok(result.errors.some((e) => e.includes("duplicates")));
});

test("validateJobDefinition rejects a missing args.image", () => {
  const def = { type: "container", version: "0.1", ops: [{ type: "container/run", id: "a", args: {} }] };
  const result = validateJobDefinition(def);
  assert.equal(result.valid, false);
  assert.ok(result.errors.some((e) => e.includes("args.image is required")));
});

test("validateJobDefinition rejects an invalid expose value", () => {
  const def = {
    type: "container",
    version: "0.1",
    ops: [{ type: "container/run", id: "a", args: { image: "x", expose: -5 } }],
  };
  const result = validateJobDefinition(def);
  assert.equal(result.valid, false);
  assert.ok(result.errors.some((e) => e.includes("args.expose")));
});

test("validateJobDefinition accepts a valid port-range expose string", () => {
  const def = {
    type: "container",
    version: "0.1",
    ops: [{ type: "container/run", id: "a", args: { image: "x", expose: "8000-8010" } }],
  };
  assert.equal(validateJobDefinition(def).valid, true);
});

test("validateJobDefinition rejects an unknown key inside args", () => {
  const def = {
    type: "container",
    version: "0.1",
    ops: [{ type: "container/run", id: "a", args: { image: "x", bogus_key: 1 } }],
  };
  const result = validateJobDefinition(def);
  assert.equal(result.valid, false);
  assert.ok(result.errors.some((e) => e.includes('unknown key "bogus_key"')));
});
