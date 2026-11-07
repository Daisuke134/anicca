"""MG-01 real public-host S1: incumbent vs Qwen3-4B on one verified snapshot.

The incumbent fixed-rule planner and the actual language model inspect
different representations of the SAME independently hashed six-page
public website snapshot. Only public owned content is read; no personal
data, no email, no site modification, no notifications.

A 1-snapshot agreement is NOT a proof of accuracy, benefit, causal effect,
or product readiness. Metrics label actual model forward pass separately
from official public-site byte readback. All model and URL inputs are pinned.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from manager_core.digital_environment import PAGES, validate_catalog, verify_readback
from manager_core.owned_catalog_planner import _read_served_bundle
from manager_core.zero_ui_host_shadow_v1 import run_public_host_shadow
from manager_core.digital_handoff import PUBLIC_BASE

SCHEMA="manager.mg01.public_s1.case.v1"
RECEIPT_SCHEMA="manager.mg01.public_s1.real_model_comparison.v1"
MODEL="Qwen/Qwen3-4B-Instruct-2507"
GGUF_SHA256="2fde00ce69dd4899c70d020845e2638353015bba0fdf161b3eb965f2bca4464e"
GGUF_SIZE=2497280736
SOURCE_CATALOG=ROOT / "public_goods/service/catalog.json"
_DECISION=re.compile(r"^(NO_ACTION|REVIEW_ONLY)[\s\.\u3002\u3001]*$")
_HEX64=re.compile(r"^[0-9a-f]{64}$")


class AnchorFeatures(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.official=[]
        self.self_nav=[]
    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        row=dict(attrs)
        if "data-official" in row:
            self.official.append({"href":row.get("href"),"aria":row.get("aria-label")})
        if "aria-current" in row:
            self.self_nav.append({
                "href":row.get("href"),
                "aria_current":row.get("aria-current"),
            })


def prepare_verified_website_case(
    manifest: dict, bodies: dict[str,bytes], raw_manifest: bytes, catalog: dict,
    *, observed_at: datetime,
) -> dict:
    """Use one immutable public snapshot for BOTH incumbent and model features."""
    if not isinstance(observed_at,datetime) or observed_at.utcoffset() is None:
        raise ValueError("timezone-aware observation required")
    validate_catalog(catalog)
    if type(raw_manifest) is not bytes or len(raw_manifest)>128_000:
        raise ValueError("untrusted manifest bytes")
    try:
        if json.loads(raw_manifest.decode("utf-8")) != manifest:
            raise ValueError("manifest content mismatch")
    except (UnicodeError,TypeError,json.JSONDecodeError) as exc:
        raise ValueError("invalid manifest bytes") from exc
    site_proof=verify_readback(manifest,bodies)
    snap_sha=sha256(raw_manifest).hexdigest()

    start=time.perf_counter()
    incumbent=run_public_host_shadow(
        enabled=True,
        read_snapshot=lambda: (manifest,bodies,raw_manifest),
        catalog=catalog,
        observed_at=observed_at,
    )
    baseline_sec=time.perf_counter()-start
    incumbent_decision=incumbent["candidate"]["decision"]
    if incumbent_decision not in ("NO_ACTION","REVIEW_ONLY") or incumbent["world_action"]!="NO_ACTION":
        raise ValueError("incumbent did not return inert documented decision")

    rows=[]
    for name in sorted(PAGES):
        html=bodies[name].decode("utf-8")
        parser=AnchorFeatures()
        parser.feed(html)
        official=[
            {"href":x["href"]}
            for x in parser.official
        ]
        rows.append({
            "page":name,
            "body_sha256":sha256(bodies[name]).hexdigest(),
            "official_links":official,
            "self_nav_aria_current":parser.self_nav,
        })

    return {
        "schema":SCHEMA,
        "public_url":PUBLIC_BASE,
        "source_commit":manifest["source_commit"],
        "manifest_sha256":snap_sha,
        "pages":len(bodies),
        "observed_at":observed_at.isoformat(),
        "features":{
            "source_sha256":snap_sha,
            "pages":rows,
            "expected_official_resources":[
                {"id":r["id"],"domain":r["domain"],"url":r["url"]}
                for r in catalog["resources"]
            ],
        },
        "baseline":{
            "decision":incumbent_decision,
            "rule":"existing_manager_owned_catalog_planner",
            "input_manifest_sha256":snap_sha,
            "runtime_seconds":round(baseline_sec,7),
        },
        "technical_proof":site_proof["technical_proof"],
        "human_outcome_measured":False,
        "world_action":"NO_ACTION",
    }


def render_model_prompt(case: dict) -> str:
    """Only features derived from same verified public bytes, NO incumbent label."""
    if case.get("schema")!=SCHEMA:
        raise ValueError("invalid site case")
    features=case["features"]
    if (features.get("source_sha256")!=case.get("manifest_sha256")
            or len(features.get("pages",[]))!=6):
        raise ValueError("unbound public feature projection")
    payload=json.dumps(features,ensure_ascii=False,sort_keys=True,separators=(",",":"))
    prompt=(
        "<|im_start|>user\n"
        "You are an independent quality checker of a PUBLIC, company-owned informational website. "
        "There is no personal/user data. Do NOT modify the site or contact anyone.\n"
        "Your task: check whether the fixed allowed maintenance rules permit a REVIEW for this current snapshot.\n"
        "Allowed rules: "
        "(1) An anchor marked data-official in finance.html, mental.html, or control.html "
        "that unambiguously references one expected official resource but uses the wrong href may be REVIEW_ONLY. "
        "(2) A finance.html or mental.html self-navigation link missing aria-current=page may be REVIEW_ONLY. "
        "If none is proven, choose NO_ACTION. When unsure choose NO_ACTION. "
        "This is not evidence of human benefit or welfare.\n"
        "Reply with exactly one standalone line containing one of the two labels "
        "[NO_ACTION, REVIEW_ONLY]. No other words.\n"
        f"Verified public-site features: {payload}\n"
        "<|im_end|>\n<|im_start|>assistant\n"
    )
    if len(prompt)>11000 or any(_DECISION.fullmatch(line.strip()) for line in prompt.splitlines()):
        raise ValueError("unsafe prompt layout for generated-answer-only parsing")
    return prompt


def parse_model_decision(stdout: str, expected_prompt: str) -> str|None:
    """Prevent echoed prompt's labels from being mis-scored as a model answer."""
    if type(stdout) is not str or type(expected_prompt) is not str:
        raise ValueError("text required")
    if any(_DECISION.fullmatch(l.strip()) for l in expected_prompt.splitlines()):
        return None
    text=re.sub(r"\x1b\[[0-9;]*m","",stdout)
    # Earlier b12137 one-shot CLI still echoed the prompt in some modes.
    if expected_prompt in text:
        text=text.rsplit(expected_prompt,1)[-1]
    else:
        marker="<|im_start|>assistant\n"
        if marker in text:
            text=text.rsplit(marker,1)[-1]
        # Without the exact assistant marker, a partial prompt echo is safe
        # only because render_model_prompt provably contains NO standalone
        # decision label; strict full-line matching below rejects summaries.
    choices=[m.group(1) for row in text.splitlines()
             if (m:=_DECISION.fullmatch(row.strip())) is not None]
    return choices[0] if len(choices)==1 else None


def independent_check(case: dict, public_reader: Callable[[],tuple[dict,dict,bytes]])->dict:
    """Second fresh independent public readback of the same exact manifest+pages."""
    if case.get("schema")!=SCHEMA:
        raise ValueError("invalid comparison case")
    try:
        m,b,raw=public_reader()
        if json.loads(raw)!=m:
            raise ValueError("raw source changed")
        proof=verify_readback(m,b)
        if (sha256(raw).hexdigest()!=case["manifest_sha256"]
                or m["source_commit"]!=case["source_commit"]
                or proof["technical_proof"]!=case["technical_proof"]):
            return {"status":"READBACK_MISMATCH","public_site_unchanged":False}
        return {
            "status":"SAME_PUBLIC_SNAPSHOT",
            "public_site_unchanged":True,
            "independent_public_manifest_sha256":sha256(raw).hexdigest(),
            "pages_reverified":len(b),
        }
    except (OSError,ValueError,TypeError,KeyError):
        return {"status":"READBACK_MISMATCH","public_site_unchanged":False}


def score_model_vs_incumbent(
    case:dict, model_decision:str|None,
    *, model_latency_sec:float, baseline_latency_sec:float,
    host_read_latency_sec:float, readback:dict,
    model_sha256:str, gguf_verified:bool,
)->dict:
    """Descriptive SAME-SNAPSHOT agreement only; NEVER human benefit or efficacy."""
    if case.get("schema")!=SCHEMA or case["world_action"]!="NO_ACTION":
        raise ValueError("invalid case")
    if model_sha256!=GGUF_SHA256 and not _HEX64.fullmatch(str(model_sha256)):
        raise ValueError("invalid GGUF sha")
    if type(gguf_verified) is not bool:
        raise ValueError("GGUF verification required")
    for seconds in (model_latency_sec,baseline_latency_sec,host_read_latency_sec):
        if type(seconds) not in (float,int) or not math.isfinite(seconds) or seconds<0:
            raise ValueError("invalid measured latency")
    if readback.get("status")!="SAME_PUBLIC_SNAPSHOT":
        status="READBACK_MISMATCH"
        agreement=None
    elif model_decision not in ("NO_ACTION","REVIEW_ONLY") or not gguf_verified:
        status="MODEL_OUTPUT_INVALID"
        agreement=None
    else:
        status="ACTUAL_PUBLIC_HOST_MODEL_SHADOW_TECHNICAL"
        agreement=(model_decision==case["baseline"]["decision"])
    return {
        "schema":RECEIPT_SCHEMA,
        "status":status,
        "source_commit":case["source_commit"],
        "source_manifest_sha256":case["manifest_sha256"],
        "public_url":case["public_url"],
        "pages":case["pages"],
        "baseline_decision":case["baseline"]["decision"],
        "model_decision":model_decision,
        "agreement_with_incumbent":agreement,
        "number_of_real_site_snapshots":1,
        "model_id":MODEL,
        "model_sha256":model_sha256,
        "model_forward_pass_verified":gguf_verified,
        "baseline_latency_seconds":round(float(baseline_latency_sec),6),
        "model_latency_seconds":round(float(model_latency_sec),6),
        "host_latency_seconds":round(float(host_read_latency_sec),6),
        "independent_readback":readback,
        "runner_standard_public_list_price_usd":0.0,
        "actual_provider_invoice_usd":None,
        "cost_source":"https://docs.github.com/en/actions/concepts/billing-and-usage",
        "execution_environment":"GitHub Actions ubuntu-24.04 standard PUBLIC repository",
        "external_writes":0,
        "provider_writes":0,
        "notifications_sent":0,
        "personal_data_accessed":False,
        "world_action":"NO_ACTION",
        "production_user_count":0,
        "proves_business_value_or_human_welfare":False,
        "causal_effect_verified":False,
        "model_production_approved":False,
        "full_real_business_s1_acceptance_claimed":False,
        "scientific_boundary":"One model-vs-rule public-site decision: technical agreement/disagreement only; not welfare or generalization.",
    }


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--llama-cli",type=Path,required=True)
    p.add_argument("--model",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--dry-run",action="store_true")
    args=p.parse_args()
    start=time.perf_counter()
    manifest,bodies,raw=_read_served_bundle()
    host_sec=time.perf_counter()-start
    catalog=json.loads(SOURCE_CATALOG.read_text(encoding="utf-8"))
    case=prepare_verified_website_case(manifest,bodies,raw,catalog,observed_at=datetime.now(timezone.utc))
    prompt=render_model_prompt(case)
    prompt_sha=sha256(prompt.encode()).hexdigest()

    if args.dry_run:
        report={"status":"REAL_PUBLIC_SITE_SOURCE_ONLY_NO_MODEL",
                "manifest_sha256":case["manifest_sha256"],
                "prompt_sha256":prompt_sha,
                "model_forward_pass_verified":False,
                "no_personal_data":True}
    else:
        from qwen3_mame_text_eval import build_llama_command
        if args.model.stat().st_size!=GGUF_SIZE:
            raise ValueError("model byte size mismatch")
        h=sha256()
        with args.model.open("rb") as stream:
            for chunk in iter(lambda:stream.read(8*1024*1024),b""):
                h.update(chunk)
        if h.hexdigest()!=GGUF_SHA256:
            raise ValueError("pinned GGUF hash mismatch")
        cmd=build_llama_command(str(args.llama_cli),str(args.model),prompt)
        start_model=time.perf_counter()
        proc=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                            timeout=150,text=True,encoding="utf-8",errors="replace")
        latency=time.perf_counter()-start_model
        if proc.returncode!=0:
            raise RuntimeError(f"llama CLI failed with exit code {proc.returncode}")
        answer=parse_model_decision(proc.stdout,prompt)
        readback=independent_check(case,_read_served_bundle)
        report=score_model_vs_incumbent(
            case,answer,model_latency_sec=latency,
            baseline_latency_sec=case["baseline"]["runtime_seconds"],
            host_read_latency_sec=host_sec,
            readback=readback,model_sha256=GGUF_SHA256,gguf_verified=True,
        )
        report.update({
            "prompt_sha256":prompt_sha,
            "model_raw_stdout_sha256":sha256(proc.stdout.encode()).hexdigest(),
            "llama_cpp_release":"b12137",
            "github_run_id":os.getenv("GITHUB_RUN_ID"),
            "model_invocations":1,
            "runner_model_artifact_downloaded":True,
            "no_new_production_deployment":True,
        })

    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({
        "status":report["status"],
        "source_sha256":report.get("source_manifest_sha256",report.get("manifest_sha256")),
        "incumbent":report.get("baseline_decision"),
        "model":report.get("model_decision"),
        "model_seconds":report.get("model_latency_seconds"),
        "readback":report.get("independent_readback"),
        "receipt":str(args.output)},ensure_ascii=False),flush=True)
    if report["status"] not in ("ACTUAL_PUBLIC_HOST_MODEL_SHADOW_TECHNICAL","REAL_PUBLIC_SITE_SOURCE_ONLY_NO_MODEL"):
        raise SystemExit("Real model comparison not accepted; fail-safe and preserve receipt")


if __name__=="__main__":
    main()
