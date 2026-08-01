"use strict";
const { createHash } = require("node:crypto");
const UUID=/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const REGISTRY=/^funder-registry:[0-9a-f]{64}$/; const SHA=/^[0-9a-f]{64}$/; const ID=/^[a-z0-9][a-z0-9._-]{1,99}$/;
const sha=(x)=>createHash("sha256").update(String(x)).digest("hex");
function stable(v){if(Array.isArray(v))return`[${v.map(stable).join(",")}]`;if(v&&typeof v==="object")return`{${Object.keys(v).sort().map(k=>`${JSON.stringify(k)}:${stable(v[k])}`).join(",")}}`;return JSON.stringify(v);}
function fail(x){throw new Error(`funder submission-day ${x} invalid`);}
function url(v){let x;try{x=new URL(String(v||""));}catch{fail("URL");}if(x.protocol!=="https:"||x.username||x.password||!x.hostname.includes("."))fail("URL");x.hash="";return x.toString();}
function day(ms){const p=new Intl.DateTimeFormat("en-CA",{timeZone:"Asia/Tokyo",year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(new Date(ms));const g=t=>p.find(x=>x.type===t).value;return`${g("year")}-${g("month")}-${g("day")}`;}
function evidence(claim,sources,field){if(!claim||!sources.has(claim.source_id)){fail("evidence");}const excerpt=String(claim[field]||"").trim();if(!excerpt||excerpt.length>1500||!sources.get(claim.source_id).content.includes(excerpt))fail("evidence");return{source_id:claim.source_id,evidence_sha256:sha(excerpt)};}
function buildFunderSubmissionDayGate(input={}){
 const tenant=String(input.tenantId||"").trim(), attempt=String(input.attemptId||"").toLowerCase(), evaluated=Date.parse(String(input.evaluatedAt||"")), reg=input.registryEntry||{};
 if(!tenant||tenant.length>128||!UUID.test(attempt)||!Number.isFinite(evaluated)||!REGISTRY.test(String(reg.registry_id||""))||!ID.test(String(reg.funder_id||""))||!Array.isArray(input.officialSources)||!input.assessment)fail("input");
 const rootUrls=new Set([url(reg.official_url),url(reg.source_url)]), sources=new Map(), roots=[];
 for(const raw of input.officialSources){const id=String(raw&&raw.source_id||""),u=url(raw&&raw.url),f=Date.parse(String(raw&&raw.fetched_at||"")),content=String(raw&&raw.content||"");
  if(!ID.test(id)||sources.has(id)||!Number.isFinite(f)||f>evaluated||evaluated-f>6*3600000||day(f)!==day(evaluated)||!content||content.length>2_000_000||!SHA.test(String(raw.content_sha256||""))||sha(content)!==raw.content_sha256||!Array.isArray(raw.links))fail("source");
  const links=[...new Set(raw.links.map(url))]; const s={source_id:id,url:u,fetched_at:new Date(f).toISOString(),content_sha256:raw.content_sha256,links,content};sources.set(id,s);if(rootUrls.has(u))roots.push(s);
 }
 if(roots.length<1)fail("linked source"); const linked=new Set([...rootUrls,...roots.flatMap(x=>x.links)]);if([...sources.values()].some(x=>!linked.has(x.url)))fail("linked source");
 const a=input.assessment, assessed=(a.assessed_source_ids||[]).map(String);if(a.program_id!==reg.funder_id||new Set(assessed).size!==assessed.length||stable([...assessed].sort())!==stable([...sources.keys()].sort()))fail("assessment");
 const kit=input.companyFacts||{},kitText=String(kit.content||"");if(kit.ref!=="application-kit://KIT.md"||!kitText||!SHA.test(String(kit.digest||""))||sha(kitText)!==kit.digest)fail("company facts");
 const refs={deadline:evidence(a.deadline,sources,"evidence_excerpt"),location:evidence(a.location,sources,"evidence_excerpt"),solo:evidence(a.solo,sources,"evidence_excerpt"),terms:evidence(a.terms,sources,"evidence_excerpt"),eligibility:evidence(a.eligibility,sources,"program_evidence_excerpt")};
 const factExcerpt=String(a.eligibility.company_fact_excerpt||"").trim();if(!factExcerpt||!kitText.includes(factExcerpt)||!String(a.eligibility.rationale||"").trim())fail("eligibility evidence");
 if(!["open","closed","rolling","late_open"].includes(a.deadline.status)||!["yes","no","unknown"].includes(a.solo.value)||!["eligible","ineligible","unknown"].includes(a.eligibility.value))fail("assessment");
 const closes=a.deadline.closes_at===null?null:Date.parse(String(a.deadline.closes_at));if(a.deadline.closes_at!==null&&!Number.isFinite(closes))fail("deadline");
 if(a.deadline.display_date!==null&&!/^\d{4}-\d{2}-\d{2}$/.test(String(a.deadline.display_date)))fail("deadline");
 const terms=String(a.terms.summary||"").replace(/\s+/g," ").trim(), location=String(a.location.value||"").replace(/\s+/g," ").trim();if(!terms||terms.length>1000||!location||location.length>300)fail("assessment");
 const termsHash=sha(terms);let decision="allow",reason="all five submission-day facts verified";
 const drift=(reg.next_deadline!==null&&reg.next_deadline!==a.deadline.display_date)||(reg.terms_hash!==null&&reg.terms_hash!==termsHash)||(reg.solo_allowed!=="unknown"&&reg.solo_allowed!==a.solo.value)||(reg.location!=="unknown"&&reg.location!==location);
 if(drift){decision="registry_refresh_required";reason="same-day official facts contradict a known registry fact";}
 else if(reg.status==="closed"||a.deadline.status==="closed"||(Number.isFinite(closes)&&closes<=evaluated)){decision="deadline_closed";reason="official deadline is closed";}
 else if(a.solo.value!=="yes"){decision="solo_not_verified";reason="solo founder acceptance is not verified";}
 else if(a.eligibility.value!=="eligible"){decision="eligibility_not_verified";reason="current eligibility is not verified";}
 const core={schema_version:1,tenant_id:tenant,attempt_id:attempt,registry_id:reg.registry_id,funder_id:reg.funder_id,evaluated_at:new Date(evaluated).toISOString(),tokyo_day:day(evaluated),decision,submit_allowed:decision==="allow",reason,deadline_status:a.deadline.status,deadline_at:Number.isFinite(closes)?new Date(closes).toISOString():null,deadline_display_date:a.deadline.display_date,location,solo_allowed:a.solo.value,eligibility:a.eligibility.value,terms_hash:termsHash,kit_ref:kit.ref,kit_digest:kit.digest,company_fact_evidence_sha256:sha(factExcerpt),rationale_sha256:sha(a.eligibility.rationale),evidence_refs:refs,source_receipts:[...sources.values()].map(({content,links,...x})=>({...x,link_count:links.length})).sort((x,y)=>x.source_id.localeCompare(y.source_id))};
 const digest=sha(stable(core));return Object.freeze({...core,gate_id:`funder-day-gate:${digest}`,gate_digest:digest});
}
module.exports={buildFunderSubmissionDayGate};
