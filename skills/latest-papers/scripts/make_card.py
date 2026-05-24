#!/usr/bin/env python3
"""latest-papers : render the research digest as METHOD-FLOW DIAGRAMS
(FRAME 1) via the installed `nano-banana` CLI (kingbootoshi/
nano-banana-2-skill). NO raw fal API, NO wrapper indirection.
(memory: feedback_use_nano_banana_cli_directly)

FRAME 1 (source: awesome-nano-banana-pro-prompts No.7/No.2 + Dais
2026-05-19): each paper = a left->right FLOW DIAGRAM (boxes+arrows+icons)
of the method, NOT 3 text lines. Break it down with a diagram as if a
teacher explained it.

spec.json:
{
 "date":"2026-05-19",
 "papers":[{"n":1,"title_en":"Code as Agent Harness (2605.18747)",
   "input":"コード","rel1":"推論","mechanism":"実行+検証",
   "rel2":"反映","result":"環境モデル","loop":true,
   "why":"Agent基盤を統一(Anicca直結)"}, ... 3-4 ...]
}
Usage: python3 make_card.py spec.json out.png
out.png: <DIR>/<NAME>.png  (DIR/NAME derived for nano-banana -o/-d)
"""
import json, os, shutil, subprocess, sys, glob

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]
OUTDIR = os.path.dirname(out_path) or "."
NAME = os.path.splitext(os.path.basename(out_path))[0]
os.makedirs(OUTDIR, exist_ok=True)
papers = spec["papers"]
assert 3 <= len(papers) <= 4

panels = []
for p in papers:
    loop = " add a curved back-arrow loop from the last box to the first." \
        if p.get("loop") else ""
    panels.append(
        f"PANEL {p['n']} bold heading exactly: {p['n']}. {p['title_en']}\n"
        f" a left-to-right FLOW DIAGRAM: rounded boxes joined by thick "
        f"labelled arrows, each box a small icon + short JP label, exactly: "
        f"[{p['input']}] -({p['rel1']})-> [{p['mechanism']}] "
        f"-({p['rel2']})-> [{p['result']}].{loop}\n"
        f" one callout line exactly: => {p['why']}")

PROMPT = (
"An editorial RESEARCH INFOGRAPHIC, 3:2, off-white background, deep indigo "
"+ charcoal, one coral accent, bold rounded Japanese Gothic, crisp "
"PERFECTLY legible Japanese. Break EACH paper down with a DIAGRAM as if a "
"teacher explained it on a clean board - NOT a text card.\n\n"
f"Title bar exactly: 今日の重要AI論文 {spec['date']} (arXiv)\n\n"
f"{len(papers)} stacked paper PANELS, thin divider between, each:\n\n"
+ "\n\n".join(panels) +
"\n\nEach panel MUST be boxes connected by arrows (a flow diagram), not "
"bullet text. Render ONLY the exact Japanese/strings as labels, "
"perfectly legible, no garbled characters, no watermark, no logo.")

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
