#!/usr/bin/env node
"use strict";
const fs=require("node:fs");
const quote=value=>value===null?"NULL":`'${String(value).replaceAll("'","''")}'`;
function render(gate){if(!gate||gate.schema_version!==1||!/^funder-freshness-gate:[0-9a-f]{64}$/.test(String(gate.gate_id||""))||gate.gate_digest!==gate.gate_id.slice(gate.gate_id.indexOf(":")+1))throw new Error("funder asset freshness gate invalid");const values=[gate.tenant_id,gate.attempt_id,gate.gate_id,gate.funder_id,gate.evaluated_at,gate.decision,gate.submit_allowed,gate.kit_digest,JSON.stringify(gate.dashboard_receipt),JSON.stringify(gate.mrr_receipt),JSON.stringify(gate.claim_receipts),JSON.stringify(gate.asset_receipts),JSON.stringify(gate.refresh_reasons),gate.gate_digest].map(quote);return `\\set ON_ERROR_STOP on
BEGIN;
INSERT INTO public.lm_funder_asset_freshness_gates (tenant_id,attempt_id,gate_id,funder_id,evaluated_at,decision,submit_allowed,kit_digest,dashboard_receipt,mrr_receipt,claim_receipts,asset_receipts,refresh_reasons,gate_digest) VALUES (${values.join(",")}) ON CONFLICT (tenant_id,attempt_id) DO NOTHING;
COMMIT;
SELECT gate_id,decision,submit_allowed FROM public.lm_funder_asset_freshness_gates WHERE tenant_id=${quote(gate.tenant_id)} AND attempt_id=${quote(gate.attempt_id)}::uuid;
`;}
if(require.main===module){try{const file=process.argv[2];if(!file)throw new Error("usage: render-funder-asset-freshness-sql <gate.json>");process.stdout.write(render(JSON.parse(fs.readFileSync(file,"utf8"))));}catch(error){process.stderr.write(`${error.message}\n`);process.exitCode=1;}}
module.exports={render};
