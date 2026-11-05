"""Append 2 English P07-1 REAL human reward-habit study slides to archive.

Source archive: 96 -> 98 slides/pages + Japanese note for each.
Keep the 34-slide public presentation and its PDF/manuscript intact.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from PIL import Image
from pptx import Presentation
from pypdf import PdfReader,PdfWriter
import re

from build_p04_45_appendix import (
    base,card,text,shape_box,TEAL,BLUE,ORANGE,RED,LIGHT2,PP_ALIGN
)
from export_p04_45_pdf import render_slide
from build_60min_journal_club import add_pdf_footer

ROOT=Path(__file__).resolve().parent
PPTX=ROOT/"AI_BEHAVIOR_JOURNAL_CLUB_JA.pptx"
PDF=ROOT/"AI_BEHAVIOR_JOURNAL_CLUB_JA.pdf"
NOTES=ROOT/"SPEAKER_NOTES_JA.md"

NARRATIONS=[
(97,"Real human reward-habit prediction",
 "今回の研究は完全な架空サンプルではなく、Anne Collinsの公開された報酬学習課題を使用しています。"
 "論文は2026年のNature Human Behaviourで、データとMATLABコードはMITライセンスで公開されています。"
 "そのうち5研究を対象とし、原データから選択と報酬の順序を保持して約27万件の実試行を読み取り、"
 "現在選択を予測するときに未来の正解や結果を混ぜないようにしました。"
 "比較したのは報酬のみ、習慣のみ、報酬プラス習慣、そして作業記憶も加えた簡略モデルです。"
 "基本課題の未知参加者16人で、Log lossは報酬のみ0.5108から報酬・習慣・記憶の0.4866に改善しました。"
 "さらに別の4研究、EEG・fMRI・発達・確率報酬の実データでもモデルを再調整せずに調べました。"
 "ただし簡略化した予測器であり、論文の全モデルや脳内機構の厳密な再現ではありません。"),
(98,"Observed repeats are not the same as habits",
 "実人間の行動の反復は、何かに失敗した後でも同じ選択を繰り返したかで分析できます。"
 "4つの報酬が正誤に近い課題、延べ445人で、報酬がなかった後の同じ行動の反復率は、"
 "低負荷9.3パーセント、高負荷21.4パーセントでした。"
 "一方、報酬が確率的な課題では低負荷50.7パーセント、高負荷48.3パーセントで、"
 "報酬がなかったことと失敗は同じではありません。"
 "Turnerらの2026年Nature CommunicationsのSNS研究は、2696人のX投稿行動で"
 "報酬学習と習慣の混合モデルを分析しています。今回は同論文の図用の確認群1558人の"
 "公開パラメータから相関を計算しましたが、元モデル全体の再学習ではありません。"
 "これらは観測された選択の分析であり、生活の改善、反すうの減少、"
 "人間への介入効果まで実証したものではありません。次はP07-2です。"),
]

def foot(slide,n,total):
    for shp in slide.shapes:
        if shp.has_text_frame and re.fullmatch(r"\s*\d+\s*/\s*\d+\s*",shp.text):
            for para in shp.text_frame.paragraphs:
                for run in para.runs: run.text=f"{n} / {total}"
            break

def run():
    deck=Presentation(str(PPTX))
    oldpdf=PdfReader(str(PDF))
    if len(deck.slides)!=96 or len(oldpdf.pages)!=96:
        raise RuntimeError("Only append when research archive is 96 slides/pages")

    s=base(deck,"APPENDIX / P07-1 | ACTUAL HUMAN BEHAVIOR",
           "Reward alone does not fully explain choices",
           "Same real trials, disjoint participants, held-out experiments",
           "Collins (2026), Nature Human Behaviour | MIT original code/data")
    card(s,.72,2.37,3.92,2.38,"Reward-only","Log loss 0.5108\nExpe1: 10,461 held-out trials",BLUE,16.5)
    card(s,4.88,2.37,3.92,2.38,"Habit-only","Log loss 0.6874\nSame held-out trials",ORANGE,16.5)
    card(s,9.04,2.37,3.92,2.38,"Reward+Habit+Memory","Log loss 0.4866\nBest validated model",TEAL,15.4)
    shape_box(s,.86,5.15,11.66,1.29,LIGHT2)
    text(s,1.04,5.36,11.23,.86,
         "5 real experimental datasets | 269,603 eligible observed trials\n"
         "Prediction only: does not establish a psychological mechanism or benefit.",
         15.2,TEAL,True,PP_ALIGN.CENTER)

    s=base(deck,"APPENDIX / P07-1 | HABIT VS REWARD",
           "Repeating an action is not proof of a habit",
           "Observed repeated choices after NO reward, split by feedback type",
           "Collins WMH (2026); Turner et al. Nat Commun (2026)")
    card(s,.72,2.35,5.85,2.42,
         "Mostly deterministic feedback",
         "After no reward:\nLow load 9.3%  |  High load 21.4%",TEAL,16.1)
    card(s,6.78,2.35,5.80,2.42,
         "Probabilistic feedback",
         "After no reward:\nLow load 50.7%  |  High load 48.3%",BLUE,16.1)
    shape_box(s,.87,5.20,11.62,1.26,LIGHT2)
    text(s,1.06,5.39,11.24,.81,
         "No reward ≠ wrong choice in a stochastic world.\n"
         "X posting: 2,696 real users; hybrid reward+habit studied independently.",
         15.2,ORANGE,True,PP_ALIGN.CENTER)

    assert len(deck.slides)==98
    for i,slide in enumerate(deck.slides,1):foot(slide,i,98)
    for index,name,words in NARRATIONS:
        frame=deck.slides[index-1].notes_slide.notes_text_frame
        if frame:frame.text=f"第{index}枚｜{name}\n\n{words}\n\n参照：P07-1_JA.md。"
    deck.save(str(PPTX))

    images=[render_slide(deck.slides[i]) for i in range(96,98)]
    with TemporaryDirectory() as tmp:
        td=Path(tmp)
        source=td/"extra.pdf"
        images[0].save(str(source),save_all=True,append_images=images[1:],
                       resolution=180,quality=95)
        added=PdfReader(str(source))
        writer=PdfWriter()
        for i in range(1,99):
            old=i<=96
            writer.add_page(oldpdf.pages[i-1] if old else added.pages[i-97])
            if old:
                fill=deck.slides[i-1].background.fill
                if fill.type==1:
                    col=fill.fore_color.rgb
                    background=(col[0]/255,col[1]/255,col[2]/255)
                else:
                    background=(1,1,1)
                add_pdf_footer(writer,writer.pages[-1],i,98,background)
        target=td/"merged.pdf"
        with target.open("wb") as f:writer.write(f)
        PDF.write_bytes(target.read_bytes())
    assert len(PdfReader(str(PDF)).pages)==98

    old=NOTES.read_text(encoding="utf-8").replace("全96枚の発表者ノート","全98枚の発表者ノート").replace("全96枚の","全98枚の")
    marker="## P07-1 actual human reward/habit evidence (97–98)"
    section="\n\n---\n\n"+marker+"\n\n"
    section+="\n\n".join(
        f"## {num}｜{label}\n\n{story}\n" for num,label,story in NARRATIONS
    )
    if marker not in old: NOTES.write_text(old+section+"\n",encoding="utf-8")
    print("RESEARCH_ARCHIVE 98 PPTX/98 PDF, all two new English slides with Japanese notes; live 34 unchanged")

if __name__=="__main__":run()
