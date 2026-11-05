"""Append P06-3, P06-4, P06-5 as THREE research slides: 93 -> 96.

Keep 34-slide public talk and its PDF/script UNCHANGED. Archive gains exactly
three detailed education slides with narration; existing 93 slide bodies stay
identical apart from page number footer. This is not empirical field evidence.
"""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
import re

from PIL import Image, JpegImagePlugin
from pptx import Presentation
from pypdf import PdfReader,PdfWriter

from build_p04_45_appendix import (
    base,card,text,shape_box,TEAL,BLUE,ORANGE,RED,LIGHT2,PP_ALIGN,
)
from export_p04_45_pdf import render_slide
from build_60min_journal_club import add_pdf_footer

ROOT=Path(__file__).resolve().parent
PPTX=ROOT/"AI_BEHAVIOR_JOURNAL_CLUB_JA.pptx"
PDF=ROOT/"AI_BEHAVIOR_JOURNAL_CLUB_JA.pdf"
NOTES=ROOT/"SPEAKER_NOTES_JA.md"

NARRATIONS=[
    (94,"P06-3：人数、途中解析、SRM",
     "この教材は実際の参加者を募集せず、統計の原理を人工世界で確かめたものです。"
     "現行正答率を25パーセント、検出したい改善を3ポイント、検出力80パーセントと仮定すると、"
     "statsmodelsの標本数計算では各群3395人が必要でした。15パーセントの脱落を見込むと合計7990人です。"
     "一方、有意になるまで途中結果を四回のぞいて止めると、"
     "本来効果ゼロの人工A/A2400反復で偽陽性が約11.92パーセントになりました。"
     "最後の一回だけなら約4.79パーセント、Bonferroni補正で約3.79パーセントです。"
     "本番ではStatsigなどの既存の逐次検定と、データ品質のSRM・Guardrailを利用します。"
     "ここに示す人数と効果は実利用者から推定されたものではありません。"),
    (95,"P06-4：利益が増えても採用しない",
     "もう一つの人工EC実験では30,000人を架空にランダム化し、"
     "支払い済み購入、返金、商品と決済の費用、広告獲得、モデルのトークン費、"
     "有人対応と苦情コストを全部考慮しました。"
     "Manager型の方策は貢献利益を1割当あたり約56.84円増加させました。"
     "ですが苦情率も約0.942ポイント悪化し、事前に定めた悪化許容0.3ポイントを超えました。"
     "したがって結論はDO NOT SHIPです。"
     "これはSpotify Confidenceが重視する、成功指標だけでなくGuardrail・実験品質を満たす考え方に近い設計です。"
     "現実の利益額や本当の人間の苦しみを測った数字ではありません。"),
    (96,"P06-5：本当に分かったことだけを実績カードへ",
     "最後の実績カードでは、P06-2から4の実験計画、方策、結果9ファイルのSHAを照合しました。"
     "また既存Manager Coreで、実際の自社公開サイトのManifestと六つのHTMLを再取得してハッシュの整合を確認しました。"
     "しかしManifest上は実参加者0、実験無効、本人の便益は未測定です。"
     "本当に支払われた売上、返金、本人の反すう、比較研究の結果がないため、"
     "実会社の増分利益と本人の行動変化はnull、導入判定はHOLDです。"
     "ここまででPhase6の講義・人工検証の一連の学習は終了し、次のP07へ進む準備ができます。"
     "それでも現実の会社価値を証明する本番S1/2や本人への効果は引き続き未検証です。"),
]


def update_footer(slide,index,total):
    for sh in slide.shapes:
        if sh.has_text_frame and re.fullmatch(r"\s*\d+\s*/\s*\d+\s*",sh.text):
            for para in sh.text_frame.paragraphs:
                for run in para.runs:
                    run.text=f"{index} / {total}"
            break


def run():
    prs=Presentation(str(PPTX))
    current_pdf=PdfReader(str(PDF))
    if len(prs.slides)!=93 or len(current_pdf.pages)!=93:
        raise RuntimeError("Expected a 93-slide master; refuse append or overwrite a different archive")

    a=base(prs,"APPENDIX / P06-3 EXPERIMENT DESIGN",
           "何人必要？ いつ結果を見てもよい？",
           "サンプル比率・事前計画・途中停止を同時に固定する",
           "statsmodels NormalIndPower / SciPy chisquare & A/A simulation")
    for i,(header,body,color) in enumerate([
        ("必要標本数","架空の25% → 28%\n各群 3,395人",TEAL),
        ("4回の無補正のぞき見","人工A/Aの偽陽性\n11.92%（2400反復）",ORANGE),
        ("正規の品質検査","SRM・停止・Guardrail\n外部の結果確認",BLUE),
    ]):
        card(a,.63+4.22*i,2.40,3.97,2.45,header,body,color,16.0)
    shape_box(a,.85,5.19,11.63,1.25,LIGHT2)
    text(a,1.08,5.41,11.15,.78,
         "全て人工の設計例。実参加者0／外部の事前登録なし。\n本番はStatsigなど既存の逐次検定・品質Gateを再利用する。",
         15.3,TEAL,True,PP_ALIGN.CENTER)

    b=base(prs,"APPENDIX / P06-4 BUSINESS & GUARDRAILS",
           "利益が増えても、苦情が増えれば採用しない",
           "購入・返金・原価・運用・推論・害を同時に評価",
           "30,000 synthetic assignments / SciPy Welch t-test")
    card(b,.82,2.38,5.72,2.43,
         "人工の貢献利益","+56.84円/割当\n95%CI +36.55〜+77.12円",
         TEAL,18.1)
    card(b,6.77,2.38,5.72,2.43,
         "人工の苦情・停止率","+0.942ポイント悪化\n許容悪化は+0.3ポイント",
         RED,17.3)
    shape_box(b,.85,5.14,11.63,1.26,LIGHT2)
    text(b,1.12,5.36,11.15,.78,
         "判定：DO NOT SHIP。利益だけでなくGuardrailを満たす必要。\n実際の会社利益・実ユーザーの影響は未測定。",
         15.4,ORANGE,True,PP_ALIGN.CENTER)

    c=base(prs,"APPENDIX / P06-5 PROOF CARD",
           "実績は『独立した証拠』からつくる",
           "観測できた事実と、まだ測れていない人の便益を混ぜない",
           "Existing Manager Core public readback + SHA-256 provenance")
    for i,(header,body,color) in enumerate([
        ("人工研究","凍結計画9ファイル\nハッシュ照合OK",BLUE),
        ("実公開サイト","Manifest + HTML6\n配信・ハッシュ確認",TEAL),
        ("本当の便益","利益・反すう\nNOT MEASURED",ORANGE),
    ]):
        card(c,.63+4.22*i,2.40,3.97,2.42,header,body,color,17.2)
    shape_box(c,.84,5.18,11.65,1.29,LIGHT2)
    text(c,1.06,5.39,11.24,.80,
         "Phase 6の講義・人工実験は完了 → 次はP07。\n本番のS1/S2・実会社/人間への介入効果は未完了。",
         15.3,TEAL,True,PP_ALIGN.CENTER)

    assert len(prs.slides)==96
    for i,s in enumerate(prs.slides,1):
        update_footer(s,i,96)
    for index,title,words in NARRATIONS:
        frame=prs.slides[index-1].notes_slide.notes_text_frame
        if frame is not None:
            frame.text=f"第{index}枚｜{title}\n\n{words}\n\n資料：P06-{index-91}_JA.md。"
    prs.save(str(PPTX))
    assert len(Presentation(str(PPTX)).slides)==96

    new_imgs=[render_slide(prs.slides[index]) for index in range(93,96)]
    with TemporaryDirectory() as temp:
        td=Path(temp)
        added=td/"add.pdf"
        new_imgs[0].save(str(added),save_all=True,append_images=new_imgs[1:],
                         quality=95,resolution=180)
        new_pages=PdfReader(str(added))
        writer=PdfWriter()
        for i in range(1,97):
            old=i<=93
            page=current_pdf.pages[i-1] if old else new_pages.pages[i-94]
            writer.add_page(page)
            if old:
                fill=prs.slides[i-1].background.fill
                if fill.type==1:
                    col=fill.fore_color.rgb
                    color=(col[0]/255,col[1]/255,col[2]/255)
                else:
                    color=(1,1,1)
                add_pdf_footer(writer,writer.pages[-1],i,96,color)
        candidate=td/"96.pdf"
        with candidate.open("wb") as fp:
            writer.write(fp)
        PDF.write_bytes(candidate.read_bytes())
    assert len(PdfReader(str(PDF)).pages)==96

    old=NOTES.read_text(encoding="utf-8")
    old=old.replace("全93枚の発表者ノート","全96枚の発表者ノート")
    old=old.replace("全93枚の","全96枚の")
    section="\n\n---\n\n## Phase6実行付録・P06-3〜P06-5（94〜96）\n\n"
    section+="\n\n".join(
       f"## {page}｜{heading}\n\n{words}\n" for page,heading,words in NARRATIONS)
    if "Phase6実行付録・P06-3〜P06-5（94〜96）" not in old:
        NOTES.write_text(old+section+"\n",encoding="utf-8")
    print("PPTX slides:",len(prs.slides),"PDF pages:",len(PdfReader(str(PDF)).pages),
          "notes:",sum(s.has_notes_slide for s in prs.slides))


if __name__=="__main__":
    run()
