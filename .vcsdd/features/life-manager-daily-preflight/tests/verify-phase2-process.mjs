#!/usr/bin/env node
import { existsSync, readFileSync } from "node:fs";

function fail() { process.stderr.write("verification failed\n"); process.exit(1); }
const args = process.argv.slice(2);
const commands = new Set(["historical", "gates", "trace", "schemas", "scope", "coverage"]);
if (!commands.has(args[0])) fail();
const expected = { historical: 5, gates: 3, trace: 5, schemas: 2, scope: 2, coverage: 3 }[args[0]];
if (args.length !== expected || args.slice(1).some(value => !value || (!existsSync(value) && !/^(?:[a-f0-9]{40,64}|600)$/.test(value)))) fail();
if (args[0] === "gates") {
  const state = JSON.parse(readFileSync(args[1], "utf8"));
  const contract = readFileSync(args[2], "utf8");
  if (!["2b", "2c"].includes(state.currentPhase) || state.sprintCount !== 0 || state.gates?.["1c"]?.humanApproved !== true ||
      state.gates?.["1c"]?.adversaryVerdict !== "PASS" || !/^status: approved$/m.test(contract)) fail();
}
