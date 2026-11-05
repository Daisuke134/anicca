"""Append P07-4 CBT/ACT and value-aligned plan safety slides to canonical PPTX.

Cloud-only deterministic artifact authoring: original first 112 slides preserved;
new English appendix slides include complete Japanese speaker notes.
This is an educational record, not evidence of treatment effectiveness.
"""
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
import re

ROOT = Path(__file__).resolve().parents[1] / "journal_club"
PPTX = ROOT / "AI_BEHAVIOR_JOURNAL_CLUB_JA.pptx"
NOTES = ROOT / "SPEAKER_NOTES_JA.md"

NAVY = RGBColor(23, 43, 62)
TEAL = RGBColor(0, 122, 127)
MUTED = RGBColor(85, 106, 124)
LIGHT = RGBColor(241, 247, 248)
PALE = RGBColor(233, 244, 245)
GOLD = RGBColor(181, 113, 20)


def label(slide, content, x, y, w, h, font_size=15, color=NAVY, bold=False):
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    frame = shape.text_frame
    frame.word_wrap = True
    frame.margin_left = Inches(0.03)
    frame.margin_top = Inches(0.03)
    for i, item in enumerate(content.split("\n")):
        par = frame.paragraphs[0] if i == 0 else frame.add_paragraph()
        par.text = item
        for run in par.runs:
            run.font.name = "Aptos"
            run.font.size = Pt(font_size)
            run.font.bold = bold
            run.font.color.rgb = color


def panel(slide, x, y, w, h, color=LIGHT):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(x), Inches(y), Inches(w), Inches(h)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()


def page(pres, topic, title, subtitle, source):
    slide = pres.slides.add_slide(pres.slide_layouts[0])
    panel(slide, 0, 0, 0.16, 7.5, TEAL)
    label(slide, topic, .48, .2, 12, .34, 11, TEAL, True)
    label(slide, title, .48, .66, 12.2, .72, 25, NAVY, True)
    label(slide, subtitle, .48, 1.48, 12.1, .40, 14, MUTED)
    panel(slide, .5, 7.02, 12.22, .01, PALE)
    label(slide, source, .53, 7.06, 11.35, .27, 8, MUTED)
    label(slide, f"{len(pres.slides)} / 114", 12.0, 7.06, .78, .27, 9, MUTED)
    return slide


def append():
    p = Presentation(PPTX)
    if len(p.slides) not in (112, 114):
        raise ValueError(f"expected 112 or 114 slides, got {len(p.slides)}")
    if len(p.slides) == 112:
        for slide in p.slides:
            for shape in slide.shapes:
                if shape.has_text_frame and re.fullmatch(
                    r"\s*\d+ / 112\s*", shape.text
                ):
                    shape.text = shape.text.replace("/ 112", "/ 114")

        a = page(p, "APPENDIX / P07-4 | CBT AND ACT",
                 "From behavior triggers to values-aligned actions",
                 "CBT and ACT overlap, but their core intervention questions differ",
                 "ACBS About ACT; APA 2026; NICE NG222 (2022; reviewed 2026)")
        for i, (name, title, example) in enumerate([
            ("CBT", "Thoughts, feelings and behavior",
             "Behavioral activation, experiments, examining interpretations"),
            ("ACT", "Psychological flexibility",
             "Acceptance, defusion, present moment, self-as-context"),
            ("VALUES", "Chosen direction and committed action",
             "One meaningful user-chosen next step, with permission to rest"),
        ]):
            y = 2.11 + i * 1.28
            panel(a, .85, y, 11.56, 1.08)
            label(a, name, 1.03, y + .13, 2.10, .35, 15, TEAL, True)
            label(a, title, 3.00, y + .11, 8.85, .34, 17, NAVY, True)
            label(a, example, 3.00, y + .59, 8.85, .35, 12, MUTED)
        label(a, "Evidence for therapy is NOT evidence that Manager treats distress.",
              .94, 6.36, 11.45, .38, 12, GOLD, True)
        a.notes_slide.notes_text_frame.text = (
            "第113枚｜P07-4 CBTとACTの基本と違い\n\n"
            "CBTは考え・感情・行動・文脈の関係を検討し、行動活性化や"
            "行動実験、解釈の再検討などを用います。ACTは心理的柔軟性を"
            "中心に置き、acceptance、cognitive defusion、present-moment awareness、"
            "self-as-context、values、committed actionの6プロセスで整理できます。"
            "どちらかが万能に優秀という話ではなく、対象者や比較条件によります。"
            "NICEなどの治療ガイドラインと、一般の習慣プランを混同しません。"
            "Managerで実装したのは、本人の非臨床の目標を下書きする安全なソフト部品で、"
            "心理療法の自動提供や効果実証ではありません。"
        )

        b = page(p, "APPENDIX / P07-4 | ONE LEARN + BUILD TODO",
                 "An opt-in plan is not an autonomous intervention.",
                 "Reuse the Habit Designer; connect only the missing permission gate",
                 "Manager code: p07_4_value_action_gate.py + 15 cloud unit tests")
        items = [
            ("USER CHOICE", "Self-chosen value, anchor, tiny action, 1–5 minutes"),
            ("REUSE", "Existing Habit Designer JSON with safe_t_flag"),
            ("SAFETY", "No consent / revoked / unavailable / clinical -> NO_ACTION"),
            ("READ-ONLY", "Explicit nonclinical case -> DRAFT_ONLY, zero external effects"),
            ("EVIDENCE", "Software 15 tests passed; no human-benefit trial"),
        ]
        for i, (name, description) in enumerate(items):
            y = 2.11 + i * .78
            panel(b, .85, y, 11.56, .64, LIGHT if i % 2 == 0 else PALE)
            label(b, name, 1.05, y + .16, 3.12, .30, 12, TEAL, True)
            label(b, description, 4.12, y + .13, 8.0, .38, 13, NAVY)
        label(b, "NEXT CLASS: P07-5 Vipassana / suffering. BFM-01 stays active in the ONE roadmap.",
              .93, 6.44, 11.42, .36, 11, GOLD, True)
        b.notes_slide.notes_text_frame.text = (
            "第114枚｜学んだら実装：P07-4の安全な価値→行動の接続\n\n"
            "Managerの既存Habit Designer APIを再発明せず、"
            "新たな小さいゲートだけを追加しました。ユーザーが自分で選んだ価値と"
            "行動・時間・場所、明示的opt-inがあるときのみDRAFT_ONLY。"
            "同意なし、撤回、利用不可、臨床的・医学的領域ならNO_ACTION。"
            "AI生成の行動指示をそのまま実行権限として採用せず、通知・外部効果はゼロ。"
            "ソフトウェアの15テストは合格しても、人間の心理的な便益は未測定。"
            "P07-5は次のヴィパッサナー・苦・執着・解脱。"
            "BFM-01のBe.FM実行はHugging Faceのアクセス許可とクラウド認証が必要で、"
            "同じ一つのロードマップに紐づけて継続します。"
        )
        assert len(p.slides) == 114
        p.save(PPTX)

    # Notes file keeps the two new slides consistent in the same existing source.
    t = NOTES.read_text(encoding="utf-8")
    if "第114枚｜学んだら実装" not in t:
        t += "\n\n## P07-4｜CBT・ACT・心理的柔軟性＋Manager実装（第113〜114枚）\n"
        for i in (112, 113):
            ptxt = p.slides[i].notes_slide.notes_text_frame.text
            t += f"\n### 第{i+1}枚\n\n{ptxt}\n"
        NOTES.write_text(t, encoding="utf-8")

    verified = Presentation(PPTX)
    if len(verified.slides) != 114:
        raise AssertionError("research archive slide count not 114")
    for n in (112, 113):
        if not verified.slides[n].has_notes_slide:
            raise AssertionError(f"no notes for page {n+1}")
        if len(verified.slides[n].notes_slide.notes_text_frame.text) < 80:
            raise AssertionError("missing full Japanese speaker notes")

    print(f"RESEARCH_P07_4_SLIDES_VERIFIED count={len(verified.slides)} "
          f"notes_new=2 pptx_bytes={PPTX.stat().st_size}")


if __name__ == "__main__":
    append()
