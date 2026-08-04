#!/usr/bin/env python3
"""Fail-closed verifier for the Gate 9 competitor-video pipeline."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess

from intel_store import read_jsonl, validate_store


NATIVE_URL = re.compile(r"^https://www\.tiktok\.com/@[^/]+/video/([0-9]+)$")
BASELINE_DISCOVERY_RUN = "c763b04b5c8f487ca8daf3f326b9bdfa"
BASELINE_SCHEDULED_RUN = "3368cdd366b4e142ee1c6102a458b63d"


class Gate9Error(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Gate9Error(message)


def load_json(path: pathlib.Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"expected JSON object: {path}")
    return value


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unique(rows: list[dict], field: str, label: str) -> dict[str, dict]:
    indexed: dict[str, dict] = {}
    for row in rows:
        value = row.get(field)
        require(isinstance(value, str) and value, f"{label} missing {field}")
        require(value not in indexed, f"duplicate {label} {field}: {value}")
        indexed[value] = row
    return indexed


def exact_native_url(row: dict, label: str) -> None:
    match = NATIVE_URL.fullmatch(row.get("native_url") or row.get("source_url") or "")
    require(match is not None, f"{label} does not use an exact TikTok video URL")
    if row.get("native_id") is not None:
        require(match.group(1) == row["native_id"], f"{label} native URL/id mismatch")


def verified_file(path_value: str, digest: str, label: str) -> pathlib.Path:
    path = pathlib.Path(path_value)
    require(path.is_file(), f"{label} missing: {path}")
    require(sha256(path) == digest, f"{label} hash mismatch: {path}")
    return path


def verify_gate9(engine: pathlib.Path) -> dict:
    engine = pathlib.Path(engine)
    intel = engine / "intel"
    evidence = engine / "evidence"

    registry = load_json(intel / "video-sources.json")
    require(registry.get("schema_version") == "marketing.video-source-registry.v1",
            "invalid video source registry schema")
    sources = unique(registry.get("sources", []), "id", "video source")
    require({row["language"] for row in sources.values()} >= {"en", "ja"},
            "English and Japanese video sources are required")
    for row in sources.values():
        require(row.get("enabled") is True, f"video source disabled: {row['id']}")
        require(len(row.get("product_ids", [])) == 1,
                f"video source must map to exactly one product: {row['id']}")
    mapping = {row["language"]: row["product_ids"][0] for row in sources.values()}
    require(mapping.get("en") == "ebook-en" and mapping.get("ja") == "ebook-ja",
            "video source language/product mapping is wrong")

    tool_lock = load_json(intel / "video-tools.lock.json")
    require(tool_lock.get("schema_version") == "marketing.video-tools-lock.v1",
            "invalid video tool lock schema")
    tools = tool_lock.get("tools", {})
    runtime_versions = {
        "yt-dlp": subprocess.run(["yt-dlp", "--version"], check=True,
                                 capture_output=True, text=True).stdout.strip(),
        "openai-whisper": subprocess.run(
            ["python3", "-c", "import whisper; print(whisper.__version__)"],
            check=True, capture_output=True, text=True).stdout.strip(),
        "ffmpeg": subprocess.run(["ffmpeg", "-version"], check=True,
                                 capture_output=True, text=True).stdout.split()[2],
    }
    require(runtime_versions == {name: row["version"] for name, row in tools.items()},
            "video tool runtime versions differ from lock")

    observations = read_jsonl(intel / "video-observations.jsonl")
    transcripts = read_jsonl(intel / "video-transcripts.jsonl")
    judgments = read_jsonl(intel / "video-hook-judgments.jsonl")
    hook_evidence = read_jsonl(intel / "hook-evidence.jsonl")
    hooks = read_jsonl(intel / "hook-library.jsonl")
    observation_by_id = unique(observations, "id", "observation")
    transcript_by_id = unique(transcripts, "id", "transcript")
    judgment_by_transcript = unique(judgments, "transcript_id", "judgment")
    hook_by_id = unique(hooks, "id", "hook")
    evidence_by_hook = unique(hook_evidence, "hook_id", "hook evidence")
    require(len(observation_by_id) >= 40, "Gate 9 baseline of 40 observations not reached")
    require(len(transcript_by_id) >= 4, "Gate 9 baseline of 4 transcripts not reached")
    require(set(judgment_by_transcript) == set(transcript_by_id),
            "every transcript must have exactly one judgment")
    require(set(evidence_by_hook) == set(hook_by_id),
            "every hook must have exactly one evidence row")
    require(len(hook_by_id) >= 11, "Gate 9 baseline of 11 hooks not reached")
    validate_store(intel / "hook-library.jsonl", "hook-library")

    for row in observations:
        require(row.get("schema_version") == "marketing.video-observation.v1",
                "invalid observation schema")
        require(row.get("source_id") in sources, "observation has unknown source")
        exact_native_url(row, row["id"])
        verified_file(row["evidence_path"], row["evidence_sha256"], "observation evidence")
        require(row.get("product_ids") == sources[row["source_id"]]["product_ids"],
                "observation product mapping differs from registry")

    for row in transcripts:
        require(row.get("schema_version") == "marketing.video-transcript.v1",
                "invalid transcript schema")
        require(row.get("source_id") in sources, "transcript has unknown source")
        exact_native_url(row, row["id"])
        media = verified_file(row["media_path"], row["media_sha256"], "transcript media")
        transcript = verified_file(row["transcript_path"], row["transcript_sha256"],
                                   "transcript JSON")
        require(media.stat().st_size == row["media_bytes"], "transcript media byte count differs")
        body = load_json(transcript)
        require(len(body.get("segments", [])) == row["segment_count"],
                "transcript segment count differs")
        require(row.get("product_ids") == sources[row["source_id"]]["product_ids"],
                "transcript product mapping differs from registry")

    accepted: set[str] = set()
    for row in judgments:
        require(row.get("schema_version") == "marketing.video-hook-judgment.v1",
                "invalid judgment schema")
        ids = row.get("accepted_hook_ids")
        require(isinstance(ids, list) and len(ids) == len(set(ids)),
                "judgment accepted_hook_ids invalid")
        require(not (accepted & set(ids)), "hook accepted by multiple judgments")
        accepted.update(ids)
    require(accepted == set(hook_by_id), "judgments and canonical hook set differ")

    for row in hook_evidence:
        require(row.get("schema_version") == "marketing.hook-evidence.v1",
                "invalid hook evidence schema")
        require(row["transcript_id"] in transcript_by_id,
                "hook evidence references unknown transcript")
        exact_native_url(row, row["id"])
        transcript = transcript_by_id[row["transcript_id"]]
        for field in ("transcript_path", "transcript_sha256", "media_path", "media_sha256"):
            require(row[field] == transcript[field], f"hook evidence {field} differs from transcript")
        verified_file(row["transcript_path"], row["transcript_sha256"], "hook transcript evidence")
        verified_file(row["media_path"], row["media_sha256"], "hook media evidence")
        require(hook_by_id[row["hook_id"]]["source_url"] == row["source_url"],
                "hook source URL differs from evidence")

    rerun = load_json(evidence / "intel" / "video-discovery" /
                      BASELINE_DISCOVERY_RUN / "run.json")
    require(rerun.get("new_observations") == 0, "idempotent discovery appended observations")
    require(all(row.get("status") == "success" for row in rerun.get("sources", [])),
            "idempotent discovery source failed")

    runners = load_json(engine / "report" / "runners.json")["runners"]
    mine_command = runners["mine"]["command"]
    require(mine_command[-2:] == ["intel", "daily"], "mine runner is not wired to intel daily")
    run_dir = evidence / "runs" / "2026-08-01" / "mine" / BASELINE_SCHEDULED_RUN
    execution = load_json(run_dir / "execution.json")
    require(execution.get("returncode") == 0 and not execution.get("quarantined"),
            "scheduled Gate 9 mine run did not succeed")
    daily = load_json(run_dir / "stdout.txt")
    for step in ("video_discover", "video_ingest", "video_judge"):
        require(step in daily.get("steps", {}), f"scheduled daily output missing {step}")
    deliveries = read_jsonl(engine / "state" / "run-deliveries.jsonl")
    delivery = [row for row in deliveries if row.get("run_id") == BASELINE_SCHEDULED_RUN]
    require(len(delivery) == 1 and delivery[0].get("status") == "delivered",
            "scheduled Gate 9 Telegram delivery missing")

    source_files = [
        intel / "video_intel.py", intel / "video_hook_judge.py",
        intel / "intel_daily.py", engine / "bin" / "lm",
    ]
    require(all("openclaw" not in path.read_text(encoding="utf-8").lower()
                for path in source_files), "Gate 9 source has an OpenClaw dependency")

    hooks_by_language = {
        language: sum(row.get("language") == language for row in hooks)
        for language in ("en", "ja")
    }
    require(hooks_by_language["en"] >= 5 and hooks_by_language["ja"] >= 6,
            "Gate 9 bilingual hook baseline not reached")
    return {
        "schema_version": "marketing.gate9-verification.v1",
        "passed": True,
        "counts": {
            "video_observations": len(observations),
            "video_transcripts": len(transcripts),
            "video_judgments": len(judgments),
            "hooks": len(hooks),
            "hook_evidence": len(hook_evidence),
        },
        "hooks_by_language": hooks_by_language,
        "source_product_mapping": mapping,
        "tool_versions": runtime_versions,
        "idempotency": {
            "run_id": rerun["run_id"],
            "new_observations": rerun["new_observations"],
        },
        "scheduled_run": {
            "run_id": execution["run_id"],
            "mine_command": mine_command,
            "daily_run_id": daily["run_id"],
            "telegram_message_ids": delivery[0]["message_ids"],
        },
        "openclaw_dependency": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", type=pathlib.Path,
                        default=pathlib.Path(__file__).resolve().parent.parent)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args(argv)
    try:
        result = verify_gate9(args.engine)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"passed": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    rendered = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
