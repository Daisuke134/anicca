"""Update an EXISTING benchmark slide; preserve 34-slide/93-slide counts.

Replace the lower-priority SSDataBench card by BehaviorBench/Be.FM1.5 and add
source/precision to speaker notes. This is a factual, source-grounded update,
not an extra presentation slide. PDFs are revised only on matched pages.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import re

from pptx import Presentation
from PIL import Image
from pypdf import PdfReader, PdfWriter

from export_p04_45_pdf import render_slide
from build_60min_journal_club import add_pdf_footer

ROOT=Path(__file__).resolve().parent
PAGES=[
    ("AI_BEHAVIOR_JOURNAL_CLUB_60MIN_JA",26),
    ("AI_BEHAVIOR_JOURNAL_CLUB_JA",42),
]
NEW_NARRATION=(
    "共通ベンチマークは既に存在します。例えばSimBenchは20の人間行動データセットを使い、"
    "人間の分布への忠実さを評価します。Human Behavior Benchは米国の実成人1,244人の回答に基づく"
    "1,199課題を用意し、うち960問は非公開です。これは未来の購買や介入効果を直接測るものではありません。"
    "重要な進展としてBehaviorBenchが、個人予測と集団分布の20シナリオを評価し、"
    "Qwen3-4Bを元にしたBe.FM 1.5-4Bの公開LoRAも提供しています。"
    "ただし評価コードはMITでも、公開データセットの利用条件はCC BY-NC-NDです。"
    "Artificial Societies Benchmarkは複数の妥当性診断を、HumanStudy-Benchは実験の元手順と"
    "統計的な結果の再現を扱い、Socratesは研究単位で未見の回答予測を検査します。"
    "一つの数字をそのまま個人・集団・因果・実利益の世界順位とみなさないことが重要です。"
)
SOURCE7="B07 https://github.com/umich-foreseer/behaviorbench_eval | https://huggingface.co/befm/BeFM1.5-4B"

def replace_text(prs, idx):
    slide=prs.slides[idx]
    counts={"label":0,"measurement":0,"description":0,"sources":0}
    mapping={
        "SSDataBench":("BehaviorBench", "label"),
        "5 statistical patterns":("20 scenarios", "measurement"),
        "相関・系列・統計的現実性":("個別・分布／Be.FM 1.5", "description"),
        "[B01] [B02] [B03] [B04] [B05] [B06]":(
            "[B01] [B02] [B03] [B07] [B05] [B06]","sources"),
    }
    for shape in slide.shapes:
        if not getattr(shape,"has_text_frame",False):
            continue
        for para in shape.text_frame.paragraphs:
            for run in para.runs:
                for old,(new,category) in mapping.items():
                    if old in run.text:
                        run.text=run.text.replace(old,new)
                        counts[category]+=1
    if any(x!=1 for x in counts.values()):
        raise RuntimeError(f"Expected one replacement per field on slide {idx+1}: {counts}")
    frame=slide.notes_slide.notes_text_frame
    if frame is None:
        raise AssertionError("Speaker notes missing")
    existing=frame.text
    if "共通ベンチマークはすでに存在します。" in existing:
        prior=existing.split("共通ベンチマークはすでに存在します.",1)
        # Original internal note is the narration + concise page metadata.
        frame.text=prior[0]+NEW_NARRATION+"\n\n一次資料: "+SOURCE7
    else:
        frame.text=existing+"\n\n更新（2026-11-04）: "+NEW_NARRATION+"\n一次資料: "+SOURCE7
    return slide

def patch_pdf(pptx, target, one_based):
    prs=Presentation(str(pptx))
    image=render_slide(prs.slides[one_based-1])
    original=PdfReader(str(target))
    assert len(original.pages)==len(prs.slides)
    with TemporaryDirectory() as temp:
        from pathlib import Path
        tmp=Path(temp)
        replacement=tmp/"page.pdf"
        image.save(str(replacement),resolution=180,quality=95)
        page=PdfReader(str(replacement)).pages[0]
        writer=PdfWriter()
        for idx in range(len(original.pages)):
            writer.add_page(page if idx==one_based-1 else original.pages[idx])
            if idx==one_based-1:
                add_pdf_footer(writer,writer.pages[-1],one_based,len(prs.slides),(1,1,1))
        out=tmp/"new.pdf"
        with out.open("wb") as fp: writer.write(fp)
        target.write_bytes(out.read_bytes())
    assert len(PdfReader(str(target)).pages)==len(prs.slides)

def update_notes():
    path=ROOT/"SPEAKER_NOTES_JA.md"
    s=path.read_text(encoding="utf-8")
    a=s.index("## 42｜共通ベンチマークは、すでに存在する")
    b=s.index("\n---\n",a)
    section=s[a:b]
    replacement=(
        "## 42｜共通ベンチマークは、すでに存在する\n\n"
        "共通ベンチマークは、すでに存在する\n想定 1〜1.5分\n\n"
        +NEW_NARRATION+"\n\n"
        "B01 https://simbench.tiancheng.hu/\n"
        "B02 https://arxiv.org/abs/2609.30030\n"
        "B03 https://www.getrehearsals.com/human-behavior-bench\n"
        "B05 https://social-simulation-arena.com/\n"
        "B06 https://aclanthology.org/2025.emnlp-main.1530/\n"
        +SOURCE7+"\n\n一次資料: [B01] [B02] [B03] [B07] [B05] [B06]\n"
    )
    s=s[:a]+replacement+s[b:]
    path.write_text(s,encoding="utf-8")
    script=ROOT/"SPEAKER_SCRIPT_60MIN_JA.md"
    t=script.read_text(encoding="utf-8")
    a=t.index("## 26｜共通ベンチマークは、すでに存在する")
    b=t.index("\n---\n",a)
    portion=t[a:b]
    if "### 読み上げ原稿" not in portion:
        raise ValueError("Slide26 script content not found")
    pre=portion.split("### 読み上げ原稿",1)[0]
    t=t[:a]+pre+"### 読み上げ原稿\n\n"+NEW_NARRATION+"\n"+t[b:]
    script.write_text(t,encoding="utf-8")

def run():
    for prefix,page in PAGES:
        ppt=ROOT/(prefix+".pptx")
        pdf=ROOT/(prefix+".pdf")
        deck=Presentation(str(ppt))
        assert len(deck.slides) in (34,93)
        replace_text(deck,page-1)
        deck.save(str(ppt))
        patch_pdf(ppt,pdf,page)
        print(prefix, "slide",page,"slidecount",len(deck.slides))
    update_notes()
    print("Slide 26 and 42 updated; presentation duration unchanged")

if __name__=="__main__":run()
