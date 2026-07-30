// lib/providers/gmail.js — confirmation-email reader (spec E1 / TODO #8).
//
// E1 can be satisfied by a real confirmation email read out of the mailbox. The existing
// registration_confirmation_classify.py is dead code today — nothing in production calls it —
// and this provider is where it gets wired to a live inbox.
//
// Every function refuses until TODO #7/#8 land.
"use strict";

const refuse = (name) => async () => {
  throw new Error(`NOT_IMPLEMENTED: gmail.${name}`);
};

module.exports = {
  // TRACK/E1: -> {ok, message_id, subject, received_at} for a given target.
  findConfirmationEmail: refuse("findConfirmationEmail"),
  // -> the full message (headers + parts) so the guest key can be extracted from the body/ics.
  readMessage: refuse("readMessage"),
};
