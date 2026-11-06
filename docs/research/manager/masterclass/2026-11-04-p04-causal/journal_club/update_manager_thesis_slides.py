"""Unify the Manager thesis across the long and 60-minute PPTX/PDF decks.

The 60-minute journal club retains its balanced 33-slide field introduction;
only the final 3 Manager slides change. The long 85-slide reference deck
changes only its matching original slides 46–48 (and their notes).
Both PDF artifacts are synchronized by replacing exactly those pages.
"""
from __future__ import annotations

import re
import tempfile
from pathlib import Path

from PIL import Image, JpegImagePlugin
from pypdf import PdfReader, PdfWriter
from pptx import Presentation
from pptx.enum.text import PP_ALIGN

from build_p04_45_appendix import (
    base,card,shape_box,text,TEAL,BLUE,ORANGE,NAVY,MUTED,LIGHT2,RED
)
from export_p04_45_pdf import render_slide
from build_60min_journal_club import add_pdf_footer

ROOT=Path(__file__).resolve().parent
LONG_PPTX=ROOT/"AI_BEHAVIOR_JOURNAL_CLUB_JA.pptx"
LONG_PDF=ROOT/"AI_BEHAVIOR_JOURNAL_CLUB_JA.pdf"
SHORT_PPTX=ROOT/"AI_BEHAVIOR_JOURNAL_CLUB_60MIN_JA.pptx"
SHORT_PDF=ROOT/"AI_BEHAVIOR_JOURNAL_CLUB_60MIN_JA.pdf"
LONG_NOTES=ROOT/"SPEAKER_NOTES_JA.md"
SHORT_SCRIPT=ROOT/"SPEAKER_SCRIPT_60MIN_JA.md"
SHORT_SCHEDULE=ROOT/"RUN_OF_SHOW_60MIN_JA.md"

TITLES=[
    "Manager：What-if Machine × Executor",
    "実証するのは、製品・流通・人への便益",
    "『結果で語る』——まだ未検証のことも示す",
]

NARRATION=[
"""ここから最後の3枚は、私たちの研究仮説としてのManagerです。分野の既存研究と、私たちがこれから検証したい主張は区別してください。核となる仮説は、人間の反応を正確に予測するWhat-ifモデルと、実際の行動を安全に行うExecutorを組み合わせれば、製品開発やマーケティング、日常生活で人を助ける意思決定を継続的に改善できるのではないか、というものです。

構造としては、人や環境の状態を理解し、複数の介入を比較し、許可された行動だけ実行し、現実の結果を独立に測定する循環です。単にそれらしい回答を生成するだけのシミュレーションではありません。ここで強調したいのは、理論上の可能性は非常に大きくても、世界一の企業や万能な介入ができると証明されたわけではない点です。計測可能な仮説として扱います。""",
"""この考えが正しいなら、Managerという基盤モデル自体を企業へ売ることを最初の必須条件にはしなくてよいはずです。Manager自身が人の求める製品やサービスを作り、必要な人へ届け、その価値を改善する。それを実際の製品で証明します。第一に製品の課題解決率、継続利用、返金やコストを含む貢献利益です。第二に配信やマーケティングの増分獲得、獲得費用、継続顧客の利益です。

そして第三は、人の暮らしや苦しみの軽減です。単にアプリへの滞在時間が増えたのではなく、たとえば反すうのPTQ、マインドフルネスのFFMQ、本人が望む生活機能や負の影響を独立に測ります。生体信号は補助であり、抑うつや強迫症状の診断・治療をAIだけで済ませるという話ではありません。データ利用・同意・安全性が前提です。""",
"""最後の問いは、もし本当に優れたWhat-ifマシンがあるなら、それによって実際に何が改善したのか、ということです。過去の投稿を模倣したり、多数のフォロワーを集めたりするだけでなく、比較対象より顧客が本当に必要とする製品を作ったのか。広告費などを差し引いて利益が増えたのか。本人の反すうや苦痛が減ったのか。そこを厳しく確かめたいと考えています。

私たちはここまで、因果推論の教材として人工データでRCTや方策比較を実行していますが、実際の人間に対する成功はまだ示していません。次は事前登録、独立した実測、公開可能なベンチマークと第三者再現です。モデルや評価コードは可能な範囲でオープンにし、将来の独自重みも権利と安全性を確認して公開を目指します。皆さんなら、この仮説を最も厳しく、かつ公平に確かめるために、どの実験を最初に設計しますか。""",
]


def create_three(prs,total:int):
    pages=[]
    k=base(prs,"MANAGER / RESEARCH THESIS",TITLES[0],
           "行動を『予測する』から、『介入・実行・検証する』へ",
           "Manager thesis — hypothesis, not a validated global optimum")
    stages=[
        ("① Behavior", "人と状況の状態\n反応を予測",TEAL),
        ("② What-if", "候補施策の因果効果\n不確実性を比較",BLUE),
        ("③ Executor", "同意・権限の範囲で\n実際に行動",ORANGE),
        ("④ Evidence", "結果・害・費用を\n独立に測定",TEAL),
    ]
    for i,(name,desc,color) in enumerate(stages):
        x=.61+i*3.17
        card(k,x,2.48,2.99,2.07,name,desc,color,17)
        if i!=3:
            text(k,x+3.01,3.27,.19,.31,"→",14,TEAL,True)
    shape_box(k,.78,5.08,11.83,1.01,LIGHT2)
    text(k,.96,5.27,11.45,.58,
         "大きな可能性は研究仮説。どの意思決定が本当に改善したか、実験で反証可能にする。",
         15.7,TEAL,True,PP_ALIGN.CENTER)
    pages.append(k)

    k=base(prs,"MANAGER / THREE TESTABLE OUTCOMES",TITLES[1],
           "最初にManagerを直接売るのではなく、Managerが生んだ成果を示す",
           "Commercial + well-being metrics / synthetic evidence ≠ clinical efficacy")
    cards=[
        ("製品が求められる", "実際の課題解決\n継続率・返金率\n貢献利益",TEAL),
        ("必要な人へ届く", "増分の顧客獲得\n獲得費用・LTV\n配信後の純利益",BLUE),
        ("苦しみが軽減する", "反すう/PTQ\nマインドフルネス/FFMQ\n生活機能・害・同意",ORANGE),
    ]
    for i,(name,detail,color) in enumerate(cards):
        card(k,.64+i*4.22,2.37,3.97,2.66,name,detail,color,17.3)
    shape_box(k,.82,5.41,11.8,1.02,LIGHT2)
    text(k,1.06,5.55,11.25,.71,
         "フォロワー数・視聴回数・売上だけでは不十分。費用を差し引いた利益と本人の実測便益で判断する。",
         16.1,TEAL,True,PP_ALIGN.CENTER)
    pages.append(k)

    k=base(prs,"MANAGER / EVIDENCE FIRST",TITLES[2],
           "分野の評価方法を、実世界の製品・方策の検証へつなげる",
           "Next: registered trials, independent evidence, responsible open publication")
    card(k,.69,2.35,5.83,2.37,
         "いま確認できていること",
         "人工データでの因果推論・RCT\n方策価値のコード検証\n研究プロトコルと発表資料",TEAL,17)
    card(k,6.72,2.35,5.81,2.37,
         "これから証明すること",
         "実在研究の未見予測\n製品・流通の増分成果\n本人の心理・生活の改善",ORANGE,17)
    shape_box(k,.84,5.08,11.67,1.29,LIGHT2)
    text(k,1.02,5.26,11.25,.92,
         "可能な範囲でコード／重みを公開し、第三者に検証してもらう。\n問い：最初にどの実験で、この仮説を厳しく試すべきか？",
         15.4,TEAL,True,PP_ALIGN.CENTER)
    pages.append(k)
    for i,slide in enumerate(pages):
        for shape in slide.shapes:
            if shape.has_text_frame and re.fullmatch(r"\d+\s*/\s*82",shape.text.strip()):
                for p in shape.text_frame.paragraphs:
                    for r in p.runs:
                        r.text=f"{i+1} / {total}"
    return pages


def swap_slides(deck_path:Path,target_indices:list[int]):
    prs=Presentation(str(deck_path))
    expected=85 if "60MIN" not in deck_path.name else 33
    if len(prs.slides)!=expected:
        raise RuntimeError(f"Unexpected {deck_path.name} slide count {len(prs.slides)}")
    if target_indices!=([45,46,47] if expected==85 else [30,31,32]):
        raise AssertionError("Unsafe slide selection")
    old_ids=list(prs.slides._sldIdLst)
    new=create_three(prs,expected)
    updated=list(prs.slides._sldIdLst)
    additions=updated[-3:]
    for i in target_indices:
        prs.part.drop_rel(old_ids[i].rId)
    replacements={i:additions[k] for k,i in enumerate(target_indices)}
    ids=prs.slides._sldIdLst
    for node in list(ids):ids.remove(node)
    for i,sldid in enumerate(old_ids):
        ids.append(replacements.get(i,sldid))
    for position,i in enumerate(target_indices):
        slide=prs.slides[i]
        frame=slide.notes_slide.notes_text_frame
        if frame is not None:
            frame.text=(
                f"第{i+1:02d}枚｜{TITLES[position]}\n"
                +f"発表本編目安{[1.7,1.6,1.7][position]}分\n\n"
                +NARRATION[position]
                +"\n\n参照：MANAGER_WHAT_IF_EXECUTOR_THESIS_JA.md／P04-6_JA.md。"
                +" 心理尺度PTQ・FFMQを含む測定案は科学的検証前。"
            )
    prs.save(str(deck_path))
    verified=Presentation(str(deck_path))
    assert len(verified.slides)==expected
    assert all(verified.slides[i].has_notes_slide for i in target_indices)
    return [verified.slides[i] for i in target_indices]


def patch_pdf(pdf_path:Path,target_indices:list[int],slide_images):
    source=PdfReader(str(pdf_path))
    pages=len(source.pages)
    expected=85 if "60MIN" not in pdf_path.name else 33
    assert pages==expected
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"replacements.pdf"
        slide_images[0].save(str(p),save_all=True,
                             append_images=slide_images[1:],quality=95,resolution=180)
        replacement=PdfReader(str(p))
        out=PdfWriter()
        slots={v:k for k,v in enumerate(target_indices)}
        for i in range(expected):
            page=replacement.pages[slots[i]] if i in slots else source.pages[i]
            out.add_page(page)
            if i in slots:
                add_pdf_footer(out,out.pages[-1],i+1,expected)
        target=Path(td)/"final.pdf"
        with target.open("wb") as f:out.write(f)
        pdf_path.write_bytes(target.read_bytes())
    assert len(PdfReader(str(pdf_path)).pages)==expected


def patch_long_notes():
    textvalue=LONG_NOTES.read_text(encoding="utf-8")
    for pos,slide_no in enumerate((46,47,48)):
        pat=rf"(?ms)^## {slide_no:02d}｜[^\n]+\n.*?(?=^## {slide_no+1:02d}｜)"
        replacement=(
            f"## {slide_no:02d}｜{TITLES[pos]}\n\n"
            +f"想定{[1.7,1.6,1.7][pos]}分\n\n"
            +NARRATION[pos]
            +"\n\n出典：本資料の仮説メモMANAGER_WHAT_IF_EXECUTOR_THESIS_JA.md／P04-6_JA.md\n\n---\n\n"
        )
        new,n=re.subn(pat,lambda _:replacement,textvalue,count=1)
        if n!=1:
            raise AssertionError(f"Cannot find full notes section {slide_no}")
        textvalue=new
    LONG_NOTES.write_text(textvalue,encoding="utf-8")


def patch_short_script():
    s=SHORT_SCRIPT.read_text(encoding="utf-8")
    for pos,slide_no in enumerate((31,32,33)):
        head=(f"## {slide_no:02d}｜{TITLES[pos]}\n\n"
              +f"**章：** Manager：私たちが検証したい方向と議論　"
              +f"**目安：** {[1.7,1.6,1.7][pos]}分　**元資料：** 詳細版{46+pos}枚\n\n"
              +f"### 読み上げ原稿\n\n{NARRATION[pos]}\n\n")
        pat=(rf"(?ms)^## {slide_no:02d}｜.*?"
             + (rf"(?=^## {slide_no+1:02d}｜)" if slide_no<33 else r"(?=\Z)"))
        new,n=re.subn(pat,lambda _:head,s,count=1)
        if n!=1:raise AssertionError(f"Cannot locate {slide_no} in short script")
        s=new
    SHORT_SCRIPT.write_text(s,encoding="utf-8")

    t=SHORT_SCHEDULE.read_text(encoding="utf-8")
    for i,title in zip((31,32,33),TITLES):
        patt=rf"(?m)^\| {i} \| 4[678] \| .*? \| .*? \|$"
        replacement=(f"| {i} | {45+(i-30)} | {[1.7,1.6,1.7][i-31]} | {title} |")
        t,n=re.subn(patt,replacement,t,count=1)
        if n!=1:raise AssertionError(f"Cannot locate {i} in run of show")
    t=t.replace(
      "Managerの方向、科学的検証、討論",
      "What-if×Executorの研究仮説、製品・流通・心理の実測証拠、公開と検証"
    )
    SHORT_SCHEDULE.write_text(t,encoding="utf-8")


def run():
    for pptx,pdf,indices in [
        (LONG_PPTX,LONG_PDF,[45,46,47]),
        (SHORT_PPTX,SHORT_PDF,[30,31,32]),
    ]:
        slides=swap_slides(pptx,indices)
        images=[render_slide(x) for x in slides]
        patch_pdf(pdf,indices,images)
        print(pptx.name,len(Presentation(str(pptx)).slides),
              pdf.name,len(PdfReader(str(pdf)).pages))
    patch_long_notes()
    patch_short_script()
    print("Synced Japanese scripts for slides 31-33 / 46-48")


if __name__=="__main__":run()
