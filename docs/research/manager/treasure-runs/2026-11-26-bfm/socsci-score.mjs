import fs from 'node:fs';
import crypto from 'node:crypto';
const b=fs.readFileSync(process.argv[2]);
const sha=crypto.createHash('sha1').update('blob '+b.length+'\0').update(b).digest('hex');
if(sha!=='6b98b188930abea9ec89628bfd7a1a682f6a9c0d')throw Error('wrong input blob');
const score=(rows)=>{const keys=new Set();let invalid=0,sum=0,exact=0,dupes=0;const groups={};for(const r of rows){let k=[r.condition,r.task,r.sample_id].join(":");if(keys.has(k))dupes++;keys.add(k);let p=r.condition+":"+r.task;let g=groups[p]??={attempted:0,valid:0,sum:0,exact:0};g.attempted++;if(!Number.isFinite(r.pred)||!Number.isFinite(r.truth)||!(r.hi>r.lo)||r.pred<r.lo||r.pred>r.hi||r.truth<r.lo||r.truth>r.hi){invalid++;continue}let score=1-Math.abs(r.pred-r.truth)/(r.hi-r.lo);g.valid++;g.sum+=score;g.exact+=+(r.pred===r.truth);sum+=score;exact+=+(r.pred===r.truth)}return {n:rows.length,duplicates:dupes,invalid,valid:rows.length-invalid,normalized_valid_only:sum/(rows.length-invalid),normalized_invalid_zero:sum/rows.length,exact,groups:Object.entries(groups).map(([pair,g])=>({pair,attempted:g.attempted,valid:g.valid,normalized_valid:g.sum/g.valid,normalized_invalid_zero:g.sum/g.attempted,exact:g.exact}))}};
const result=score(b.toString('utf8').trim().split('\n').map(JSON.parse));
if(result.n!==512||result.duplicates!==0||result.valid!==499)throw Error('denominator mismatch');
console.log(JSON.stringify({source_blob:sha,...result},null,2));
