#!/usr/bin/env python3
"""Freeze and render the Gate 11 no-network renderer benchmark."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import time

ENGINE = pathlib.Path(__file__).resolve().parent.parent
HERE = pathlib.Path(__file__).resolve().parent
FIELDS = {
    "schema_version", "fixture_id", "language", "product_id", "account_id",
    "hook_id", "script", "cta", "source_asset", "source_sha256", "voice",
    "target_duration_seconds", "width", "height",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with pathlib.Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_jsonl(path: pathlib.Path) -> list[dict]:
    if not pathlib.Path(path).exists():
        return []
    rows = []
    for number, line in enumerate(pathlib.Path(path).read_text(encoding="utf-8").splitlines(), 1):
        require(bool(line.strip()), f"blank JSONL line: {path}:{number}")
        row = json.loads(line)
        require(isinstance(row, dict), f"JSONL row must be object: {path}:{number}")
        rows.append(row)
    return rows


def _load(path: pathlib.Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"object required: {path}")
    return value


def build_fixtures(engine: pathlib.Path = ENGINE) -> list[dict]:
    engine = pathlib.Path(engine)
    hooks = read_jsonl(engine / "intel" / "hook-library.jsonl")
    choices = {
        "ebook-en": [row for row in hooks if row.get("status") == "active" and
                     row.get("product_ids") == ["ebook-en"]][:5],
        "ebook-ja": [row for row in hooks if row.get("status") == "active" and
                     row.get("product_ids") == ["ebook-ja"]][:5],
    }
    require(all(len(rows) == 5 for rows in choices.values()), "five active hooks required per ebook")
    settings = {
        "ebook-en": {
            "language": "en", "account_id": "tiktok.monk_anicca", "voice": "Samantha",
            "asset": pathlib.Path("/Users/anicca/anicca-monk-factory/characters/en/icon_v2_full.png"),
        },
        "ebook-ja": {
            "language": "ja", "account_id": "tiktok.obou_anicca", "voice": "Kyoko",
            "asset": pathlib.Path("/Users/anicca/anicca-monk-factory/characters/jp/icon_anime.png"),
        },
    }
    fixtures = []
    for product_id in ("ebook-en", "ebook-ja"):
        product = _load(engine / "registry" / "products" / f"{product_id}.json")
        setting = settings[product_id]
        for index, hook in enumerate(choices[product_id], 1):
            fixtures.append({
                "schema_version": "marketing.renderer-fixture.v1",
                "fixture_id": f"fixture.{product_id}.{index:03d}",
                "language": setting["language"],
                "product_id": product_id,
                "account_id": setting["account_id"],
                "hook_id": hook["id"],
                "script": f"{hook['text']} {product['cta']}",
                "cta": product["cta"],
                "source_asset": str(setting["asset"]),
                "source_sha256": sha256(setting["asset"]),
                "voice": setting["voice"],
                "target_duration_seconds": 15,
                "width": 720,
                "height": 1280,
            })
    return fixtures


def validate_fixture(row: dict, *, engine: pathlib.Path = ENGINE, check_asset: bool = True) -> None:
    require(set(row) == FIELDS, "fixture fields differ")
    require(row["schema_version"] == "marketing.renderer-fixture.v1", "fixture schema differs")
    require(row["language"] in {"en", "ja"}, "fixture language invalid")
    require(row["product_id"] in {"ebook-en", "ebook-ja"}, "fixture product invalid")
    account = _load(pathlib.Path(engine) / "registry" / "accounts" /
                    f"{row['account_id']}.json")
    require(account["product_id"] == row["product_id"], "account product mismatch")
    require(account["language"] == row["language"], "account language mismatch")
    require((row["width"], row["height"]) == (720, 1280), "fixture must be 9:16")
    require(isinstance(row["script"], str) and row["cta"] in row["script"], "script CTA missing")
    require(isinstance(row["target_duration_seconds"], (int, float)) and
            5 <= row["target_duration_seconds"] <= 30, "fixture duration invalid")
    if check_asset:
        asset = pathlib.Path(row["source_asset"])
        require(asset.is_file(), f"source asset missing: {asset}")
        require(sha256(asset) == row["source_sha256"], "source asset hash mismatch")


def load_fixtures(path: pathlib.Path) -> list[dict]:
    document = _load(pathlib.Path(path))
    require(document.get("schema_version") == "marketing.renderer-fixtures.v1", "fixture set schema differs")
    fixtures = document.get("fixtures")
    require(isinstance(fixtures, list), "fixtures must be a list")
    return fixtures


def append_receipt(path: pathlib.Path, receipt: dict) -> bool:
    rows = read_jsonl(path)
    matches = [row for row in rows if row.get("attempt_id") == receipt.get("attempt_id")]
    if matches:
        require(matches[0] == receipt, "conflicting replay")
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    return True


def validate_receipt(receipt: dict, fixture: dict, *, check_output: bool = True) -> None:
    required = {
        "schema_version", "attempt_id", "fixture_id", "renderer_id", "renderer_version",
        "license", "status", "reason", "started_at", "finished_at", "latency_ms",
        "cost_usd", "input_sha256", "output_path", "output_sha256", "probe",
        "publication_effects",
    }
    require(set(receipt) == required, "receipt fields differ")
    require(receipt["schema_version"] == "marketing.renderer-attempt.v1", "receipt schema differs")
    require(receipt["fixture_id"] == fixture["fixture_id"], "receipt fixture mismatch")
    require(receipt["status"] in {"success", "failed", "unavailable"}, "receipt status invalid")
    require(receipt["cost_usd"] == 0, "Gate 11 cost must be zero")
    require(receipt["publication_effects"] == [], "Gate 11 external effects forbidden")
    require(receipt["input_sha256"] == fixture["source_sha256"], "receipt input hash mismatch")
    if receipt["status"] == "success":
        require(receipt["reason"] is None, "successful receipt reason must be null")
        probe = receipt["probe"]
        require(probe["width"] == fixture["width"] and probe["height"] == fixture["height"],
                "output dimensions differ")
        require(probe["video_codec"] == "h264" and probe["audio_codec"] == "aac",
                "A/V codecs differ")
        require(2 <= probe["duration"] <= 35, "output duration invalid")
        if check_output:
            output = pathlib.Path(receipt["output_path"])
            require(output.is_file(), f"output missing: {output}")
            require(sha256(output) == receipt["output_sha256"], "output hash mismatch")
    else:
        require(isinstance(receipt["reason"], str) and receipt["reason"], "failure reason missing")
        require(receipt["output_path"] is None and receipt["output_sha256"] is None,
                "unavailable output must be null")


def _iso_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _attempt_id(fixture_id: str, renderer_id: str) -> str:
    value = hashlib.sha256(f"{fixture_id}\0{renderer_id}\0v1".encode()).hexdigest()[:24]
    return f"attempt.{value}"


def _escape_ass(value: str) -> str:
    return value.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}").replace("\n", r"\N")


def _write_ass(path: pathlib.Path, fixture: dict, duration: float = 30.0) -> None:
    text = _escape_ass(fixture["script"])
    body = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280
[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,Arial,42,&H00FFFFFF,&H000000FF,&H00101010,&H90000000,-1,0,0,0,100,100,0,0,3,2,0,2,50,50,96,1
[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
Dialogue: 0,0:00:00.00,0:00:{duration:05.2f},Default,,0,0,0,,{text}
"""
    path.write_text(body, encoding="utf-8")


def _probe(path: pathlib.Path) -> dict:
    result = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries",
        "stream=codec_type,codec_name,width,height:format=duration", "-of", "json", str(path)
    ], check=True, capture_output=True, text=True)
    data = json.loads(result.stdout)
    video = next(row for row in data["streams"] if row["codec_type"] == "video")
    audio = next(row for row in data["streams"] if row["codec_type"] == "audio")
    return {"width": video["width"], "height": video["height"],
            "duration": round(float(data["format"]["duration"]), 3),
            "video_codec": video["codec_name"], "audio_codec": audio["codec_name"]}


def render_safety(fixture: dict, output_root: pathlib.Path) -> dict:
    started_at = _iso_now()
    started = time.monotonic()
    work = pathlib.Path(output_root) / fixture["fixture_id"]
    work.mkdir(parents=True, exist_ok=True)
    audio = work / "voice.aiff"
    captions = work / "captions.ass"
    output = work / "safety-local.mp4"
    _write_ass(captions, fixture)
    subprocess.run(["say", "-v", fixture["voice"], "-r", "175", "-o", str(audio),
                    fixture["script"]], check=True, capture_output=True)
    ass_path = str(captions).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    vf = ("scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,"
          f"subtitles='{ass_path}'")
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-loop", "1",
        "-i", fixture["source_asset"], "-i", str(audio), "-vf", vf,
        "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage",
        "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "128k",
        "-shortest", "-movflags", "+faststart", str(output)
    ], check=True, capture_output=True)
    elapsed = int((time.monotonic() - started) * 1000)
    version = subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True,
                             text=True).stdout.splitlines()[0]
    return {
        "schema_version": "marketing.renderer-attempt.v1",
        "attempt_id": _attempt_id(fixture["fixture_id"], "safety-local"),
        "fixture_id": fixture["fixture_id"], "renderer_id": "safety-local",
        "renderer_version": version, "license": "local-tools-and-owned-inputs",
        "status": "success", "reason": None, "started_at": started_at,
        "finished_at": _iso_now(), "latency_ms": elapsed, "cost_usd": 0,
        "input_sha256": fixture["source_sha256"], "output_path": str(output),
        "output_sha256": sha256(output), "probe": _probe(output),
        "publication_effects": [],
    }


def unavailable_receipt(fixture: dict, renderer_id: str, reason: str) -> dict:
    now = _iso_now()
    return {
        "schema_version": "marketing.renderer-attempt.v1",
        "attempt_id": _attempt_id(fixture["fixture_id"], renderer_id),
        "fixture_id": fixture["fixture_id"], "renderer_id": renderer_id,
        "renderer_version": "not-executed", "license": "repository-code-license-only",
        "status": "unavailable", "reason": reason, "started_at": now,
        "finished_at": now, "latency_ms": 0, "cost_usd": 0,
        "input_sha256": fixture["source_sha256"], "output_path": None,
        "output_sha256": None, "probe": None, "publication_effects": [],
    }


def render_all(fixtures_path: pathlib.Path, receipts_path: pathlib.Path,
               output_root: pathlib.Path) -> dict:
    require(shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None,
            "ffmpeg and ffprobe required")
    require(shutil.which("say") is not None, "macOS say required")
    fixtures = load_fixtures(fixtures_path)
    existing = {row["attempt_id"]: row for row in read_jsonl(receipts_path)}
    appended = 0
    skipped = 0
    for fixture in fixtures:
        validate_fixture(fixture, check_asset=True)
        attempt_id = _attempt_id(fixture["fixture_id"], "safety-local")
        if attempt_id in existing:
            validate_receipt(existing[attempt_id], fixture, check_output=True)
            skipped += 1
            continue
        receipt = render_safety(fixture, output_root)
        validate_receipt(receipt, fixture, check_output=True)
        appended += int(append_receipt(receipts_path, receipt))
    first = fixtures[0]
    blockers = {
        "omniavatar-monk": "no durable free execution artifact or local CUDA runtime",
        "musetalk": "checkpoint commercial terms and local GPU capacity not verified",
        "longcat-video-avatar": "official path requires multi-GPU capacity unavailable locally",
    }
    for renderer_id, reason in blockers.items():
        receipt = unavailable_receipt(first, renderer_id, reason)
        if receipt["attempt_id"] in existing:
            append_receipt(receipts_path, existing[receipt["attempt_id"]])
            skipped += 1
        else:
            appended += int(append_receipt(receipts_path, receipt))
    return {"status": "success", "fixtures": len(fixtures), "appended": appended, "skipped": skipped}


def verify_outputs(fixtures_path: pathlib.Path, receipts_path: pathlib.Path) -> dict:
    fixtures = load_fixtures(fixtures_path)
    by_fixture = {row["fixture_id"]: row for row in fixtures}
    receipts = read_jsonl(receipts_path)
    for row in receipts:
        require(row.get("fixture_id") in by_fixture, "receipt fixture unknown")
        validate_receipt(row, by_fixture[row["fixture_id"]], check_output=True)
    safety = [row for row in receipts if row["renderer_id"] == "safety-local" and row["status"] == "success"]
    for fixture in fixtures:
        require(any(row["fixture_id"] == fixture["fixture_id"] for row in safety),
                f"missing successful safety receipt: {fixture['fixture_id']}")
    require(len(safety) == 10, "exactly ten successful safety receipts required")
    return {"status": "success", "fixtures": len(fixtures), "safety_success": len(safety),
            "failed": sum(row["status"] == "failed" for row in receipts),
            "unavailable": sum(row["status"] == "unavailable" for row in receipts)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    freeze = commands.add_parser("freeze")
    freeze.add_argument("--output", type=pathlib.Path, default=HERE / "renderer-fixtures.json")
    render = commands.add_parser("render")
    render.add_argument("--fixtures", type=pathlib.Path, default=HERE / "renderer-fixtures.json")
    render.add_argument("--receipts", type=pathlib.Path, default=ENGINE / "evidence/renderers/gate11/attempts.jsonl")
    render.add_argument("--output-root", type=pathlib.Path, default=ENGINE / "evidence/renderers/gate11/outputs")
    verify = commands.add_parser("verify")
    verify.add_argument("--fixtures", type=pathlib.Path, default=HERE / "renderer-fixtures.json")
    verify.add_argument("--receipts", type=pathlib.Path, default=ENGINE / "evidence/renderers/gate11/attempts.jsonl")
    args = parser.parse_args(argv)
    try:
        if args.command == "freeze":
            value = {"schema_version": "marketing.renderer-fixtures.v1", "fixtures": build_fixtures()}
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            result = {"status": "success", "fixtures": 10, "output": str(args.output)}
        elif args.command == "render":
            result = render_all(args.fixtures, args.receipts, args.output_root)
        else:
            result = verify_outputs(args.fixtures, args.receipts)
    except (OSError, ValueError, KeyError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
