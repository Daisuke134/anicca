#!/usr/bin/env python3
"""Burn word-level karaoke captions onto a 9:16 clip.

Transcribes the clip itself (clip-relative timing) with faster-whisper
word_timestamps=True, builds a karaoke-style ASS subtitle (current word
highlighted), and burns it in with ffmpeg. Optionally adds a hook banner
over the first N seconds.

Usage:
  burn_captions.py <in.mp4> <out.mp4> [--hook "TEXT"] [--model tiny] [--lang en]

Run with the SamurAIGPT venv (has faster-whisper):
  ~/.cache/anicca-clones/AI-Youtube-Shorts-Generator/.venv/bin/python burn_captions.py ...
"""
import argparse, os, subprocess, sys, tempfile


def fmt_ass_ts(t: float) -> str:
    h = int(t // 3600); m = int((t % 3600) // 60); s = t % 60
    cs = int(round((s - int(s)) * 100))
    return f"{h:d}:{m:02d}:{int(s):02d}.{cs:02d}"


def ass_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "(").replace("}", ")")


def build_ass(words, hook, width, height):
    """words = list of (start, end, text). Karaoke: show a rolling window of
    ~5 words, current word in accent color."""
    play_w, play_h = width, height
    cap_fs = max(16, round(play_w * 0.085))
    hook_fs = max(14, round(play_w * 0.072))
    margin_lr = max(12, round(play_w * 0.06))
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {play_w}
PlayResY: {play_h}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Arial Black,{cap_fs},&H00FFFFFF,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,3,2,2,{margin_lr},{margin_lr},90,1
Style: Hook,Arial Black,{hook_fs},&H0000F0FF,&H000000FF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,3,2,8,{margin_lr},{margin_lr},70,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    accent = "&H0000F0FF"  # amber-ish BGR
    white = "&H00FFFFFF"
    n = len(words)
    WIN = 3
    for i, (st, en, txt) in enumerate(words):
        # rolling window centered on current word
        lo = max(0, i - WIN // 2)
        hi = min(n, lo + WIN)
        lo = max(0, hi - WIN)
        parts = []
        for j in range(lo, hi):
            w = ass_escape(words[j][2])
            if j == i:
                parts.append(f"{{\\c{accent}\\fscx112\\fscy112}}{w}{{\\c{white}\\fscx100\\fscy100}}")
            else:
                parts.append(w)
        text = " ".join(parts).strip()
        lines.append(
            f"Dialogue: 0,{fmt_ass_ts(st)},{fmt_ass_ts(en)},Cap,,0,0,0,,{text}"
        )
    if hook:
        hk = ass_escape(hook.upper())
        lines.append(
            f"Dialogue: 1,{fmt_ass_ts(0.0)},{fmt_ass_ts(2.0)},Hook,,0,0,0,,{hk}"
        )
    return head + "\n".join(lines) + "\n"


def transcribe_words(clip, model_size, lang):
    from faster_whisper import WhisperModel
    m = WhisperModel(model_size, device="cpu", compute_type="int8")
    segs, _ = m.transcribe(clip, language=lang, word_timestamps=True)
    words = []
    for s in segs:
        for w in (s.words or []):
            t = w.word.strip()
            if t:
                words.append((float(w.start), float(w.end), t))
    return words


def probe_dims(clip):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", clip],
        capture_output=True, text=True,
    ).stdout.strip()
    w, h = out.split("x")
    return int(w), int(h)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp")
    ap.add_argument("outp")
    ap.add_argument("--hook", default=None)
    ap.add_argument("--model", default="tiny")
    ap.add_argument("--lang", default="en")
    a = ap.parse_args()

    w, h = probe_dims(a.inp)
    print(f"[burn] dims {w}x{h}", file=sys.stderr)
    words = transcribe_words(a.inp, a.model, a.lang)
    print(f"[burn] {len(words)} words", file=sys.stderr)
    ass = build_ass(words, a.hook, w, h)
    with tempfile.NamedTemporaryFile("w", suffix=".ass", delete=False) as f:
        f.write(ass)
        ass_path = f.name
    # burn in
    rc = subprocess.run([
        "ffmpeg", "-y", "-i", a.inp,
        "-vf", f"ass={ass_path}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "copy", a.outp,
    ], capture_output=True, text=True)
    os.unlink(ass_path)
    if rc.returncode != 0:
        print("ffmpeg failed:\n" + rc.stderr[-800:], file=sys.stderr)
        sys.exit(1)
    print(a.outp)


if __name__ == "__main__":
    main()
