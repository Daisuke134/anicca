"use strict";
const assert = require("node:assert/strict");
const { createHash, randomUUID } = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const { buildFunderSubmissionDayGate } = require("./funder-submission-day.js");
const { appendFunderSubmissionDayGate } = require("./funder-submission-day-store.js");
const SQL = fs.readFileSync(path.join(__dirname, "../migrations/2026-08-02-lm-funder-submission-day.sql"), "utf8");
const sha = (x) => createHash("sha256").update(x).digest("hex");
function fixture() {
  const content = "Applications close August 2 at 11:59pm PT. Solo founders may apply. Fellows work in New York. Terms are $400K for 7%. Frontier software founders are eligible.";
  const kit = "Anicca is an autonomous AI software company built by Daisuke as a solo founder.";
  return { tenantId:"dais-local", attemptId:randomUUID(), evaluatedAt:"2026-08-02T03:00:00.000Z",
    registryEntry:{ registry_id:`funder-registry:${"a".repeat(64)}`, funder_id:"spc-f26", official_url:"https://spc.example/program", source_url:"https://spc.example/program", next_deadline:"2026-08-02", terms_hash:null, solo_allowed:"yes", location:"New York", status:"open" },
    officialSources:[{ source_id:"program", url:"https://spc.example/program", fetched_at:"2026-08-02T02:30:00.000Z", content, content_sha256:sha(content), links:[] }],
    companyFacts:{ ref:"application-kit://KIT.md", digest:sha(kit), content:kit },
    assessment:{ program_id:"spc-f26", assessed_source_ids:["program"],
      deadline:{ status:"open", closes_at:"2026-08-03T06:59:00.000Z", display_date:"2026-08-02", source_id:"program", evidence_excerpt:"Applications close August 2 at 11:59pm PT." },
      location:{ value:"New York", source_id:"program", evidence_excerpt:"Fellows work in New York." },
      solo:{ value:"yes", source_id:"program", evidence_excerpt:"Solo founders may apply." },
      terms:{ summary:"$400K for 7%", source_id:"program", evidence_excerpt:"Terms are $400K for 7%." },
      eligibility:{ value:"eligible", source_id:"program", program_evidence_excerpt:"Frontier software founders are eligible.", company_fact_excerpt:"autonomous AI software company", rationale:"AI software and solo founder requirements match." }
    }
  };
}
test("all five same-day official facts create one submit-allowed receipt",()=>{
  const gate=buildFunderSubmissionDayGate(fixture());
  assert.equal(gate.submit_allowed,true); assert.equal(gate.decision,"allow");
  assert.match(gate.gate_id,/^funder-day-gate:[0-9a-f]{64}$/); assert.match(gate.terms_hash,/^[0-9a-f]{64}$/);
  assert.equal(JSON.stringify(gate).includes("Applications close"),false);
});
test("stale, fabricated, unlinked, and registry-drift evidence fail closed",()=>{
  const stale=fixture(); stale.officialSources[0].fetched_at="2026-08-01T00:00:00Z"; assert.throws(()=>buildFunderSubmissionDayGate(stale),/source/i);
  const fake=fixture(); fake.assessment.solo.evidence_excerpt="invented"; assert.throws(()=>buildFunderSubmissionDayGate(fake),/evidence/i);
  const link=fixture(); link.officialSources.push({...link.officialSources[0],source_id:"other",url:"https://evil.example/x"}); link.assessment.assessed_source_ids.push("other"); assert.throws(()=>buildFunderSubmissionDayGate(link),/linked/i);
  const drift=fixture(); drift.registryEntry.location="San Francisco"; assert.equal(buildFunderSubmissionDayGate(drift).decision,"registry_refresh_required");
});
test("closed deadline, solo no or unknown, and non-eligible judgment never allow submit",()=>{
  for (const mutate of [
    x=>{x.assessment.deadline.status="closed";x.assessment.deadline.closes_at="2026-08-01T00:00:00Z";},
    x=>{x.assessment.solo.value="no";}, x=>{x.assessment.solo.value="unknown";},
    x=>{x.assessment.eligibility.value="ineligible";}, x=>{x.assessment.eligibility.value="unknown";}
  ]) { const input=fixture(); mutate(input); assert.equal(buildFunderSubmissionDayGate(input).submit_allowed,false); }
});
test("ledger is append-only, tenant/attempt-bound, exact replay only",async()=>{
  assert.match(SQL,/CREATE TABLE IF NOT EXISTS public\.lm_funder_submission_day_gates/i); assert.match(SQL,/ENABLE ROW LEVEL SECURITY/i);
  assert.match(SQL,/REVOKE ALL .* FROM PUBLIC/i); assert.doesNotMatch(SQL,/UPDATE public\./i);
  const gate=buildFunderSubmissionDayGate(fixture()); const calls=[];
  const saved=await appendFunderSubmissionDayGate(gate,{query:async(sql,params)=>{calls.push({sql,params});return {rows:[{gate_id:params[2]}]};}});
  assert.equal(saved.inserted,true); assert.match(calls[0].sql,/ON CONFLICT .* DO NOTHING/i);
  await assert.rejects(()=>appendFunderSubmissionDayGate(gate,{query:async()=>({rows:[]})}),/collision/i);
});
