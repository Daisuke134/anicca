"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const { resolveLateRecipients } = require("./late-recipient-resolver.js");

function emptyDeps(overrides = {}) {
  return {
    connectedGmail: async () => [],
    approvedContacts: async () => [],
    publicWeb: async () => [],
    ...overrides,
  };
}

test("includes the organizer while excluding self, resources, and declined attendees", async () => {
  const result = await resolveLateRecipients({
    uid: "user-1",
    actorEmails: ["me@example.invalid"],
    event: {
      id: "event-organizer",
      organizer: { displayName: "Organizer", email: "organizer@example.invalid" },
      attendees: [
        { displayName: "Me", email: "me@example.invalid", self: true, responseStatus: "accepted" },
        { displayName: "Room", email: "room@example.invalid", resource: true, responseStatus: "accepted" },
        { displayName: "Declined", email: "declined@example.invalid", responseStatus: "declined" },
      ],
    },
  }, emptyDeps());

  assert.equal(result.status, "resolved");
  assert.deepEqual(result.candidates.map((candidate) => candidate.email), ["organizer@example.invalid"]);
  assert.equal(result.candidates[0].event_role, "organizer");
  assert.ok(result.evidenceRefs.includes("calendar:event:event-organizer:organizer:0"));
  assert.ok(!Object.hasOwn(result, "send"));
});

test("keeps a non-declined Calendar attendee as a recipient candidate", async () => {
  const result = await resolveLateRecipients({
    uid: "user-1",
    actorEmails: ["me@example.invalid"],
    event: {
      id: "event-attendee",
      attendees: [
        { displayName: "Me", email: "me@example.invalid", self: true },
        { displayName: "Attendee", email: "Attendee@Example.Invalid", responseStatus: "accepted" },
      ],
    },
  }, emptyDeps());

  assert.equal(result.status, "resolved");
  assert.equal(result.candidates.length, 1);
  assert.equal(result.candidates[0].email, "attendee@example.invalid");
  assert.equal(result.candidates[0].event_role, "attendee");
});

test("merges Calendar and connected Gmail evidence by verified email", async () => {
  const calls = [];
  const result = await resolveLateRecipients({
    uid: "user-1",
    actorEmails: ["me@example.invalid"],
    event: {
      id: "event-merge",
      attendees: [{ displayName: "Calendar Name", email: "Person@Example.Invalid" }],
    },
  }, emptyDeps({
    connectedGmail: async (context) => {
      calls.push(["gmail", context.uid, context.event.id]);
      return [{
        display_name: "Gmail Name",
        email: "person@example.invalid",
        evidence_refs: ["gmail:thread-1"],
        confidence: "high",
        event_role: "attendee",
      }];
    },
  }));

  assert.equal(result.status, "resolved");
  assert.equal(result.candidates.length, 1);
  assert.equal(result.candidates[0].email, "person@example.invalid");
  assert.deepEqual(result.candidates[0].evidence_refs, [
    "calendar:event:event-merge:attendee:0",
    "gmail:thread-1",
  ]);
  assert.deepEqual(calls, [["gmail", "user-1", "event-merge"]]);
});

test("uses an approved Contacts candidate when Calendar and Gmail have no address", async () => {
  const calls = [];
  const result = await resolveLateRecipients({
    uid: "user-1",
    actorEmails: [],
    event: { id: "event-contact", summary: "Project sync", attendees: [] },
  }, emptyDeps({
    connectedGmail: async () => { calls.push("gmail"); return []; },
    approvedContacts: async (context) => {
      calls.push(["contacts", context.uid, context.event.summary]);
      return [{
        display_name: "Contact Person",
        email: "contact@example.invalid",
        evidence_refs: ["contacts:person-1"],
        confidence: "high",
        event_role: "attendee",
      }];
    },
    publicWeb: async () => { calls.push("web"); return []; },
  }));

  assert.equal(result.status, "resolved");
  assert.equal(result.candidates[0].email, "contact@example.invalid");
  assert.equal(result.candidates[0].source, "contacts");
  assert.deepEqual(calls, ["gmail", ["contacts", "user-1", "Project sync"], "web"]);
});

test("does not auto-resolve a public-web-only candidate and requests confirmation once", async () => {
  const calls = [];
  const result = await resolveLateRecipients({
    uid: "user-1",
    actorEmails: [],
    event: { id: "event-web", summary: "Public meeting", attendees: [] },
  }, emptyDeps({
    connectedGmail: async () => { calls.push("gmail"); return []; },
    approvedContacts: async () => { calls.push("contacts"); return []; },
    publicWeb: async () => {
      calls.push("web");
      return [{
        display_name: "Public Person",
        email: "public@example.invalid",
        evidence_refs: ["web:official-profile"],
        confidence: "medium",
        event_role: "attendee",
      }];
    },
    requestUserConfirmation: async (context) => {
      calls.push(["confirm", context.candidates.map((candidate) => candidate.email)]);
      return null;
    },
  }));

  assert.equal(result.status, "ambiguous");
  assert.equal(result.candidates[0].email, "public@example.invalid");
  assert.deepEqual(calls, [
    "gmail",
    "contacts",
    "web",
    ["confirm", ["public@example.invalid"]],
  ]);
  assert.ok(!Object.hasOwn(result, "send"));
});

test("requests one user confirmation after every evidence stage has no candidate", async () => {
  const calls = [];
  const result = await resolveLateRecipients({
    uid: "user-1",
    actorEmails: [],
    event: { id: "event-missing", summary: "Unresolved meeting", attendees: [] },
  }, emptyDeps({
    connectedGmail: async () => { calls.push("gmail"); return []; },
    approvedContacts: async () => { calls.push("contacts"); return []; },
    publicWeb: async () => { calls.push("web"); return []; },
    requestUserConfirmation: async (context) => {
      calls.push(["confirm", context.candidates.length]);
      return null;
    },
  }));

  assert.equal(result.status, "missing");
  assert.deepEqual(result.candidates, []);
  assert.deepEqual(calls, ["gmail", "contacts", "web", ["confirm", 0]]);
  assert.ok(!Object.hasOwn(result, "send"));
});

test("accepts one explicit user-confirmed email without inventing an address", async () => {
  const result = await resolveLateRecipients({
    uid: "user-1",
    actorEmails: [],
    event: { id: "event-confirmed", summary: "Confirmed meeting", attendees: [] },
  }, emptyDeps({
    requestUserConfirmation: async () => ({
      display_name: "Confirmed Person",
      email: "confirmed@example.invalid",
      evidence_refs: ["telegram:confirmation-1"],
    }),
  }));

  assert.equal(result.status, "resolved");
  assert.deepEqual(result.candidates, [{
    display_name: "Confirmed Person",
    email: "confirmed@example.invalid",
    source: "user_confirmation",
    evidence_refs: ["telegram:confirmation-1"],
    confidence: 1,
    event_role: "attendee",
  }]);
  assert.ok(!Object.hasOwn(result, "send"));
});

test("marks conflicting verified emails ambiguous, never fabricates an email, and exposes no send action", async () => {
  const result = await resolveLateRecipients({
    uid: "user-1",
    actorEmails: [],
    event: {
      id: "event-conflict",
      organizer: { displayName: "Organizer", email: "organizer@example.invalid" },
    },
  }, emptyDeps({
    connectedGmail: async () => [{
      display_name: "Different Person",
      email: "different@example.invalid",
      evidence_refs: ["gmail:thread-conflict"],
    }],
    requestUserConfirmation: async () => null,
  }));

  assert.equal(result.status, "ambiguous");
  assert.deepEqual(result.candidates.map((candidate) => candidate.email), [
    "organizer@example.invalid",
    "different@example.invalid",
  ]);
  assert.equal(result.candidates.some((candidate) => /organizer|different/.test(candidate.email)), true);
  assert.equal(result.candidates.some((candidate) => candidate.email.includes("@example.invalid")), true);
  assert.ok(!Object.hasOwn(result, "send"));
  assert.ok(!result.candidates.some((candidate) => candidate.email === "event-conflict@example.invalid"));
});
