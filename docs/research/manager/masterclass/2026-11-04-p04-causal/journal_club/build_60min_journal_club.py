"""Build a focused, 60-minute journal club deck for computational neuroscience.

KEEP the canonical detailed 82/85-slide deck intact. Select 31 originals and add
two carefully scripted introductory slides: 33 presentation slides in 42 min,
plus 18 min questions. Every slide has Japanese presenter notes and a standalone
verbatim script; the complete updated 85-slide detail deck stays available for QA.

Requires python-pptx, pypdf, Pillow and the existing PDF slide renderer.
"""
from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, JpegImagePlugin
from pypdf import PdfReader, PdfWriter
from pptx import Presentation

from build_p04_45_appendix import base, card, text, shape_box, TEAL, BLUE, ORANGE, NAVY, MUTED, LIGHT2, PP_ALIGN
from export_p04_45_pdf import render_slide, add_footer_overlay

ROOT=Path(__file__).resolve().parent
FULL_PPTX=ROOT/"AI_BEHAVIOR_JOURNAL_CLUB_JA.pptx"
FULL_PDF=ROOT/"AI_BEHAVIOR_JOURNAL_CLUB_JA.pdf"
LIVE_PPTX=ROOT/"AI_BEHAVIOR_JOURNAL_CLUB_60MIN_JA.pptx"
LIVE_PDF=ROOT/"AI_BEHAVIOR_JOURNAL_CLUB_60MIN_JA.pdf"
SCRIPT=ROOT/"SPEAKER_SCRIPT_60MIN_JA.md"
SCHEDULE=ROOT/"RUN_OF_SHOW_60MIN_JA.md"

# Numeric entries are one-based ORIGINAL slide numbers; H/N are new slides.
SELECTION=[1,2,3,4,"H","N",5,7,8,10,12,13,34,35,36,37,38,39,40,18,19,20,21,22,33,42,43,44,32,45,46,47,48]
TIMES=[0.5,1.0,1.1,1.1,1.5,1.3,1.2,1.4,1.5,1.5,1.4,1.4,1.2,1.2,1.2,1.2,1.2,1.2,1.4,1.1,1.2,1.3,1.2,1.3,1.3,1.1,1.3,1.4,1.2,0.8,1.7,1.6,1.7]
assert len(SELECTION)==len(TIMES)==33
assert round(sum(TIMES),1)==41.7

CHAPTERS=[
    (1,7,"入門：何をシミュレーションするのか"),
    (8,12,"研究史：エージェントから人間の反応予測まで"),
    (13,19,"研究の現在：代表モデルと企業が挑む課題"),
    (20,27,"科学的評価：人間データ・ベンチマーク・未見評価"),
    (28,30,"介入と因果推論：予測だけでは足りない"),
    (31,33,"Manager：私たちが検証したい方向と議論"),
]

def chapter_for(number:int)->str:
    return next(x[2] for x in CHAPTERS if x[0]<=number<=x[1])


def create_history(p):
    # Use the same source deck's design for consistent 16:9 styling.
    s=base(p,"FIELD PRIMER / RESEARCH HISTORY","人間行動シミュレーションは、LLMより前からある",
           "一つの直線的な発展ではなく、複数の研究伝統が合流している",
           "Epstein & Axtell 1996 / Park et al. UIST 2023 / Kolluri et al. EMNLP 2025")
    cells=[
        ("1996","ABM・Sugarscape","少数の行動規則から\n集団・社会の構造を生成",TEAL),
        ("2023","Generative Agents","LLM＋記憶・計画・\n振り返りで仮想社会を生成",BLUE),
        ("2024–25","個人模型・実験回答学習","面接・調査と大規模な\n実人間回答で反応を推定",TEAL),
        ("2026","効果予測・評価の厳密化","未見研究・因果効果・\n一般化と限界を検証",ORANGE),
    ]
    for i,(yr,name,desc,color) in enumerate(cells):
        x=.55+i*3.21
        shape_box(s,x,2.30,3.02,2.65)
        text(s,x+.19,2.47,2.6,.45,yr,22,color,True)
        text(s,x+.19,3.03,2.69,.48,name,15.6,NAVY,True)
        text(s,x+.19,3.62,2.69,.94,desc,14,NAVY)
        if i<3:text(s,x+3.00,3.20,.26,.45,"→",18,TEAL,True)
    shape_box(s,.72,5.34,11.90,.87,LIGHT2)
    text(s,.89,5.49,11.5,.48,"問い：それらしい社会を作ることと、現実の人や介入効果を予測することは同じか？",16,TEAL,True)
    return s


def create_neuroscience(p):
    s=base(p,"FIELD PRIMER / COMPUTATIONAL NEUROSCIENCE",
           "神経科学の言葉に置き換えると、何をモデル化するのか",
           "内部状態・観測・行動・方策・結果を区別すると、分野全体が見えてくる",
           "Conceptual analogy: state-space models / decision models / causal inference")
    cells=[
        ("潜在状態 s","意欲・信念・疲労・記憶","直接は見えず、行動や報告から推定",BLUE),
        ("観測 o","発話・選択・調査回答","モデルが再現しようとする外部データ",TEAL),
        ("方策 π(a|s)","何を選ぶか・いつ介入するか","行動や介入を選択する規則",BLUE),
        ("評価・介入 do(a)","予測と因果効果は異なる","モデルが現実の結果と一致するか検証",ORANGE),
    ]
    for i,(name,desc,detail,color) in enumerate(cells):
        x=.63+(i%2)*6.15;y=2.28+(i//2)*1.78
        shape_box(s,x,y,5.91,1.58)
        text(s,x+.20,y+.12,5.45,.33,name,16.3,color,True)
        text(s,x+.20,y+.54,5.45,.35,desc,17.0,NAVY,True)
        text(s,x+.20,y+.98,5.45,.40,detail,12.3,MUTED)
    text(s,.85,6.20,11.9,.37,"ただし、脳回路の機序を説明することと、社会・消費・対人行動を予測することは別の検証課題。",12.5,MUTED)
    return s


H_SCRIPT=(
"ここで少しだけ歴史を整理します。この分野はChatGPTやLLMが登場して突然生まれたわけではありません。"
"1996年のEpsteinとAxtellの『Growing Artificial Societies』は、個々のエージェントに単純な行動規則を与え、"
"相互作用によって集団や社会のパターンが現れることを示しました。これはABM、エージェントベースモデルの代表例です。"
"2023年のGenerative Agentsでは、LLMに記憶、振り返り、計画を組み合わせ、25体の仮想住民が行動する設計が注目されました。"
"続いて本人インタビューを使った個人モデルや、実験参加者の回答データによる追加学習が進みました。"
"2026年には、表面的な人間らしさだけでなく、未知の回答や介入効果を当てるかという評価が重要な論点になっています。"
"これらは一本道の進化ではなく、社会科学、計算論、機械学習が合流してきた流れです。"
)
N_SCRIPT=(
"計算論的神経科学と共通する言葉に置き換えると理解しやすくなります。"
"人の頭の中には、動機や信念、疲労など、直接は見えない潜在状態があります。"
"私たちはその状態を、選択や発話、質問紙の回答といった観測データから推定します。"
"その状態から次に何を選ぶかを表すのが方策で、強化学習や状態空間モデルに近い考え方です。"
"ただし、何が起きるかを予測するモデルと、こちらが介入したとき何が変わるかを予測するモデルは違います。"
"この違いは神経科学でも重要ですが、社会現象や購買行動を対象にした場合、評価に必要なデータも変わります。"
"今日の話では、脳内の機構を直接証明したと主張するのではなく、状態、反応、方策、因果、評価の対応に注目してください。"
)

BRIDGES={
    1:"今日は細かなAI製品の使い方ではなく、AIで人間の行動を模す研究分野を基礎から紹介します。最後に私たちのManager構想へつなげます。",
    3:"まず、神経科学でも混同しやすい二つの意味の『エージェント』を分けます。",
    5:"今の研究を理解するために、代表的な研究史を少し振り返ります。",
    6:"ここで、計算論的神経科学の概念へ一度翻訳してみます。",
    8:"ここから、歴史をつくった代表的な研究を4つだけ追います。",
    12:"次に、研究者や企業が現在どのような方法を採っているか俯瞰します。",
    19:"ここまでが代表的アプローチです。ここからは性能の数字をどう信じるかが主題です。",
    20:"シミュレーションの『精度』には複数の意味があります。評価を分けて考えましょう。",
    25:"次は未知の人・研究・時間へどこまで一般化できるかです。",
    28:"最後の重要な科学的問いは、予測したことと介入した効果が違う点です。",
    30:"ここまで分野の要点をまとめます。次の3枚だけ私たちの研究構想です。",
    31:"ここからは既存研究ではなく、私たちのManagerという研究構想について話します。実証済みだという説明ではありません。",
    33:"以上で本編を終えます。残り約18分、皆さんの研究分野からもぜひご意見を伺いたいです。",
}


def scrub_note(textvalue:str)->str:
    # Notes are already Japanese paragraphs written by the earlier presentation team.
    # Strip bibliographies / meta notes, but retain substantive narration.
    raw=textvalue.replace("\r","")
    raw=re.split(r"\n(?:出典|一次資料|参考資料|確認日|R01:|B01:|C01:|E01:)",raw,maxsplit=1)[0]
    raw=re.sub(r"^.*?想定\s*[\d.〜～-]+\s*分[^\n]*\n","",raw,count=1,flags=re.S)
    raw=raw.strip()
    raw=re.sub(r"\n{3,}","\n\n",raw)
    return raw


def get_script(page_number:int, identifier, source)->str:
    if identifier=="H":return H_SCRIPT
    if identifier=="N":return N_SCRIPT
    s=source.slides[identifier-1]
    note=s.notes_slide.notes_text_frame.text if s.has_notes_slide else ""
    body=scrub_note(note)
    # Avoid duplicate first-line slide title as a standalone label.
    first=body.split("\n",1)
    if len(first)>1 and len(first[0])<80 and not first[0].endswith("。"):
        body=first[1].lstrip()
    if page_number==26:
        body=("共通ベンチマークはすでに存在します。SimBenchは集団の回答分布、"
              "Artificial Societies Benchmarkは人間らしい回答の統計的な性質を複数の診断で検査します。"
              "Human Behavior Benchは個人の実人間回答に基づく未見課題を使い、"
              "Socratesの研究では実験単位を隠した評価が重要です。"
              "他にも時系列の統計的現実性や、未来の研究結果を後から採点する仕組みがあります。"
              "要点は、同じ『人間シミュレーションのベンチマーク』という名前でも、"
              "集団の分布、個人の回答、因果効果、長期行動など、何を測っているかが違うことです。"
              "比較する前に対象・情報・費用・失敗数・未見条件を揃えます。")
    if page_number in BRIDGES:
        body=BRIDGES[page_number]+"\n\n"+body
    return body


def get_title(slide)->str:
    stop=("JOURNAL CLUB","APPENDIX /","FIELD PRIMER","RESEARCH DIRECTION")
    texts=[s.text.strip().replace("\n","／")
           for s in slide.shapes if getattr(s,"has_text_frame",False) and s.text.strip()]
    for item in texts:
        if len(item)>7 and not item.startswith(stop) and not re.fullmatch(r"\d+\s*/\s*\d+",item):
            return item[:95]
    return texts[0] if texts else "(無題)"


def fix_live_footer(s,number:int):
    total=33
    for shape in s.shapes:
        if shape.has_text_frame and re.fullmatch(r"\s*\d+\s*/\s*\d+\s*",shape.text):
            for para in shape.text_frame.paragraphs:
                for run in para.runs:
                    run.text=f"{number} / {total}"
            break


def add_pdf_footer(writer, p, number, total, background=(1.0,1.0,1.0)):
    # Replicate footer replacement of the original PDF while keeping its drawing.
    from pypdf.generic import DictionaryObject,NameObject,DecodedStreamObject,ArrayObject
    resources=p["/Resources"].get_object()
    fonts=resources.get(NameObject("/Font"))
    if fonts is None:
        fonts=DictionaryObject()
        resources[NameObject("/Font")]=fonts
    else:
        fonts=fonts.get_object()
    font=DictionaryObject({
        NameObject("/Type"):NameObject("/Font"),
        NameObject("/Subtype"):NameObject("/Type1"),
        NameObject("/BaseFont"):NameObject("/Helvetica"),
        NameObject("/Encoding"):NameObject("/WinAnsiEncoding"),
    })
    fonts[NameObject("/ManagerFoot")]=writer._add_object(font)
    # Remove previous /82 footer and redraw current /33 footer.
    stream=DecodedStreamObject()
    br,bg,bb=background
    dark=(br+bg+bb)/3 < .4
    cr,cg,cb=(.88,.93,.96) if dark else (.33,.42,.49)
    stream.set_data((f"q {br:.3f} {bg:.3f} {bb:.3f} rg 830 3 129 42 re f Q\n"
                     f"BT /ManagerFoot 8 Tf {cr:.3f} {cg:.3f} {cb:.3f} rg "
                     f"865 15 Td ({number} / {total}) Tj ET\n").encode("ascii"))
    ref=writer._add_object(stream)
    c=p.get(NameObject("/Contents"))
    if c is None:p[NameObject("/Contents")]=ref
    elif isinstance(c,ArrayObject):c.append(ref)
    else:p[NameObject("/Contents")]=ArrayObject([c,ref])


def build():
    source=Presentation(str(FULL_PPTX))
    prior=len(source.slides)
    if prior not in (82,85):
        raise RuntimeError(f"Expected 82/85-source deck, found {prior}; inspect before building")
    if len(PdfReader(str(FULL_PDF)).pages)!=prior:
        raise RuntimeError("Full PDF not aligned with source slide count")
    create_history(source)
    create_neuroscience(source)
    original_ids=list(source.slides._sldIdLst)
    chosen=[]
    for item in SELECTION:
        index={"H":prior,"N":prior+1}.get(item,item-1 if isinstance(item,int) else -1)
        chosen.append(original_ids[index])
    for sldid in original_ids:
        if sldid not in chosen:
            source.part.drop_rel(sldid.rId)
    ids=source.slides._sldIdLst
    for child in list(ids):ids.remove(child)
    for child in chosen:ids.append(child)
    if len(source.slides)!=33:
        raise AssertionError("Focused deck wrong slide count")

    # The original source note is read separately because source now contains a selection.
    canonical=Presentation(str(FULL_PPTX))
    slide_info=[]
    for k,(slide,item,mins) in enumerate(zip(source.slides,SELECTION,TIMES),start=1):
        fix_live_footer(slide,k)
        chapter=chapter_for(k)
        body=get_script(k,item,canonical)
        if not body.strip():
            raise AssertionError("Speaker script missing for slide "+str(k))
        note=f"第{k:02d}枚｜{chapter}｜目安{mins:.1f}分\n\n"+body
        frame=slide.notes_slide.notes_text_frame
        if frame is not None:frame.text=note
        title=get_title(slide)
        slide_info.append({"page":k,"source":item,"title":title,
                           "minutes":mins,"chapter":chapter,"script":body})
    source.save(str(LIVE_PPTX))
    saved=Presentation(str(LIVE_PPTX))
    assert len(saved.slides)==33
    assert all(s.has_notes_slide and s.notes_slide.notes_text_frame.text.strip()
               for s in saved.slides)

    # Build a short PDF from the detailed PDF (no re-rendering) and 2 new pages.
    pdf=PdfReader(str(FULL_PDF))
    h=render_slide(saved.slides[4])
    n=render_slide(saved.slides[5])
    with tempfile.TemporaryDirectory() as td:
        extra=Path(td)/"extra.pdf"
        h.save(str(extra),save_all=True,append_images=[n],quality=95,resolution=180)
        extra_pdf=PdfReader(str(extra))
        writer=PdfWriter()
        for k,entry in enumerate(SELECTION,1):
            src_index={"H":0,"N":1}.get(entry)
            page=extra_pdf.pages[src_index] if src_index is not None else pdf.pages[entry-1]
            writer.add_page(page)
            if isinstance(entry,int):
                fill=canonical.slides[entry-1].background.fill
                if fill.type==1:
                    col=fill.fore_color.rgb
                    background=(col[0]/255.0,col[1]/255.0,col[2]/255.0)
                else:
                    background=(1.0,1.0,1.0)
            else:
                background=(1.0,1.0,1.0)
            add_pdf_footer(writer,writer.pages[-1],k,33,background)
        with LIVE_PDF.open("wb") as f:
            writer.write(f)
    assert len(PdfReader(str(LIVE_PDF)).pages)==33

    preface=(
        "# AI人間行動シミュレーション｜60分発表・全ページ日本語読み上げ原稿\n\n"
        "**対象：** 神経科学・計算論的神経科学の研究者および修士課程M1・M2。分野の専門知識は仮定しない。\n\n"
        "**2026-11-05 13:00–14:00（日本時間）を想定。** 本編33枚約41.7分、質疑15分、移動・画面操作など約3分の余裕。"
        "数字の読み上げや質問によって遅れたら、以下の優先ルートに従って短縮する。\n\n"
        "**重要：** 今日の目的はManagerの宣伝ではなく、研究の全体像・方法・評価・限界を理解してもらうこと。"
        "Managerは最後の3枚・約5分。企業発表は自己報告と明示し、単一指標で優劣を順位付けしない。"
        "P04-6の詳しい数学や追加人工実験は予備資料に残し、本編で詳述しない。\n\n"
        "発表順と各ページの読み上げ内容は以下。実際に読む際は『出典』を逐一読み上げず、脚注を参照する。\n"
    )
    blocks=[preface]
    for x in slide_info:
        blocks.append(
            f"\n---\n\n## {x['page']:02d}｜{x['title']}\n\n"
            f"**章：** {x['chapter']}　**目安：** {x['minutes']:.1f}分　"
            f"**元資料：** {'新規追加' if isinstance(x['source'],str) else f'詳細版{x['source']}枚'}\n\n"
            f"### 読み上げ原稿\n\n{x['script'].strip()}\n"
        )
    SCRIPT.write_text("\n".join(blocks),encoding="utf-8")

    lines=[
        "# ジャーナルクラブ｜発表用33枚の進行表",
        "",
        "**対象:** 計算論的神経科学／神経科学の研究者とM1・M2。ゼロから分野を説明。",
        "**時間:** 13:00–13:42本編（計41.7分）、13:42–13:57質疑15分、13:57–14:00移動・余裕約3分。",
        "**方針:** 発表版33枚と詳細保存版82枚を分ける。最後の3枚のみManager。",
        "",
        "| 発表章 | スライド | 持ち時間 | 主に伝えること |",
        "|---|---:|---:|---|",
    ]
    for a,b,label in CHAPTERS:
        mins=sum(TIMES[a-1:b])
        explanations={
            1:"エージェント2種類、モデルの部品、歴史、神経科学との対応",
            8:"代表研究：Generative Agents／本人模型／Socrates／介入効果",
            13:"Aaru、Simile、Rothko、Listen、Persimmon、Ampersandと独立検証",
            20:"人間分布、個人・条件差、ベンチマーク、未見研究評価",
            28:"予測と介入効果の差、分布が変わる問題、3つのまとめ",
            31:"Managerの方向、科学的検証、討論",
        }
        lines.append(f"| {label} | {a}–{b} | {mins:.1f}分 | {explanations[a]} |")
    lines.extend([
        "",
        "## 全ページ対応表",
        "",
        "| 発表用ページ | 詳細版の元ページ | 時間(分) | タイトル |",
        "|---:|---|---:|---|",
    ])
    for x in slide_info:
        origin="新規（歴史）" if x["source"]=="H" else "新規（神経科学ブリッジ）" if x["source"]=="N" else str(x["source"])
        lines.append(f"| {x['page']} | {origin} | {x['minutes']:.1f} | {x['title'].replace('|','／')} |")
    lines.extend([
        "",
        "## 途中で時間が押した場合",
        "",
        "- **省略可能**：新旧比較の補助例である本編16（Listen Twins）、17（Persimmon）、23（効果量のずれ）を各20〜30秒で要約すれば約2分短縮可能。",
        "- **絶対に残す**：本編3–7（基礎・歴史・神経科学）、8–11（研究の起点）、20–27（ベンチマーク）、28（相関と因果）、30（全体まとめ）、31–33（Managerと議論）。",
        "- **難しい数式は口頭では深掘りしない**：TVDは『回答割合のズレ』、ATEは『介入したときの平均差』と説明し、式は質疑で扱う。",
        "- **スライドの全文を読む必要はない**：各ページは一つのメッセージ。読み上げ原稿は発表準備用のガイド。自身の言葉で説明してもよい。",
        "- **企業の数値を混ぜない**：自己報告・対象・分母・指標・検証範囲を脚注で示す。",
        "",
        "## 質疑のための詳細資料",
        "",
        "詳細版85枚（元の講義とP04-4〜P04-6付録）は手元に保持。"
        "P04-6の人工実験と講義は P04-6_JA.md に分離し、必要な質問時だけ参照。"
    ])
    SCHEDULE.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("LIVE",len(saved.slides),"slides",len(PdfReader(str(LIVE_PDF)).pages),
          "PDF pages; scripted",len(slide_info),"pages; talk minutes",sum(TIMES))
    for x in slide_info:
        print(f"{x['page']:02d} source={x['source']!s:>2} {x['minutes']:.1f}min  {x['title'][:60]}")


if __name__=="__main__":
    build()
