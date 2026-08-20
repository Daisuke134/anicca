"use strict";

const {
  appendHonneJaShadowHold,
  holdHonneJaShadowPublications,
  honneJaShadowStatus,
  marketingVideoShadowConfig,
  planMarketingVideoShadowGeneration,
} = require("./honne-ja-shadow-runtime.js");

const HONNE_EN_SLOTS = Object.freeze(["07:00", "11:00", "20:30"]);

function honneEnShadowConfig(env = {}, options = {}) {
  return marketingVideoShadowConfig(env, {
    ...options,
    envPrefix: "LM_HONNE_EN",
    slots: HONNE_EN_SLOTS,
    defaultProductId: "honne-ai",
    defaultFormatId: "reelclaw",
    defaultLocale: "en",
  });
}

function honneEnShadowStatus(rows, options = {}) {
  return honneJaShadowStatus(rows, { ...options, slots: HONNE_EN_SLOTS });
}

module.exports = {
  HONNE_EN_SLOTS,
  appendHonneEnShadowHold: appendHonneJaShadowHold,
  holdHonneEnShadowPublications: holdHonneJaShadowPublications,
  honneEnShadowConfig,
  honneEnShadowStatus,
  planHonneEnShadowGeneration: planMarketingVideoShadowGeneration,
};
