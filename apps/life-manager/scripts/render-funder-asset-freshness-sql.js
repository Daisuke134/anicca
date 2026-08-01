#!/usr/bin/env node
"use strict";
const fs=require("node:fs"),{validateFunderAssetFreshnessGate}=require("../lib/funder-asset-freshness.js");
const quote=value=>value===null?"NULL":`'${String(value).replaceAll("'","''")}'`;
function render(candidate){const gate=validateFunderAssetFreshnessGate(candidate),values=[gate.tenant_id,gate.attempt_id,gate.gate_id,gate.funder_id,gate.evaluated_at,gate.expires_at,gate.decision,gate.submit_allowed,gate.kit_digest,gate.kit_captured_at,JSON.stringify(gate.submission_binding),JSON.stringify(gate.payload_claim_receipts),JSON.stringify(gate.dashboard_receipt),JSON.stringify(gate.mrr_receipt),JSON.stringify(gate.claim_receipts),JSON.stringify(gate.asset_receipts),JSON.stringify(gate.refresh_reasons),gate.gate_digest,gate.attestation_signature].map(quote);return `\\set ON_ERROR_STOP on
BEGIN;
DO $gate$
DECLARE persisted_digest text;
BEGIN
  INSERT INTO public.lm_funder_asset_freshness_gates (tenant_id,attempt_id,gate_id,funder_id,evaluated_at,expires_at,decision,submit_allowed,kit_digest,kit_captured_at,submission_binding,payload_claim_receipts,dashboard_receipt,mrr_receipt,claim_receipts,asset_receipts,refresh_reasons,gate_digest,attestation_signature) VALUES (${values.join(",")}) ON CONFLICT (tenant_id,attempt_id) DO NOTHING;
  SELECT gate_digest INTO persisted_digest FROM public.lm_funder_asset_freshness_gates WHERE tenant_id=${quote(gate.tenant_id)} AND attempt_id=${quote(gate.attempt_id)}::uuid;
  IF persisted_digest IS DISTINCT FROM ${quote(gate.gate_digest)} THEN RAISE EXCEPTION 'funder asset freshness gate collision'; END IF;
END
$gate$;
COMMIT;
SELECT gate_id,decision,submit_allowed FROM public.lm_funder_asset_freshness_gates WHERE tenant_id=${quote(gate.tenant_id)} AND attempt_id=${quote(gate.attempt_id)}::uuid;
`;}
if(require.main===module){try{const file=process.argv[2];if(!file)throw new Error("usage: render-funder-asset-freshness-sql <gate.json>");process.stdout.write(render(JSON.parse(fs.readFileSync(file,"utf8"))));}catch(error){process.stderr.write(`${error.message}\n`);process.exitCode=1;}}
module.exports={render};
