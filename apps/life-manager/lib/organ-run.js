"use strict";
// lib/organ-run.js — spec 2026-08-01-lm-daily-organ-design.md §3 row 1c.
//
// Every organ in the tick was already try/catch-wrapped, so a THROW could not kill its siblings.
// Nothing measured how LONG one took, which is the failure that actually happened: organs share one
// per-user budget, and `tenant timeout 90000ms` named the user but never the organ that ate it.
// runOrgan is that missing measurement, and it keeps the existing swallow-and-continue contract.

async function runOrgan({ label, uid, run, log, now }) {
  // `log` defaults rather than being required: this wrapper's entire job is to never take down its
  // caller, and a missing logger would otherwise throw from the catch block and propagate — the
  // exact failure the wrapper exists to prevent.
  const write = log || console.log;
  const clock = now || Date.now;
  const started = clock();
  const who = `uid=${String(uid || "?").slice(0, 12)}`;
  try {
    const value = await run();
    write(`[${label}] ${who} ms=${clock() - started}`);
    return value;
  } catch (e) {
    write(`[${label}] ${who} ms=${clock() - started} err ${e && e.message}`);
    return null;
  }
}

module.exports = { runOrgan };
