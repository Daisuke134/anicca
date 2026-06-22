// VCSDD RED→GREEN: cook must use the MODEL's query when it provides one. The old bash
// `ARGS="${ANICCA_ARGS:-{}}"` mis-parses (the `{}` default inside `${...}` appends a stray `}`),
// so a real arg `{"query":"X"}` became `{"query":"X"}}` (invalid JSON) → fell to the hourly seed →
// the model's curiosity was ALWAYS discarded. Extract the resolver to a pure module + test it.
import { test } from "node:test";
import assert from "node:assert/strict";
import { resolveQuery, SEEDS } from "../resolve-query.mjs";

test("uses the model's query when ANICCA_ARGS provides one", () => {
  assert.equal(resolveQuery('{"query":"ZZZ DISTINCTIVE solana arb"}', 0), "ZZZ DISTINCTIVE solana arb");
});

test("trims whitespace-only query and falls back to a seed", () => {
  const q = resolveQuery('{"query":"   "}', 0);
  assert.ok(SEEDS.includes(q), `whitespace query should fall to a seed, got ${q}`);
});

test("no ANICCA_ARGS → rotating seed (deterministic by hour bucket)", () => {
  assert.equal(resolveQuery("", 0), SEEDS[0]);
  assert.equal(resolveQuery(undefined, 1), SEEDS[1 % SEEDS.length]);
});

test("empty object → seed", () => {
  assert.ok(SEEDS.includes(resolveQuery("{}", 2)));
});

test("INVALID json (the exact old-bug shape with a stray brace) → seed, never throws", () => {
  assert.ok(SEEDS.includes(resolveQuery('{"query":"X"}}', 3)));
});

test("seed rotates with the hour bucket (never re-searches the same thing forever)", () => {
  const a = resolveQuery("", 0), b = resolveQuery("", 1);
  assert.notEqual(a, b);
});
