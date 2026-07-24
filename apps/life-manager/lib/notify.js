// lib/notify.js — structured location-gate late notice through our existing Resend path.
"use strict";

const { sendLateNotice: resendLateNotice } = require("./mail-resend.js");

async function sendLateNotice(_uid, event, opts = {}) {
  const toAttendees = (Array.isArray(event && event.attendees) ? event.attendees : [])
    .filter((attendee) => attendee && attendee.email && !attendee.self && !attendee.organizer)
    .map((attendee) => attendee.email);
  if (!toAttendees.length) return { sent: false, reason: "no_destination" };
  const result = await resendLateNotice({
    toAttendees,
    userName: opts.userName,
    event,
    etaMinutes: opts.etaMinutes,
    userEmail: opts.userEmail,
    resendKey: opts.resendKey,
    fetchImpl: opts.fetchImpl,
  });
  return { ...result, to: toAttendees, event: event.summary, etaMinutes: opts.etaMinutes };
}

module.exports = { sendLateNotice };
