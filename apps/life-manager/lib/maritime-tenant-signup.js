'use strict';
const {projectFinancialRecord}=require('./financial-record-contract.js');
const UID=/^lm_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
// Per-tenant self-signup registry. The tenant agent creates its OWN new account
// on its own Maritime computer with its own agent mail; founder/company accounts
// and sessions are never inputs. Capafy is first; every platform we earn on is
// added here as its tenant runbook lands. State and credentials live only in the
// tenant home (index references below, never values).
const TENANT_PLATFORMS=Object.freeze([
 Object.freeze({id:'capafy',enabled:true,firstAction:'publish_listing',stateDir:'state/capafy-autopublish'}),
 Object.freeze({id:'promptbase',enabled:false,firstAction:'publish_listing',stateDir:'state/promptbase'}),
 Object.freeze({id:'apify',enabled:false,firstAction:'publish_actor',stateDir:'state/apify'}),
 Object.freeze({id:'note',enabled:false,firstAction:'publish_article',stateDir:'state/note'}),
 Object.freeze({id:'substack',enabled:false,firstAction:'publish_article',stateDir:'state/substack'}),
 Object.freeze({id:'medium',enabled:false,firstAction:'publish_article',stateDir:'state/medium'}),
 Object.freeze({id:'crowdworks',enabled:false,firstAction:'submit_proposal',stateDir:'state/crowdworks'}),
 Object.freeze({id:'lancers',enabled:false,firstAction:'submit_proposal',stateDir:'state/lancers'}),
 Object.freeze({id:'coconala',enabled:false,firstAction:'publish_service',stateDir:'state/coconala'}),
 Object.freeze({id:'contra',enabled:false,firstAction:'submit_proposal',stateDir:'state/contra'}),
 Object.freeze({id:'guru',enabled:false,firstAction:'submit_proposal',stateDir:'state/guru'}),
 Object.freeze({id:'whop',enabled:false,firstAction:'publish_product',stateDir:'state/whop'}),
 Object.freeze({id:'x402',enabled:false,firstAction:'sell_service',stateDir:'state/x402'}),
]);
const NEXT_STATE=Object.freeze({none:'signed_up',signed_up:'bound',bound:'first_action_done',first_action_done:null});
function buildTenantSignupPlan({uid,platformId}={}){
 const invalid=()=>{throw new Error('tenant_signup_plan_invalid');};
 const platform=TENANT_PLATFORMS.find(p=>p.id===platformId);
 if(typeof uid!=='string'||!UID.test(uid)||!platform||!platform.enabled)invalid();
 return Object.freeze({
  tenantId:uid,platformId,
  signup:Object.freeze({identityRef:'tenant-home/vault/agent-mail',credentialStorage:'tenant_home_only',accountOwner:'tenant_agent'}),
  steps:Object.freeze([
   Object.freeze({id:'allocate_computer',detail:'maritime_end_user_agent_via_ensureAgent'}),
   Object.freeze({id:'agent_self_signup',detail:'own_agent_mail_new_account_on_tenant_computer'}),
   Object.freeze({id:'binding_persist',detail:platform.stateDir}),
   Object.freeze({id:'first_revenue_action',detail:platform.firstAction}),
   Object.freeze({id:'report_emit',detail:'daily_result_and_dashboard'}),
  ]),
 });
}
function advanceTenantPlatformState(current,next){
 if(!Object.prototype.hasOwnProperty.call(NEXT_STATE,current)||NEXT_STATE[current]!==next){
  throw new Error('tenant_signup_state_invalid');
 }
 return next;
}
// Per-user dashboard projection (the /open shape, per tenant): earnings grouped
// by platform from verified financial records only, plus what the agent is
// actually doing (actions + work entries from the daily result). Unverified or
// missing observations stay unknown; nothing is estimated.
function buildTenantDashboard({dailyResult,financialRecords=[]}={}){
 const invalid=()=>{throw new Error('tenant_dashboard_invalid');};
 if(!dailyResult||typeof dailyResult.tenantId!=='string'||!UID.test(dailyResult.tenantId)||!Array.isArray(financialRecords))invalid();
 const uid=dailyResult.tenantId;
 const byPlatform=new Map();
 let unmeasuredRecords=0;
 for(const raw of financialRecords){
  const record=projectFinancialRecord(raw);
  if(record.subject_id!==uid||record.scope!=='business')invalid();
  if(record.kind!=='business_revenue')continue;
  if(record.verification.status!=='verified'){unmeasuredRecords++;continue;}
  const platform=record.source.provider;
  if(!byPlatform.has(platform))byPlatform.set(platform,new Map());
  const byCurrency=byPlatform.get(platform);
  byCurrency.set(record.currency,(byCurrency.get(record.currency)||0)+record.amount_minor);
 }
 const earningsByPlatform=[...byPlatform.entries()].sort(([a],[b])=>a<b?-1:1).map(([platform,byCurrency])=>({
  platform,amounts:[...byCurrency.entries()].sort(([a],[b])=>a<b?-1:1).map(([currency,amountMinor])=>({currency,amountMinor})),
 }));
 return Object.freeze({
  schemaVersion:1,tenantId:uid,date:dailyResult.date,timezone:dailyResult.timezone,
  earningsStatus:earningsByPlatform.length?'observed':'unknown',
  earningsByPlatform,unmeasuredRecords,
  totals:dailyResult.financial,
  actions:dailyResult.actions,
  activity:Object.freeze(dailyResult.work.map(work=>Object.freeze({
   jobId:work.jobId,status:work.status,artifactRefs:work.artifactRefs,errorClass:work.errorClass}))),
  reportingChannels:Object.freeze(['email_daily','browser_page']),
 });
}
module.exports={TENANT_PLATFORMS,buildTenantSignupPlan,advanceTenantPlatformState,buildTenantDashboard};
