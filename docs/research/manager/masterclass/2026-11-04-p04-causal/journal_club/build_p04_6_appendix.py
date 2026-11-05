"""Add three P04-6 appendix slides to the detailed research deck (82 -> 85).

The live 33-slide presentation is a separate artifact: do not insert this
technical material into its main body. The existing 82 PPTX slide bodies
remain untouched except for footer totals.
"""
from __future__ import annotations

import re
import tempfile
from pathlib import Path

from PIL import Image, JpegImagePlugin
from pypdf import PdfReader, PdfWriter
from pptx import Presentation

from build_p04_45_appendix import base, card, text, shape_box, TEAL, BLUE, RED, ORANGE, NAVY, MUTED, LIGHT2, PP_ALIGN
from export_p04_45_pdf import render_slide
from build_60min_journal_club import add_pdf_footer

ROOT=Path(__file__).resolve().parent
PPTX=ROOT/"AI_BEHAVIOR_JOURNAL_CLUB_JA.pptx"
PDF=ROOT/"AI_BEHAVIOR_JOURNAL_CLUB_JA.pdf"
NOTES=ROOT/"SPEAKER_NOTES_JA.md"

def append():
    prs=Presentation(str(PPTX))
    if len(prs.slides)==85:
        print("Already 85 slides; not adding twice")
        return
    if len(prs.slides)!=82 or len(PdfReader(str(PDF)).pages)!=82:
        raise RuntimeError("Expected coordinated 82-slide/PDF sources")
    narrations=[]

    s=base(prs,"APPENDIX / P04-6 PREREGISTRATION",
          "分析する前に、予測・仮説・評価方法を固定する",
          "Pre-analysis Plan：研究目的・対象・主要成果・比較方策・人数・分析規則",
          "J-PAL trial registration / AEA Registry / P04-6 synthetic plan")
    card(s,.70,2.32,5.82,1.78,"① 対象と比較","誰・いつ・何をするか／\n介入の候補と権限",TEAL,17)
    card(s,6.72,2.32,5.82,1.78,"② 主要評価と停止規則","何を主要成果とするか／\n固定標本数・多重性",BLUE,17)
    shape_box(s,.86,4.46,11.70,1.23,LIGHT2)
    text(s,1.08,4.76,11.15,.56,"人工結果を生成する前に計画JSONを保存し、SHA-256を固定",19,TEAL,True,PP_ALIGN.CENTER)
    text(s,.94,6.10,11.50,.41,"ローカルのハッシュ保存は、外部機関に登録されたRCTの代わりではない。",14,RED,True)
    narrations.append((
        83,"事前登録と分析計画",
        "P04-6は、予測精度ではなく意思決定方策そのものの増分価値を評価します。"
        "この実験では、対象、介入、対照、主要指標、人数、有意水準、停止条件を結果を見る前に決めました。"
        "結果生成前にローカル計画書をSHA256で固定しています。"
        "ただし外部の研究登録は行っておらず、これは完全架空の教育実験です。"
        "事前登録は研究結果を知ってから有利な指標を選ぶ行為を避けるために重要です。"
    ))

    s=base(prs,"APPENDIX / P04-6 POLICY-VS-POLICY RCT",
          "『施策』ではなく『施策を選ぶ方法』をRCTで比較",
          "完全架空40,000人：双方に同じ事前特徴・候補行動を与える",
          "P04-6 synthetic n=40,000 / 96 total unit tests")
    card(s,.70,2.32,5.79,1.58,"Manager型の方策","低意欲の人に通知",TEAL,21)
    card(s,6.75,2.32,5.79,1.58,"比較ヒューリスティック","低意欲・低疲労の人に通知",BLUE,18)
    shape_box(s,.80,4.34,11.75,1.37,LIGHT2)
    text(s,.97,4.59,11.28,.54,"推定増分 +1.61 pt  ／  95%CI +0.69〜+2.54 pt",22,TEAL,True,PP_ALIGN.CENTER)
    text(s,1.06,5.12,11.02,.32,"成果 − 通知負担0.02／回 の合成効用を評価",12,MUTED,False,PP_ALIGN.CENTER)
    text(s,.91,6.10,11.44,.42,"比較相手は合理的な固定ルールだが、あらゆる方策の最強baselineではない。",13,RED,True)
    narrations.append((
        84,"方策対方策の無作為化比較",
        "施策そのものの効果と、施策を選ぶ方策の効果は異なります。"
        "今回、架空40,000人をManager型のルールまたは比較ルールへ無作為割当しました。"
        "両者は同じ特徴と二つの候補行動を使います。主な指標はタスク完了から人工的な通知負担0.02を引いた効用です。"
        "平均差は+1.61ポイント、95%区間は+0.69〜+2.54ポイントでした。"
        "生成ルールで理論上の真値+2.00ポイントを知っています。これが人間の実験結果ではないことを強調します。"
    ))

    s=base(prs,"APPENDIX / P04-6 OPTIONAL PEEKING",
          "結果を見ながら途中停止すると、偽陽性率が膨らむ",
          "人工A/A試験750回：真の効果はゼロ、未補正の名目5%検定",
          "P04-6 synthetic null Monte Carlo / J-PAL pre-analysis plans")
    card(s,.76,2.46,5.71,1.94,"最終1回の検定","偽陽性 4.27%",TEAL,23)
    card(s,6.72,2.46,5.71,1.94,"途中6回で有意なら成功","偽陽性 15.20%",RED,23)
    shape_box(s,.83,4.79,11.69,1.05,LIGHT2)
    text(s,1.00,5.04,11.24,.51,"途中解析は、群逐次法などで誤判定率を事前に制御できる",17,NAVY,True,PP_ALIGN.CENTER)
    narrations.append((
        85,"途中のぞきと偽陽性",
        "名目5%の検定を何度も途中で実行し、都合のよい時点で有意なら成功とすると、実験全体の誤判定率は高くなります。"
        "効果ゼロの人工A/A試験を750回繰り返したところ、最終1回で4.27%、途中6回のどこかで有意なら15.20%の偽陽性率でした。"
        "途中解析が悪いのではなく、順序と判定規則を事前に設計し、補正なしの都合のよい停止を避けることが重要です。"
        "研究の実登録や本当のユーザーへの介入は行っていません。"
    ))

    assert len(prs.slides)==85
    for k,slide in enumerate(prs.slides,1):
        for sh in slide.shapes:
            if sh.has_text_frame and re.fullmatch(r"\s*\d+\s*/\s*(?:82|85)\s*",sh.text):
                for para in sh.text_frame.paragraphs:
                    for run in para.runs:run.text=f"{k} / 85"
                break
    for page,title,body in narrations:
        frame=prs.slides[page-1].notes_slide.notes_text_frame
        if frame is not None:frame.text=f"第{page}枚｜{title}\n\n{body}"
    prs.save(str(PPTX))
    assert len(Presentation(str(PPTX)).slides)==85

    old_pdf=PdfReader(str(PDF))
    with tempfile.TemporaryDirectory() as td:
        extra=Path(td)/"appendix.pdf"
        pics=[render_slide(prs.slides[i]) for i in range(82,85)]
        pics[0].save(str(extra),save_all=True,append_images=pics[1:],
                     quality=95,resolution=180)
        added=PdfReader(str(extra))
        assert len(added.pages)==3
        writer=PdfWriter()
        for k in range(1,86):
            pg=old_pdf.pages[k-1] if k<=82 else added.pages[k-83]
            writer.add_page(pg)
            if k<=82:
                fill=prs.slides[k-1].background.fill
                if fill.type==1:
                    col=fill.fore_color.rgb
                    bg=(col[0]/255,col[1]/255,col[2]/255)
                else:bg=(1,1,1)
                add_pdf_footer(writer,writer.pages[-1],k,85,bg)
        target=Path(td)/"85.pdf"
        with target.open("wb") as f:writer.write(f)
        target.replace(PDF)
    assert len(PdfReader(str(PDF)).pages)==85

    contents=NOTES.read_text(encoding="utf-8")
    contents=contents.replace("全82枚の発表者ノート","全85枚の発表者ノート")
    contents=contents.replace("全82枚の","全85枚の")
    addon="\n\n---\n\n## P04-6：追加研究付録（83〜85）\n\n"
    addon+="\n\n".join(
        f"## {k}｜{title}\n\n{body}\n" for k,title,body in narrations)
    if "P04-6：追加研究付録（83〜85）" not in contents:
        NOTES.write_text(contents+addon+"\n",encoding="utf-8")

    after=Presentation(str(PPTX))
    assert all(s.has_notes_slide for s in after.slides)
    print("MASTER SLIDES",len(after.slides),"PDF",len(PdfReader(str(PDF)).pages),
          "NOTES",sum(s.has_notes_slide for s in after.slides))


if __name__=="__main__":
    append()
