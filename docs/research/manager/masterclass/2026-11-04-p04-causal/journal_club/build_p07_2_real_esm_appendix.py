"""Append two P07-2 research slides: archive 98 -> 100 English slides,
Japanese speaker notes. Do not alter the 34-slide public talk."""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
import re

from pptx import Presentation
from pypdf import PdfReader,PdfWriter
from PIL import Image
from build_p04_45_appendix import base,card,text,shape_box,TEAL,BLUE,ORANGE,LIGHT2,PP_ALIGN
from export_p04_45_pdf import render_slide
from build_60min_journal_club import add_pdf_footer

ROOT=Path(__file__).resolve().parent
PPTX=ROOT/"AI_BEHAVIOR_JOURNAL_CLUB_JA.pptx"
PDF=ROOT/"AI_BEHAVIOR_JOURNAL_CLUB_JA.pdf"
NOTES=ROOT/"SPEAKER_NOTES_JA.md"
STORIES=[
(99,"Latent state vs observed signal",
 "P07-2で重要なのは、行動・自己報告・EEGなどの観測と、直接は見えない注意・感情・反すうなどの潜在状態を区別することです。"
 "一人がスマートフォンを見続けても、喜び・習慣・仕事・不安の回避など複数の状態があり、"
 "観測行動から心理状態を一意に決めることはできません。"
 "Mind Wanderingとは課題から内的思考へ注意が移ること、Ruminationは反復的な思考のパターンであり、同じではありません。"
 "Task focus、意図的MW、意図しないMW、反すう、心配、meta-awarenessは区別します。"
 "2026年のZhangとKoolのGLM-HMM研究は93人の実人間において潜在的な注意状態を行動から推定し、時々のプローブ回答で検証しました。"
 "ただし2状態HMMが推定した状態は、本人の本当の内的状態そのものと等しいわけではありません。"
 "DMNやEEGの特徴をMind Wanderingの絶対的な真実と呼ばないことも重要です。"),
(100,"Real experience sampling and next-state prediction",
 "今回はopenESMに公開されたHoebekeの反すう関連の自己報告40人と、"
 "Dejonckheereの感情・ストレスの自己報告100人を取得しました。"
 "同じ日の隣接した時点を1件の予測例にし、未来の回答は入力に入れず、人物ごとに学習・検証・テストへ分割しました。"
 "Hoebekeでは実際の1450遷移を利用し、直前のBroodingをそのまま使うと未知8人のテストRMSEは30.80、"
 "検証群で採用したRidgeでは25.98でした。"
 "Dejonckheereでは6890遷移を利用し、未知20人のテストで直前のストレス27.30に対し、RandomForest24.54でした。"
 "ただしDejonckheereの公開TSVには反すうを直接測る項目がないため、ストレス予測を反すう予測と呼びません。"
 "また、どちらも自分の生活の中で実際に回答した数値を予測しただけで、治療や反すうの減少を実証していません。"),
]

def update_footer(slide,n,total):
    for shape in slide.shapes:
        if shape.has_text_frame and re.fullmatch(r"\s*\d+\s*/\s*\d+\s*",shape.text):
            for paragraph in shape.text_frame.paragraphs:
                for run in paragraph.runs:run.text=f"{n} / {total}"
            break

def run():
    pres=Presentation(str(PPTX));pdf=PdfReader(str(PDF))
    if len(pres.slides)!=98 or len(pdf.pages)!=98:
        raise RuntimeError("Expected 98-page research archive; no duplicate append")

    slide=base(pres,"APPENDIX / P07-2 | OBSERVED VS LATENT",
        "The same action can reflect different inner states",
        "Observe behavior and self-report; infer attention, affect and thoughts probabilistically",
        "Zhang & Kool (2026) GLM-HMM | 2025 mind wandering measurement review")
    for i,(label,body,col) in enumerate([
       ("Observations","Choice / response time\nExperience sampling / EEG",BLUE),
       ("Latent hypotheses","Attention / affect / awareness\nRumination / worry",ORANGE),
       ("Evaluation","Hold out people and time\nCheck probes and uncertainty",TEAL),
    ]):
        card(slide,.70+4.22*i,2.4,3.98,2.38,label,body,col,15.9)
    shape_box(slide,.86,5.21,11.64,1.22,LIGHT2)
    text(slide,1.08,5.40,11.19,.72,
         "Mind wandering ≠ rumination ≠ harm.\nPredictive state inference is not a validated intervention.",
         15.6,TEAL,True,PP_ALIGN.CENTER)

    slide=base(pres,"APPENDIX / P07-2 | ACTUAL HUMAN ESM",
        "Forecast next self-report — with real people",
        "Participant-disjoint heldout tests; strong last-value baseline",
        "OpenESM Hoebeke (2022), Dejonckheere (2019) | CC BY 4.0")
    card(slide,.80,2.38,5.76,2.43,
       "Brooding / rumination-related","40 people | 1,450 transitions\nRMSE: 30.80 → 25.98",TEAL,17.4)
    card(slide,6.74,2.38,5.76,2.43,
       "Stress / affect — distinct label","100 people | 6,890 transitions\nRMSE: 27.30 → 24.54",BLUE,17.0)
    shape_box(slide,.84,5.20,11.66,1.24,LIGHT2)
    text(slide,1.08,5.42,11.2,.75,
       "Self-reports forecast only. No mind-wandering probe/EEG was analyzed.\nNo real intervention or reduced rumination demonstrated.",
       15.4,ORANGE,True,PP_ALIGN.CENTER)

    assert len(pres.slides)==100
    for i,s in enumerate(pres.slides,1):update_footer(s,i,100)
    for number,label,story in STORIES:
        frame=pres.slides[number-1].notes_slide.notes_text_frame
        if frame:frame.text=f"第{number}枚｜{label}\n\n{story}\n\n詳しい方法と出典: P07-2_JA.md。"
    pres.save(str(PPTX))
    images=[render_slide(pres.slides[i]) for i in range(98,100)]
    with TemporaryDirectory() as tmp:
        td=Path(tmp)
        new=td/"extra.pdf"
        images[0].save(str(new),save_all=True,append_images=images[1:],resolution=180,quality=95)
        pdfnew=PdfReader(str(new))
        writer=PdfWriter()
        for i in range(1,101):
            was_old=i<=98
            writer.add_page(pdf.pages[i-1] if was_old else pdfnew.pages[i-99])
            if was_old:
                fill=pres.slides[i-1].background.fill
                if fill.type==1:
                    col=fill.fore_color.rgb
                    color=(col[0]/255,col[1]/255,col[2]/255)
                else:color=(1,1,1)
                add_pdf_footer(writer,writer.pages[-1],i,100,color)
        out=td/"full.pdf"
        with out.open("wb") as stream:writer.write(stream)
        PDF.write_bytes(out.read_bytes())
    original=NOTES.read_text(encoding="utf-8").replace("全98枚の","全100枚の")
    label="## P07-2: Latent mental states / real ESM (99–100)"
    add="\n\n---\n\n"+label+"\n\n"
    add+="\n\n".join(f"## {number}｜{title}\n\n{story}\n" for number,title,story in STORIES)
    if label not in original:NOTES.write_text(original+add+"\n",encoding="utf-8")
    print("ARCHIVE",len(pres.slides),"PDF",len(PdfReader(str(PDF)).pages),
          "speaker notes",sum(x.has_notes_slide for x in pres.slides),"LIVE_34_UNCHANGED")

if __name__=="__main__":run()
