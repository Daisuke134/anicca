"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { resolveLocalAgentUsageAttribution } = require("./cfo-local-agent-usage-attribution.js");
const registry = require("../config/cfo-financial-units.json");

const cases = [
  ["gig", "gig-hourly", "gig_work"], ["gig-loop", "self-fix-gig-loop", "gig_work"], ["gig-oauth-parity", "gig-oauth-refresh", "gig_work"], ["freelancer-work-sync", "freelancer-bid", "gig_work"], ["bounty", "bounty-daily", "gig_work"],
  ["job-search", "job-search-daily", "job_income"], ["capafy", "capafy-daily", "capafy_marketplace"], ["capafy-loop", "self-fix-capafy-loop", "capafy_marketplace"], ["capafy-verify", "budget-guard-probe", "capafy_marketplace"],
  ["life-manager", "life-manager-daily", "life_manager_saas"], ["life-manager-dev", "life-manager-dev-daily", "life_manager_saas"], ["life-manager-dev-promote", "life-manager-promote-daily", "life_manager_saas"], ["reddit", "reddit-loop-daily", "life_manager_saas"], ["reddit-loop", "self-fix-reddit-loop", "life_manager_saas"],
  ["larry-marketing", "larry-campaign", "anicca_ios"], ["honne-marketing", "reelclaw-honne-daily", "anicca_ios"],
];
const expectedIds = ["gig_work", "job_income", "capafy_marketplace", "life_manager_saas", "anicca_ios"];

test("maps every closed rule to a registered frozen attribution receipt", () => {
  assert.ok(expectedIds.every((id) => registry.financial_units.some((unit) => unit.financial_unit_id === id)));
  for (const [loop, taskLabel, financial_unit_id] of cases) {
    const receipt = resolveLocalAgentUsageAttribution(loop, taskLabel);
    assert.deepEqual(receipt, { mapping_id: "local_agent_usage_v1", financial_unit_id, attribution_status: "attributed" });
    assert.deepEqual(Object.keys(receipt), ["mapping_id", "financial_unit_id", "attribution_status"]); assert.ok(Object.isFrozen(receipt));
  }
  for (const [loop, taskLabel] of [["connector", "connector-send"], ["connector-outbound-loop", "self-fix-connector-outbound-loop"], ["gig", "gig"]]) assert.deepEqual(resolveLocalAgentUsageAttribution(loop, taskLabel), { mapping_id: "local_agent_usage_v1", financial_unit_id: null, attribution_status: "unattributed" });
});

test("rejects invalid loop and task labels with fixed redacted errors", () => {
  for (const loop of ["", " gig", 1, null]) assert.throws(() => resolveLocalAgentUsageAttribution(loop, "task"), new RegExp("^Error: cfo_local_agent_attribution_invalid:invalid_loop$"));
  for (const taskLabel of ["", " task", 1, null]) assert.throws(() => resolveLocalAgentUsageAttribution("gig", taskLabel), new RegExp("^Error: cfo_local_agent_attribution_invalid:invalid_task_label$"));
});
