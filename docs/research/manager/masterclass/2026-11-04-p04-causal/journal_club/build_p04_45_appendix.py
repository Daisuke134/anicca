"""Add eight P04-4 / P04-5 research appendix slides to the verified 74-slide deck.

The original 1-74 slide order and body content are preserved.
Only page-count footers are updated. The new slides include PPTX speaker notes.
"""
from __future__ import annotations

import re
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parent
DECK = ROOT / "AI_BEHAVIOR_JOURNAL_CLUB_JA.pptx"
FONT = "Noto Sans CJK JP"
NAVY = RGBColor(23, 43, 62)
MUTED = RGBColor(85, 106, 124)
TEAL = RGBColor(0, 122, 127)
BLUE = RGBColor(50, 117, 170)
ORANGE = RGBColor(181, 113, 20)
RED = RGBColor(169, 76, 69)
LIGHT = RGBColor(241, 247, 248)
LIGHT2 = RGBColor(233, 244, 245)
WHITE = RGBColor(255, 255, 255)
BORDER = RGBColor(213, 226, 231)

NOTES = []


def shape_box(slide, x, y, w, h, bg=LIGHT, rounded=True):
    rect = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE,
        Inches(x), Inches(y), Inches(w), Inches(h))
    rect.fill.solid()
    rect.fill.fore_color.rgb = bg
    rect.line.fill.background()
    return rect


def text(slide, x, y, w, h, value, size=16, color=NAVY, bold=False, align=None):
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = shape.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = Inches(0.02)
    tf.margin_right = Inches(0.02)
    tf.margin_top = Inches(0.02)
    tf.margin_bottom = Inches(0.02)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    for j, line in enumerate(str(value).split("\n")):
        p = tf.paragraphs[0] if j == 0 else tf.add_paragraph()
        p.text = line
        if align is not None:
            p.alignment = align
        for run in p.runs:
            run.font.name = FONT
            run.font.size = Pt(size)
            run.font.bold = bold
            run.font.color.rgb = color
    return shape


def base(prs, label, title, subtitle, source):
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    shape_box(slide, 0, 0, .16, 7.5, TEAL, rounded=False)
    text(slide, .48, .19, 11.8, .30, label, 11, TEAL, True)
    text(slide, .48, .66, 12.25, .71, title, 24.5, NAVY, True)
    text(slide, .51, 1.44, 12.05, .56, subtitle, 14.2, MUTED)
    shape_box(slide, .50, 7.04, 12.25, .012, BORDER, rounded=False)
    text(slide, .51, 7.09, 11.6, .22, source, 8, MUTED)
    page = len(prs.slides)
    text(slide, 12.0, 7.09, .79, .23, f"{page} / 82", 8, MUTED)
    return slide


def card(slide, x, y, w, h, header, body, accent=TEAL, size=16):
    shape_box(slide, x, y, w, h)
    text(slide, x+.20, y+.14, w-.40, .35, header, 15.5, accent, True)
    text(slide, x+.20, y+.59, w-.38, h-.75, body, size, NAVY)


def note(slide, number, title, paragraphs, references):
    content = f"{number:02d}｜{title}\n" + "\n\n".join(paragraphs) + "\n\n出典：" + references
    NOTES.append(content)
    frame = slide.notes_slide.notes_text_frame
    if frame is not None:
        frame.text = content


def add_slides(prs):
    s = base(prs, "APPENDIX / P04-4 HETEROGENEOUS EFFECTS",
             "ATEがプラスでも、全員に介入すべきとは限らない",
             "24,000人の完全架空RCT：介入前の意欲と疲労で効果が変わる",
             "P04-4 synthetic only / Wager & Athey (2018)")
    card(s, .62, 2.32, 5.87, 1.34, "集団平均 ATE", "真のATE +2.92pt / 推定 +2.68pt")
    card(s, 6.70, 2.32, 5.87, 1.34, "条件付き平均 CATE", "特徴 X で条件づけた E[Y(1)−Y(0)|X]", BLUE)
    card(s, .62, 3.85, 5.87, 1.78, "低意欲の人", "疲労低 +16pt\n疲労高 +10pt", TEAL, 18)
    card(s, 6.70, 3.85, 5.87, 1.78, "高意欲の人", "疲労低 −4pt\n疲労高 −10pt", RED, 18)
    text(s, .85, 5.95, 11.8, .53, "本質：平均値が良くても、特定の状態では害になることがある", 18, TEAL, True)
    note(s, 75, "CATE：平均と個人差", [
        "ATEは集団平均。CATEは同じ事前特徴を持つ集団の平均であり、個人の真の反実仮想を保証するものではありません。",
        "24,000人の完全架空RCTで、低意欲ではプラス、高意欲ではマイナスとなる世界を構成しました。これを現実の通知研究の証拠として扱ってはいけません。"
    ], "Wager & Athey 2018; P04-4_JA.md")

    s = base(prs, "APPENDIX / P04-4 CAUSAL EXPERIMENT",
             "4つの状態を、別々に推定する",
             "群間差の推定は元の潜在結果生成式とおおむね一致する",
             "P04-4 synthetic n=24,000 / seed 20261144")
    rows = [("低意欲・疲労低", 16.0, 17.67), ("低意欲・疲労高", 10.0, 9.82),
            ("高意欲・疲労低", -4.0, -4.54), ("高意欲・疲労高", -10.0, -11.36)]
    text(s, .70, 2.25, 8.0, .33, "状態                                     理論CATE      推定CATE", 14, MUTED, True)
    for k, (name, oracle, est) in enumerate(rows):
        y = 2.72 + k * .79
        shape_box(s, .66, y, 12.0, .67, LIGHT if k % 2 == 0 else LIGHT2)
        text(s, .88, y+.08, 6.0, .48, name, 17, NAVY, True)
        text(s, 7.36, y+.08, 2.3, .48, f"{oracle:+.1f} pt", 17, TEAL if oracle > 0 else RED, True)
        text(s, 10.1, y+.08, 2.3, .48, f"{est:+.2f} pt", 17, NAVY)
    text(s, .85, 6.24, 11.6, .38, "無作為化・事前に定めた4群で推定。これは個々人の確定的な効果ではない。", 13, MUTED)
    note(s, 76, "CATEの推定値", [
        "低意欲・疲労低17.67pt、低意欲・疲労高9.82pt、高意欲・疲労低−4.54pt、高意欲・疲労高−11.36ptを推定しました。",
        "真の効果は人工世界であらかじめ設定。実世界では個別潜在結果を観測できず、未観測交絡・多重比較・データ選別の問題も残ります。"
    ], "P04-4_JA.md; experiments/p04_4_heterogeneous_effects.py")

    s = base(prs, "APPENDIX / P04-4 POLICY VALUE",
             "CATEを使い、介入すべき相手を選ぶ",
             "未使用の架空9,619人に対して、方策をIPWで独立に評価",
             "P04-4 holdout IPW / synthetic trial only")
    card(s, .68, 2.31, 5.82, 1.54, "学習したルール", "低意欲 → 通知する\n高意欲 → 通知しない", TEAL, 19)
    card(s, 6.69, 2.31, 5.82, 1.54, "比較対象", "誰にも通知しない\n全員に通知する", BLUE, 18)
    shape_box(s, .73, 4.14, 11.85, 1.42, LIGHT2)
    text(s, .92, 4.31, 8.1, .57, "未通知方策に対する増分 +6.28 pt", 27, TEAL, True)
    text(s, .95, 4.98, 10.7, .39, "近似95% CI：+4.84〜+7.72 pt  |  人工世界の理論増分：+6.42 pt", 15, NAVY)
    text(s, .91, 5.90, 11.4, .46, "学習と評価を分離しても、現実の人への効果や安全性は証明されない。", 15, RED, True)
    note(s, 77, "CATEから介入方策へ", [
        "乱数で分けた約60%のデータで4群の効果を推定し、残り9,619人には学習を使わず、IPWで方策の価値を採点しました。",
        "通知しない方策との差は+6.28ポイント、近似95%区間は+4.84〜+7.72ptでした。因果効果そのもの、同意、コスト、安全性を考えないまま自律実行してよいわけではありません。"
    ], "P04-4_JA.md; P04-4_SYNTHETIC_RESULTS.json")

    s = base(prs, "APPENDIX / P04-4 MEDIATION",
             "「誰に効くか」と「なぜ効くか」は別の問い",
             "媒介分析：A→M→Y と、A→Y の経路を分けて考える",
             "P04-4 synthetic linear SEM / mediation assumptions required")
    card(s, .64, 2.27, 3.94, 1.84, "介入 A", "通知など\n（この例は無作為化）", TEAL, 17)
    card(s, 4.72, 2.27, 3.94, 1.84, "媒介 M", "気づき・認知反応\n（処置後の変数）", BLUE, 17)
    card(s, 8.80, 2.27, 3.84, 1.84, "結果 Y", "タスク完了\n（この例は連続量）", ORANGE, 17)
    text(s, 4.36, 2.92, .30, .45, "→", 22, TEAL)
    text(s, 8.46, 2.92, .30, .45, "→", 22, TEAL)
    shape_box(s, 1.02, 4.48, 11.23, 1.20, LIGHT2)
    text(s, 1.22, 4.70, 10.5, .56, "直接 0.12 ＋ 間接 0.12 ＝ 総効果 0.24", 23, TEAL, True, PP_ALIGN.CENTER)
    text(s, .81, 6.01, 11.7, .44, "注意：処置のRCTだけでは媒介から結果への因果効果は識別できない。", 14, RED, True)
    note(s, 78, "媒介分析", [
        "介入後に変わる媒介変数M（例えば気づき）を通じて結果が変わる経路と直接経路を分けます。人工線形モデルで総効果0.24、直接効果0.12、間接効果0.12を設定し、近い値を推定しました。",
        "媒介から結果への交絡やcross-worldの仮定が問題になります。Aを無作為化しただけで媒介効果が自動的に証明されるわけではありません。"
    ], "P04-4_JA.md; mediation example synthetic only")

    s = base(prs, "APPENDIX / P04-5 HOLDOUT DESIGN",
             "未知の『研究』を予測するベンチマーク",
             "同一研究をまたいだリークを避けるため、study IDで分割する",
             "P04-5 synthetic studies=180 / no actual published RCT evaluated")
    card(s, .67, 2.32, 5.85, 1.49, "学習", "90研究：過去の介入効果から学習", BLUE, 17)
    card(s, 6.70, 2.32, 5.85, 1.49, "検証", "30研究：Ridgeの正則化を選択", BLUE, 17)
    card(s, .67, 4.05, 5.85, 1.49, "未見研究（既知領域）", "30研究：IDは未見、領域は学習済", TEAL, 17)
    card(s, 6.70, 4.05, 5.85, 1.49, "未見研究（新領域）", "30研究：生成規則に新たなシフト", ORANGE, 17)
    text(s, .9, 5.96, 11.7, .51, "個人レベルのtrain/test分割だけでは、研究単位の汎化を測れない。", 16, NAVY, True)
    note(s, 79, "未見の研究で評価する", [
        "完全架空の180研究を学習90、検証30、同領域未見30、新領域未見30に分けました。研究IDの重複はありません。",
        "人や回答をランダム分割しただけでは、同じ研究の正解情報が訓練側に残る恐れがあります。LLMの場合、事前学習で公開論文を知っている可能性もあります。"
    ], "P04-5_JA.md; J-PAL Dataverse and Many Labs 2 are future candidates only")

    s = base(prs, "APPENDIX / P04-5 PREDICTION FREEZE",
             "予測を先に固定し、それから正解を開く",
             "重要なのは、精度を出す前に採点方法と利用可能情報を確定すること",
             "P04-5 synthetic split / SHA256 prediction receipt")
    steps = [
        ("① 事前情報", "研究対象・介入・baseline"),
        ("② 予測", "ゼロ・平均・Ridge"),
        ("③ 予測凍結", "CSV + SHA256"),
        ("④ 採点", "保存後にgoldを開封"),
    ]
    for k, (a, b) in enumerate(steps):
        x = .62 + k*3.18
        card(s, x, 2.72, 2.99, 2.28, a, b, TEAL if k != 3 else ORANGE, 15)
    text(s, .86, 5.50, 11.8, .49, "人工goldは別ファイル保存。本番ではモデル側から物理的にアクセス不能にする。", 14, RED, True)
    note(s, 80, "予測凍結とデータ汚染", [
        "今回のコードは学習・検証・未見の事前メタデータだけから予測し、予測CSVのSHA256を保存します。その後だけ採点プログラムが人工goldを読みます。",
        "これは順序の再現教材で、人工gold自体は同一リポジトリにあります。結果公表前に予測を登録した本物の前向き研究と同じ証拠価値を主張しません。"
    ], "P04-5_JA.md; P04-5_FREEZE_RECEIPT.json")

    s = base(prs, "APPENDIX / P04-5 RESULTS",
             "未知領域では、予測誤差が悪化する",
             "MAE（ポイント、低いほど良い）｜架空の未見研究30件＋30件",
             "P04-5_SYNTHETIC_BENCHMARK_RESULTS.json / synthetic only")
    heads = [("予測方法",.9,5.15), ("既知領域",6.20,2.34), ("新領域",9.07,2.6)]
    for h,x,w in heads:
        text(s,x,2.34,w,.39,h,16,MUTED,True)
    vals = [
        ("常に効果0", "2.99", "5.77"),
        ("学習平均", "2.27", "4.18"),
        ("Ridge回帰", "1.55", "3.99"),
    ]
    for i,(name, a, b) in enumerate(vals):
        y=2.91+i*.89
        shape_box(s,.72,y,11.90,.77,LIGHT2 if i==2 else LIGHT)
        text(s,.96,y+.12,4.9,.50,name,19,TEAL if i==2 else NAVY,i==2)
        text(s,6.23,y+.12,2.4,.50,a+" pt",19,TEAL if i==2 else NAVY,i==2)
        text(s,9.10,y+.12,2.4,.50,b+" pt",19,TEAL if i==2 else NAVY,i==2)
    text(s,.93,5.99,11.6,.52,"新領域の予測誤差は既知領域の約2.6倍：OOD評価を分ける必要がある。",15,RED,True)
    note(s, 81, "合成未見研究の評価", [
        "30件ずつの架空研究で、ゼロ予測・平均予測・Ridgeを比較。RidgeのMAEは既知領域1.55pt、新領域3.99ptです。実在RCTの予測結果ではありません。",
        "未知の研究IDに対して性能を維持しても、未知領域で性能が保たれる保証はありません。分割の単位と予測誤差の尺度を明示します。"
    ], "P04-5_JA.md; synthetic evaluation output")

    s = base(prs, "APPENDIX / P04-5 NEXT VALIDATION",
             "Managerが『現実の実験効果』を予測した証拠はまだない",
             "人工ベンチマークの成功と、未見の公開RCTでの検証を区別する",
             "J-PAL / Many Labs 2 candidate corpora; no empirical validation claimed")
    card(s,.74,2.29,5.78,1.70,"今回できたこと","180架空研究の再現可能なsplit・凍結・評価\n全80件の単体テスト成功",TEAL,16)
    card(s,6.70,2.29,5.78,1.70,"研究上まだ必要なこと","実公開RCTの選定・権利検査\n予測の事前登録と独立採点",ORANGE,16)
    shape_box(s,.85,4.41,11.58,1.37,LIGHT2)
    text(s,1.04,4.70,11.0,.84,"P04-4：講義＋人工実験完了\nP04-5：講義＋人工ベンチマーク完了／公開実験検証は未完了",17,NAVY,True,PP_ALIGN.CENTER)
    text(s,.95,6.12,11.4,.42,"次の講義：P04-6 事前登録・意思決定価値。P04-5の公開実験評価も継続。",14,TEAL,True)
    note(s,82,"P04-5の到達点と次",[
        "今回の成果は再現可能な人工ベンチマーク、研究単位のHoldout、予測凍結、単純なベースライン比較です。結果公開前の本物のRCTではまだ試していません。",
        "今後はJ-PAL・Many Labs 2等の適切な公開実験を比較、データ利用許可と汚染の可能性を検査し、可能なら未来の試験の結果発表前に予測を事前登録します。"
    ], "P04-5_JA.md; ROADMAP_STATUS_JA.md")


def run():
    prs=Presentation(str(DECK))
    before=len(prs.slides)
    if before == 82:
        print("Already 82 slides, not appending twice")
        return
    if before != 74:
        raise RuntimeError(f"Expected exactly 74 input slides, found {before}. Refusing unsafe append.")
    add_slides(prs)
    if len(prs.slides) != 82:
        raise AssertionError("Expected 82 slides")
    # Preserve all prior slide content; only update page-total run text.
    changed=0
    for idx, slide in enumerate(list(prs.slides)[:74], start=1):
        for shp in slide.shapes:
            if not shp.has_text_frame:
                continue
            if re.fullmatch(r"\s*\d+\s*/\s*74\s*", shp.text):
                paras=shp.text_frame.paragraphs
                if len(paras)==1 and len(paras[0].runs)==1:
                    paras[0].runs[0].text=f"{idx} / 82"
                    changed+=1
    prs.save(str(DECK))
    # Add detailed Japanese notes in the existing canonical markdown.
    note_path=ROOT/"SPEAKER_NOTES_JA.md"
    s=note_path.read_text(encoding="utf-8")
    s=s.replace("全74枚の発表者ノート", "全82枚の発表者ノート")
    s=s.replace("全74枚の", "全82枚の")
    appendix="\n\n---\n\n## P04-4/P04-5：追加付録8枚（75〜82）\n\n"
    appendix+="\n\n---\n\n".join("## "+str(i+75)+"｜"+n.split("\n",1)[0].split("｜",1)[-1]+"\n\n"+n.split("\n",1)[1]
                                    for i,n in enumerate(NOTES))
    if "追加付録8枚（75〜82）" not in s:
        note_path.write_text(s+appendix+"\n",encoding="utf-8")
    print("slides",len(prs.slides),"old footers changed",changed,"new notes",len(NOTES))


if __name__ == "__main__":
    run()
