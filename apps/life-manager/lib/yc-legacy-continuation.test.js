"use strict";

const assert = require("node:assert/strict");
const { createHash } = require("node:crypto");
const test = require("node:test");

const { buildYcLegacyContinuationReceipt } = require("./yc-legacy-continuation.js");

const LEGACY_ID = "99b966b0-7e90-4856-ab0d-93651488a4ea";
const CURRENT_ID = "0b61fe42-e383-490d-b60e-04f1ad7ec5df";
const sha = (value) => createHash("sha256").update(value, "utf8").digest("hex");
const build = (input) => buildYcLegacyContinuationReceipt(input, { now: () => Date.parse("2026-08-01T23:46:00.000Z") });

function valid() {
  const homeBody = "Authenticated applications. Anicca. Fall 2026. In review. View your full application.";
  const legacyBody = "Anicca historical application. Summer 2026. Application answers follow.";
  return {
    recordedAt: "2026-08-01T23:45:00.000Z",
    legacyApplicationId: LEGACY_ID,
    currentApplicationId: CURRENT_ID,
    home: {
      url: "https://apply.ycombinator.com/home",
      observedAt: "2026-08-01T23:43:00.000Z",
      authenticated: true,
      body: homeBody,
      bodySha256: sha(homeBody),
      applicationLinks: [
        `https://apply.ycombinator.com/apps/${CURRENT_ID}`,
        `https://apply.ycombinator.com/apps/${CURRENT_ID}/edit`,
      ],
    },
    legacy: {
      url: `https://apply.ycombinator.com/apps/${LEGACY_ID}`,
      observedAt: "2026-08-01T23:44:00.000Z",
      accessible: true,
      body: legacyBody,
      bodySha256: sha(legacyBody),
      applicationLinks: [`https://apply.ycombinator.com/apps/${LEGACY_ID}#company`],
    },
    assessment: {
      decision: "separate_historical_application",
      homeBatch: "Fall 2026",
      homeStatus: "In review",
      legacyBatch: "Summer 2026",
      continuationControlObserved: false,
      homeBatchExcerpt: "Fall 2026",
      homeStatusExcerpt: "In review",
      legacyBatchExcerpt: "Summer 2026",
      rationale: "Current authenticated Home links the submitted Fall application while the legacy preview remains a distinct Summer application.",
    },
    effects: {
      browserRef: "browser-profile://cloakbrowser/daily-driver",
      endpoint: "http://127.0.0.1:9222",
      existingPageCount: 45,
      createdOwnedPages: 1,
      closedOwnedPages: 1,
      browserCloseOperations: 0,
      writeOperations: 0,
      submitOperations: 0,
    },
  };
}

test("fresh authenticated surfaces produce a privacy-minimal separate-history receipt", () => {
  const input = valid();
  const receipt = build(input);
  assert.equal(receipt.decision, "separate_historical_application");
  assert.equal(receipt.same_application, false);
  assert.equal(receipt.current_home.legacy_link_present, false);
  assert.equal(receipt.current_home.current_link_present, true);
  assert.equal(receipt.legacy_preview.accessible, true);
  assert.equal(receipt.safe_operational_action, "keep_current_application_no_duplicate");
  assert.equal(receipt.effects.write_operations, 0);
  assert.equal(receipt.effects.submit_operations, 0);
  assert.match(receipt.receipt_digest, /^[0-9a-f]{64}$/);
  assert.ok(Object.isFrozen(receipt));
  const serialized = JSON.stringify(receipt);
  assert.doesNotMatch(serialized, /Authenticated applications|Application answers follow|Current authenticated Home links/);
  assert.doesNotMatch(serialized, /homeBatchExcerpt|legacyBatchExcerpt|rationale/);
});

test("agent-owned surface labels are preserved without deterministic batch semantics", () => {
  const input = valid();
  input.home.body = input.home.body.replace("Fall 2026", "Current cohort shown").replace("In review", "Provider status shown");
  input.home.bodySha256 = sha(input.home.body);
  input.legacy.body = input.legacy.body.replace("Summer 2026", "Historical cohort shown");
  input.legacy.bodySha256 = sha(input.legacy.body);
  Object.assign(input.assessment, {
    homeBatch: "Current cohort shown",
    homeStatus: "Provider status shown",
    legacyBatch: "Historical cohort shown",
    homeBatchExcerpt: "Current cohort shown",
    homeStatusExcerpt: "Provider status shown",
    legacyBatchExcerpt: "Historical cohort shown",
  });
  const receipt = build(input);
  assert.equal(receipt.current_home.batch, "Current cohort shown");
  assert.equal(receipt.current_home.status, "Provider status shown");
  assert.equal(receipt.legacy_preview.batch, "Historical cohort shown");
});

test("identity, provenance, chronology, semantic evidence, and zero-effect violations fail closed", () => {
  const cases = [];
  const same = valid(); same.currentApplicationId = LEGACY_ID; cases.push(same);
  const oldOnHome = valid(); oldOnHome.home.applicationLinks.push(`https://apply.ycombinator.com/apps/${LEGACY_ID}`); cases.push(oldOnHome);
  const missingCurrent = valid(); missingCurrent.home.applicationLinks = [`https://apply.ycombinator.com/apps/${LEGACY_ID}`]; cases.push(missingCurrent);
  const wrongHome = valid(); wrongHome.home.url = "https://example.com/home"; cases.push(wrongHome);
  const wrongLegacyPath = valid(); wrongLegacyPath.legacy.url = `https://apply.ycombinator.com/apps/${CURRENT_ID}`; cases.push(wrongLegacyPath);
  const inaccessible = valid(); inaccessible.legacy.accessible = false; cases.push(inaccessible);
  const missingExcerpt = valid(); missingExcerpt.assessment.legacyBatchExcerpt = "Winter 2026"; cases.push(missingExcerpt);
  const unrelatedHomeBatch = valid(); unrelatedHomeBatch.assessment.homeBatchExcerpt = "Anicca"; cases.push(unrelatedHomeBatch);
  const unrelatedHomeStatus = valid(); unrelatedHomeStatus.assessment.homeStatusExcerpt = "Anicca"; cases.push(unrelatedHomeStatus);
  const unrelatedLegacyBatch = valid(); unrelatedLegacyBatch.assessment.legacyBatchExcerpt = "Anicca"; cases.push(unrelatedLegacyBatch);
  const reversed = valid(); reversed.home.observedAt = "2026-08-01T23:44:30.000Z"; cases.push(reversed);
  const stale = valid(); stale.home.observedAt = "2026-08-01T22:00:00.000Z"; cases.push(stale);
  const staleReceipt = valid(); staleReceipt.home.observedAt = "2026-08-01T22:43:00.000Z"; staleReceipt.legacy.observedAt = "2026-08-01T22:44:00.000Z"; staleReceipt.recordedAt = "2026-08-01T22:45:00.000Z"; cases.push(staleReceipt);
  const digestSwap = valid(); digestSwap.home.bodySha256 = "f".repeat(64); cases.push(digestSwap);
  const unknown = valid(); unknown.assessment.decision = "maybe_continuable"; cases.push(unknown);
  const control = valid(); control.assessment.continuationControlObserved = true; cases.push(control);
  const write = valid(); write.effects.writeOperations = 1; cases.push(write);
  const submit = valid(); submit.effects.submitOperations = 1; cases.push(submit);
  const browserClose = valid(); browserClose.effects.browserCloseOperations = 1; cases.push(browserClose);
  const tabLeak = valid(); tabLeak.effects.closedOwnedPages = 0; cases.push(tabLeak);
  const currentOnLegacy = valid(); currentOnLegacy.legacy.applicationLinks.push(`https://apply.ycombinator.com/apps/${CURRENT_ID}`); cases.push(currentOnLegacy);
  const foreignLink = valid(); foreignLink.home.applicationLinks = [`https://example.com/apps/${CURRENT_ID}`]; cases.push(foreignLink);
  const queryLink = valid(); queryLink.home.applicationLinks[0] += "?copied=true"; cases.push(queryLink);
  const extra = valid(); extra.home.cookie = "secret"; cases.push(extra);
  for (const input of cases) {
    assert.throws(() => build(input), /YC legacy continuation/i);
  }
});

test("duplicate or malformed application inventories and invalid bodies fail closed", () => {
  const duplicate = valid(); duplicate.home.applicationLinks.push(duplicate.home.applicationLinks[0]);
  const malformed = valid(); malformed.legacy.applicationLinks = ["not-a-url"];
  const blank = valid(); blank.home.body = ""; blank.home.bodySha256 = sha("");
  const padded = valid(); padded.assessment.homeBatchExcerpt = " Fall 2026 ";
  for (const input of [duplicate, malformed, blank, padded]) {
    assert.throws(() => build(input), /YC legacy continuation/i);
  }
});
