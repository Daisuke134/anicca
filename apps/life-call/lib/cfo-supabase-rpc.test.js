"use strict";

const assert = require("node:assert/strict");
const { test } = require("node:test");
const { createCfoSupabaseRpc } = require("./cfo-supabase-rpc.js");

const URL = "https://project.supabase.co";
const KEY = "service-role-secret";

function response(body = {}, status = 200) { return { ok: status >= 200 && status < 300, status, json: async () => body }; }
function throwsWithMessage(fn, pattern) { assert.throws(fn, error => { assert.match(error.message, pattern); return true; }); }
async function rejectsWithMessage(call, pattern) { await assert.rejects(call, error => { assert.match(error.message, pattern); return true; }); }

async function replayThroughHostileJsonBoundary(rpc, parentError) {
  const config = {
    base: URL,
    supaKey: KEY,
    fetchImpl: async () => ({
      ok: true,
      status: 200,
      json: async () => { throw parentError; },
    }),
  };
  let replayed;
  try { await rpc.postRpc(config, "hostile_json", {}); } catch (error) { replayed = error; }
  assert.notEqual(replayed, parentError);
  assert.equal(replayed.message, "operation_failed:invalid_json");
  return replayed;
}

test("fail() tags errors with the given prefix; internal() recognizes only its own instance's tags", () => {
  const a = createCfoSupabaseRpc("prefix_a_failed:");
  const b = createCfoSupabaseRpc("prefix_b_failed:");
  let errorA;
  a.runOperation(() => {
    try { a.fail("reason"); } catch (error) { errorA = error; }
    assert.equal(a.internal(errorA), true, "an instance recognizes its own tagged error");
    assert.equal(b.internal(errorA), false, "a different instance must not recognize another instance's tagged error");
  });
  assert.equal(errorA.message, "prefix_a_failed:reason");
  assert.equal(a.internal(new Error("plain")), false);
  assert.equal(a.internal(null), false);
  assert.equal(a.internal("not-an-object"), false);
});

test("internal provenance survives same-operation propagation but not a later operation", () => {
  const rpc = createCfoSupabaseRpc("operation_failed:");
  const allowed = new Set(["value"]);
  let propagated;
  rpc.runOperation(() => {
    try {
      try { rpc.exact({ value: 1 }, allowed); rpc.fail("same_operation"); } catch (error) {
        assert.equal(rpc.internal(error), true);
        throw error;
      }
    } catch (error) {
      propagated = error;
      assert.equal(rpc.internal(error), true);
    }
  });
  rpc.exact({ value: 1 }, allowed);
  assert.equal(rpc.internal(propagated), false);
});

test("internal provenance stays independent for overlapping operations and clears after settlement", async () => {
  const rpc = createCfoSupabaseRpc("operation_failed:");
  const allowed = new Set(["value"]);
  let release;
  const gate = new Promise(resolve => { release = resolve; });
  async function operation(reason) {
    rpc.exact({ value: 1 }, allowed);
    await gate;
    try { rpc.fail(reason); } catch (error) { return error; }
  }

  const firstPromise = operation("first");
  const secondPromise = operation("second");
  release();
  const [first, second] = await Promise.all([firstPromise, secondPromise]);
  assert.equal(first.message, "operation_failed:first");
  assert.equal(second.message, "operation_failed:second");
  assert.notEqual(first, second);
  assert.equal(rpc.internal(first), false);
  assert.equal(rpc.internal(second), false);
});

test("runOperation restores outer provenance after a successful nested operation", async () => {
  const rpc = createCfoSupabaseRpc("operation_failed:");
  const outerError = await rpc.runOperation(async () => {
    let error;
    try { rpc.fail("outer"); } catch (caught) { error = caught; }
    await rpc.runOperation(async () => {
      assert.equal(rpc.internal(error), false);
    });
    assert.equal(rpc.internal(error), true);
    return error;
  });
  assert.equal(rpc.internal(outerError), false);
});

test("runOperation restores outer provenance after a failing nested operation", async () => {
  const rpc = createCfoSupabaseRpc("operation_failed:");
  await rpc.runOperation(async () => {
    let outerError;
    try { rpc.fail("outer"); } catch (caught) { outerError = caught; }
    await assert.rejects(() => rpc.runOperation(async () => { rpc.fail("inner"); }), error => {
      assert.equal(error.message, "operation_failed:inner");
      return true;
    });
    assert.equal(rpc.internal(outerError), true);
  });
});

test("runOperation keeps truly overlapping success and failure provenance independent", async () => {
  const rpc = createCfoSupabaseRpc("operation_failed:");
  let release;
  const gate = new Promise(resolve => { release = resolve; });
  const failing = rpc.runOperation(async () => {
    await gate;
    try { rpc.fail("overlap"); } catch (error) { return error; }
  });
  const succeeding = rpc.runOperation(async () => {
    await gate;
    return "success";
  });
  release();
  const [error, result] = await Promise.all([failing, succeeding]);
  assert.equal(error.message, "operation_failed:overlap");
  assert.equal(result, "success");
  assert.equal(rpc.internal(error), false);
});

test("runOperation leaves no ambient provenance after success or failure settles", async () => {
  const rpc = createCfoSupabaseRpc("operation_failed:");
  const error = await rpc.runOperation(async () => {
    try { rpc.fail("settled"); } catch (caught) { return caught; }
  });
  assert.equal(rpc.internal(error), false);
  await Promise.resolve();
  assert.equal(rpc.internal(error), false);
  await rpc.runOperation(async () => {});
  assert.equal(rpc.internal(error), false);
});

test("detached descendant from a successful callback expires inherited provenance", async () => {
  const rpc = createCfoSupabaseRpc("operation_failed:");
  let release;
  const gate = new Promise(resolve => { release = resolve; });
  let parentError;
  let descendant;

  const result = await rpc.runOperation(async () => {
    try { rpc.fail("successful_parent"); } catch (error) {
      parentError = error;
      descendant = (async () => {
        await gate;
        assert.equal(rpc.internal(parentError), false);
        const replayed = await replayThroughHostileJsonBoundary(rpc, parentError);
        assert.equal(rpc.internal(replayed), false);
      })();
      return "success";
    }
  });

  assert.equal(result, "success");
  release();
  await descendant;
});

test("detached descendant from a failing callback expires inherited provenance", async () => {
  const rpc = createCfoSupabaseRpc("operation_failed:");
  let release;
  const gate = new Promise(resolve => { release = resolve; });
  let parentError;
  let descendant;

  const operation = rpc.runOperation(async () => {
    try { rpc.fail("failing_parent"); } catch (error) {
      parentError = error;
      descendant = (async () => {
        await gate;
        assert.equal(rpc.internal(parentError), false);
        const replayed = await replayThroughHostileJsonBoundary(rpc, parentError);
        assert.equal(rpc.internal(replayed), false);
      })();
      throw error;
    }
  });

  await assert.rejects(operation, error => {
    assert.equal(error, parentError);
    return true;
  });
  release();
  await descendant;
});

test("exact() enforces a plain object with exactly the allowed enumerable own keys", () => {
  const { exact } = createCfoSupabaseRpc("t_failed:");
  const allowed = new Set(["a", "b"]);
  assert.doesNotThrow(() => exact({ a: 1, b: 2 }, allowed));
  for (const bad of [null, undefined, 42, [], new Proxy({ a: 1, b: 2 }, {}), { a: 1 }, { a: 1, b: 2, c: 3 }]) {
    throwsWithMessage(() => exact(bad, allowed), /^t_failed:invalid_input$/);
  }
  const withGetter = {}; Object.defineProperty(withGetter, "a", { enumerable: true, get: () => 1 }); Object.defineProperty(withGetter, "b", { enumerable: true, value: 2 });
  throwsWithMessage(() => exact(withGetter, allowed), /^t_failed:invalid_input$/);
  const nonEnumerable = { b: 2 }; Object.defineProperty(nonEnumerable, "a", { enumerable: false, value: 1 });
  throwsWithMessage(() => exact(nonEnumerable, allowed), /^t_failed:invalid_input$/);
  throwsWithMessage(() => exact({ a: 1 }, allowed, "custom_reason"), /^t_failed:custom_reason$/);
});

test("validDate() accepts real calendar dates only, including leap-year boundaries", () => {
  const { validDate } = createCfoSupabaseRpc("t_failed:");
  assert.equal(validDate("2026-08-09"), true);
  assert.equal(validDate("2024-02-29"), true, "2024 is a leap year");
  assert.equal(validDate("2026-02-29"), false, "2026 is not a leap year");
  assert.equal(validDate("2000-02-29"), true, "2000 is a leap year (divisible by 400)");
  assert.equal(validDate("1900-02-29"), false, "1900 is not a leap year (divisible by 100, not 400)");
  for (const bad of ["2026-13-01", "2026-00-01", "2026-01-32", "not-a-date", 42, null, undefined, "2026/08/09"]) {
    assert.equal(validDate(bad), false);
  }
});

test("uuid() rejects non-UUID strings and the nil UUID, and lowercases valid input", () => {
  const { uuid } = createCfoSupabaseRpc("t_failed:");
  assert.equal(uuid("30000000-0000-4000-8000-000000000001", "bad"), "30000000-0000-4000-8000-000000000001");
  assert.equal(uuid("30000000-0000-4000-8000-000000000001".toUpperCase(), "bad"), "30000000-0000-4000-8000-000000000001");
  for (const bad of ["not-a-uuid", "00000000-0000-0000-0000-000000000000", 42, null, undefined, ""]) {
    throwsWithMessage(() => uuid(bad, "bad_uuid"), /^t_failed:bad_uuid$/);
  }
});

test("timestamp() validates RFC3339 including zone-offset bounds", () => {
  const { timestamp } = createCfoSupabaseRpc("t_failed:");
  assert.equal(timestamp("2026-08-09T06:00:01.000Z"), true);
  assert.equal(timestamp("2026-08-09T06:00:01+09:00"), true);
  for (const bad of ["not-a-timestamp", "2026-08-09T25:00:00Z", "2026-08-09T06:00:00+24:00", "2026-08-09", 42, null]) {
    assert.equal(timestamp(bad), false);
  }
});

test("validateOptions() requires trimmed http(s) credentials and defaults fetchImpl to globalThis.fetch", () => {
  const { validateOptions } = createCfoSupabaseRpc("t_failed:");
  const fetchImpl = async () => {};
  const config = validateOptions({ supaUrl: URL, supaKey: KEY, fetchImpl });
  assert.deepEqual(config, { base: URL, supaKey: KEY, fetchImpl });
  assert.equal(validateOptions({ supaUrl: `${URL}/`, supaKey: KEY, fetchImpl }).base, URL, "trailing slashes are stripped");
  for (const bad of [
    { supaUrl: "", supaKey: KEY, fetchImpl }, { supaUrl: URL, supaKey: "", fetchImpl },
    { supaUrl: " https://x.co", supaKey: KEY, fetchImpl }, { supaUrl: "ftp://x.co", supaKey: KEY, fetchImpl },
    { supaUrl: "https://u:p@x.co", supaKey: KEY, fetchImpl }, { supaUrl: "https://x.co?a=1", supaKey: KEY, fetchImpl },
    { supaUrl: URL, supaKey: KEY, fetchImpl: "not-a-function" }, null, 42,
  ]) throwsWithMessage(() => validateOptions(bad), /^t_failed:[a-z0-9_]+$/);
});

test("validateOptions() rejects unknown enumerable keys (catches missing allowed-key membership)", () => {
  const { validateOptions } = createCfoSupabaseRpc("t_failed:");
  const opts = { supaUrl: URL, supaKey: KEY, fetchImpl: async () => {}, unexpected: true };
  throwsWithMessage(() => validateOptions(opts), /^t_failed:invalid_options$/);
});

test("validateOptions() rejects symbol keys (catches string-only own-key filtering)", () => {
  const { validateOptions } = createCfoSupabaseRpc("t_failed:");
  const opts = { supaUrl: URL, supaKey: KEY, fetchImpl: async () => {} };
  opts[Symbol("unexpected")] = true;
  throwsWithMessage(() => validateOptions(opts), /^t_failed:invalid_options$/);
});

test("validateOptions() rejects non-enumerable own keys (catches descriptor enumerability omission)", () => {
  const { validateOptions } = createCfoSupabaseRpc("t_failed:");
  const opts = { supaUrl: URL, supaKey: KEY, fetchImpl: async () => {} };
  Object.defineProperty(opts, "unexpected", { enumerable: false, value: true });
  throwsWithMessage(() => validateOptions(opts), /^t_failed:invalid_options$/);
});

test("freeze() deep-freezes without cycling infinitely on shared or circular references", () => {
  const { freeze } = createCfoSupabaseRpc("t_failed:");
  const shared = { x: 1 };
  const value = { a: shared, b: shared };
  const circular = {}; circular.self = circular;
  assert.doesNotThrow(() => freeze(circular));
  const frozen = freeze(value);
  assert.equal(Object.isFrozen(frozen), true);
  assert.equal(Object.isFrozen(frozen.a), true);
  assert.equal(frozen.a, frozen.b);
});

test("postRpc() posts to the given rpc path with service-role headers and returns the parsed body", async () => {
  const { postRpc } = createCfoSupabaseRpc("t_failed:");
  const calls = [];
  const config = { base: URL, supaKey: KEY, fetchImpl: async (url, init) => { calls.push({ url, init }); return response({ ok: true }); } };
  const parsed = await postRpc(config, "lm_example_rpc", { p_uid: "tenant-a" });
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, `${URL}/rest/v1/rpc/lm_example_rpc`);
  assert.equal(calls[0].init.method, "POST");
  assert.deepEqual(calls[0].init.headers, { apikey: KEY, Authorization: `Bearer ${KEY}`, "Content-Type": "application/json" });
  assert.deepEqual(JSON.parse(calls[0].init.body), { p_uid: "tenant-a" });
  assert.deepEqual(parsed, { ok: true });
});

test("postRpc() fails closed on network throw without reading a response", async () => {
  const { postRpc } = createCfoSupabaseRpc("t_failed:");
  const config = { base: URL, supaKey: KEY, fetchImpl: async () => { throw new Error("boom"); } };
  await rejectsWithMessage(() => postRpc(config, "lm_example_rpc", {}), /^t_failed:network$/);
});

test("postRpc() fails closed on a non-2xx status and never reads the response body", async () => {
  const { postRpc } = createCfoSupabaseRpc("t_failed:");
  let jsonCalls = 0;
  const config = { base: URL, supaKey: KEY, fetchImpl: async () => ({ ok: false, status: 409, json: () => { jsonCalls += 1; throw new Error("must not read"); } }) };
  await rejectsWithMessage(() => postRpc(config, "lm_example_rpc", {}), /^t_failed:provider_409$/);
  assert.equal(jsonCalls, 0);
});

test("postRpc() fails closed on a malformed response object or unreadable JSON", async () => {
  const { postRpc } = createCfoSupabaseRpc("t_failed:");
  await rejectsWithMessage(() => postRpc({ base: URL, supaKey: KEY, fetchImpl: async () => null }, "lm_example_rpc", {}), /^t_failed:invalid_response$/);
  await rejectsWithMessage(() => postRpc({ base: URL, supaKey: KEY, fetchImpl: async () => ({ ok: true, status: 200, json: "not-a-function" }) }, "lm_example_rpc", {}), /^t_failed:invalid_json$/);
});
