#!/usr/bin/env node
"use strict";

const { runPanelPrivacyEval } = require("./panel-privacy-harness.js");

runPanelPrivacyEval()
  .then((result) => {
    console.log(
      `Panel privacy eval: api=${result.api} browser=${result.browser} `
      + `recipes=${result.recipes} channels=${result.channels} judge=deterministic`,
    );
  })
  .catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
