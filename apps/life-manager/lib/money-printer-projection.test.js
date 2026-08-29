"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { projectMoneyPrinter } = require("./money-printer-projection.js");

const TENANT = "tenant-a";
const OBSERVED_AT = "2026-08-29T00:00:00.000Z";

function fixture(overrides = {}) {
  const opportunity = {
    tenant_id: TENANT,
    opportunity_id: "opportunity-1",
    status: "QUALIFYING",
    amount_minor: "50000",
    currency: "JPY",
    title: "A paid opportunity",
    source_url: "https://example.test/opportunity-1",
  };
  const input = {
    tenantId: TENANT,
    observedAt: OBSERVED_AT,
    opportunities: [opportunity],
    runtimeJobs: [],
    generalReceipts: [],
    applicationReceipts: [],
    humanTasks: [],
    earnings: [],
  };
  if (overrides.foreignTenant) {
    input.opportunities = [{ ...opportunity, tenant_id: "tenant-b" }];
  }
  if (overrides.unverifiedCash) {
    input.earnings = [{
      tenant_id: TENANT,
      entry_key: "earning-1",
      kind: "financial_external_income",
      amount_minor: "100",
      currency: "JPY",
      verified: false,
      occurred_at: OBSERVED_AT,
    }];
  }
  return { ...input, ...overrides };
}

test("projection separates opportunity value from verified cash", () => {
  const view = projectMoneyPrinter(fixture());
  assert.equal(view.metrics.opportunity_value, "50000");
  assert.equal(view.metrics.paid_verified, "0");
});

test("projection rejects cross-tenant and unverified money", () => {
  assert.throws(() => projectMoneyPrinter(fixture({ foreignTenant: true })), /tenant/);
  assert.throws(() => projectMoneyPrinter(fixture({ unverifiedCash: true })), /verified/);
});
