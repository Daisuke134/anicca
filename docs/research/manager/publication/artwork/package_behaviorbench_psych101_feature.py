#!/usr/bin/env python3
"""Prepare one JA+EN canonical Manager blog feature and self-authored figure.

Existing 96 articles/56 media are retained. No website deployment or network.
This script only stages a content-addressed, reviewable publication package.
Usage:
  python3 package_behaviorbench_psych101_feature.py \
    --manifest /tmp/manifest.json \
    --article-ja /tmp/article-ja.md --article-en /tmp/article-en.md \
    --figure /tmp/figure.png --outdir /tmp/staged_repo
"""
from pathlib import Path
from hashlib import sha256
from argparse import ArgumentParser
from copy import deepcopy
import json

TOKEN="{{BEHAVIORBENCH_DATA_FLOW_IMAGE}}"
ARTICLE_BASE="docs/research/manager/articles/"
PACKAGE="docs/research/manager/publication/2026-10-19/"
NAMES={
"ja":("2026-11-08-behaviorbench-psych101-what-human-ai-learns-ja.md",
      "manager-behaviorbench-psych101-training-data-ja",
      "「人間の行動を学習するAI」は、実際には何を学習しているのか",
      "BehaviorBenchとPsych-101の学習データ・教師ラベル・評価・権利を一次資料で比較"),
"en":("2026-11-08-behaviorbench-psych101-what-human-ai-learns-en.md",
      "manager-behaviorbench-psych101-training-data-en",
      "What Does a Foundation Model of Human Behavior Actually Learn?",
      "A source-grounded comparison of behavioral training data, supervised targets, evaluations, and licenses")
}

def sha(raw:bytes)->str:
    return sha256(raw).hexdigest()

def package(manifest_file:Path,articles:dict,figure_file:Path,outdir:Path)->dict:
    existing=json.loads(manifest_file.read_text("utf8"))
    data=deepcopy(existing)
    existing_slugs={x["slug"] for x in data["articles"]}
    before=(len(data["articles"]),len(data["media"]))
    fig=figure_file.read_bytes()
    imagehash=sha(fig)
    media_path=f"media/{imagehash}.png"
    media_url=f"https://aniccaai.com/blog/manager/{media_path}"
    if not any(m["sha256"]==imagehash for m in data["media"]):
        data["media"].append({"package_path":media_path,
                              "sha256":imagehash,"public_url":media_url})
    outimage=outdir/PACKAGE/media_path
    outimage.parent.mkdir(parents=True,exist_ok=True)
    outimage.write_bytes(fig)
    for lang in ("ja","en"):
        filename,slug,title,description=NAMES[lang]
        if slug in existing_slugs:
            raise ValueError(f"duplicate release slug {slug}")
        text=articles[lang].read_text("utf8")
        if text.count(TOKEN)!=1:
            raise ValueError(f"expected one source image placeholder for {lang}")
        text=text.replace(TOKEN,media_url)
        encoded=text.encode("utf8")
        digest=sha(encoded)
        source_rel=ARTICLE_BASE+filename
        destrel=f"{lang}/{slug}.md"
        source=outdir/source_rel
        packaged=outdir/PACKAGE/destrel
        source.parent.mkdir(parents=True,exist_ok=True)
        packaged.parent.mkdir(parents=True,exist_ok=True)
        source.write_bytes(encoded);packaged.write_bytes(encoded)
        data["articles"].append({
            "source":source_rel,"source_sha256":digest,
            "slug":slug,"language":lang,"title":title,
            "package_path":destrel,"canonical_url":f"https://aniccaai.com/blog/{slug}",
            "date":"2026-11-08","project":"Manager","lang":lang,
            "n_papers_cited":sum(line.startswith("- [") for line in text.splitlines()),
            "word_count":len(text.split()),"character_count":len(text),
            "markdown":text,"sha256":digest,
            "description":description,
            "series_order":207 if lang=="ja" else 127
        })
    target=outdir/PACKAGE/"manifest.json"
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n","utf8")
    return {"old_articles":before[0],"new_articles":len(data["articles"]),
            "old_media":before[1],"new_media":len(data["media"]),
            "image_sha256":imagehash,
            "source_slugs":[NAMES[x][1] for x in ("ja","en")],
            "publication_status":"PREPARED_NOT_LIVE"}

if __name__=="__main__":
    p=ArgumentParser()
    p.add_argument("--manifest",required=True)
    p.add_argument("--article-ja",required=True)
    p.add_argument("--article-en",required=True)
    p.add_argument("--figure",required=True)
    p.add_argument("--outdir",required=True)
    a=p.parse_args()
    report=package(Path(a.manifest),
                   {"ja":Path(a.article_ja),"en":Path(a.article_en)},
                   Path(a.figure),Path(a.outdir))
    print(json.dumps(report,ensure_ascii=False,indent=2))
