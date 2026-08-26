#!/usr/bin/env node
"use strict";

const {
  JA_LANE,
  parseArgs: parseLaneArgs,
  runAniccaWidgetCanary,
} = require("./anicca-en-widget-canary.js");

function parseArgs(argv = []) {
  return parseLaneArgs(argv, JA_LANE);
}

function runAniccaJaWidgetCanary(argv = [], deps = {}) {
  return runAniccaWidgetCanary(argv, deps, JA_LANE);
}

if (require.main === module) runAniccaJaWidgetCanary(process.argv.slice(2)).then((result) => process.stdout.write(`${JSON.stringify(result)}\n`)).catch((error) => { process.stderr.write(`${error.message}\n`); process.exitCode = 1; });

module.exports = { JA_LANE, parseArgs, runAniccaJaWidgetCanary };
