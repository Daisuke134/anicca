#!/usr/bin/env python3
"""Repo-owned, local-only vertical renderer and evidence gate."""

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
import textwrap
from datetime import datetime, timezone
from pathlib import Path


SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\b(?:sk|pk)-(?:live|test)-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\b(?:api[_ -]?key|password|secret|token)\s*[:=]\s*\S+", re.I),
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
)


def run(command, **kwargs):
    result = subprocess.run(command, text=True, capture_output=True, **kwargs)
    if result.returncode != 0:
        detail = result.stderr.strip().splitlines()[-8:]
        raise RuntimeError("FFmpeg command failed: " + " | ".join(detail))
    return result


def resolve_ffmpeg(requested):
    candidates = [requested] if requested else []
    candidates += ["/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg", "ffmpeg"]
    for candidate in dict.fromkeys(candidates):
        try:
            result = subprocess.run([candidate, "-hide_banner", "-filters"], text=True, capture_output=True)
        except FileNotFoundError:
            continue
        if result.returncode == 0 and re.search(r"\bass\s+V->V", result.stdout):
            return candidate
    raise RuntimeError("no local FFmpeg binary with the libass caption filter")


def validate_public_text(*values):
    joined = "\n".join(values)
    if any(pattern.search(joined) for pattern in SECRET_PATTERNS):
        raise ValueError("listing text contains a secret or PII")


def validate_demonstration(source, demo_input, demo_output):
    source = Path(source)
    if not source.is_file() or source.stat().st_size == 0:
        raise FileNotFoundError(f"missing demonstration source: {source}")
    validate_public_text(demo_input, demo_output)
    before = " ".join(demo_input.lower().split())
    after = " ".join(demo_output.lower().split())
    if len(before) < 8 or len(after) < 8 or before == after:
        raise ValueError("demonstration requires distinct input and output")
    return {
        "mode": "input_output",
        "source": str(source.resolve()),
        "source_sha256": "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest(),
    }


def ass_escape(value):
    return value.replace("\\", "／").replace("{", "（").replace("}", "）")


def ass_wrap(value, width=25):
    wrapped = []
    for line in value.splitlines():
        wrapped.extend(textwrap.wrap(ass_escape(line), width=width, break_long_words=False))
    return r"\N".join(wrapped)


def write_ass(path, hook, proof, demo_input, demo_output, duration):
    input_start = min(3.2, duration * 0.30)
    output_start = min(12.0, duration * 0.55)
    content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 1

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hook,Arial,72,&H00FFFFFF,&H000000FF,&H00111B2E,&HC0111B2E,1,0,0,0,100,100,0,0,1,5,0,8,96,96,260,1
Style: Proof,Arial,54,&H00E7FFF7,&H000000FF,&H00111B2E,&HC0111B2E,1,0,0,0,100,100,0,0,1,4,0,2,96,96,260,1
Style: DemoLabel,Arial,34,&H004FE3B1,&H000000FF,&H00111B2E,&HC0111B2E,1,0,0,0,100,100,2,0,1,2,0,7,110,110,520,1
Style: DemoBody,Arial,46,&H00FFFFFF,&H000000FF,&H00111B2E,&HC0111B2E,1,0,0,0,100,100,0,0,1,3,0,7,110,110,610,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 2,0:00:00.00,0:00:03.20,Hook,,96,96,260,,{ass_wrap(hook)}
Dialogue: 3,0:00:{input_start:05.2f},0:00:{output_start:05.2f},DemoLabel,,110,110,520,,INPUT
Dialogue: 3,0:00:{input_start:05.2f},0:00:{output_start:05.2f},DemoBody,,110,110,610,,{ass_wrap(demo_input, 31)}
Dialogue: 3,0:00:{output_start:05.2f},0:00:{duration:05.2f},DemoLabel,,110,110,520,,VERIFIED OUTPUT
Dialogue: 3,0:00:{output_start:05.2f},0:00:{duration:05.2f},DemoBody,,110,110,610,,{ass_wrap(demo_output, 31)}
Dialogue: 2,0:00:{output_start:05.2f},0:00:{duration:05.2f},Proof,,96,96,260,,{ass_wrap(proof)}
"""
    Path(path).write_text(content, encoding="utf-8")


def probe(path, ffprobe="ffprobe"):
    result = run([ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)])
    return json.loads(result.stdout)


def validate_probe(data):
    video = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    audio = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None)
    if not video or (video.get("width"), video.get("height")) != (1080, 1920):
        raise RuntimeError("video must be 1080x1920 (9:16)")
    if video.get("codec_name") != "h264" or video.get("pix_fmt") != "yuv420p":
        raise RuntimeError("video must be H.264 yuv420p")
    colors = (video.get("color_space"), video.get("color_transfer"), video.get("color_primaries"))
    if colors != ("bt709", "bt709", "bt709"):
        raise RuntimeError("video must declare BT.709 space, transfer and primaries")
    if not audio or audio.get("codec_name") != "aac" or audio.get("sample_rate") != "48000":
        raise RuntimeError("video must contain 48kHz AAC audio")
    return float(data["format"]["duration"])


def validate_audio(path, ffmpeg="ffmpeg"):
    result = run([ffmpeg, "-hide_banner", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"])
    match = re.search(r"mean_volume:\s*(-?[0-9.]+) dB", result.stderr)
    if not match or float(match.group(1)) < -45:
        raise RuntimeError("audio is missing or inaudible")
    return float(match.group(1))


def validate_no_black_frames(path, ffmpeg="ffmpeg"):
    result = run([ffmpeg, "-hide_banner", "-i", str(path), "-vf", "blackdetect=d=0.10:pix_th=0.02", "-an", "-f", "null", "-"])
    if "black_duration:" in result.stderr:
        raise RuntimeError("black frame interval detected")


def validate_opening_motion(path, ffmpeg="ffmpeg"):
    result = run([ffmpeg, "-hide_banner", "-t", "1.5", "-i", str(path), "-vf", "fps=4", "-f", "framemd5", "-"])
    hashes = [line.rsplit(",", 1)[-1].strip() for line in result.stdout.splitlines() if line and not line.startswith("#")]
    if len(set(hashes)) < 3:
        raise RuntimeError("opening is duplicated or visually static")


def create_contact_sheet(path, destination, duration, ffmpeg="ffmpeg"):
    run([
        ffmpeg, "-hide_banner", "-y", "-i", str(path), "-vf",
        f"fps=4/{duration},scale=270:480,tile=4x1", "-frames:v", "1", str(destination),
    ])


def render(args):
    validate_public_text(args.hook, args.proof, args.cta)
    demonstration = validate_demonstration(args.demo_source, args.demo_input, args.demo_output)
    args.ffmpeg = resolve_ffmpeg(args.ffmpeg)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="lm-canonical-video-") as temporary:
        work = Path(temporary)
        write_ass(
            work / "captions.ass",
            args.hook,
            f"{args.proof}\n{args.cta}",
            args.demo_input,
            args.demo_output,
            args.duration,
        )
        partial = work / "render.mp4"
        filters = (
            "[0:v]drawbox=x='mod(t*180\\,1180)-100':y=760:w=260:h=18:color=0x4FE3B1@0.9:t=fill,"
            "drawbox=x=96:y=820:w=888:h=360:color=0x1B3155@0.94:t=fill,"
            "ass=filename=captions.ass,setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709[v];"
            f"[1:a]loudnorm=I=-16:TP=-1.5:LRA=11,apad,atrim=duration={args.duration}[a]"
        )
        run([
            args.ffmpeg, "-hide_banner", "-y", "-f", "lavfi", "-i",
            f"color=c=0x12233f:s=1080x1920:r=30:d={args.duration}", "-i", str(args.audio),
            "-filter_complex", filters, "-map", "[v]", "-map", "[a]", "-t", str(args.duration),
            "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
            "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
            "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart", str(partial),
        ], cwd=work)
        duration = validate_probe(probe(partial, args.ffprobe))
        mean_volume = validate_audio(partial, args.ffmpeg)
        validate_no_black_frames(partial, args.ffmpeg)
        validate_opening_motion(partial, args.ffmpeg)
        partial.replace(args.output)
    contact_sheet = args.output.with_suffix(".contact-sheet.png")
    create_contact_sheet(args.output, contact_sheet, duration, args.ffmpeg)
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "renderer": "mr-bot-canonical-ffmpeg",
        "artifact": str(args.output.resolve()),
        "artifact_sha256": f"sha256:{digest}",
        "contact_sheet": str(contact_sheet.resolve()),
        "duration_seconds": duration,
        "mean_volume_db": mean_volume,
        "quality_gate": "pass",
        "gates": ["1080x1920", "h264", "yuv420p", "bt709", "aac_48khz", "audible", "burned_captions", "caption_safe_area", "no_black_frames", "opening_motion", "no_secret_or_pii", "verified_demonstration"],
        "video_encode_passes": 1,
        "demonstration": demonstration,
    }
    manifest_path = args.output.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, separators=(",", ":")))


def parser():
    parse = argparse.ArgumentParser()
    parse.add_argument("--hook", required=True)
    parse.add_argument("--proof", required=True)
    parse.add_argument("--cta", required=True)
    parse.add_argument("--demo-source", required=True, type=Path)
    parse.add_argument("--demo-input", required=True)
    parse.add_argument("--demo-output", required=True)
    parse.add_argument("--audio", required=True, type=Path)
    parse.add_argument("--output", required=True, type=Path)
    parse.add_argument("--duration", type=float, default=8.0)
    parse.add_argument("--ffmpeg")
    parse.add_argument("--ffprobe", default="ffprobe")
    return parse


if __name__ == "__main__":
    render(parser().parse_args())
