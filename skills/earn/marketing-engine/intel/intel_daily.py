#!/usr/bin/env python3
"""One bounded daily intel pass across text and competitor-video sources."""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import uuid

import intel_pull
import video_hook_judge
import video_intel


def run_daily(*, source_registry: pathlib.Path, video_registry: pathlib.Path,
              intel_root: pathlib.Path, evidence_root: pathlib.Path,
              pull=intel_pull.run_pull, discover=video_intel.discover_videos,
              ingest=video_intel.ingest_transcripts, judge=None,
              run_id: str | None = None, observed_at: str | None = None) -> dict:
    evidence_root = pathlib.Path(evidence_root)
    evidence_root.mkdir(parents=True, exist_ok=True)
    run_id = run_id or uuid.uuid4().hex
    observed_at = observed_at or dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    run_dir = evidence_root / run_id
    run_dir.mkdir(exist_ok=False)
    if judge is None:
        def judge(**kwargs):
            return video_hook_judge.judge_pending_video_hooks(
                **kwargs, judge=video_hook_judge.agent_hook_judge)
    steps = {}
    steps["text_pull"] = pull(
        registry_path=source_registry, intel_root=intel_root,
        evidence_root=evidence_root / "text-pulls", judge=intel_pull.agent_judge)
    steps["video_discover"] = discover(
        registry_path=video_registry, intel_root=intel_root,
        evidence_root=evidence_root / "video-discovery")
    steps["video_ingest"] = ingest(
        registry_path=video_registry, intel_root=intel_root,
        evidence_root=evidence_root / "video-ingest")
    steps["video_judge"] = judge(
        intel_root=intel_root, evidence_root=evidence_root / "video-judge")
    allowed = {
        "text_pull": {"success", "partial"},
        "video_discover": {"success", "partial"},
        "video_ingest": {"success", "partial", "skipped"},
        "video_judge": {"success", "skipped"},
    }
    hard_failure = any(steps[name].get("status") not in accepted
                       for name, accepted in allowed.items())
    if hard_failure:
        status = "failed"
    elif any(step["status"] == "partial" for step in steps.values()):
        status = "partial"
    else:
        status = "success"
    receipt = {"schema_version": "marketing.intel-daily.v1", "run_id": run_id,
               "observed_at": observed_at, "status": status, "steps": steps}
    (run_dir / "run.json").write_text(json.dumps(receipt, ensure_ascii=False,
                                                  sort_keys=True, indent=2) + "\n",
                                       encoding="utf-8")
    return receipt
