"""P05-1 appendix, 85->87. Main 33-slide presentation remains unchanged."""
from __future__ import annotations

import re
import tempfile
from pathlib import Path

from PIL import Image, JpegImagePlugin
from pypdf import PdfReader, PdfWriter
from pptx import Presentation

from build_p04_45_appendix import (
    base, card, text, shape_box, TEAL, BLUE, RED, ORANGE, NAVY, MUTED,
    LIGHT2, PP_ALIGN,
)
from export_p04_45_pdf import render_slide
from build_60min_journal_club import add_pdf_footer

ROOT = Path(__file__).resolve().parent
PPTX = ROOT / "AI_BEHAVIOR_JOURNAL_CLUB_JA.pptx"
PDF = ROOT / "AI_BEHAVIOR_JOURNAL_CLUB_JA.pdf"
NOTES = ROOT / "SPEAKER_NOTES_JA.md"

NARRATIONS = [
    (
        86, "既存の行動Ontologyを再利用する",
        "P05-1で初めて取り組む問いは、行動・予測・実行・結果を共通の意味でどう結ぶかです。"
        "しかし新しいOntologyを一から作るのではありません。行動科学のCOM-B、BCT Taxonomy、BCIO、"
        "証拠のPROV-O、JSON-LD、SHACL、すでに存在するManager Coreの状態機械と監査を"
        "結ぶ研究から始めます。BCIOに基づいた2025年の禁煙RCT効果予測の研究では、"
        "405件の報告・971試験アーム・82特徴量を用いて未知条件の禁煙率を予測し、"
        "Ontology-informed rulesのMAEは9.15パーセントポイントでした。"
        "これは禁煙率の予測であって、行動変容の因果効果そのものが同じ精度で当たるという話ではありません。"
        "またBCIOは行動変容の研究領域に強い一方、企業のマーケティングや実行権限そのものを全面的に"
        "定義するものでもないので、既存標準の分業を明確にします。"
    ),
    (
        87, "状態・証拠・実行権限を混同しない",
        "重要なことは、情報の出典と時点です。"
        "利用者の言葉、AIが推測した動機、提案した通知、送信系のreceipt、"
        "独立に観測されたタスク完了、そして通知が原因だったとする推定はすべて別物です。"
        "Graphは正規のログや証拠から再構築できる読み取り専用の投影にし、実行権限を発行できないようにします。"
        "また後から知った情報を過去の判断時点へ流用しないため、事実が成立した時間と"
        "記録した時間を分けます。"
        "今回、完全人工の5イベントについて既存Manager Coreを再利用し、"
        "26件の単体テストで時点・出典・推測・receipt・独立確認の区別を検査しました。"
        "ここから先は、同一の問いにflat JSONとGraph投影を使う比較を行い、"
        "本当にGraphが必要かも実験で判断します。実人間の心の状態や介入効果の証明ではありません。"
    ),
]


def build():
    prs = Presentation(str(PPTX))
    if len(prs.slides) == 87:
        print("Already 87 slides; no duplicate append")
        return
    if len(prs.slides) != 85 or len(PdfReader(str(PDF)).pages) != 85:
        raise RuntimeError("Expected 85-slide master and 85-page PDF")

    s = base(prs, "APPENDIX / P05-1 ONTOLOGY",
             "すでにあるOntologyを組み合わせればいい",
             "『行動を表現する』ことと、『現実を推定・検証する』ことは別",
             "W3C PROV-O / BCIO / JSON-LD / P05-1 research 2026-11-04")
    blocks = [
        ("行動科学", "COM-B・BCTTv1（93技法）\nBCIO：介入／対象／文脈", TEAL),
        ("意味・証拠", "JSON-LD・PROV-O\nSHACL：関係の検証", BLUE),
        ("実行・通信", "既存Manager Core\nMCP・A2A：外部接続", ORANGE),
    ]
    for i, (header, body, color) in enumerate(blocks):
        card(s, .68 + 4.22 * i, 2.37, 3.96, 2.37, header, body, color, 17)
    shape_box(s, .81, 5.17, 11.72, 1.23, LIGHT2)
    text(s, 1.06, 5.38, 11.3, .83,
         "BCIOで禁煙介入971アームを記述する先行研究あり。\nManagerは新しいOntologyより、予測と実行・独立評価の接続を研究する。",
         15.8, TEAL, True, PP_ALIGN.CENTER)

    s = base(prs, "APPENDIX / P05-1 EVIDENCE",
             "Graphは証拠の投影。真実や実行権限そのものではない",
             "予測・提案・送信レシート・観測結果・因果効果を混同しない",
             "Existing Manager Core reused / P05-1 synthetic 5 events; 26 tests")
    info = [
        ("観測", "時刻と出典", TEAL),
        ("推測", "確信度とモデル版", BLUE),
        ("候補", "NO_ACTIONも残す", ORANGE),
        ("receipt", "送信≠効果", BLUE),
        ("readback", "独立観測", TEAL),
    ]
    for i, (header, body, color) in enumerate(info):
        x = .53 + 2.54 * i
        card(s, x, 2.39, 2.33, 1.92, header, body, color, 13.7)
    shape_box(s, .89, 4.93, 11.60, 1.40, LIGHT2)
    text(s, 1.08, 5.15, 11.16, .98,
         "実行許可はGraphから発生しない。\n元のledgerと独立した権限・結果確認が正本。後知恵の情報リークを防ぐ。",
         16.1, TEAL, True, PP_ALIGN.CENTER)

    if len(prs.slides) != 87:
        raise AssertionError("Expected 87 slides")
    for i, slide in enumerate(prs.slides, 1):
        for shape in slide.shapes:
            if shape.has_text_frame and re.fullmatch(r"\s*\d+\s*/\s*(?:82|85|87)\s*", shape.text):
                for p in shape.text_frame.paragraphs:
                    for run in p.runs:
                        run.text = f"{i} / 87"
                break
    for page, heading, narration in NARRATIONS:
        frame = prs.slides[page - 1].notes_slide.notes_text_frame
        if frame is not None:
            frame.text = f"第{page}枚｜{heading}\n\n{narration}\n\n参考：P05-1_JA.md"
    prs.save(str(PPTX))
    assert len(Presentation(str(PPTX)).slides) == 87

    old_pdf = PdfReader(str(PDF))
    pictures = [render_slide(prs.slides[i]) for i in range(85, 87)]
    with tempfile.TemporaryDirectory() as td:
        extra = Path(td) / "appendix.pdf"
        pictures[0].save(str(extra), save_all=True,
                         append_images=pictures[1:], quality=95, resolution=180)
        additional = PdfReader(str(extra))
        writer = PdfWriter()
        for k in range(1, 88):
            pg = old_pdf.pages[k - 1] if k <= 85 else additional.pages[k - 86]
            writer.add_page(pg)
            if k <= 85:
                f = prs.slides[k - 1].background.fill
                if f.type == 1:
                    c = f.fore_color.rgb
                    bg = (c[0]/255, c[1]/255, c[2]/255)
                else:
                    bg = (1, 1, 1)
                add_pdf_footer(writer, writer.pages[-1], k, 87, bg)
        target = Path(td) / "87.pdf"
        with target.open("wb") as handle:
            writer.write(handle)
        target.replace(PDF)
    assert len(PdfReader(str(PDF)).pages) == 87

    md = NOTES.read_text(encoding="utf-8")
    md = md.replace("全85枚の発表者ノート", "全87枚の発表者ノート")
    md = md.replace("全85枚の", "全87枚の")
    extra_md = "\n\n---\n\n## P05-1：Ontology・状態・証拠（86〜87）\n\n"
    extra_md += "\n\n".join(
        f"## {page}｜{heading}\n\n{narration}\n"
        for page, heading, narration in NARRATIONS)
    if "P05-1：Ontology・状態・証拠（86〜87）" not in md:
        NOTES.write_text(md + extra_md + "\n", encoding="utf-8")
    latest = Presentation(str(PPTX))
    assert all(slide.has_notes_slide for slide in latest.slides)
    print("PPTX", len(latest.slides), "PDF", len(PdfReader(str(PDF)).pages),
          "NOTES", sum(slide.has_notes_slide for slide in latest.slides))


if __name__ == "__main__":
    build()
