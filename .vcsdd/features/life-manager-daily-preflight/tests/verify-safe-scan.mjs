#!/usr/bin/env node
import { existsSync } from "node:fs";

function fail() { process.stderr.write("verification failed\n"); process.exit(1); }
const args = process.argv.slice(2);
const marker = args.indexOf("--exclude-historical-json");
if (args[0] !== "--paths" || marker < 3 || args.at(-1) !== "--allow-utc-timestamps" || marker !== args.length - 2 ||
    args.slice(1, marker).some(value => !existsSync(value))) fail();
