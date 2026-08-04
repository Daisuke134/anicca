#!/usr/bin/env python3
"""Bounded native-video discovery tool; creative judgment lives in the agent."""

from __future__ import annotations

import datetime as dt
import fcntl
import hashlib
import json
import pathlib
import statistics
import subprocess
import tempfile
import uuid
from urllib.parse import urlparse


class VideoIntelError(ValueError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise VideoIntelError(message)


def load_video_registry(path: pathlib.Path) -> dict:
    value = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    _require(isinstance(value, dict), "video registry must be an object")
    _require(value.get("schema_version") == "marketing.video-source-registry.v1",
             "invalid video registry schema")
    limits = value.get("limits")
    _require(isinstance(limits, dict), "limits required")
    for key in ("max_posts_per_source", "max_downloads_per_run",
                "max_download_bytes", "max_duration_seconds"):
        _require(isinstance(limits.get(key), int) and limits[key] > 0, f"invalid {key}")
    transcription = value.get("transcription")
    _require(isinstance(transcription, dict) and set(transcription) == {
        "engine", "model", "device"}, "transcription config invalid")
    _require(transcription["engine"] == "openai-whisper", "unsupported transcription engine")
    _require(all(isinstance(transcription[key], str) and transcription[key]
                 for key in ("model", "device")), "transcription values required")
    qualification = value.get("qualification")
    _require(isinstance(qualification, dict), "qualification required")
    for key in ("post_min_views", "creator_average_views", "creator_floor_views"):
        _require(isinstance(qualification.get(key), int) and qualification[key] >= 0,
                 f"invalid {key}")
    sources = value.get("sources")
    _require(isinstance(sources, list) and sources, "sources required")
    seen = set()
    required = {"id", "platform", "handle", "profile_url", "language", "product_ids", "enabled"}
    for source in sources:
        _require(isinstance(source, dict) and set(source) == required,
                 "video source fields invalid")
        _require(source["id"] not in seen, f"duplicate source id {source['id']}")
        seen.add(source["id"])
        _require(source["platform"] in {"tiktok", "instagram", "youtube"},
                 "unsupported video platform")
        _require(isinstance(source["handle"], str) and source["handle"], "handle required")
        _require(isinstance(source["enabled"], bool), "enabled must be boolean")
        _require(isinstance(source["product_ids"], list) and len(source["product_ids"]) == 1,
                 "each video source must map to exactly one product")
        parsed = urlparse(source["profile_url"])
        _require(parsed.scheme == "https" and bool(parsed.netloc), "profile_url must be https")
    return value


def yt_dlp_collector(source: dict, limit: int) -> dict:
    completed = subprocess.run(
        ["yt-dlp", "--flat-playlist", "--playlist-end", str(limit),
         "--dump-single-json", "--no-warnings", source["profile_url"]],
        text=True, capture_output=True, timeout=120, check=False,
    )
    if completed.returncode != 0:
        reason = (completed.stderr or completed.stdout or "yt-dlp failed").strip()[-1000:]
        raise RuntimeError(reason)
    value = json.loads(completed.stdout)
    if not isinstance(value, dict) or not isinstance(value.get("entries"), list):
        raise RuntimeError("yt-dlp returned no playlist entries")
    return value


def _native_url(source: dict, entry: dict) -> str:
    value = entry.get("webpage_url") or entry.get("url")
    _require(isinstance(value, str), "native URL missing")
    parsed = urlparse(value)
    expected_hosts = {
        "tiktok": {"www.tiktok.com", "tiktok.com"},
        "instagram": {"www.instagram.com", "instagram.com"},
        "youtube": {"www.youtube.com", "youtube.com", "youtu.be"},
    }
    _require(parsed.scheme == "https" and parsed.netloc.lower() in expected_hosts[source["platform"]],
             "native URL platform mismatch")
    return value


def _number_or_none(value, field: str):
    if value is None:
        return None
    _require(isinstance(value, (int, float)) and not isinstance(value, bool),
             f"{field} must be numeric or null")
    _require(value >= 0, f"{field} must be non-negative")
    return value


def _append_new(path: pathlib.Path, rows: list[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(f".{path.name}.lock")
    lock_path.touch(exist_ok=True)
    with lock_path.open("r+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        existing = []
        if path.exists():
            existing = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        keys = {(row["source_id"], row["native_id"]) for row in existing}
        additions = [row for row in rows if (row["source_id"], row["native_id"]) not in keys]
        if additions:
            payload = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True,
                                         separators=(",", ":")) + "\n"
                              for row in existing + additions)
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                             prefix=f".{path.name}.", delete=False) as handle:
                handle.write(payload)
                temp_path = pathlib.Path(handle.name)
            temp_path.replace(path)
        return len(additions)


def discover_videos(registry_path: pathlib.Path, intel_root: pathlib.Path,
                    evidence_root: pathlib.Path, collector=yt_dlp_collector,
                    observed_at: str | None = None, run_id: str | None = None) -> dict:
    registry = load_video_registry(registry_path)
    observed_at = observed_at or dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    run_id = run_id or uuid.uuid4().hex
    run_dir = pathlib.Path(evidence_root) / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    floors = registry["qualification"]
    source_receipts = []
    observations = []
    successes = 0
    for source in registry["sources"]:
        if not source["enabled"]:
            continue
        try:
            raw = collector(source, registry["limits"]["max_posts_per_source"])
            raw_bytes = (json.dumps(raw, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")) + "\n").encode("utf-8")
            evidence_path = run_dir / f"{source['id']}.json"
            evidence_path.write_bytes(raw_bytes)
            evidence_sha = hashlib.sha256(raw_bytes).hexdigest()
            entries = raw["entries"][:registry["limits"]["max_posts_per_source"]]
            rows = []
            views = []
            for entry in entries:
                native_id = str(entry.get("id") or "")
                _require(bool(native_id), "native video ID missing")
                metrics = {
                    "views": _number_or_none(entry.get("view_count"), "views"),
                    "likes": _number_or_none(entry.get("like_count"), "likes"),
                    "comments": _number_or_none(entry.get("comment_count"), "comments"),
                    "shares": _number_or_none(entry.get("repost_count"), "shares"),
                    "saves": _number_or_none(entry.get("save_count"), "saves"),
                }
                if metrics["views"] is not None:
                    views.append(metrics["views"])
                row = {
                    "schema_version": "marketing.video-observation.v1",
                    "id": f"observation.{source['platform']}.{native_id}.v1",
                    "source_id": source["id"], "platform": source["platform"],
                    "handle": source["handle"], "language": source["language"],
                    "product_ids": source["product_ids"], "native_id": native_id,
                    "native_url": _native_url(source, entry),
                    "published_at_unix": _number_or_none(entry.get("timestamp"), "timestamp"),
                    "observed_at": observed_at,
                    "duration_seconds": _number_or_none(entry.get("duration"), "duration"),
                    "caption": entry.get("title") if isinstance(entry.get("title"), str) else None,
                    "metrics": metrics,
                    "meets_post_view_floor": (metrics["views"] is not None and
                                               metrics["views"] >= floors["post_min_views"]),
                    "evidence_path": str(evidence_path), "evidence_sha256": evidence_sha,
                }
                rows.append(row)
            average = statistics.fmean(views) if views else None
            floor = min(views) if views else None
            cohort = {
                "observed_posts": len(entries), "posts_with_views": len(views),
                "average_views": average, "floor_views": floor,
                "meets_creator_consistency_floor": (
                    average is not None and floor is not None and
                    average >= floors["creator_average_views"] and
                    floor >= floors["creator_floor_views"]),
            }
            observations.extend(rows)
            successes += 1
            source_receipts.append({"source_id": source["id"], "status": "success",
                                    "reason": None, "items": len(rows), "cohort": cohort,
                                    "evidence_path": str(evidence_path), "sha256": evidence_sha})
        except Exception as exc:
            source_receipts.append({"source_id": source["id"], "status": "error",
                                    "reason": str(exc)[:1000], "items": 0, "cohort": None,
                                    "evidence_path": None, "sha256": None})
    added = _append_new(pathlib.Path(intel_root) / "video-observations.jsonl", observations) if observations else 0
    if successes == 0:
        status = "failed"
    elif successes < sum(bool(row["enabled"]) for row in registry["sources"]):
        status = "partial"
    else:
        status = "success"
    receipt = {"schema_version": "marketing.video-discovery-run.v1", "run_id": run_id,
               "observed_at": observed_at, "status": status,
               "new_observations": added, "sources": source_receipts}
    (run_dir / "run.json").write_text(json.dumps(receipt, ensure_ascii=False,
                                                  sort_keys=True, indent=2) + "\n",
                                       encoding="utf-8")
    return receipt


def yt_dlp_downloader(observation: dict, destination: pathlib.Path, limits: dict) -> pathlib.Path:
    destination.mkdir(parents=True, exist_ok=True)
    template = str(destination / "source.%(ext)s")
    completed = subprocess.run(
        ["yt-dlp", "--no-playlist", "--max-filesize", str(limits["max_download_bytes"]),
         "-f", "b[ext=mp4]/b", "-o", template, observation["native_url"]],
        text=True, capture_output=True, timeout=180, check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout or "yt-dlp download failed").strip()[-1000:])
    files = [path for path in destination.glob("source.*") if path.is_file()]
    if len(files) != 1:
        raise RuntimeError("download did not produce exactly one media file")
    return files[0]


def whisper_transcriber(media: pathlib.Path, destination: pathlib.Path,
                        config: dict, language: str) -> pathlib.Path:
    completed = subprocess.run(
        ["whisper", str(media), "--model", config["model"], "--device", config["device"],
         "--language", language, "--task", "transcribe", "--output_dir", str(destination),
         "--output_format", "json", "--verbose", "False", "--word_timestamps", "True"],
        text=True, capture_output=True, timeout=600, check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout or "whisper failed").strip()[-1000:])
    generated = destination / f"{media.stem}.json"
    if not generated.is_file():
        raise RuntimeError("whisper transcript file missing")
    target = destination / "transcript.json"
    generated.replace(target)
    return target


def _validate_transcript(path: pathlib.Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), "transcript must be object")
    _require(isinstance(value.get("language"), str) and value["language"], "transcript language missing")
    _require(isinstance(value.get("text"), str) and value["text"].strip(), "transcript text missing")
    segments = value.get("segments")
    _require(isinstance(segments, list) and segments, "transcript segments missing")
    for segment in segments:
        _require(isinstance(segment, dict), "transcript segment invalid")
        _require(isinstance(segment.get("start"), (int, float)) and
                 isinstance(segment.get("end"), (int, float)) and
                 segment["end"] > segment["start"] >= 0,
                 "transcript timestamps invalid")
        _require(isinstance(segment.get("text"), str) and segment["text"].strip(),
                 "transcript segment text missing")
    return value


def ingest_transcripts(registry_path: pathlib.Path, intel_root: pathlib.Path,
                       evidence_root: pathlib.Path, downloader=yt_dlp_downloader,
                       transcriber=whisper_transcriber, observed_at: str | None = None,
                       run_id: str | None = None) -> dict:
    registry = load_video_registry(registry_path)
    intel_root = pathlib.Path(intel_root)
    observations_path = intel_root / "video-observations.jsonl"
    _require(observations_path.is_file(), "video observations missing; run video-discover first")
    observations = [json.loads(line) for line in observations_path.read_text(encoding="utf-8").splitlines()]
    transcript_ledger = intel_root / "video-transcripts.jsonl"
    existing = ([json.loads(line) for line in transcript_ledger.read_text(encoding="utf-8").splitlines()]
                if transcript_ledger.exists() else [])
    processed = {(row["source_id"], row["native_id"]) for row in existing}
    limits = registry["limits"]
    candidates = [row for row in observations
                  if row["meets_post_view_floor"] and
                  (row["source_id"], row["native_id"]) not in processed and
                  row["duration_seconds"] is not None and
                  row["duration_seconds"] <= limits["max_duration_seconds"]]
    candidates.sort(key=lambda row: row["metrics"]["views"], reverse=True)
    selected = candidates[:limits["max_downloads_per_run"]]
    observed_at = observed_at or dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    run_id = run_id or uuid.uuid4().hex
    run_dir = pathlib.Path(evidence_root) / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    new_rows = []
    item_receipts = []
    for observation in selected:
        item_dir = run_dir / observation["native_id"]
        try:
            media = downloader(observation, item_dir, limits)
            _require(media.is_file(), "downloaded media missing")
            media_bytes = media.stat().st_size
            _require(media_bytes <= limits["max_download_bytes"], "download exceeds byte cap")
            transcript_path = transcriber(media, item_dir, registry["transcription"],
                                          observation["language"])
            transcript = _validate_transcript(transcript_path)
            row = {
                "schema_version": "marketing.video-transcript.v1",
                "id": f"transcript.{observation['platform']}.{observation['native_id']}.v1",
                "source_id": observation["source_id"], "native_id": observation["native_id"],
                "native_url": observation["native_url"], "language": transcript["language"],
                "product_ids": observation["product_ids"], "observed_at": observed_at,
                "media_path": str(media), "media_bytes": media_bytes,
                "media_sha256": hashlib.sha256(media.read_bytes()).hexdigest(),
                "transcript_path": str(transcript_path),
                "transcript_sha256": hashlib.sha256(transcript_path.read_bytes()).hexdigest(),
                "segment_count": len(transcript["segments"]),
                "transcription_engine": registry["transcription"]["engine"],
                "transcription_model": registry["transcription"]["model"],
            }
            new_rows.append(row)
            item_receipts.append({"native_id": observation["native_id"], "status": "success",
                                  "reason": None, "media_bytes": media_bytes,
                                  "transcript_segments": len(transcript["segments"])})
        except Exception as exc:
            item_receipts.append({"native_id": observation["native_id"], "status": "error",
                                  "reason": str(exc)[:1000], "media_bytes": None,
                                  "transcript_segments": None})
    added = _append_new(transcript_ledger, new_rows) if new_rows else 0
    if not selected:
        status = "skipped"
    elif added == len(selected):
        status = "success"
    elif added:
        status = "partial"
    else:
        status = "failed"
    receipt = {"schema_version": "marketing.video-ingest-run.v1", "run_id": run_id,
               "observed_at": observed_at, "status": status, "selected": len(selected),
               "new_transcripts": added, "items": item_receipts}
    (run_dir / "run.json").write_text(json.dumps(receipt, ensure_ascii=False,
                                                  sort_keys=True, indent=2) + "\n",
                                       encoding="utf-8")
    return receipt
