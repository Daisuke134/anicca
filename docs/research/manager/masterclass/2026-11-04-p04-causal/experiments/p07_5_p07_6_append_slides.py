"""Append P07-5 Vipassana and P07-6 benefits/harms to canonical research slides.

No images or copyrighted scale items. Four EN slides with JA speaker notes.
Never label the software as clinically validated or spiritually diagnostic.
Re-runnable (114 -> 118 slides, then no-op).
"""
from pathlib import Path
import re
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

BASE = Path(__file__).resolve().parents[1] / "journal_club"
PPTX = BASE / "AI_BEHAVIOR_JOURNAL_CLUB_JA.pptx"
NOTES = BASE / "SPEAKER_NOTES_JA.md"
INK = RGBColor(19, 42, 59)
TEAL = RGBColor(8, 126, 125)
GRAY = RGBColor(81, 102, 117)
SOFT = RGBColor(239, 247, 247)
SOFT2 = RGBColor(226, 241, 242)
GOLD = RGBColor(179, 104, 22)


def txt(slide, value, x, y, w, h, font=15, color=INK, bold=False):
    sh = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = sh.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(.04)
    tf.margin_right = Inches(.02)
    tf.margin_top = Inches(.03)
    for i, line in enumerate(value.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        p.space_after = Pt(3)
        for run in p.runs:
            run.font.name = "Aptos"
            run.font.size = Pt(font)
            run.font.bold = bold
            run.font.color.rgb = color


def rect(slide, x, y, w, h, color=SOFT):
    sh = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h)
    )
    sh.fill.solid()
    sh.fill.fore_color.rgb = color
    sh.line.fill.background()


def new_slide(deck, topic, title, subtitle, reference):
    sh = deck.slides.add_slide(deck.slide_layouts[0])
    rect(sh, 0, 0, .15, 7.5, TEAL)
    txt(sh, topic, .49, .20, 12, .34, 11, TEAL, True)
    txt(sh, title, .49, .67, 12, .76, 25, INK, True)
    txt(sh, subtitle, .51, 1.49, 11.89, .45, 14, GRAY)
    rect(sh, .50, 7.01, 12.23, .012, SOFT2)
    txt(sh, reference, .55, 7.04, 11.33, .28, 8, GRAY)
    txt(sh, f"{len(deck.slides)} / 118", 12.01, 7.04, .84, .28, 9, GRAY)
    return sh


def add_notes(slide, value):
    slide.notes_slide.notes_text_frame.text = value


def append():
    deck = Presentation(PPTX)
    if len(deck.slides) not in (114, 118):
        raise ValueError(f"Unexpected original slide count {len(deck.slides)}")
    if len(deck.slides) == 114:
        for slide in deck.slides:
            for shape in slide.shapes:
                if (shape.has_text_frame
                        and re.fullmatch(r"\s*\d+ / 114\s*", shape.text)):
                    shape.text = shape.text.replace("/ 114", "/ 118")

        # 115: three characteristics
        s = new_slide(
            deck, "P07-5 / VIPASSANA + BEHAVIORAL SCIENCE",
            "Three characteristics are not model labels.",
            "Interpret the Buddhist source faithfully; test behavior separately.",
            "SN 22.59; SN 56.11; MN 10; neurophenomenology 2024 n=1",
        )
        for k, (name, title, meaning) in enumerate([
            ("ANICCA", "Impermanence",
             "Conditioned experiences change; time series alone cannot certify insight"),
            ("DUKKHA", "Unsatisfactoriness",
             "Suffering is not identical to a wellbeing questionnaire score"),
            ("ANATTĀ", "Not-self",
             "The five aggregates cannot be equated to a neural activity classifier"),
        ]):
            y = 2.13 + k * 1.22
            rect(s, .87, y, 11.57, 1.03)
            txt(s, name, 1.10, y+.15, 2.35, .32, 15, TEAL, True)
            txt(s, title, 3.34, y+.12, 8.6, .36, 17, INK, True)
            txt(s, meaning, 3.34, y+.60, 8.4, .28, 12, GRAY)
        txt(s, "No automatic stream-entry, wisdom-stage or enlightenment diagnosis.",
            .94, 6.45, 11.6, .32, 12, GOLD, True)
        add_notes(s, (
            "第115枚｜ヴィパッサナーの三相とAIが証明できる範囲\n\n"
            "無常（Anicca）は経験の変化、苦（Dukkha）は痛みだけでなく固定できない"
            "条件的な経験への執着に伴う不満足性、無我（Anattā）は五蘊を恒常で"
            "自在に支配できる自己として認めないという議論。SN22.59とSN56.11の"
            "初期経典に基づく教理であり、心理尺度の点数や脳画像の分類と同義ではない。"
            "Yangら2024年NeuroImageの7T研究は熟練瞑想者1人・26ランのケーススタディ。"
            "洞察段階と脳活動の関連は興味深いが、万人に対する悟り判定器を支持しない。"
            "Managerでは自己報告と行動と実際の介入効果を必ず分ける。"
        ))

        # 116: satipatthana and product boundary
        s = new_slide(
            deck, "P07-5 / FOUR FOUNDATIONS",
            "Observe experience. Do not certify awakening.",
            "Body, feeling tone, mind state and Dhamma categories are NOT four clinical stages.",
            "MN 10; SN 12.2; p07_5_experience_observation.py",
        )
        stages = [
            ("BODY", "posture, breath, movement"),
            ("FEELING TONE", "pleasant / unpleasant / neutral"),
            ("MIND STATE", "attention, anger, concentration etc."),
            ("DHAMMA", "hindrances, aggregates, sense fields etc."),
        ]
        for i, (name, sub) in enumerate(stages):
            y = 2.06 + i * .94
            rect(s, .90, y, 11.46, .78, SOFT if i % 2 == 0 else SOFT2)
            txt(s, name, 1.14, y+.16, 3.28, .38, 14, TEAL, True)
            txt(s, sub, 4.32, y+.14, 7.9, .44, 16, INK)
        txt(s, "Opt-in + read-only + NO_ACTION; no meditation initiation or medical inference.",
            .94, 6.42, 11.5, .35, 12, GOLD, True)
        add_notes(s, (
            "第116枚｜四念処は観察枠組みであり、4つの達成段階ではない\n\n"
            "MN10の身念処は呼吸・身体・姿勢、受念処は快・不快・中性、心念処は"
            "心の状態、法念処は五蓋・五蘊・六処・七覚支等を扱う。"
            "P07-5の新しいPython契約は、本人が許可した自己報告についてこの四区分を"
            "概念上のラベルとし、悟り・観智・脳マーカー・医学的診断を推定しない。"
            "強いリトリートや臨床治療の要求には自律的に瞑想指導せずNO_ACTION/STOP経路。"
            "縁起の触→受→愛→取は学習の枠組みを与えるが、特定の人工ニューラルネットの"
            "物理的な機序と同一とは認めない。"
        ))

        # 117: outcomes and scale rights
        s = new_slide(
            deck, "P07-6 / MEASURE WHAT MATTERS",
            "Benefit = chosen outcomes, not engagement.",
            "Prediction, behavior, welfare, autonomy and harms need independent evidence.",
            "WHO-5 2024 (NC-SA license); OECD 2025; WHOQOL; PROMIS; FFMQ",
        )
        outcome_cards = [
            ("PREDICT", "Calibration and held-out accuracy"),
            ("BEHAVIOR", "User-chosen real actions and denominator"),
            ("WELFARE", "Wellbeing and day-to-day functioning"),
            ("AUTONOMY", "Opt-in, right to decline, intervention burden"),
            ("HARM", "Actively solicit unwanted effects and impairment"),
        ]
        for i, (name, sub) in enumerate(outcome_cards):
            y = 2.00 + i * .80
            rect(s, .87, y, 11.55, .68)
            txt(s, name, 1.10, y+.14, 3.13, .37, 14, TEAL, True)
            txt(s, sub, 4.12, y+.13, 8.04, .40, 14, INK)
        txt(s, "WHO-5 questionnaire is CC BY-NC-SA 3.0 IGO; no unlicensed commercial copy.",
            .93, 6.39, 11.65, .34, 11, GOLD, True)
        add_notes(s, (
            "第117枚｜P07-6：本当の価値の多次元測定\n\n"
            "瞑想時間や通知クリック率と本人が望む生活の改善は異なる。"
            "モデルの予測精度、本人の自己選択の行動、生活機能・Wellbeing、"
            "自律性、害の五領域を分けて測る。WHO-5は過去2週間の5項目を0〜5点で"
            "採点し4倍して0〜100点にするが、WHOの2024版質問票は"
            "CC BY-NC-SA 3.0 IGO。企業内での商業的な転記は権利確認が必要。"
            "WHOQOL・PROMIS・FFMQ・PTQ・MedEx等も正式版と許諾と妥当性を確認する。"
            "Managerの0〜10の参考入力は未検証の独自参考指標で、臨床尺度ではない。"
        ))

        # 118: harms & guarded code
        s = new_slide(
            deck, "P07-6 / ADVERSE EVENTS + CAUSAL EVAL",
            "A quiet inbox is not evidence of no harm.",
            "Measure impact actively; honor STOP; keep assignment separate from delivery.",
            "Farias 2020; Lindahl 2017; Britton 2022; Van Dam 2025",
        )
        rows = [
            ("REPORTED EVENT", "Distress, sleep change, impairment; ask actively"),
            ("STOP / REFER", "User revocation or harm must override engagement"),
            ("MEASURE ONLY", "Single response cannot establish intervention effect"),
            ("RCT / ITT", "Use original random assignment, NOT notification delivery"),
        ]
        for i, (name, sub) in enumerate(rows):
            y = 2.15 + i * .94
            rect(s, .89, y, 11.52, .77, SOFT if i % 2 == 0 else SOFT2)
            txt(s, name, 1.12, y+.15, 3.30, .36, 14, TEAL, True)
            txt(s, sub, 4.24, y+.13, 7.95, .42, 14, INK)
        txt(s, "25 synthetic safety tests; no independent Manager benefit RCT or clinical claims.",
            .92, 6.45, 11.5, .33, 11, GOLD, True)
        add_notes(s, (
            "第118枚｜P07-6：瞑想に関連する有害事象を無視しない\n\n"
            "Fariasら2020は83研究・6703人で全体8.3%、実験研究3.7%、"
            "観察研究33.2%と測定方法等で変化。Lindahlら2017は59種の経験を"
            "7領域で整理。Brittonら2022は96人を能動的に質問して37%が"
            "生活機能への負の影響を報告。Van Damら2025の886人の調査では"
            "生活機能障害9.1%。これらは同じ『普遍的危険率』ではない。"
            "P07-6ソフトは同意、撤回、機能・睡眠・苦痛などの本人報告から"
            "NO_ACTION、MEASURE_ONLY、STOP、STOP_AND_REFERだけを返し、"
            "勝手に医療的診断や外部通知をしない。"
            "またRCTの元の無作為割付と、後から補正された配信状態を区別し、"
            "元のHeartStepsの記述的な+12.95歩を因果効果として扱わない。"
            "25件のソフトウェアテストは人間の治療・実介入の有効性を証明しない。"
        ))
        assert len(deck.slides) == 118
        deck.save(PPTX)

    prior = NOTES.read_text(encoding="utf-8")
    if "第118枚｜P07-6" not in prior:
        prior += "\n\n## P07-5/6｜Vipassana・洞察の限界・Wellbeingと瞑想の有害事象（第115〜118枚）\n"
        for i in range(114, 118):
            prior += f"\n### 第{i + 1}枚\n\n" + deck.slides[i].notes_slide.notes_text_frame.text + "\n"
        NOTES.write_text(prior, encoding="utf-8")
    validated = Presentation(PPTX)
    assert len(validated.slides) == 118
    for i in range(114, 118):
        assert validated.slides[i].has_notes_slide
        assert len(validated.slides[i].notes_slide.notes_text_frame.text) > 100
    print("P075_P076_RESEARCH_SLIDES_VERIFIED", len(validated.slides),
          "ja_speaker_notes_added", 4)


if __name__ == "__main__":
    append()
