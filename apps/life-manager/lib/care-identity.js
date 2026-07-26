"use strict";
// lib/care-identity.js — §10.1 U8: how Life Manager names itself to the outside world.
//
// 「Life Manager（AI secretary, acting for <user>）」— the delegation is stated in the identification
// ITSELF, so a provider reading a booking form or an email knows, in the first thing they read, that
// they are dealing with an agent acting for a named person. U8's rule is 本人を装わない: we never type
// the user's bare name into a free-text field as though the user typed it.
//
// This lives in its own module because both the 11c web-form executor and the (still unimplemented)
// email route must use the SAME string. Two copies would eventually disagree, and the one that
// drifted would be the one that impersonated someone.

const U8_TEMPLATE = "Life Manager（AI secretary, acting for {user}）";

function formatU8Identification(userName) {
  return U8_TEMPLATE.replace("{user}", String(userName || "").trim());
}

module.exports = { U8_TEMPLATE, formatU8Identification };
