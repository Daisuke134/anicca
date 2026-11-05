"""Append P05-2 two research-only slides (87→89). Keep 33-slide talk unchanged.

Uses existing PowerPoint and PDF appendix builders. Adds full Japanese narration.
The original 87 slides remain ordered and their text changes only in footer.
New PDF pages rendered at 180 dpi; existing PDF pages retained with footer update.
"""
from __future__ import annotations
import re
import tempfile
from pathlib import Path

from PIL import Image, JpegImagePlugin
from pypdf import PdfReader, PdfWriter
from pptx import Presentation

from build_p04_45_appendix import (
    base, card, text, shape_box, TEAL, BLUE, ORANGE, NAVY, MUTED,
    LIGHT2, RED, PP_ALIGN,
)
from export_p04_45_pdf import render_slide
from build_60min_journal_club import add_pdf_footer

ROOT = Path(__file__).resolve().parent
PPTX = ROOT / "AI_BEHAVIOR_JOURNAL_CLUB_JA.pptx"
PDF = ROOT / "AI_BEHAVIOR_JOURNAL_CLUB_JA.pdf"
NOTES = ROOT / "SPEAKER_NOTES_JA.md"

NARRATIONS = [
    (
      88,"P05-2：既存レコードを正しく結ぶ",
      "P05-2は、予測と意思決定から実行と結果まで、同じ処理を追跡できるかという講義です。"
      "まず再発明しないことが重要です。runtime/contracts/common-record.schema.jsonにはJob、"
      "Effect、Receipt、RuntimeEventという既存のJSON Schemaがあり、その意味を守って読み取ります。"
      "たとえばJobのeffect_keyはEffectのidempotency_keyに相当し、Effectのeffect_idとは別物です。"
      "Receiptを結ぶときはeffect_id、run_id、loop_id、providerの一致を確認します。"
      "現在の4種の記録には正式なprediction_id、decision_id、experiment_idが共通必須として存在せず、"
      "今回の教材では勝手に作ったIDで完結したと言わず、未解決の契約ギャップとして表示します。"
      "さらに、ProviderのReceiptがあっても、実際の人間の改善や介入の因果効果は証明されない点を強調します。"
      "既存のManager CoreのNO_ACTIONと実行権限を維持し、追加のTraceは読み取り専用にしました。"
    ),
    (
      89,"P05-2：TinyFishとListen Labs APIを本当に使って確認",
      "今回はブラウザーとAPIを両方動かしました。TinyFishでListen Labsの公式API仕様と"
      "作成・公開・課金の違いを確認し、Mac miniから提供された組織キーを一時的に読み込んで、"
      "GET wallets と GET studies をそれぞれHTTP 200で実行しました。"
      "ウォレットは1件という匿名件数だけを保存し、参加者の回答、調査タイトル、"
      "ウォレット残高、キーの値は保存していません。新規調査の作成、公開、費用発生の操作も0件です。"
      "Listen Twinsの人間予測モデルを呼ぶ公開APIは、確認した文書にはありません。"
      "別に、実在のManager共通Schemaを読み取る人工Traceを実行し、"
      "同じrun・effect・receiptの整合性、異なるtenantやrunからの不正な結合の拒否、"
      "後から届くレシートの時刻を確認しました。P05-2新規48テストを含む全193テストに成功しています。"
      "これらはソフトウェアの技術実験であり、Managerが人の苦しみを減らした実証ではありません。"
      "本編発表は33枚のままにして、この2枚は質問と補足研究のために保存します。"
    ),
]

def run():
    presentation = Presentation(str(PPTX))
    reader = PdfReader(str(PDF))
    if len(presentation.slides) == 89 and len(reader.pages) == 89:
        print("already 89 slides/pages")
        return
    if len(presentation.slides) != 87 or len(reader.pages) != 87:
        raise RuntimeError("Refuse append unless exactly 87 slides and 87 PDF pages")

    first = base(presentation, "APPENDIX / P05-2 COMMON CONTRACT",
        "共通のIDをつなぐ。でも新しい権限は作らない",
        "既存Job → Effect → Receipt → RuntimeEventを同じスコープと時点で追跡",
        "Manager Core / runtime common-record.schema.json (existing)")
    blocks=[
        ("Job","job_id\neffect_key",TEAL),
        ("Effect","effect_id\nidempotency_key",BLUE),
        ("Receipt","receipt_id\neffect_id",ORANGE),
        ("Runtime","event_id\nrun_id",TEAL),
    ]
    for i,(head,body,color) in enumerate(blocks):
        card(first,.66+i*3.16,2.47,2.96,2.05,head,body,color,17.5)
    shape_box(first,.77,5.05,11.80,1.25,LIGHT2)
    text(first,.97,5.22,11.34,.84,
        "予測ID・判断IDは既存共通レコードの必須項目ではない。\n欠落を勝手に埋めず、Receipt≠人間の改善として扱う。",
        16.0,TEAL,True,PP_ALIGN.CENTER)

    second = base(presentation, "APPENDIX / P05-2 REAL API + SYNTHETIC TRACE",
        "Listen Labs APIへ認証付きGET：HTTP 200",
        "TinyFishで実ブラウザーを操作し、Mac miniでStudy APIへ読み取り接続",
        "P05-2 read-only API probe + synthetic trace, 2026-11-04")
    card(second,.68,2.44,5.84,2.20,
         "実APIで確かめたこと",
         "GET /wallets → HTTP 200\nGET /studies → HTTP 200\n作成・公開・課金・回答保存：0",TEAL,16.3)
    card(second,6.72,2.44,5.84,2.20,
         "人工契約実験で確かめたこと",
         "run／effect／receiptを厳密に照合\n別テナント・時間リークを拒否\nP05-2新規48件／累計193件PASS",BLUE,15.4)
    shape_box(second,.85,5.08,11.60,1.17,LIGHT2)
    text(second,1.00,5.25,11.23,.78,
         "Listen Twinsの予測APIは未確認。\n本番発表33枚は変えず、研究付録として保存する。",
         16.1,ORANGE,True,PP_ALIGN.CENTER)

    assert len(presentation.slides)==89
    for k,slide in enumerate(presentation.slides,1):
        for shape in slide.shapes:
            if shape.has_text_frame and re.fullmatch(r"\s*\d+\s*/\s*(?:82|85|87|89)\s*",shape.text):
                for para in shape.text_frame.paragraphs:
                    for run in para.runs:
                        run.text=f"{k} / 89"
                break
    for page,title,words in NARRATIONS:
        tf=presentation.slides[page-1].notes_slide.notes_text_frame
        if tf is not None:
            tf.text=f"第{page}枚｜{title}\n\n{words}\n\n資料：P05-2_JA.md。"
    presentation.save(str(PPTX))
    new = Presentation(str(PPTX))
    assert len(new.slides)==89
    assert all(slide.has_notes_slide for slide in new.slides)

    img=[render_slide(new.slides[i]) for i in range(87,89)]
    with tempfile.TemporaryDirectory() as temp:
        appendix=Path(temp)/"appendix.pdf"
        img[0].save(str(appendix),save_all=True,append_images=img[1:],
                    quality=95,resolution=180)
        extra=PdfReader(str(appendix))
        writer=PdfWriter()
        for k in range(1,90):
            page=reader.pages[k-1] if k<=87 else extra.pages[k-88]
            writer.add_page(page)
            if k<=87:
                fill=new.slides[k-1].background.fill
                if fill.type==1:
                    c=fill.fore_color.rgb
                    bg=(c[0]/255,c[1]/255,c[2]/255)
                else:
                    bg=(1,1,1)
                add_pdf_footer(writer,writer.pages[-1],k,89,bg)
        output=Path(temp)/"89.pdf"
        with output.open("wb") as fp:
            writer.write(fp)
        output.replace(PDF)
    assert len(PdfReader(str(PDF)).pages)==89

    md=NOTES.read_text(encoding="utf-8")
    md=md.replace("全87枚の発表者ノート","全89枚の発表者ノート")
    md=md.replace("全87枚の","全89枚の")
    section="\n\n---\n\n## P05-2：共通IDとListen Labs実API確認（88〜89）\n\n"
    section+="\n\n".join(f"## {p}｜{title}\n\n{words}\n"
                         for p,title,words in NARRATIONS)
    if "P05-2：共通IDとListen Labs実API確認（88〜89）" not in md:
        NOTES.write_text(md+section+"\n",encoding="utf-8")
    print("PPTX",len(new.slides),"PDF",len(PdfReader(str(PDF)).pages),
          "NOTES",sum(slide.has_notes_slide for slide in new.slides))

if __name__=="__main__":
    run()
