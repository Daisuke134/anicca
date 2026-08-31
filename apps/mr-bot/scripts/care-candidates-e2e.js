#!/usr/bin/env node
"use strict";

const { evaluateCareCandidates } = require("../lib/care-candidates");

const DEFINITIONS = [
  {
    providerId: "otakibashi-sora",
    publicName: "小滝橋そら内科クリニック",
    officialUrl: "https://otakibashi-sora.clinic/",
    proximityRank: 1,
    usualProvider: false,
  },
  {
    providerId: "shinjuku-nanairo",
    publicName: "新宿なないろクリニック",
    officialUrl: "https://sjk-nanairo.tokyo/",
    proximityRank: 4,
    usualProvider: false,
  },
  {
    providerId: "hirooka",
    publicName: "ヒロオカクリニック",
    officialUrl: "https://www.h-cl.org/",
    proximityRank: 5,
    usualProvider: false,
  },
];

evaluateCareCandidates(DEFINITIONS).then((receipt) => {
  process.stdout.write(`${JSON.stringify(receipt)}\n`);
  if (receipt.candidates.length !== 3 || !receipt.selected_provider_id) process.exitCode = 1;
}).catch((error) => {
  process.stderr.write(`care-candidates-e2e: ${error.message}\n`);
  process.exitCode = 1;
});
