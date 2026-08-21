"""Adapt a full source article (the note source, with explainer + paid run/results) into an HONEST FREE Zenn
explainer. Repeatable: cuts the paid section + every first-person run/test/next-chapter claim, so the free
version never lies (no 「動かしてみた/検証」). Zenn renders mermaid + markdown tables natively → NO image upload.
Usage: zenn-adapt.py <source.md> <out.md> <slug> <title> <emoji> <topics-csv> <paid-from-heading> [closing]
Env knobs: ZENN_CUT_LINES (comma source-line ranges to also drop, 1-based, e.g. '15-17,44') for article-specific
run-claim spots the generic patterns miss."""
import sys, re, os
src, out, slug, title, emoji, topics_csv, paid_from = sys.argv[1:8]
# An empty paid-from is destructive: the cut below is ^##\s*<paid_from>, so ""
# matches the FIRST heading and deletes the whole body. On 2026-07-26 that
# turned a 148-line article into a 17-line stub which Zenn refused to serve.
if not paid_from.strip():
    sys.exit(
        "zenn-adapt: paid-from must name a heading; pass a sentinel that "
        "appears in no heading for a fully free article"
    )
closing = sys.argv[8] if len(sys.argv) > 8 else \
    "この記事では、その仕組みを解説しました。仕組みそのものに興味を持ってもらえたら嬉しいです。"
md = open(src).read()
raw_lines = md.split('\n')

# 0) article-specific explicit line drops (1-based ranges), applied to the RAW source first
drop = set()
for rng in filter(None, os.environ.get("ZENN_CUT_LINES","").split(',')):
    a,_,b = rng.partition('-'); b = b or a
    drop.update(range(int(a), int(b)+1))
md = '\n'.join(l for i,l in enumerate(raw_lines,1) if i not in drop)

# 0) strip the SOURCE front matter: the Zenn header is prepended below, and
# leaving the original one produced a second --- block inside the body.
md = re.sub(r"\A---\r?\n.*?\r?\n---(?:\r?\n|$)", "", md, count=1, flags=re.S)
# 1) strip H1, all local images (Zenn = mermaid/tables native; no thumb/infographic/figures)
md = re.sub(r'^#\s+.+$', '', md, count=1, flags=re.M)
md = re.sub(r'!\[[^\]]*\]\([^)]*images/[^)]+\)\s*', '', md)
# 2) CUT the paid section: from the paid-from heading to the end
md = re.split(r'^##\s*'+re.escape(paid_from), md, maxsplit=1, flags=re.M)[0]
# 3) cut generic run-claim blocks (やったこと / 結果) and run-promise / next-chapter sentences
md = re.sub(r'\**やったこと[:：]\**.*?(?=\n##|\n\**結果[:：])', '', md, flags=re.S)
md = re.sub(r'\**結果[:：]\**.*?(?=\n##)', '', md, flags=re.S)
md = re.sub(r'[^。\n]*(?:次の章|動かしてみたら|動かしてみた結果|実際の動かし方|実際にお金を入れて動かし)[^。\n]*。', '', md)
md = md.replace('実際の動かし方と、動かしてみた結果をお伝えします', 'Automatonを分かりやすく解説します')
# 4) un-blockquote, normalize blank lines, blank line around every table
md = re.sub(r'^>\s?', '', md, flags=re.M)
def space_tables(s):
    L=s.split('\n'); o=[]
    for l in L:
        p=o[-1] if o else ''
        istbl=lambda x:x.lstrip().startswith('|')
        if istbl(l) and not istbl(p) and p.strip(): o.append('')
        if not istbl(l) and l.strip() and istbl(p): o.append('')
        o.append(l)
    return '\n'.join(o)
md = space_tables(re.sub(r'\n{3,}','\n\n',md).strip())
# 5) frontmatter + honest closing (NO upsell / note link)
topics = '", "'.join(t.strip() for t in topics_csv.split(',') if t.strip())
title_esc = title.replace(chr(92), chr(92)*2).replace(chr(34), chr(92)+chr(34))
front = f'---\ntitle: "{title_esc}"\nemoji: "{emoji}"\ntype: "tech"\ntopics: ["{topics}"]\npublished: false\n---\n\n'
open(out,'w').write(front + md + f"\n\n## さいごに\n{closing}\n")
print(f"adapted → {out}")
