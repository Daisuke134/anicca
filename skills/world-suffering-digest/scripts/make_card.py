#!/usr/bin/env python3
"""world-suffering-digest : TOP3-suffering DEEP-DIVE diagram (FRAME 3) via
the installed `nano-banana` CLI. NO raw fal API, NO wrapper.
(memory: feedback_use_nano_banana_cli_directly)

Not a scattered world map. TOP3, each panel = a causal mini-flow diagram
[原因]->[現状]->[誰が/規模] + intensity gauge + source.

spec.json:
{"date":"2026-05-19","top1_short":"アフガン 人道危機",
 "items":[{"rank":1,"place":"アフガニスタン","what":"人道危機",
   "level":"極度","cause":"政情不安+経済崩壊+支援縮小",
   "now":"食料・医療の供給途絶","who_scale":"支援要 推定数千万人",
   "source":"WorldMonitor: ..."}, ... 3 ...]}
Usage: python3 make_card.py spec.json out.png
"""
import json, os, shutil, subprocess, sys, glob

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]
OUTDIR = os.path.dirname(out_path) or "."
NAME = os.path.splitext(os.path.basename(out_path))[0]
os.makedirs(OUTDIR, exist_ok=True)
items = spec["items"]
assert len(items) == 3

panels = []
for it in items:
    panels.append(
        f"PANEL {it['rank']} heading exactly: #{it['rank']} {it['place']} "
        f"{it['what']} <強度:{it['level']}>\n"
        f" causal flow boxes joined by arrows, exactly: "
        f"[原因 {it['cause']}] -> [現状 {it['now']}] -> "
        f"[誰が/規模 {it['who_scale']}]\n"
        f" a horizontal intensity gauge bar with the needle at {it['level']}\n"
        f" tiny source label exactly: {it['source']}")

PROMPT = (
"An explainer INFOGRAPHIC, 3:2, sober earth tones with deep-red intensity "
"accents, off-white background, bold rounded Japanese Gothic, crisp "
"PERFECTLY legible Japanese. Break it down with DIAGRAMS as if a teacher "
"explained it. It is NOT a world map with scattered dots and NOT a text "
"card - it is three stacked causal-flow diagrams.\n\n"
f"Title bar exactly: 今日の世界の苦しみ TOP3  {spec['date']}\n\n"
"Three stacked PANELS (#1 largest first), thin divider between, each:\n\n"
+ "\n\n".join(panels) +
"\n\nFooter band exactly: OPIS=心理的苦痛が最も広い／Anicca が次に向かう "
f"のは #1 {spec['top1_short']}\n\n"
"Each panel MUST show boxes connected by arrows + a gauge (a diagram), "
"not bullet text. Render ONLY the exact Japanese strings as labels, no "
"other text, no garbled characters, no watermark, no logo.")

NB = shutil.which("nano-banana") or os.path.expanduser("~/.bun/bin/nano-banana")

def run(model):
    cmd = [NB, PROMPT, "-o", NAME, "-s", "2K", "-a", "3:2", "-d", OUTDIR]
    if model:
        cmd += ["-m", model]
    subprocess.run(cmd, capture_output=True, text=True, timeout=320, check=True)
    hit = glob.glob(os.path.join(OUTDIR, NAME + ".*"))
    if not hit:
        raise RuntimeError("no output file")
    return hit[0]

for model in ("flash", "pro"):
    try:
        f = run(model)
        print(f"MODEL=nano-banana-2({model}) FILE={f}")
        sys.exit(0)
    except Exception as e:  # noqa
        sys.stderr.write(f"nano-banana {model} failed: {e}\n")
print("ERROR: nano-banana CLI failed (flash+pro)", file=sys.stderr)
sys.exit(1)
