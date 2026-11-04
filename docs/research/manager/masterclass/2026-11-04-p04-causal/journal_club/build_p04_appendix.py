"""Append 6 P04-1/P04-3 appendix slides to the 68-slide canonical source.

No AI-generated marketing claims. Keeps the original deck's first 68 pages.
Run: python journal_club/build_p04_appendix.py --source SOURCE.pptx --output DEST.pptx
"""
from pathlib import Path
import argparse
import re
import sys
import numpy as np
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

NAVY = RGBColor(23,43,62)
TEAL = RGBColor(0,122,127)
PALE = RGBColor(233,245,244)
GRAY = RGBColor(85,106,124)
LIGHT = RGBColor(245,248,250)
RED = RGBColor(184,56,52)
AMBER = RGBColor(181,113,20)
WHITE = RGBColor(255,255,255)


def rect(slide,x,y,w,h,fill=WHITE,line=None,radius=False):
    shape=slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,
                                Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid(); shape.fill.fore_color.rgb=fill
    if line is None:shape.line.fill.background()
    else:shape.line.color.rgb=line
    return shape


def textbox(slide,text,x,y,w,h,size=18,bold=False,color=NAVY,align=None):
    shp=slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf=shp.text_frame; tf.clear(); tf.word_wrap=True
    tf.margin_top=Inches(.015);tf.margin_bottom=Inches(.01)
    tf.margin_left=Inches(.03);tf.margin_right=Inches(.03)
    for k,line in enumerate(str(text).split('\n')):
        p=tf.paragraphs[0] if k==0 else tf.add_paragraph()
        p.text=line;p.space_before=Pt(0);p.space_after=Pt(0)
        if align is not None:p.alignment=align
        for r in p.runs:
            r.font.name='Noto Sans CJK JP';r.font.size=Pt(size)
            r.font.bold=bold;r.font.color.rgb=color
    return shp


def setup_slide(prs,kicker,title,desc,number,source):
    s=prs.slides.add_slide(prs.slide_layouts[0])
    rect(s,0,0,.16,7.5,TEAL)
    textbox(s,kicker.upper(),.48,.18,11.8,.3,size=11,bold=True,color=TEAL)
    textbox(s,title,.48,.60,12.20,.72,size=27,bold=True)
    textbox(s,desc,.51,1.48,12.00,.54,size=16,color=GRAY)
    rect(s,.5,7.04,12.25,.015,RGBColor(222,232,235))
    textbox(s,source,.51,7.10,11.50,.21,size=8,color=GRAY)
    textbox(s,f'{number:02d} / 74',12.00,7.10,.78,.23,size=8,color=GRAY,align=PP_ALIGN.RIGHT)
    return s


def card(s,title,body,x,y,w,h=.95,color=TEAL):
    rect(s,x,y,w,h,LIGHT,radius=True)
    textbox(s,title,x+.12,y+.09,w-.25,.31,size=14,bold=True,color=color)
    textbox(s,body,x+.12,y+.43,w-.25,h-.43,size=11,color=NAVY)


def arrow(s,x1,y1,x2,y2,color=GRAY):
    from pptx.enum.shapes import MSO_CONNECTOR
    from pptx.enum.dml import MSO_LINE_DASH_STYLE
    sh=s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,Inches(x1),Inches(y1),Inches(x2),Inches(y2))
    sh.line.color.rgb=color;sh.line.width=Pt(2)
    return sh


def build(source,output,figure_dir):
    prs=Presentation(source)
    assert len(prs.slides)==68, f'Expected canonical 68 slides, found {len(prs.slides)}'
    for slide in prs.slides:
        for shape in slide.shapes:
            if not shape.has_text_frame:continue
            for p in shape.text_frame.paragraphs:
                for r in p.runs:
                    r.text=re.sub(r'(\b\d{1,2}\s*/\s*)68\b',r'\g<1>74',r.text)

    # 69: confounding vs collider and the counterfactual target.
    s=setup_slide(prs,'APPENDIX / P04-1 REVIEW','交絡・媒介・Collider：なぜ「全部調整」が危険か',
                  '因果構造を描いてから、調整してよい介入前変数を選ぶ',69,'P04-1 / Hernán & Robins, Causal Inference: What If')
    card(s,'交絡（調整の候補）','A ← U → Y\n介入前の共通原因U',.62,2.23,3.86,1.25)
    card(s,'媒介（総効果では要注意）','A → M → Y\n経路の一部を消す',4.71,2.23,3.86,1.25,AMBER)
    card(s,'Collider（条件付けに注意）','A → S ← U → Y\nS=1選択がバイアスに',8.80,2.23,3.86,1.25,RED)
    rect(s,.65,4.05,12.02,1.9,PALE,radius=True)
    textbox(s,'潜在的結果',.93,4.22,2.0,.37,size=18,bold=True,color=TEAL)
    textbox(s,'Yᵢ(1) = 通知したとき       Yᵢ(0) = 通知しなかったとき',2.75,4.26,9.45,.40,size=20,bold=True)
    textbox(s,'ATE = E[Y(1) − Y(0)]。同じ人の二つの結果を実データでは同時に観測できない。',.94,5.08,11.5,.48,size=16)

    # 70 target trial & identifiability.
    s=setup_slide(prs,'APPENDIX / P04-3 IDENTIFICATION','RCTなしで効果を識別するための4条件',
                  'まずtarget trialを定義し、推定対象・処置・time zero・結果を先に固定',70,
                  'Hernán & Robins, What If / P04-3 教育用資料')
    card(s,'① 交換可能性','(Y(1),Y(0)) ⟂ A | X\n未測定交絡がない仮定',.65,2.22,5.89,1.40)
    card(s,'② Positivity','0 < e(X) < 1\nどちらの処置にも機会がある',6.78,2.22,5.89,1.40)
    card(s,'③ Consistency','Y = Y(A)\n処置内容・時間・結果を固定',.65,3.84,5.89,1.40)
    card(s,'④ 干渉への配慮','他者への通知が本人の結果を変えないか\n口コミや集団効果に注意',6.78,3.84,5.89,1.40)
    rect(s,.68,5.65,11.95,.6,PALE,radius=True)
    textbox(s,'仮定をデータ精度で証明することはできない。欠ければ「識別不能」と返す。',.83,5.76,11.65,.33,size=15,bold=True,color=TEAL)

    # 71 g formula and actual results.
    s=setup_slide(prs,'APPENDIX / P04-3 G-FORMULA','「同じ人の特徴」で比べ、元の人口構成に戻す',
                  '介入前Xで層別 → 層内比較 → 対象集団のP(X)で平均する',71,
                  'P04-3 synthetic n=30,000 seed=20261104 / Hernán & Robins')
    textbox(s,'ATE = Σₓ P(X=x) × [ E(Y|A=1,X=x) − E(Y|A=0,X=x) ]',.74,2.15,12.08,.60,size=21,bold=True,color=TEAL)
    card(s,'高い意欲（50%）','通知あり70% − なし80%\n→ −10 ポイント',.7,2.98,5.94,1.20)
    card(s,'低い意欲（50%）','通知あり10% − なし20%\n→ −10 ポイント',6.78,2.98,5.87,1.20)
    textbox(s,'観察差',1.13,4.65,2.3,.42,size=16,bold=True,color=GRAY)
    textbox(s,'+26.12 pt',3.10,4.54,3.07,.61,size=27,bold=True,color=RED)
    textbox(s,'標準化ATE',6.8,4.65,2.3,.42,size=16,bold=True,color=GRAY)
    textbox(s,'−9.98 pt',9.15,4.54,3.11,.61,size=27,bold=True,color=TEAL)
    textbox(s,'全て人工データ。欠けた交絡因子を自動で補うことはできない。',1.17,5.57,10.8,.43,size=16)

    # 72 IPW/AIPW + result chart.
    s=setup_slide(prs,'APPENDIX / P04-3 IPW & AIPW','IPWとAIPW：どちらのモデルが何を補正するか',
                  'e(X)=通知される確率  ／  mₐ(X)=その行動をした場合の結果予測',72,
                  'P04-3 synthetic 30,000 / AIPW not cross-fitted')
    card(s,'IPW（重み付け）','起きにくい処置の観測を重くする\n確率eが0/1付近なら不安定',.70,2.10,5.95,1.21)
    card(s,'AIPW（二重ロバスト）','結果モデルmₐと選択モデルeを併用\n未測定交絡は解決しない',6.78,2.10,5.85,1.21)
    im=str(Path(figure_dir)/'p04_3_estimates.png')
    s.shapes.add_picture(im,Inches(1.08),Inches(3.45),width=Inches(11.2),height=Inches(2.87))

    # 73 DiD plot.
    s=setup_slide(prs,'APPENDIX / P04-3 DID','DiD：施策前後の変化を比較する',
                  '介入後の単純差ではなく、非介入群の自然な変化を差し引く',73,
                  'Synthetic 2x2 example only / Goodman-Bacon 2021; Callaway & Sant’Anna 2021')
    s.shapes.add_picture(str(Path(figure_dir)/'p04_3_did.png'),Inches(.79),Inches(2.18),width=Inches(7.0),height=Inches(3.93))
    rect(s,8.1,2.55,4.45,2.95,PALE,radius=True)
    textbox(s,'介入群：38 − 30 = +8pt',8.35,2.86,3.99,.55,size=17,bold=True)
    textbox(s,'比較群：25 − 20 = +5pt',8.35,3.58,3.99,.55,size=17,bold=True)
    textbox(s,'DiD = +3pt',8.35,4.35,3.98,.57,size=23,bold=True,color=TEAL)
    textbox(s,'平行トレンド・同時ショック・導入時点の違いに注意',.85,6.24,11.82,.33,size=13,color=GRAY)

    # 74 Manager connection and next.
    s=setup_slide(prs,'APPENDIX / MANAGER RESEARCH GATE','Managerのwhat-ifに必要なのは「識別のゲート」',
                  '行動予測が高精度でも、それだけでは介入効果の根拠にならない',74,
                  'P04-1–P04-3 synthetic research / Next: P04-4 CATE & mediation')
    stages=[('① Target trial','対象・時点・権限'),('② DAG / overlap','交絡・干渉・欠測'),('③ 反実仮想推定','g-formula / IPW / AIPW'),('④ 独立検証','RCTと害・費用')]
    for i,(a,b) in enumerate(stages):
        x=.59+i*3.17
        card(s,a,b,x,2.40,3.01,1.23,color=TEAL if i<3 else AMBER)
        if i<3:textbox(s,'→',x+2.92,2.72,.32,.41,size=20,bold=True,color=TEAL)
    rect(s,.66,4.14,12.00,1.48,PALE,radius=True)
    textbox(s,'識別できないときは、unknown / abstain を返す',.94,4.35,11.23,.49,size=21,bold=True,color=TEAL)
    textbox(s,'P04-3：人工3万人・26テスト  |  実人間の因果効果：未検証  |  次：P04-4（誰に何が効くか）',.95,5.05,11.43,.36,size=14)

    assert len(prs.slides)==74
    prs.save(output)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--source',required=True);p.add_argument('--output',required=True)
    p.add_argument('--figures',default='figures')
    args=p.parse_args()
    build(args.source,args.output,args.figures)
