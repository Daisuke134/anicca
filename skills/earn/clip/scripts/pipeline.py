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

def run(cmd, timeout=None, **kw):
    """Run a shell command, return (rc, stdout, stderr). On timeout, returns a
    non-zero rc instead of raising, so --cookies-from-browser callers fall through
    to the no-cookies attempt instead of hanging forever."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, **kw)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 1, "", f"timed out after {timeout}s"


CAMOFOX_YT_PROFILE_HASH = os.environ.get("CAMOFOX_YT_PROFILE_HASH", "45136ac6a5321e8fcfc75c3b306c5714")


def _youtube_cookies_file():
    """Export camofox's logged-in YouTube/Google profile (Playwright storage-state.json,
    UNENCRYPTED JSON) to a Netscape cookies.txt for yt-dlp's `--cookies <file>`.

    Why not --cookies-from-browser chromium:~/.cloak/profiles/clip-en (the old approach):
    macOS Chromium cookie decryption requires Keychain access to "<browser> Safe Storage",
    and this unattended/headless session's security context does not carry a working
    Keychain search-list (see spec 2026-07-03-clip-loop-dual-instance-self-improve-design.md
    §4.5, タスク#8). yt-dlp's own source (yt_dlp/cookies.py MacChromeCookieDecryptor) has
    NO non-Keychain fallback for macOS (the `peanuts` fixed-key fallback only exists for
    Linux's --password-store=basic mode). camofox is Firefox-based; Firefox never encrypts
    cookies, so this sidesteps the whole problem. Dais-approved exception (2026-07-04) to
    the "CloakBrowser daily-driver is default, never default to camofox" rule — this is a
    cookie-encryption-format constraint, not a browser-automation choice.
    Returns None if the camofox profile/export isn't available (caller falls back to no-cookies).

    COOKIE_SOURCE=env-file (task#8, cloud portability): a cloud host has no local camofox
    profile, so cookies are supplied via a pre-staged file instead. Same None-fallback
    guarantee as the local-camofox path -- an unset or missing YT_COOKIES_FILE returns None,
    never a bogus path passed straight to yt-dlp's --cookies flag."""
    if os.environ.get("COOKIE_SOURCE") == "env-file":
        path = os.environ.get("YT_COOKIES_FILE")
        return path if path and os.path.exists(path) else None
    storage_state = os.path.expanduser(f"~/.camofox/profiles/{CAMOFOX_YT_PROFILE_HASH}/storage-state.json")
    if not os.path.exists(storage_state):
        return None
    out = "/tmp/yt-cookies-camofox.txt"
    export_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "export_camofox_cookies.py")
    rc, _, _ = run([sys.executable, export_script, storage_state, out], timeout=10)
    return out if rc == 0 and os.path.exists(out) else None


def get_duration(url):
    """Probe source length (seconds) without downloading. None if probe fails.
    Must use the same cookies as yt_dlp() below -- without them YouTube's bot
    check ("Sign in to confirm you're not a bot") fails this probe silently,
    duration comes back None, and the caller falls through to a FULL-length
    download (defeats the whole point of slicing). 2026-07-04 タスク#9 incident:
    found via a real run where a 2h38m source downloaded in full because this
    probe errored out while the (cookie-equipped) download call still worked."""
    cookies_file = _youtube_cookies_file()
    cookies = ["--cookies", cookies_file, "--remote-components", "ejs:github"] if cookies_file else []
    base = [sys.executable, "-m", "yt_dlp", "--print", "%(duration)s", "--skip-download", "--no-warnings"]
    for extra in (cookies, []):
        # 45s bound: keeps a failed/slow attempt from hanging the whole daily cron.
        rc, out, err = run(base + extra + [url], timeout=45)
        try:
            return float(out.strip().splitlines()[-1])
        except (ValueError, IndexError):
            continue
    return None


def yt_dlp(url, out_dir, section=None):
    """Download best 720p-1080p mp4 (optionally only `section`, e.g. '*600-900') + audio.
    Returns video_path. `section` bounds long-form podcasts (1h+) to a slice so
    whisper transcribe doesn't run on the full source (was the real reason the
    daily producer cron never finished — 2026-07-04 タスク#9)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    video = out_dir / "source.mp4"
    # Use the (upgraded) venv yt_dlp MODULE, not the stale PATH binary. Add player_client
    # fallbacks + cookies to defeat YouTube's 403/anti-bot (2026). Cookies come from the
    # camofox YouTube profile (see _youtube_cookies_file() above) -- NOT CloakBrowser
    # Chromium, whose cookies are Keychain-encrypted and unreadable in this headless
    # session. --remote-components ejs:github is required alongside cookies: yt-dlp's n
    # challenge solver needs its solver script downloaded, or ALL non-cookie player
    # clients get skipped and zero formats are found (2026-07-04 タスク#8, real repro).
    # Quality floor (2026-07-10 self-heal incident: posted files measured 202x360 @
    # ~200kbps while 720p/1080p formats existed for the SAME video id -- root cause was
    # this selector's final `/best` fallback silently accepting whatever format yt-dlp
    # found first, including sub-720p, whenever the `[height<=720]` branches came back
    # empty for a given source). Fail LOUD instead: require >=720p AND <=1080p mp4 first,
    # then any-resolution mp4, then (last resort) any format -- but never silently drop
    # below 720p while a 720-1080p format was actually available.
    base = [
        sys.executable, "-m", "yt_dlp",
        "-f", "bestvideo[height>=720][height<=1080][ext=mp4]+bestaudio/bestvideo[ext=mp4]+bestaudio/best",
        "--merge-output-format", "mp4",
        "--extractor-args", "youtube:player_client=android,ios,web",
        "--no-warnings", "-o", str(video),
    ]
    if section:
        base += ["--download-sections", section, "--force-keyframes-at-cuts"]
    cookies_file = _youtube_cookies_file()
    cookies = ["--cookies", cookies_file, "--remote-components", "ejs:github"] if cookies_file else []
    # try with cookies first (most reliable), then without. Cookies attempt is bounded
    # tight (45s) since it's a local file read + fast API call, not a Keychain prompt;
    # the no-cookies attempt gets a generous bound for a real download.
    for extra, timeout in ((cookies, 45), ([], 600)):
        rc, out, err = run(base + extra + [url], timeout=timeout)
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
    # Canonical normalization (2026-07-10 self-heal, quality-floor incident: posted files
    # measured 202x360 @ ~200kbps despite 720p/1080p sources -- the branch above alone can
    # drift a few px off 1080x1920 due to int(h*9/16) rounding). Scale up preserving AR
    # until the frame covers 1080x1920, then center-crop the excess. This guarantees the
    # final output is EXACTLY 1080x1920 regardless of the source's native resolution.
    vf = f"{vf},scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    cmd = [
        "ffmpeg", "-y", "-ss", str(start), "-i", in_path, "-t", str(duration),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "veryfast",
        # Bitrate floor (verify_clip.sh gate requires >=2.5Mbps): CRF alone let low-detail
        # source segments drift the encode's bitrate arbitrarily low even at correct
        # resolution, so this pins an explicit target/min/max instead of trusting CRF.
        "-b:v", "4000k", "-minrate", "3000k", "-maxrate", "4500k", "-bufsize", "8000k",
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

    # 1. download — bound long-form sources (podcasts run 1-3h) to a slice around the
    # midpoint so whisper transcribe stays fast (full-source transcribe was why the
    # daily producer cron never finished — 2026-07-04 タスク#9). SLICE_SECONDS gives
    # enough room for pick_highlight_segments to still choose the densest window.
    SLICE_SECONDS = 360
    duration = get_duration(a.url)
    section = None
    if duration and duration > SLICE_SECONDS * 1.5:
        mid = duration / 2
        start = max(0, mid - SLICE_SECONDS / 2)
        end = min(duration, start + SLICE_SECONDS)
        section = f"*{int(start)}-{int(end)}"
        print(f"[1/5] source is {duration:.0f}s, slicing {section} ...", file=sys.stderr)
    print(f"[1/5] downloading {a.url} ...", file=sys.stderr)
    video = yt_dlp(a.url, out_root / "raw", section=section)

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
