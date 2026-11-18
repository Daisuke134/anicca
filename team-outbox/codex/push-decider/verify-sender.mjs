import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
// Run the actual patched job with isolated database, Manager and APNs adapters.
const source = fs.readFileSync(process.argv[2], 'utf8').replace(/^import .*;\n/gm, '').replace(/export /g, '');
const deliveries = [], sends = [], messages = [];
let decisions = 0;
const match = (row, where) => Object.entries(where).every(([k,v]) => row[k] instanceof Date ? +row[k] === +v : row[k] === v);
const db = {
 pushToken: { findMany: async () => ['one','two'].flatMap(id => [1,2].map(device => ({id:id+device, profileId:id,token:id+device}))) },
 userSetting: { findUnique: async () => ({timezone:'UTC',language:'en'}) },
 profile: { findUnique: async ({where}) => ({metadata:{goal:where.id === 'one' ? 'Rest' : 'Focus'}}) },
 nudgeOutcome: { findMany: async () => [] },
 nudgeDelivery: {
  findFirst: async ({where}) => deliveries.find(r => match(r,where)),
  create: async ({data}) => { deliveries.push(data); return data; },
  count: async () => 0,
  updateMany: async ({where,data}) => {const row=deliveries.find(r=>match(r,where)); if(!row)return {count:0};Object.assign(row,data);return {count:1};},
  update: async ({where,data}) => Object.assign(deliveries.find(r=>r.id===where.id),data),
 },
 nudgeDeliverySend: {
  findMany: async () => [],
  findUnique: async ({where}) => sends.find(r=>match(r,where.deliveryId_pushTokenId)),
  create: async ({data}) => { const row={...data,id:String(sends.length)}; sends.push(row); return row; },
  updateMany: async ({where,data}) => { const r=sends.find(r=>r.id===where.id); if(r.status!=='queued') return {count:0}; Object.assign(r,data);return {count:1}; },
  update: async ({where,data}) => Object.assign(sends.find(r=>r.id===where.id),data),
 },
 $executeRaw: async () => {},
};
db.$transaction = async fn => fn(db);
const logger = {warn(){},error(){}};
const context = vm.createContext({createHash, prisma:db, baseLogger:{withContext:()=>logger},
 SCHEDULE_MAP:{}, getRawPushEnv:()=> 'dev',parsePushEnv:()=> 'dev',
 process:{env:{APNS_ENDPOINT:'development', MANAGER_PRODUCT_URL:'http://fixture',MANAGER_SENDER_TOKEN:'fixture'}},
 ApnsClient:{}, ApnsError:class extends Error {},getEntitlementState:async()=>({plan:'free'}),
 normalizeCatalogLang:x=>x, appName:()=> 'Anicca',toLocalDateString:()=> '2026-11-17',toLocalTimeHHMM:()=> '09:00',
 Date, JSON, AbortSignal,
 fetch:async (_,options)=> { decisions++; const request=JSON.parse(options.body).decisions[0];return {ok:true,json:async()=>({decisions:[{delivery_id:request.delivery_id,backend:'manager-v1',policy_version:'manager-generated-v1',assigned_probability:1,send:true,chosen:{text:request.push_state.profile.goal}}]})}; },
});
vm.runInContext(source,context);
const apnsClient={sendAlert:async ({payload})=>{messages.push(payload);return {apnsId:'fixture'};}};
await context.runProblemNudgeApnsSender(new Date('2026-11-17T09:00:00Z'),{apnsClient});
assert.deepEqual(messages.map(m=>m.aps.alert.body),['Rest','Focus']);
await context.runProblemNudgeApnsSender(new Date('2026-11-17T09:00:00Z'),{apnsClient});
assert.equal(messages.length,2);assert.equal(decisions,2);
assert.equal(deliveries.length,2);
for (const row of deliveries) assert.equal(JSON.parse(row.messageDetail).delivery_id,row.id);
console.log('fixture same slot 09:00: one=Rest; two=Focus; first sends=2; rerun duplicate sends=0; decision records=2');

// A later slot with an unreachable Manager must never use rotation.
deliveries.length=0;sends.length=0;messages.length=0;
context.fetch=async()=>{throw new Error('offline');};
await context.runProblemNudgeApnsSender(new Date('2026-11-17T09:00:00Z'),{apnsClient});
assert.equal(messages.length,0);
console.log('two devices per user: no duplicate user-slot send; Manager offline: sends=0');
