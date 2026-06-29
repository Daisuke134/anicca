#!/usr/bin/env python3
"""Minimal OSS clipping pipeline (= Phase 1 / v1).

Input:  a YouTube long-form URL
Output: N 9:16 short-clip mp4(s) with burned-in captions, ready to post

Stack (no external paid APIs in v1):
  yt-dlp     — source download
  whisper    — transcript with timestamps
  ffmpeg     — crop + caption burn-in

v1 highlight picker: HEURISTIC (largest density of text or middle segment).
v2 will swap in LLM scoring (SamurAIGPT or our own prompt to Claude).
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

def run(cmd, **kw):
    """Run a shell command, return (rc, stdout, stderr)."""
    p = subprocess.run(cmd, capture_output=True, text=True, **kw)
    return p.returncode, p.stdout, p.stderr


def yt_dlp(url, out_dir):
    """Download best <=720p mp4 + extract audio. Returns video_path."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    video = out_dir / "source.mp4"
    # Use the (upgraded) venv yt_dlp MODULE, not the stale PATH binary. Add player_client
    # fallbacks + cookies-from-browser to defeat YouTube's 403/anti-bot (2026). The clip-en
    # CloakBrowser profile (Chromium) carries a logged-in YouTube cookie jar.
    base = [
        sys.executable, "-m", "yt_dlp",
        "-f", "bestvideo[height<=720][ext=mp4]+bestaudio/best[height<=720]",
        "--merge-output-format", "mp4",
        "--extractor-args", "youtube:player_client=android,ios,web",
        "--no-warnings", "-o", str(video),
    ]
    cookies = ["--cookies-from-browser", "chromium:" + os.path.expanduser("~/.cloak/profiles/clip-en")]
    # try with cookies first (most reliable), then without
    for extra in (cookies, []):
        rc, out, err = run(base + extra + [url])
        if rc == 0 and video.exists():
            return str(video)
    raise RuntimeError(f"yt-dlp failed: {err}")


def transcribe(video_path):
    """Return list of {start, end, text} segments via faster-whisper (the installed engine;
    LOCAL_WHISPER_MODEL controls size, default tiny for speed)."""
    from faster_whisper import WhisperModel
    size = os.environ.get("LOCAL_WHISPER_MODEL", "tiny")
    print(f"[transcribe] faster-whisper {size}: {video_path}", file=sys.stderr)
    model = WhisperModel(size, device="cpu", compute_type="int8")
    segs, _ = model.transcribe(video_path)
    return [{"start": s.start, "end": s.end, "text": (s.text or "").strip()} for s in segs]


def pick_highlight_segments(segments, target_seconds=60):
    """v1 HEURISTIC: pick a contiguous window of ~target_seconds with the densest text.
    Density = total chars per second. Returns (start, end) tuple."""
    if not segments:
        return (0, target_seconds)
    # build sliding windows over segments
    best = None
    for i, s in enumerate(segments):
        cum_text = 0
        end_time = s["start"]
        j = i
        while j < len(segments) and segments[j]["end"] - s["start"] <= target_seconds:
            cum_text += len(segments[j]["text"])
            end_time = segments[j]["end"]
            j += 1
        duration = end_time - s["start"]
        if duration <= 0:
            continue
        density = cum_text / duration
        if best is None or density > best[0]:
            best = (density, s["start"], end_time)
    if best is None:
        return (segments[0]["start"], min(segments[-1]["end"], segments[0]["start"] + target_seconds))
    _, start, end = best
    # density (chars/sec) rewards tiny windows → guarantee a postable length (Reels want ≥8s;
    # we aim ~target). Extend the window to ~target seconds, clamped to the transcript bounds.
    vid_end = segments[-1]["end"]
    min_seconds = min(30, max(0.0, vid_end - segments[0]["start"]))
    if end - start < target_seconds:
        end = min(vid_end, start + target_seconds)
    if end - start < min_seconds:  # near the very end → pull start back
        start = max(segments[0]["start"], end - target_seconds)
    return (start, end)


def crop_916(in_path, start, end, out_path):
    """Use ffmpeg to trim [start, end] and crop center to 9:16. Out is mp4."""
    duration = end - start
    # Detect input dims via ffprobe
    rc, probe, _ = run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "json", in_path
    ])
    if rc != 0:
        raise RuntimeError("ffprobe failed")
    w, h = json.loads(probe)["streams"][0]["width"], json.loads(probe)["streams"][0]["height"]
    # 9:16 target width based on h
    target_w = int(h * 9 / 16)
    if target_w >= w:
        # already vertical-ish; just trim
        vf = f"scale={target_w}:{h}"
    else:
        # center crop
        x = (w - target_w) // 2
        vf = f"crop={target_w}:{h}:{x}:0"
    cmd = [
        "ffmpeg", "-y", "-ss", str(start), "-i", in_path, "-t", str(duration),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        str(out_path),
    ]
    rc, _, err = run(cmd)
    if rc != 0:
        raise RuntimeError(f"ffmpeg crop failed: {err[:400]}")


def segments_to_srt(segments, start_offset, dur, srt_path):
    """Convert whisper segments inside [start_offset, start_offset+dur] to SRT."""
    def to_srt_ts(t):
        h = int(t // 3600); m = int((t % 3600) // 60); s = t % 60
        return f"{h:02d}:{m:02d}:{int(s):02d},{int((s - int(s)) * 1000):03d}"
    lines = []
    idx = 1
    for s in segments:
        if s["end"] <= start_offset or s["start"] >= start_offset + dur:
            continue
        st = max(0, s["start"] - start_offset)
        en = min(dur, s["end"] - start_offset)
        if en - st < 0.05:
            continue
        lines.append(str(idx))
        lines.append(f"{to_srt_ts(st)} --> {to_srt_ts(en)}")
        lines.append(s["text"])
        lines.append("")
        idx += 1
    srt_path.write_text("\n".join(lines), encoding="utf-8")


def burn_in_subs(video_in, srt_path, video_out):
    """ffmpeg burn-in subtitles."""
    cmd = [
        "ffmpeg", "-y", "-i", video_in,
        "-vf", f"subtitles={srt_path}:force_style='Fontname=Helvetica,Fontsize=20,Outline=2,Shadow=1,MarginV=80,Bold=-1,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&'",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-c:a", "copy",
        video_out,
    ]
    rc, _, err = run(cmd)
    if rc != 0:
        raise RuntimeError(f"ffmpeg subs failed: {err[:400]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="YouTube long-form URL")
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--niche", default="general")
    ap.add_argument("--lang", default="en")
    ap.add_argument("--count", type=int, default=1, help="number of clips (v1 = 1)")
    ap.add_argument("--target-seconds", type=int, default=60)
    a = ap.parse_args()

    out_root = Path(a.out)
    out_root.mkdir(parents=True, exist_ok=True)

    # 1. download
    print(f"[1/5] downloading {a.url} ...", file=sys.stderr)
    video = yt_dlp(a.url, out_root / "raw")

    # 2. transcribe
    print(f"[2/5] transcribing ...", file=sys.stderr)
    segments = transcribe(video)
    (out_root / "transcript.json").write_text(json.dumps(segments, ensure_ascii=False, indent=2))

    # 3. pick highlight
    start, end = pick_highlight_segments(segments, target_seconds=a.target_seconds)
    print(f"[3/5] pick highlight: {start:.1f}s -> {end:.1f}s ({end-start:.1f}s)", file=sys.stderr)

    # 4. crop 9:16
    cropped = out_root / "clip.crop.mp4"
    print(f"[4/5] cropping to 9:16 ...", file=sys.stderr)
    crop_916(video, start, end, cropped)

    # 5. burn subs
    srt = out_root / "clip.srt"
    segments_to_srt(segments, start, end - start, srt)
    final = out_root / "clip.final.mp4"
    print(f"[5/5] burning subs ...", file=sys.stderr)
    burn_in_subs(str(cropped), str(srt), str(final))

    print(json.dumps({
        "clip_path": str(final),
        "duration_s": end - start,
        "source_url": a.url,
        "niche": a.niche,
        "lang": a.lang,
    }))


if __name__ == "__main__":
    main()
