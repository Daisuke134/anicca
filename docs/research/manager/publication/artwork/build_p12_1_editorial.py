#!/usr/bin/env python3
"""Build one original P12-1 editorial illustration, 2 bilingual article packages.

Source of truth remains the existing immutable Manager blog manifest.
No web fetch, copyrighted figure, external billing, or publication side effect.
"""
from pathlib import Path
from hashlib import sha256
from io import BytesIO
import json
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[5]
ARTICLES=ROOT/"docs/research/manager/articles"
PACKAGE=ROOT/"docs/research/manager/publication/2026-10-19"
NAVY="#071424"
PANEL="#152C41"
WHITE="#F4F8FF"
MUTED="#A9BFD1"
TEAL="#41E1C9"
BLUE="#88B7FF"
AMBER="#FFD080"
PINK="#FF9790"

def font(sz):
    for p in ("/System/Library/Fonts/Supplemental/Arial.ttf",
              "/System/Library/Fonts/Helvetica.ttc",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:return ImageFont.truetype(p,sz)
        except OSError:pass
    return ImageFont.load_default()

def label(d,xy,t,sz,col=WHITE):
    d.text(xy,t,font=font(sz),fill=col)

def card(d,box):
    d.rounded_rectangle(box,radius=22,fill=PANEL)

def make_figure():
    img=Image.new("RGB",(1600,900),NAVY)
    d=ImageDraw.Draw(img)
    label(d,(90,55),"ANICCA  /  MANAGER RESEARCH",27,TEAL)
    label(d,(91,109),"P12-1    ·    REPRODUCIBILITY & OPEN BENCHMARKS",29,MUTED)
    label(d,(90,184),"What does 'reproduced' really mean?",53,WHITE)
    info=[
        ("01","SAME CODE","same data + seed","Repeatability",BLUE),
        ("02","NEW FORMULA","same synthetic data","Internal cross-check",TEAL),
        ("03","OTHER TEAM","author artifacts","External reproduction",AMBER),
        ("04","OTHER DATA","independent method","Independent replication",PINK)
    ]
    for i,(num,heading,detail,result,color) in enumerate(info):
        x=86+i*379
        card(d,(x,307,x+360,600))
        label(d,(x+24,334),num,38,color)
        label(d,(x+24,397),heading,32,WHITE)
        label(d,(x+24,449),detail,24,MUTED)
        label(d,(x+24,523),result,23,color)
    d.rounded_rectangle((95,644,1510,770),radius=18,fill="#233448")
    label(d,(124,667),"THE HIDDEN LEAK:",25,AMBER)
    label(d,(124,711),"same person in train + test  !=  unseen-person generalization",27,WHITE)
    d.line((88,812,1510,812),fill="#3C5368",width=2)
    label(d,(94,826),"Original educational diagram. No human outcome or third-party study reproduced.",22,MUTED)
    buffer=BytesIO()
    img.save(buffer,format="PNG",optimize=True)
    return buffer.getvalue()

def main():
    manifest=PACKAGE/"manifest.json"
    pkg=json.loads(manifest.read_text("utf8"))
    if any(a["slug"].startswith("manager-p12-1-reproducibility-") for a in pkg["articles"]):
        raise SystemExit("Already packaged: avoid duplicate P12-1 entries")
    pic=make_figure()
    sha=sha256(pic).hexdigest()
    relative="media/"+sha+".png"
    (PACKAGE/relative).write_bytes(pic)
    url="https://aniccaai.com/blog/manager/"+relative
    pkg["media"].append({"package_path":relative,"sha256":sha,"public_url":url})
    source_info={
      "ja":("SOTAの数字より、第三者が再計算できる「失敗」を公開しよう",
            "再現可能性、外部追試、リーク、CentaurとBehaviorBench、Managerの合成検算の限界。"),
      "en":("A Leaderboard Win Is Not a Scientific Result Until Someone Else Can Check It",
            "How to distinguish code repeatability, independent reproduction, data leakage, and real behavioral evidence.")
    }
    for language in ("ja","en"):
        source=ARTICLES/f"2026-11-07-p12-1-reproducibility-{language}.md"
        txt=source.read_text("utf8")
        marker="{{P12_1_IMAGE}}"
        if txt.count(marker)!=1:raise ValueError("Expected one illustration placeholder")
        txt=txt.replace(marker,url)
        source.write_text(txt,"utf8")
        h=sha256(txt.encode()).hexdigest()
        slug=f"manager-p12-1-reproducibility-{language}"
        dest=f"{language}/{slug}.md"
        (PACKAGE/dest).write_text(txt,"utf8")
        title,description=source_info[language]
        pkg["articles"].append({
            "source":source.relative_to(ROOT).as_posix(),
            "source_sha256":h,
            "slug":slug,"language":language,"title":title,
            "package_path":dest,
            "canonical_url":f"https://aniccaai.com/blog/{slug}",
            "date":"2026-11-07","project":"Manager",
            "lang":language,"n_papers_cited":sum(x.startswith("- [") for x in txt.splitlines()),
            "word_count":len(txt.split()),"character_count":len(txt),
            "markdown":txt,"sha256":h,
            "description":description,
            "series_order":206 if language=="ja" else 126
        })
    manifest.write_text(json.dumps(pkg,ensure_ascii=False,indent=2)+"\n","utf8")
    print(json.dumps({"articles":len(pkg["articles"]),"media":len(pkg["media"]),
                      "figure_url":url,"sha256":sha},ensure_ascii=False))

if __name__=="__main__":
    main()
