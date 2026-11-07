#!/usr/bin/env python3
"""Editable native Phase 12-1 Japanese slides and speaker notes.

No existing deck is rewritten. Only one original in-house diagram is embedded.
"""
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
import json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[5]
PKG=ROOT/"docs/research/manager/publication/2026-10-19"
OUT=HERE/"MANAGER_PHASE12_P12-1_REPRODUCIBILITY_JA.pptx"
NOTES=HERE/"SPEAKER_NOTES_P12-1_JA.md"
prs=Presentation()
prs.slide_width=Inches(13.333)
prs.slide_height=Inches(7.5)
NAVY=RGBColor(7,20,36)
PANEL=RGBColor(20,43,64)
PANEL2=RGBColor(27,58,78)
WHITE=RGBColor(243,248,254)
MUTED=RGBColor(174,192,206)
TEAL=RGBColor(60,218,198)
BLUE=RGBColor(136,183,248)
AMBER=RGBColor(251,202,125)
RED=RGBColor(245,144,144)
FONT="Hiragino Sans"
notes_text=[]

def rectangle(s,x,y,w,h,color,radius=True):
    shape=s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,
                              Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid();shape.fill.fore_color.rgb=color;shape.line.fill.background()
    return shape

def text(s,value,x,y,w,h,size=23,col=WHITE,bold=False,align=PP_ALIGN.LEFT):
    shape=s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf=shape.text_frame
    tf.word_wrap=True
    tf.clear()
    p=tf.paragraphs[0];p.text=value;p.alignment=align
    p.font.name=FONT;p.font.size=Pt(size);p.font.bold=bold;p.font.color.rgb=col
    return shape

def new(section,title):
    n=len(prs.slides)+1
    s=prs.slides.add_slide(prs.slide_layouts[6])
    rectangle(s,0,0,13.333,7.5,NAVY,False)
    text(s,"ANICCA  /  MANAGER RESEARCH",.6,.25,6,.37,12,TEAL,True)
    text(s,section,10.1,.28,2.5,.35,11,MUTED,True,PP_ALIGN.RIGHT)
    text(s,title,.73,.84,11.8,1.07,28,WHITE,True)
    rectangle(s,.63,7.05,12.03,.025,PANEL2,False)
    text(s,"P12-1   •   Scientific reproducibility, not a claim of human efficacy",
         .65,7.12,10,.21,9,MUTED)
    text(s,f"{n:02d}/16",11.7,7.10,.7,.22,10,TEAL,True,PP_ALIGN.RIGHT)
    return s,n

def append(s,n,title,spoken,source=""):
    t=title+"\n\n"+spoken+"\n\n参考："+source+"\n実際の第三者による独立追試は未実施。今回の数値はすべて完全合成の教育例。"
    s.notes_slide.notes_text_frame.text=t
    notes_text.append("## Slide "+str(n).zfill(2)+"｜"+title+"\n\n"+t+"\n")

def three(section,title,a,b,c,core,spoken,source):
    s,n=new(section,title)
    for i,part in enumerate((a,b,c)):
        y=2.12+i*1.43
        rectangle(s,.83,y,7.72,1.11,PANEL)
        rectangle(s,1.02,y+.2,.09,.58,TEAL,False)
        text(s,part,1.32,y+.22,6.85,.73,20)
    rectangle(s,8.85,2.11,3.6,4.18,PANEL2)
    text(s,"KEY IDEA",9.22,2.48,2.7,.4,15,TEAL,True)
    text(s,core,9.23,3.17,2.9,2.4,22,WHITE,True)
    append(s,n,title,spoken,source)

s,n=new("OPENING","P12-1｜研究の数字を、別の人が検証できるか")
text(s,"Repeatability   →   Reproducibility   →   Replicability",.9,2.62,11.7,.6,27,TEAL,True)
text(s,"同じ実験を動かすことと、独立した研究で成立することは違う。",.94,4.04,11.3,1.0,30,WHITE,True)
text(s,"Phase 12 の最初のゴールは、主張を反証可能なArtifactへ変えること。",.98,5.65,11.0,.55,19,MUTED)
append(s,n,"P12-1の研究目的","Phase9-11ではモデルの予測/選択/社会/協調/転移を学習。P12-1で第三者が評価できる証拠へ。CI成功は科学的追試ではない。","ACM/NeurIPS artifact evaluation")

three("DEFINITIONS","3つの異なる再現性",
      "同一環境で元コードを再実行 → Repeatability",
      "別チームが著者Artifactを使う → Results Reproduced",
      "別チームが独立して結果を検証 → Results Replicated",
      "誰が・何を独立にしたか？",
      "ACMのバッジは論文審査等で評価されるものであり、著者が単独で自称しない。分野間の用語差にも注意。","ACM Artifact Badging 2026")

three("ARTIFACTS","論文の『SOTA』をClaim Cardにする",
      "何を予測する？　行動・集団分布・因果効果？",
      "誰を数える？　trial / person / study / culture？",
      "どのデータ・コード・モデル・Seed・指標？",
      "Claim → Evidence",
      "claim_id、data SHA、model SHA、code SHA、評価時点、分母、欠測、権利、baselineを最低限保存。","NeurIPS Checklist; Model Cards")

three("METRICS","行動予測はAccuracyだけではない",
      "個人の回答：NLL / Brier / Calibration",
      "集団の分布：Total Variation Distance",
      "因果効果：ATE / MRT・RCT・識別仮定",
      "指標を混ぜない",
      "尺度の違う予測スコア・心理尺度・収益を一つの世界共通Accuracyへ合算しない。","BehaviorBench; Causal inference")

s,n=new("LEAKAGE","同じ人物が学習とテストに入る罠")
rectangle(s,.85,2.15,5.49,3.95,PANEL)
rectangle(s,6.67,2.15,5.49,3.95,PANEL)
text(s,"行単位ランダム分割",1.1,2.54,4.5,.46,24,AMBER,True)
text(s,"人物A：train, testに両方存在",1.1,3.62,4.8,.9,23)
text(s,"未知人物の汎化とは呼べない",1.1,5.23,4.8,.45,19,RED,True)
text(s,"Person Holdout",6.98,2.54,4.6,.46,24,TEAL,True)
text(s,"人物Aはtrainだけ\n人物Bはtestだけ",7.0,3.62,4.75,1.5,23)
text(s,"未知の人物への評価",7.0,5.35,4.75,.43,19,TEAL,True)
append(s,n,"Data Leakageを可視化","行数nが多くても独立人が少数なら信頼区間を過小評価することがある。人物ID・研究IDを分割前に固定。","scikit-learn GroupKFold")

three("SPLIT CONTRACT","未知の何を検証したいのか",
      "Subject Holdout：未知の人物",
      "Study / Culture Holdout：未知の研究と文化",
      "Temporal Holdout：未知の未来、cutoff固定",
      "Group overlap = 0",
      "同一人物の繰返し測定を分割またぎにしない。翻訳/派生研究のリークも防止する。","GroupKFold / LeaveOneGroupOut")

three("SAMPLE UNIT","クラスタ依存を考慮した不確実性",
      "trialは必ずしも独立観測ではない",
      "人・研究ごとにまとめてBootstrap",
      "複数モデル試行でテストに過剰適合しない",
      "単位が大事",
      "150人×10 trialは1500の独立人ではない。confidence intervalの単位を事前定義。","NeurIPS Checklist")

three("BEHAVIOR BENCH","既存Benchmarksを再利用する",
      "Centaur：Psych-101 / 160実験 / 60,092人",
      "BehaviorBench：公式task ID / parser / metrics",
      "Data・model・eval codeの権利は別々",
      "Code ≠ Data License",
      "Centaur testはgated。Be.FMのライセンスの曖昧さは商用接続前に解決すべき。","Nature 2025; BehaviorBench official evaluator")

three("P11 REPLAY","OPEを元評価関数とは別に検算",
      "元の人工20,000件・seed1101を固定",
      "IPS / SNIPS / DRを別の実装で再計算",
      "元ソースSHAと実データSHAを照合",
      "0.4353910556",
      "Doubly Robust元実装と別実装の最大数値差4.32×10^-14。これは同一チームの内部検算。","P11 synthetic research code; P12-1 evidence")

three("SECOND METHOD","負の転移を別の推定器で検算",
      "元P11：Gradient Descent logistic fit",
      "今回：2つの特徴群のLog Oddsから係数推定",
      "専用係数のLog Lossが両領域で低い",
      "Synthetic A/B",
      "共通モデルの負の転移を人工的に作った演習。実BFM/LoRA学習を行ったわけではない。","P11-4; P12-1 alternate estimator")

three("SEED VARIANCE","1つのSeedだけで結論しない",
      "10 seed × 3,000架空意思決定を再実行",
      "DR推定平均 ≈ 0.43583",
      "Seed間SD ≈ 0.00938",
      "Not a human CI",
      "複数seedの変動は人工生成器に関する分散であり、個人Bootstrap・実心理的便益の不確実性とは別。","P12-1 synthetic JSON")

manifest=json.loads((PKG/"manifest.json").read_text("utf8"))
media=[m for m in manifest["media"] if m["sha256"].startswith("859f486")]
if len(media)!=1:raise AssertionError("original figure hash not found")
p=PKG/media[0]["package_path"]
s,n=new("ORIGINAL FIGURE","再現性の4段階を、一枚で理解する")
s.shapes.add_picture(str(p),Inches(.79),Inches(1.98),width=Inches(11.8),height=Inches(4.76))
append(s,n,"再現性の4段階","これはAniccaが自作した教材図。ACMの公式バッジを模倣・授与したものではない。人物がtrainとtestに混ざるリーク例も表示。","ACM; original Anicca artwork")

three("MODEL CARDS","第三者へ渡すべき資料",
      "Data/Model Card：用途・収集・欠測・権利",
      "Hash/Commit/環境：元コードとモデル版を固定",
      "再実行コマンド・結果JSON・失敗例を添える",
      "Artifact ≠ Truth",
      "SHA256はバイト同一性を検証するだけ。論文の科学的正しさ・著作権/規約の正当性は別。","Hugging Face Cards; GitHub Attestations")

three("INDEPENDENT REVIEW","本当に第三者に検証してもらう手順",
      "著者側：主張・データ権限・Scriptを公開",
      "第三者：別環境で実行・別に結果を報告",
      "一致/不一致と原因、失敗条件まで公開",
      "No self-awarded badge",
      "GitHub Actions成功をthird party results replicatedと呼ばない。査読の再現証拠を追加する。","ACM Reproduced/Replicated distinctions")

three("ACCEPTANCE","P12-1の完了と、未完了を分ける",
      "講義・同一チームの別計算検算・37テスト",
      "日英研究記事・Original図・編集可能Slide",
      "第三者再現・実行動BFM・人間効果は未完",
      "Proof level matters",
      "学習の終了は実証の終了ではない。実人間・実企業価値は別のRCT/財務証拠が必要。","P12-1 research artifact")

s,n=new("NEXT","研究を発信するなら『失敗条件』も公開する")
text(s,"勝ったスコアだけでなく、何が再現できなかったか。",1.05,2.25,10.8,1.05,31,TEAL,True)
text(s,"誰が、何を、どの版で、どの集団へ一般化できたか。",1.06,3.68,10.8,1.14,27,WHITE,True)
text(s,"次の正式講義：P12-2  長期の利益・害・社会影響",1.06,5.33,11.1,.76,21,MUTED)
append(s,n,"P12-1からP12-2へ","P12-1では再現可能なアーティファクトと公正なBenchmarkを理解した。P12-2は長期的な人の便益・害・社会影響。独立再現は未完。","ACM/NeurIPS/BehaviorBench")

assert len(prs.slides)==16
prs.save(OUT)
NOTES.write_text("# P12-1全16枚・日本語発表ノート\n\n"+"\n".join(notes_text),encoding="utf8")
print("P12-1 slides",len(prs.slides),"saved at",OUT)
