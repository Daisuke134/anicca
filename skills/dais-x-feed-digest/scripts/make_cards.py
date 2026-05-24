#!/usr/bin/env python3
"""dais-x-feed-digest : per-theme INFOGRAPHICS (FRAME 2) via the installed
`nano-banana` CLI (kingbootoshi/nano-banana-2-skill). NO raw fal API, NO
bun-run wrapper. (memory: feedback_use_nano_banana_cli_directly)

FRAME 2 (awesome-nano-banana-pro-prompts No.7/No.2 + Dais 2026-05-19):
each theme = 3 SEPARATE news, each its own bento module with a
mini-diagram + situation + EXACT number + source. NOT merged.

spec.json:
{"date":"2026-05-19","themes":[{"n":1,"label":"① AIモデル/製品 launch",
  "news":[{"headline":"...","diagram":"before->after: ...",
    "situation":"...","number":"...","source":"@x /status/..."},
    {...},{...}]}, ... 1..5 ...]}
Usage: python3 make_cards.py spec.json OUTDIR DATE
Writes OUTDIR/xfeed_DATE_<n>.(jpeg|png). Prints MODEL= per card.
"""
import json, os, shutil, subprocess, sys, glob

spec = json.load(open(sys.argv[1])); OUTDIR = sys.argv[2]; DATE = sys.argv[3]
os.makedirs(OUTDIR, exist_ok=True)
themes = spec["themes"]
assert 1 <= len(themes) <= 5
NB = shutil.which("nano-banana") or os.path.expanduser("~/.bun/bin/nano-banana")

STYLE = (
"A clean INFOGRAPHIC, 3:2, Memphis accents (#FFDAB9 peach background, "
"#00CED1 turquoise, #FF6347 tomato), playful geometric shapes in margins "
"only, crisp PERFECTLY legible Japanese. Break the news down with small "
"DIAGRAMS as if a teacher explained it. Three SEPARATE news as three "
"independent bento modules (M1/M2/M3) with thin dividers - distinct "
"unrelated stories, NOT merged into one relation map.")


def prompt_for(t):
    L = [STYLE, f"Title bar exactly: {t['label']}  {spec['date']}"]
    for i, nw in enumerate(t["news"][:3], 1):
        L += [
            f"M{i} headline exactly: {nw['headline']}",
            f"M{i} small diagram exactly (boxes/arrows/icons): {nw['diagram']}",
            f"M{i} detail line exactly: 状況: {nw['situation']}",
            f"M{i} number line exactly: 数値: {nw['number']}",
            f"M{i} tiny source exactly: {nw['source']}"]
    L.append("Modules must look visually distinct & unconnected, each with "
             "its own mini-diagram. Render ONLY the exact Japanese strings "
             "as labels, no other text, no garbled characters, no watermark.")
    return "\n".join(L)


def run(prompt, base, model):
    cmd = [NB, prompt, "-o", base, "-s", "2K", "-a", "3:2", "-d", OUTDIR]
    if model:
        cmd += ["-m", model]
    subprocess.run(cmd, capture_output=True, text=True, timeout=320, check=True)
    hit = glob.glob(os.path.join(OUTDIR, base + ".*"))
    if not hit:
        raise RuntimeError("no output")
    return hit[0]


fail = []
for t in themes:
    n = t["n"]; base = f"xfeed_{DATE}_{n}"; p = prompt_for(t); ok = False
    for model in ("flash", "pro"):
        try:
            f = run(p, base, model)
            print(f"theme {n} MODEL=nano-banana-2({model}) FILE={f}", flush=True)
            ok = True
            break
        except Exception as e:  # noqa
            sys.stderr.write(f"theme {n} {model} failed: {e}\n")
    if not ok:
        fail.append(n)
if fail:
    print(f"ERROR: themes failed: {fail}", file=sys.stderr); sys.exit(1)
print(f"CARDS_DONE {len(themes)}")
