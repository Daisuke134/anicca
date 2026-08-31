#!/usr/bin/env node
"use strict";

const { runAniccaEnSlideshowTikTokCanary } = require("./anicca-larry-ja-canary.js");

function run(argv = process.argv.slice(2), deps = {}) {
  const command = argv.length === 3 && argv[0] === "run" ? ["run-en-slideshow-tiktok", ...argv.slice(1)] : argv;
  return runAniccaEnSlideshowTikTokCanary(command, deps);
}

if (require.main === module) run().then((result) => process.stdout.write(`${JSON.stringify(result)}\n`)).catch((error) => { process.stderr.write(`${error.message}\n`); process.exitCode = 1; });

module.exports = { run };
