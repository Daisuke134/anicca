#!/usr/bin/env node
import { existsSync, readFileSync } from "node:fs";

function fail() { process.stderr.write("verification failed\n"); process.exit(1); }
const args = process.argv.slice(2);
if (args.length !== 3 || args.some(value => !existsSync(value))) fail();
let state;
try { state = JSON.parse(readFileSync(args[0], "utf8")); } catch { fail(); }
const contract = readFileSync(args[1], "utf8");
const snapshot = readFileSync(args[2], "utf8");
if (state.currentPhase !== "2b" || state.sprintCount !== 0 || state.gates?.["1c"]?.humanApproved !== true ||
    state.gates?.["1c"]?.adversaryVerdict !== "PASS" || !/^status: approved$/m.test(contract) ||
    !/^greenCommit=[a-f0-9]{40}$/m.test(snapshot) || !/^greenTree=[a-f0-9]{40}$/m.test(snapshot)) fail();
