#!/usr/bin/env python3
"""Build 26 fully editable research slides + Japanese notes + original editorial PNG.

Only python-pptx and Pillow required; original self-authored diagrams.
No external copyrighted figures/data or API calls. No production operations.
Usage: python build_behaviorbench_psych101_deck.py --outdir /private/tmp/bb_deck
"""
from __future__ import annotations
from argparse import ArgumentParser
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches,Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from PIL import Image,ImageDraw,ImageFont
import json

INK=RGBColor(243,247,254)
NAVY=RGBColor(7,20,34)
PANEL=RGBColor(21,44,63)
PANEL2=RGBColor(30,57,77)
MUTED=RGBColor(169,193,208)
TEAL=RGBColor(59,222,197)
BLUE=RGBColor(137,183,248)
AMBER=RGBColor(252,199,119)
RED=RGBColor(243,132,131)
FONT="Hiragino Sans"

SLIDES=[
("OPENING","WHAT DOES A BEHAVIOR MODEL LEARN?",["Human choices, not just descriptions","Training data and test data must be disjoint","Papers, model licenses and rights are different"],"BehaviorBench × Psych-101","研究の問いをモデルの入力・出力・採点に分解する。完了と実行動の効果を混同しない。"),
("FOUNDATION","データ、モデル、評価を別々に理解",["Dataset: 入力と観測結果","Model: 条件から確率を出す","Benchmark: 独立比較可能な課題と指標"],"Data → Model → Test","公開評価データをSFTへ混ぜると汎化能力を測れない。"),
("FOUNDATION","評価では「何が未知か」が重要",["未知のtrial ≠ 未知の人物","未知人物 ≠ 未知研究","未知研究 ≠ 未知文化・将来"],"Split = Claim","何に汎化したと主張するかで分割単位を変更する。"),
("NAMING","BehaviorBenchは同名論文が複数",["Huang et al. / arXiv 2606.24162：本講義","Yang et al. / arXiv 2606.02798：市場履歴","IJCAI 2026別研究：人格行動の表出"],"Paper ID first","同名ベンチマークを一つのデータとして扱わない。"),
("BB","BehaviorBench：4能力",["人間の行動予測・集団の模擬","戦略ゲームに勝つ意思決定","本人特徴の推定・科学知識の応用"],"4 CAPABILITIES","4能力には実行動を観測していない正解も含む。"),
("BB","BehaviorBench：12タスク",["ゲーム：初回/次回/別ゲーム予測","Big Five：項目回答/欠損回答/性格/年齢","Beauty Contest・科学論文・IEO"],"12 TASKS ≠ 1 SCORE","評価ごとのラベル・MAE/Accuracy/W/BLEURT/勝率を区別。"),
("SOURCE","MobLab：実際の経済ゲーム",["生データ569,795ゲーム記録","除外ルール適用後379,754記録","76,035人のゲーム行動履歴"],"Choice is observed","除外の条件・役割・行動範囲を確認。元データと論文の評価例数は違う。"),
("SOURCE","Big Five：自己申告ラベル",["19,630人・50質問×参加者","回答合計981,500件","個人属性を含むため利用目的に注意"],"Survey ≠ Cause","人格回答を個人の診断や広告ターゲティングへ無断転用しない。"),
("SOURCE","学術WorkflowとIEOは別",["AER 6,515 + NHB 871の論文情報","Workflowは論文の内容から構造化","IEOの124問はevaluation-only"],"Knowledge ≠ Behavior","人が実際に何を選んだかではないラベルを区別。"),
("TRAIN","649,394件は評価データではない",["11タスクでQwen/LlamaをLoRA学習","学習と評価の参加者・論文は非重複","公開HF BehaviorBenchはEVAL専用"],"649,394 TRAIN","論文v3 Section5とAppendixDの学習設定。公開JSONLをSFTへ流さない。"),
("EVAL","19,893例の評価（論文v3）",["12タスクを評価","一部公開配布の行数は論文と異なる","使用したGit/HF revisionを必ず固定"],"19,893 EVAL","論文と公開ファイルの行数差を都合よく修正しない。"),
("SPLIT","Group Holdoutを守る",["MobLab：参加者70/10/20","Big Five：参加者90/10","Workflows：2025年論文がTEST"],"SUBJECT / YEAR","同じ人物や同じ論文が両方へ入らないようにする。"),
("SPLIT","Push/Pullは未知ゲーム",["ゲーム自体をSFTから除外","本人も学習側に重複させない","未知の人と未知の課題を分けて検査"],"UNSEEN GAME","Holdoutの種類と一般化の範囲を説明。"),
("FORMAT","Evaluation JSONLは何を表す？",["system：タスク説明","user：現在の条件/本人の過去履歴","assistant：実行動/正答/論文由来ラベル"],"Same JSON ≠ Same truth","ひとつの形式でもラベルの由来は異なる。"),
("SFT","Be.FM-1.5：LoRAの具体条件",["Qwen3-4BとLlama3.3-70B","rank 8、alpha 32、全Linear層","1 epoch・LR 1e-4・seq 2048"],"LoRA SFT","論文の再現には学習レシピと許可された元データと計算資源が必要。"),
("SFT","計算資源と本当の費用を区別",["Effective batch 128","4×A100 80GB GPUs","4B約60 / 70B約600 A100-GPU時間"],"GPU HOURS ≠ $","費用はクラウド価格・入出力・失敗・再学習まで含める。"),
("METRIC","個人の予測と集団の分布",["個人：MAE、Accuracy、NLL、Brier","集団：Wasserstein、TVD等","戦略ゲーム：Win Rate"],"Individual ≠ Distribution","評価レベルが違う指標を世界共通Accuracyにしない。"),
("METRIC","サンプリングと分布の言語化",["毎回回答→集約して分布を作る","1回で確率表を説明させる","モデル順位は方式によって変わる"],"SIMULATE ≠ VERBALIZE","論文Appendix Eのスピアマン順位相関は約0.51。"),
("PSYCH","Psych-101：1行は1セッション",["160心理学実験","60,092参加者のセッション","内部に10,681,650回の選択"],"60k ROWS / 10.68m CHOICES","HF列はtext/experiment/participant。1行=1試行ではない。"),
("PSYCH","セッション履歴を文章化",["ゲーム説明・刺激・過去の選択を文章化","人間の選択を <<L>> で標識","次の選択は過去情報から予測"],"TRIAL HISTORY","未来の正解を入力に漏らさない。"),
("PSYCH","回答だけにCross Entropy",["通常のLMは全文tokenを予測","Centaurは回答tokenをloss対象","TRL CompletionOnlyLMで区間を指定"],"RESPONSE-ONLY LOSS","maskの文字実演とtokenizer本番処理は違う。"),
("PSYCH","Centaur：QLoRAによる追加学習",["Llama3.1 70B + 4bit base","LoRA rank8、追加学習0.15%","A100 80GBで約5日・1 epoch"],"HUMAN-CHOICE NLL","実人間の選択を予測する訓練。商用日本語通知・治療は未検証。"),
("RIGHTS","コード・データ・モデルの権利",["BehaviorBench evalデータ：CC BY-NC-ND","Psych-101 train Apache表示・test gated","Be.FM gated/Terms、Centaur Llama license"],"Rights ≠ Access","公開可能・学習可能・商用再利用可能は別々に確認する。"),
("TOY","Anicca完全合成の小型学習",["128セッション・1,152人工の行動","人物Group HoldoutでLogisticを学習","37/37テスト、LLMの学習はゼロ"],"SYNTHETIC ONLY","データ利用権・未来漏洩・回答maskを教材として検査。"),
("TOY","合成モデルのNLL",["定数予測Baseline：0.69070","Logistic学習後：0.53591","未知の架空人物でのみ比較"],"0.691 → 0.536","実人間の精度、Be.FM/Centaur性能、ビジネス利益を示すものではない。"),
("MANAGER","Aniccaは研究Trackと商用Trackを分ける",["研究：未見の人/研究/ゲーム予測","商用仮説：許可ある日本語候補の順位","増分効果を売るなら無作為比較が必要"],"Research ≠ Product ROI","実装の唯一のNEXTは既存MG-01..18。新しい予測器の価値は未実証。"),
]

def fnt(size):
    for p in ("/System/Library/Fonts/Supplemental/Arial.ttf",
              "/System/Library/Fonts/Helvetica.ttc",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:return ImageFont.truetype(p,size)
        except OSError:pass
    return ImageFont.load_default()

def rect(s,x,y,w,h,c):
    box=s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,Inches(x),Inches(y),Inches(w),Inches(h))
    box.fill.solid();box.fill.fore_color.rgb=c;box.line.fill.background()

def tx(s,value,x,y,w,h,size=22,color=INK,bold=False):
    a=s.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h))
    a.text_frame.clear();a.text_frame.word_wrap=True
    p=a.text_frame.paragraphs[0];p.text=value
    p.font.name=FONT;p.font.size=Pt(size);p.font.color.rgb=color;p.font.bold=bold
    return a

def make_deck(out:Path)->tuple[Path,Path]:
    r=Presentation();r.slide_width=Inches(13.333);r.slide_height=Inches(7.5)
    lines=[]
    for n,(section,title,bullets,key,note) in enumerate(SLIDES,1):
        s=r.slides.add_slide(r.slide_layouts[6])
        bg=s.background.fill;bg.solid();bg.fore_color.rgb=NAVY
        tx(s,"ANICCA  /  MANAGER RESEARCH",.62,.32,5.5,.32,12,TEAL,True)
        tx(s,"BEHAVIORBENCH  ×  PSYCH-101",8.7,.32,4.1,.32,11,MUTED,True)
        tx(s,title,.76,.91,11.9,.95,30,INK,True)
        rect(s,.78,2.01,8.02,4.55,PANEL)
        for j,b in enumerate(bullets):
            yy=2.31+j*1.34
            rect(s,1.09,yy+.07,.09,.54,TEAL)
            tx(s,b,1.35,yy,7.0,.9,21,INK)
        rect(s,9.04,2.01,3.52,4.55,PANEL2)
        tx(s,section,9.35,2.31,2.8,.3,14,TEAL,True)
        tx(s,key,9.35,3.06,2.75,2.2,24,INK,True)
        tx(s,"研究の数値とAniccaの\n合成テストを混同しない",9.36,5.53,2.77,.69,12,AMBER)
        tx(s,f"{n:02d} / {len(SLIDES)}",11.55,7.09,1.1,.25,11,MUTED,True)
        speaker=title+"\n\n"+note+"\n\n区別：参考論文の主張／合成コードの結果／未観測の実ユーザー便益。"
        s.notes_slide.notes_text_frame.text=speaker
        lines.append(f"## {n:02d}. {title}\n\n{speaker}\n")
    out.mkdir(parents=True,exist_ok=True)
    pptx=out/"MANAGER_BEHAVIORBENCH_PSYCH101_DEEP_DIVE_JA.pptx"
    script=out/"MANAGER_BEHAVIORBENCH_PSYCH101_SPEAKER_NOTES_JA.md"
    r.save(pptx);script.write_text("# BehaviorBench × Psych-101｜全26枚日本語発表ノート\n\n"+"\n".join(lines),encoding="utf8")
    return pptx,script

def make_editorial_figure(out:Path)->Path:
    out.mkdir(parents=True,exist_ok=True)
    im=Image.new("RGB",(1600,900),"#071422")
    d=ImageDraw.Draw(im)
    d.text((95,55),"ANICCA   /   BEHAVIORAL INTELLIGENCE RESEARCH",font=fnt(29),fill="#3BDECB")
    d.text((95,132),"What does the model actually learn?",font=fnt(58),fill="#F3F8FF")
    cards=[
        (94,"TRAINING","649,394 learning examples","11 supervised tasks","#3BDECB"),
        (575,"MODEL","LoRA on Qwen / Llama","Human-choice adaptation","#88B8FA"),
        (1056,"EVALUATION","19,893 held-out items","12 tasks; do NOT train here","#FFC677"),
    ]
    for x,h,t,sub,col in cards:
        d.rounded_rectangle((x,288,x+443,612),radius=23,fill="#16324A")
        d.text((x+30,320),h,font=fnt(31),fill=col)
        d.text((x+30,400),t,font=fnt(28),fill="#FFFFFF")
        d.text((x+30,483),sub,font=fnt(24),fill="#B2C7D4")
    d.line((94,684,1498,684),fill="#2B5568",width=4)
    d.text((96,713),"Psych-101 is different: 60,092 participant sessions containing 10.68M choices.",font=fnt(31),fill="#F3F8FF")
    d.text((96,820),"Original infographic · paper-reported figures · not an Anicca trained BFM.",font=fnt(23),fill="#A9C4D2")
    outpath=out/"MANAGER_BEHAVIORBENCH_PSYCH101_EDITORIAL.png"
    im.save(outpath,optimize=True)
    return outpath

if __name__=="__main__":
    parser=ArgumentParser();parser.add_argument("--outdir",default=str(Path(__file__).resolve().parent))
    args=parser.parse_args()
    out=Path(args.outdir);p,n=make_deck(out);f=make_editorial_figure(out)
    print(json.dumps({"slides":len(SLIDES),"pptx":str(p),"notes":str(n),"figure":str(f)},ensure_ascii=False))
