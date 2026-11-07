'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const {financialRecordId}=require('./financial-record-contract.js');
const {TENANT_PLATFORMS,buildTenantSignupPlan,advanceTenantPlatformState,buildTenantDashboard}=require('./maritime-tenant-signup.js');
const {buildMaritimeDailyResult}=require('./maritime-manager-report.js');
const UID='lm_11111111-1111-4111-8111-111111111111';
function row(key,kind,amount,provider='capafy',verified=true){
 return {schema_version:1,record_type:'financial_record',record_id:financialRecordId(UID,key),subject_id:UID,
 scope:'business',kind,direction:kind==='business_revenue'||kind==='payout'?'credit':'debit',amount_minor:amount,currency:'USD',
 occurred_at:'2026-10-21T01:00:00Z',recorded_at:'2026-10-21T01:00:00Z',idempotency_key:key,
 source:{provider,source_type:'marketplace',external_ref:key},
 verification:{status:verified?'verified':'unverified',observed_at:'2026-10-21T01:00:00Z',evidence_refs:['capafy://receipt/'+key]}};
}
test('capafy is the first self-signup platform and the registry is extensible',()=>{
 assert.equal(TENANT_PLATFORMS[0].id,'capafy');
 assert.equal(TENANT_PLATFORMS[0].enabled,true);
 assert.ok(TENANT_PLATFORMS.length>1);
 assert.ok(TENANT_PLATFORMS.every(p=>typeof p.id==='string'&&typeof p.firstAction==='string'));
});
test('signup plan is per-tenant, ordered, and never references founder accounts',()=>{
 const plan=buildTenantSignupPlan({uid:UID,platformId:'capafy'});
 assert.deepEqual(plan.steps.map(s=>s.id),['allocate_computer','agent_self_signup','binding_persist','first_revenue_action','report_emit']);
 assert.equal(plan.tenantId,UID);
 assert.equal(plan.platformId,'capafy');
 assert.equal(plan.signup.identityRef,'tenant-home/vault/agent-mail');
 assert.equal(plan.signup.credentialStorage,'tenant_home_only');
 assert.equal(JSON.stringify(plan).includes('founder'),false);
 assert.throws(()=>buildTenantSignupPlan({uid:'bad',platformId:'capafy'}),/tenant_signup_plan_invalid/);
 assert.throws(()=>buildTenantSignupPlan({uid:UID,platformId:'nope'}),/tenant_signup_plan_invalid/);
});
test('platform state only advances in order',()=>{
 assert.equal(advanceTenantPlatformState('none','signed_up'),'signed_up');
 assert.equal(advanceTenantPlatformState('signed_up','bound'),'bound');
 assert.equal(advanceTenantPlatformState('bound','first_action_done'),'first_action_done');
 assert.throws(()=>advanceTenantPlatformState('none','bound'),/tenant_signup_state_invalid/);
 assert.throws(()=>advanceTenantPlatformState('first_action_done','signed_up'),/tenant_signup_state_invalid/);
});
test('dashboard groups verified earnings by platform and keeps the unknown unknown',()=>{
 const daily=buildMaritimeDailyResult({enrollment:{uid:UID,timezone:'Asia/Tokyo'},periodKey:'maritime:daily:2026-10-21'});
 const dash=buildTenantDashboard({dailyResult:daily,financialRecords:[row('s1','business_revenue',1200,'capafy'),row('s2','business_revenue',300,'promptbase'),row('s3','business_revenue',999,'capafy',false)]});
 assert.deepEqual(dash.earningsByPlatform,[
  {platform:'capafy',amounts:[{currency:'USD',amountMinor:1200}]},
  {platform:'promptbase',amounts:[{currency:'USD',amountMinor:300}]}]);
 assert.equal(dash.unmeasuredRecords,1);
 assert.deepEqual(dash.reportingChannels,['email_daily','browser_page']);
 assert.equal(dash.tenantId,UID);
 const empty=buildTenantDashboard({dailyResult:daily,financialRecords:[]});
 assert.deepEqual(empty.earningsByPlatform,[]);
 assert.equal(empty.earningsStatus,'unknown');
});
