#!/usr/bin/env node
"use strict";

const {
  OBOU_LANE,
  parseArgs: parseLaneArgs,
  runAniccaWidgetCanary,
} = require("./anicca-en-widget-canary.js");

function parseArgs(argv = []) {
  return parseLaneArgs(argv, OBOU_LANE);
}

function runAniccaObouInstagramCanary(argv = [], deps = {}) {
  return runAniccaWidgetCanary(argv, deps, OBOU_LANE);
}

if (require.main === module) runAniccaObouInstagramCanary(process.argv.slice(2)).then((result) => process.stdout.write(`${JSON.stringify(result)}\n`)).catch((error) => { process.stderr.write(`${error.message}\n`); process.exitCode = 1; });

module.exports = { OBOU_LANE, parseArgs, runAniccaObouInstagramCanary };
