#!/usr/bin/env node
"use strict";

const { createHash } = require("node:crypto");

const {
  buildRuntimeJob,
  enqueueJob,
} = require("./runtime-job-store.js");

const CAPABILITY = "outbound.event.apply";
const LOOP_ID = "outbound.events";
const IDENTITY_REF = /^identity:\/\/[a-z0-9._-]+\/[a-z0-9._-]+$/i;
const BROWSER_PROFILE_REF = /^browser-profile:\/\/cloakbrowser\/[a-z0-9._-]+$/i;
const CALENDAR_REF = /^calendar:\/\/google\/[a-z0-9._-]+$/i;
const LUMA_HOSTS = new Set(["lu.ma", "luma.com", "www.luma.com"]);
const LUMA_SLUG = /^[A-Za-z0-9_-]+$/;

function required(value, label) {
  const text = String(value == null ? "" : value).trim();
  if (!text) throw new Error(`${label} is required`);
  return text;
}

function reference(value, pattern, label) {
  const text = required(value, label);
  if (!pattern.test(text)) throw new Error(`${label} reference is invalid`);
  return text;
}

function lumaSlug(value) {
  let url;
  try {
    url = new URL(required(value, "Luma event URL"));
  } catch {
    throw new Error("Luma event URL is invalid");
  }
  const parts = url.pathname.split("/").filter(Boolean);
  if (url.protocol !== "https:" || !LUMA_HOSTS.has(url.hostname.toLowerCase())) {
    throw new Error("Luma event URL is invalid");
  }
  if (parts.length !== 1 || !LUMA_SLUG.test(parts[0])) {
    throw new Error("Luma event URL is invalid");
  }
  return parts[0];
}

function eventStart(value) {
  const text = required(value, "event start");
  const time = Date.parse(text);
  if (!Number.isFinite(time) || !/[zZ]|[+-]\d\d:\d\d$/.test(text)) {
    throw new Error("event start is invalid");
  }
  return new Date(time).toISOString();
}

function buildEventApplicationJob(input = {}) {
  const tenantId = required(input.tenantId, "event tenant");
  const slug = lumaSlug(input.eventUrl);
  const startsAt = eventStart(input.eventStartIso);
  const identityRef = reference(input.identityRef, IDENTITY_REF, "identity");
  const browserProfileRef = reference(
    input.browserProfileRef,
    BROWSER_PROFILE_REF,
    "browser profile",
  );
  const calendarRef = reference(input.calendarRef, CALENDAR_REF, "calendar");
  const eventRef = `luma-event://event/${slug}?starts_at=${encodeURIComponent(startsAt)}`;
  const digest = createHash("sha256")
    .update(`${tenantId}\n${eventRef}\n${identityRef}`, "utf8")
    .digest("hex");

  return buildRuntimeJob({
    jobId: `outbound-event:${digest}`,
    tenantId,
    loopId: LOOP_ID,
    capability: CAPABILITY,
    effectClass: "publish",
    effectKey: `event-application:luma:${slug}:${digest}`,
    inputRefs: {
      event_ref: eventRef,
      identity_ref: identityRef,
      browser_profile_ref: browserProfileRef,
      calendar_ref: calendarRef,
    },
    maxAttempts: 5,
  });
}

async function enqueueEventApplication(input, storeOptions = {}, deps = {}) {
  const enqueue = deps.enqueueJob || enqueueJob;
  return enqueue(buildEventApplicationJob(input), storeOptions);
}

module.exports = {
  CAPABILITY,
  LOOP_ID,
  buildEventApplicationJob,
  enqueueEventApplication,
};
