#!/usr/bin/env node
"use strict";

const { runHealerShadow } = require("./lib/healer-shadow.js");

function parse(argv) {
  if (
    argv.length !== 6
    || argv[0] !== "--repo-root"
    || argv[2] !== "--state-dir"
    || argv[4] !== "--worktree-root"
  ) throw new Error("Connector Healer CLI invalid");
  return { repoRoot: argv[1], stateDir: argv[3], worktreeRoot: argv[5], env: process.env };
}

runHealerShadow(parse(process.argv.slice(2)))
  .then((result) => process.stdout.write(`${JSON.stringify(result)}\n`))
  .catch(() => {
    process.stderr.write("Connector Healer shadow unavailable\n", () => process.exit(2));
  });
