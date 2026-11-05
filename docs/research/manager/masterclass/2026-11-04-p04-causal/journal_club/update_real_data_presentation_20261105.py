"""Revise two EXISTING slides for actual observed UCI human choices.

Slide 28 previously used a fictional causal example. Replace it with actual
UCI Bank Marketing observations and explain why observational prediction
cannot identify calling uplift. Slide 34 adds the real open-data benchmark,
while explicitly preserving NOT-MEASURED real causal/company impact.

Slide 33's status sentence and three notes' time references get synchronized.
Public talk stays EXACTLY 34 slides, ~43 min; PDF regenerated selectively.
All 34 full manuscript chapters preserved except the edited chapters.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from hashlib import sha256
import re
from pptx import Presentation
from pypdf import PdfReader, PdfWriter
from PIL import Image

from export_p04_45_pdf import render_slide
from build_60min_journal_club import add_pdf_footer

ROOT=Path(__file__).resolve().parent
PPTX=ROOT/"AI_BEHAVIOR_JOURNAL_CLUB_60MIN_JA.pptx"
PDF=ROOT/"AI_BEHAVIOR_JOURNAL_CLUB_60MIN_JA.pdf"
SCRIPT=ROOT/"SPEAKER_SCRIPT_60MIN_JA.md"

REPLACE={
28:{
 "交絡があると観察データからの結論は、真の介入効果と逆になる":
    "実際に観測された申込結果があっても、勧誘の因果効果は別の問題",
 "[C01] [C02] 教材用の完全架空数値":
    "[C01] UCI Bank Marketing（実観測41,188件）",
 "通知を受けた人 vs 受けなかった人":
    "銀行の電話勧誘を受けた人の申込記録",
 "+26 pt":"41,188件",
 "見かけ上「効果がありそう」":
    "申込の有無を予測する実データ",
 "同じ対象へ通知する・しないを比較":
    "電話しなかった対照群が存在しない",
 "−10 pt":"不明",
 "本当に通知すると悪化（架空例）":
    "勧誘の因果効果は求められない",
 "原因：もともとの関心 U が「通知」と「完了」の両方に影響していた":
    "介入の効果を知るにはRCT等の識別が必要。分類性能≠因果効果。",
},
33:{
 "現時点：コード・人工テストは成功。実世界の利益・人間の改善は未証明。":
 "公開の実人間53,518件で予測比較。本当の増分利益・心理改善は未証明。",
},
34:{
 "分野の評価方法を、実世界の製品・方策の検証へつなげる":
 "実人間の購買・申込記録でモデルを比較。介入の効果は今後検証。",
 "人工データでの因果推論・RCT": "UCI実観測53,518件を検証",
 "方策価値のコード検証": "4種類のモデルを同条件比較",
 "研究プロトコルと発表資料": "未見データの予測性能を測定",
},
}
NARRATION={
28:(
 "ここが因果推論の最も大事な境界です。今回は、教材のための架空のプラス・マイナスの数字ではなく、"
 "実際に公開された人間の観測データを見ます。UCI Bank Marketingには、"
 "ポルトガルの銀行が実際に電話で勧誘した約4万1千件の記録があり、"
 "定期預金に申し込んだかどうかの答えも含まれています。"
 "私たちは通話後にしか分からない通話時間を除外し、"
 "事前の顧客情報で申込結果を予測するモデルを学習できました。"
 "しかしこのデータには、同じような人に電話をかけなかった対照群がありません。"
 "したがって『この人は申込しそう』と予測できても、"
 "『電話をかければ申込率が何ポイント増える』という因果効果は分かりません。"
 "この違いを解消するにはランダム割当や、明示的な識別仮定が必要です。"
 "これこそ、What-ifと単なる予測を分ける中心的な科学的課題です。"
),
33:(
 "会社を動かすAIの制御層、独自の予測モデル、人への本当の介入効果は三本の別の研究です。"
 "既存のGPTやGrokやMuseを使う管理層は、独自重みがなくても検証できます。"
 "一方、行動モデルは共通ベンチマークと実観測データで比較することから始めます。"
 "今回、UCIの実購買・申込53,518件で、4つの統計モデルを学習・比較できました。"
 "しかし会社の増分利益や本人の反すうの軽減は、別の介入研究が必要です。"
 "モデルの公開にはデータと重みの利用権、未知データへの性能、"
 "費用、悪化指標、説明書としてのModel Cardを整えます。"
 "これは今後の段階的な道筋であり、すでに万能モデルができたという発表ではありません。"
),
34:(
 "最後に、実行できたことと、まだ証明していないことを正確に分けます。"
 "今回はUCIの実人間の購買と銀行の勧誘申込、合計53,518件を利用して、"
 "Dummy、ロジスティック回帰、Random Forest、Histogram Gradient Boostingを同じデータ分割で比較しました。"
 "銀行の後期時系列テストではRandom ForestのPR-AUCが約0.379、"
 "購買セッションのテストでは約0.369でした。異なる問題の点数を一つの順位として比較してはいけません。"
 "銀行のデータは学習時と評価時で申込率が大きく異なり、分布変化が課題になると分かりました。"
 "これらは実際に観測された人間の選択をどの程度予測できるかという評価です。"
 "Managerが会社の純増利益をもたらした、"
 "あるいは本人の反すうを減らしたという因果的な結果はまだありません。"
 "だからこそ今後は、実人間の基準データを使い、未知の研究、比較群、費用、"
 "本人が望む便益と害を同じ契約で検証していきます。"
 "皆さんなら、どの研究を最初に設計するでしょうか。"
),
}

def replace_one(slide,old,new)->int:
    found=0
    for shape in slide.shapes:
        if not getattr(shape,"has_text_frame",False):
            continue
        for para in shape.text_frame.paragraphs:
            for run in para.runs:
                if old in run.text:
                    run.text=run.text.replace(old,new)
                    found+=1
    return found

def update_manuscript():
    text=SCRIPT.read_text(encoding="utf-8")
    for idx,story in NARRATION.items():
        start=f"## {idx:02d}｜"
        match=re.search(rf"(?m)^## {idx:02d}｜.*$",text)
        if not match:
            raise RuntimeError(f"missing manuscript section {idx}")
        stop=re.search(rf"(?m)^## {idx+1:02d}｜",text[match.end():])
        end=(match.end()+stop.start()) if stop else len(text)
        original=text[match.start():end]
        if "### 読み上げ原稿" not in original:
            raise RuntimeError(f"no narration section {idx}")
        prefix=original.split("### 読み上げ原稿",1)[0]
        replacement=prefix+"### 読み上げ原稿\n\n"+story+"\n\n---\n\n"
        text=text[:match.start()]+replacement+text[end:]
    text=text.replace("ここから最後の三枚だけ", "ここから最後の四枚だけ")
    SCRIPT.write_text(text,encoding="utf-8")

def run():
    deck=Presentation(str(PPTX));oldpdf=PdfReader(str(PDF))
    if len(deck.slides)!=34 or len(oldpdf.pages)!=34:
        raise RuntimeError("Must preserve 34-slide original talk")
    for idx,fields in REPLACE.items():
        slide=deck.slides[idx-1]
        for old,new in fields.items():
            n=replace_one(slide,old,new)
            if n!=1:
                raise RuntimeError(f"expected exact replacement on slide {idx}: {old!r}, got {n}")
        if idx in NARRATION:
            tf=slide.notes_slide.notes_text_frame
            if tf is not None:
                tf.text=f"第{idx}枚｜分野の評価とManagerの実証境界\n\n{NARRATION[idx]}\n\nUCI Bank Marketing DOI 10.24432/C5K306 / UCI Online Shoppers DOI 10.24432/C5F88Q。"
    for idx in (30,31):
        frame=deck.slides[idx-1].notes_slide.notes_text_frame
        if frame is not None:
            frame.text=frame.text.replace("最後の3枚","最後の4枚").replace("最後の三枚","最後の四枚")
    deck.save(str(PPTX))
    deck=Presentation(str(PPTX))
    with TemporaryDirectory() as temp:
        temp=Path(temp)
        newpages={}
        for idx in REPLACE:
            img=render_slide(deck.slides[idx-1])
            p=temp/f"{idx}.pdf"
            img.save(str(p),quality=94,resolution=180)
            newpages[idx]=PdfReader(str(p)).pages[0]
        writer=PdfWriter()
        for idx in range(1,35):
            writer.add_page(newpages[idx] if idx in newpages else oldpdf.pages[idx-1])
            if idx in newpages:
                add_pdf_footer(writer,writer.pages[-1],idx,34,(1,1,1))
        pdf=temp/"talk.pdf"
        with pdf.open("wb") as f:writer.write(f)
        PDF.write_bytes(pdf.read_bytes())
    update_manuscript()
    assert len(Presentation(str(PPTX)).slides)==len(PdfReader(str(PDF)).pages)==34
    assert sum(s.has_notes_slide for s in Presentation(str(PPTX)).slides)==34
    print("Updated main talk slide 28 actual UCI observational data, slide33 model progress, slide34 actual 53,518 real data, 34 notes/manuscript/PDF.")

if __name__=="__main__":
    run()
