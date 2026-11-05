"""P05-3/4/5 + model-to-impact milestone update.

Input: 33-slide presentation, 89-slide research archive.
Output: 34-slide broadly accessible 60-minute talk / 93-slide archive.
All slides include Japanese notes; archives preserve prior pages except footer.
Run only on the expected source version. No automatic deployment.
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import re

from PIL import Image
from pypdf import PdfReader, PdfWriter
from pptx import Presentation

from build_p04_45_appendix import (
    base, card, text, shape_box, TEAL, BLUE, ORANGE, NAVY, MUTED,
    LIGHT2, RED, PP_ALIGN,
)
from export_p04_45_pdf import render_slide
from build_60min_journal_club import add_pdf_footer

ROOT=Path(__file__).resolve().parent
FULL_PPTX=ROOT/"AI_BEHAVIOR_JOURNAL_CLUB_JA.pptx"
FULL_PDF=ROOT/"AI_BEHAVIOR_JOURNAL_CLUB_JA.pdf"
LIVE_PPTX=ROOT/"AI_BEHAVIOR_JOURNAL_CLUB_60MIN_JA.pptx"
LIVE_PDF=ROOT/"AI_BEHAVIOR_JOURNAL_CLUB_60MIN_JA.pdf"
NOTES=ROOT/"SPEAKER_NOTES_JA.md"
SCRIPT=ROOT/"SPEAKER_SCRIPT_60MIN_JA.md"
SCHEDULE=ROOT/"RUN_OF_SHOW_60MIN_JA.md"

LESSON_NOTES=[
    ("P05-3 複数AIの権限を分ける",
     "ManagerのPlannerは、行動の候補を作りますが、実行権限は持ちません。"
     "独立した権限発行者が本人や会社の許可、操作範囲、期間、予算、撤回を確認してからExecutorを通します。"
     "この研究では既存AuthorityVerifierとStateMachineを再利用し、完全人工の署名Grantで、"
     "対象・領域・予算・署名・期限切れ・撤回の6種類の権限外操作を拒否することを確認しました。"
     "この署名は教育用で本番権限ではありません。GPTやGrokやMuseが良い案を出しても、"
     "そのテキストを許可証にしてはいけません。"),
    ("P05-4 UNKNOWNは再送を意味しない",
     "外部操作は、送信した後にタイムアウトしてしまう可能性があります。"
     "そのときAIが同じ通知や支払いを二重に送らないよう、最初に安定したeffect keyで記録し、"
     "操作があったか分からない場合はUNKNOWNに保持して、同じkeyでは再送しません。"
     "既存DurableOutboxとReconcilerを使用した実験では、人工の処理後タイムアウトと照合を再現し、"
     "二重実行0のままUNKNOWNからPRESENTへ進めました。"
     "また別の人工センサーが処理を観測しても、証拠レベルはP0で、"
     "人の苦しみや利益が改善したという因果的証拠ではありません。"),
    ("P05-5 Shadowと限定実行を区別する",
     "Shadow Modeは、新しいManager候補を現場の判断と比較しても、Manager自身は外部の変更を起こさない段階です。"
     "既存のCatalog Shadow実装には、結果の非公開保存、予算管理、入力の一致、ACK不明の停止があり、"
     "今回その41件のユニットテストを実行しました。"
     "別に、disabledのShadowにモデルやPlannerを初期化させない経路も確認しています。"
     "このソフトウェア検査に合格したからといって、実会社のShadow実績や限定本番変更が完了したわけではありません。"
     "最初の対象は自社が所有する低リスクで可逆なWebページ等に限定し、権限・費用・独立したページ確認を設計するべきです。"),
    ("Managerのモデルと実世界の価値は並行して進める",
     "これが最後の研究ロードマップです。Managerの会社運営層と、独自の行動モデルは別の進行線です。"
     "会社の運営層は、現在のGPTやGrokやMuseを候補生成に利用しながらShadowで検証できます。"
     "本番の可逆な一操作は、正式な権限・停止条件・独立確認が揃って初めて実施します。"
     "モデルの重みについては、既存Qwen3の一部評価と、少数データの限定LoRA計画がありますが、"
     "実際の訓練完了とオープンウェイト公開はまだ確認できません。"
     "研究用の一番小さいアダプタと、人間行動に一般化するFoundation Modelは別です。"
     "また反すうを減らしたいなら、本人の希望と同意のもとでPTQや生活機能を観測し、"
     "比較群と害を評価する必要があります。これらの順序が、世界に実際の価値を出す最短の現実的な道筋だと考えます。"),
]

MILESTONE_TITLE="Managerはいつ動く？ 製品・モデル・人への効果の3本線"
MILESTONE_SCRIPT=(
    "ここで、今後の時系列を具体的に示します。大事なのは、会社を動かす基盤と、"
    "行動を予測する独自モデルと、人への本当の効果が、それぞれ別の進行線であることです。"
    "第一に会社運営です。現在のGPTやGrokやMuseを使いながら、まず1つの事業で実行しないShadowを試します。"
    "そして許可・費用・停止・独立確認が整った場合にだけ、自社の低リスクで元へ戻せる操作を1件試します。"
    "次にモデルの学習です。今あるQwenの評価は一部しか終わっていません。"
    "少数のHelpSteerデータを使う私有LoRAの計画もありますが、行動Foundation Modelの訓練完了ではありません。"
    "適切な行動データと未知研究でのベンチマークを整え、訓練済みアダプタを独立評価してから、"
    "公開可能な重みはModel Cardと一緒に公開します。"
    "第三に人間への影響です。反すうの減少や生活の改善は、本人の希望・同意と実際の尺度や比較を用いて"
    "測定する研究が必要です。期限は目標にできますが、結果と安全性を保証するものではありません。"
    "ここは未来の予定であり、実績を先取りして語らないことが大切です。"
)
BEGINNER_TITLE="人間行動AIを『状態・観測・選択・結果』で理解する"
BEGINNER_SUBTITLE="脳科学でも、ビジネスでも、生活でも使える4つの基本的な見方"
BEGINNER_NOTE=(
    "ここで、今日初めてこの分野を聞く人のために、四つの言葉を整理します。"
    "まず潜在状態です。意欲や疲労、興味など、外からそのまま読めないものがあります。"
    "次に観測です。実際に何を選んだか、どんな言葉を話したか、何に回答したかです。"
    "三つ目は方策で、観測から何を選ぶか、AIならどんな提案や介入を選ぶかです。"
    "四つ目は結果です。その行動の後に現実に何が起きたか、どの程度良くなったかを測ります。"
    "そして『次に何が起きるかを予測できた』ことと、"
    "『その介入が原因で変化した』ことは違います。"
    "今日の残りの研究では、どの対象をどう予測し、どう検証したかをこの枠で読み解きます。"
)


def update_footer(slide,number,total):
    for shape in slide.shapes:
        if shape.has_text_frame and re.fullmatch(r"\s*\d+\s*/\s*\d+\s*",shape.text):
            for p in shape.text_frame.paragraphs:
                for run in p.runs:
                    run.text=f"{number} / {total}"
            break


def make_full():
    prs=Presentation(str(FULL_PPTX))
    original_pdf=PdfReader(str(FULL_PDF))
    if len(prs.slides)!=89 or len(original_pdf.pages)!=89:
        raise RuntimeError("Expected original 89-slide archive; refusing duplicate mutation")
    s=base(prs,"APPENDIX / P05-3 AUTHORITY",
           "Plannerは『許可する人』ではない","複数AIの提案→独立した権限→限定Executor",
           "Existing Manager Core / AuthorityVerifier + Grant / offline only")
    for i,(h,b,c) in enumerate([
      ("Planner","行動候補・What-if\n実行権限なし",BLUE),
      ("Authority","issuer・範囲・期限\n予算・失効",ORANGE),
      ("Executor","署名許可と操作を照合\n重複防止",TEAL),
    ]):
        card(s,.66+4.22*i,2.47,3.96,2.40,h,b,c,17)
    shape_box(s,.86,5.35,11.56,.95,LIGHT2)
    text(s,1.08,5.52,11.17,.56,
        "6つの権限外操作を拒否。fixtureの署名は本番認証・本人の同意ではない。",
        16.5,TEAL,True,PP_ALIGN.CENTER)

    s=base(prs,"APPENDIX / P05-4 RECONCILIATION",
           "タイムアウト＝失敗とは限らない",
           "送信後のUNKNOWNは再送せず、元の操作キーで独立に照合する",
           "Existing DurableOutbox + Reconciler + OfflineFixtureSensor")
    card(s,.72,2.38,5.66,2.42,
         "間違った復旧",
         "タイムアウト → もう1回送る\n同じ操作が2回起きる危険",RED,17)
    card(s,6.64,2.38,5.86,2.42,
         "今回動いた安全な経路",
         "UNKNOWN → readback → PRESENT\n同じkeyのsendは1回",TEAL,17)
    shape_box(s,.87,5.22,11.60,1.03,LIGHT2)
    text(s,1.04,5.39,11.22,.65,
         "独立した人工センサーの確認もP0。人への因果効果は別に測る。",
         16.2,TEAL,True,PP_ALIGN.CENTER)

    s=base(prs,"APPENDIX / P05-5 SHADOW",
           "Shadowで比べてから、実行範囲を一つずつ広げる",
           "現場の成果とAIの提案を分ける。稼働率より誤実行を防ぐ。",
           "Existing manager_core.owned_provider_shadow; 41 tests")
    for i,(h,b,c) in enumerate([
      ("S0 テスト","型・権限・重複\nオフラインで成功",TEAL),
      ("S1 Shadow","候補を同条件で比較\n本番writeなし",BLUE),
      ("S2 限定Live","自社所有・可逆な1操作\n正規許可と独立確認",ORANGE),
    ]):
        card(s,.72+i*4.21,2.46,3.94,2.36,h,b,c,16.5)
    shape_box(s,.84,5.27,11.70,1.12,LIGHT2)
    text(s,1.03,5.45,11.30,.65,
         "今回はS0と既存Shadowテストまで。実業務S1・本番S2は未実施。",
         16.1,ORANGE,True,PP_ALIGN.CENTER)

    s=base(prs,"APPENDIX / MODEL × COMPANY × IMPACT",
           "モデル公開と、会社運営と、人の改善は別の進行線",
           "独自重みの完成を待たず、既存AIを使うManagerの制御層から検証する",
           "Milestones are conditional proposals, not achieved empirical impact")
    for i,(h,b,c) in enumerate([
      ("会社のEngine","Shadow → 1つの限定操作\n→ 比較して範囲拡大",TEAL),
      ("Behavior Model","Qwen/LoRA研究 → 権利と\n独立評価 → 公開可能な重み",BLUE),
      ("実際の行動変容","本人の希望と同意 → 尺度\n→ 比較実験 → 長期再現",ORANGE),
    ]):
        card(s,.70+i*4.22,2.34,3.93,2.58,h,b,c,15.5)
    shape_box(s,.83,5.23,11.72,1.20,LIGHT2)
    text(s,1.04,5.42,11.18,.85,
         "本当の価値＝実際に使われる製品・費用込み利益・本人の便益と害。\n未実証の数字は実績と呼ばない。",
         15.7,TEAL,True,PP_ALIGN.CENTER)

    assert len(prs.slides)==93
    for k,slide in enumerate(prs.slides,1):
        update_footer(slide,k,93)
    for i,(heading,words) in enumerate(LESSON_NOTES):
        tf=prs.slides[89+i].notes_slide.notes_text_frame
        if tf is not None:tf.text=f"第{90+i}枚｜{heading}\n\n{words}\n\n参照：P05-{3+i}_JA.md／MANAGER_MODEL_COMPANY_IMPACT_MILESTONES_JA.md。"
    prs.save(str(FULL_PPTX))

    images=[render_slide(prs.slides[k]) for k in range(89,93)]
    with TemporaryDirectory() as td:
        f=Path(td)/"extra.pdf"
        images[0].save(str(f), save_all=True, append_images=images[1:],
                       resolution=180,quality=95)
        extra=PdfReader(str(f))
        writer=PdfWriter()
        for k in range(1,94):
            page=original_pdf.pages[k-1] if k<=89 else extra.pages[k-90]
            writer.add_page(page)
            if k<=89:add_pdf_footer(writer,writer.pages[-1],k,93,(1,1,1))
        output=Path(td)/"full-93.pdf"
        with output.open("wb") as fp:writer.write(fp)
        FULL_PDF.write_bytes(output.read_bytes())
    assert len(PdfReader(str(FULL_PDF)).pages)==93

    previous=NOTES.read_text(encoding="utf-8").replace("全89枚の","全93枚の")
    suffix="\n\n---\n\n## P05-3〜5・モデル/会社/行動変容マイルストーン（90〜93）\n\n"
    suffix+="\n\n".join(
      f"## {90+k}｜{title}\n\n{words}\n"
      for k,(title,words) in enumerate(LESSON_NOTES))
    if "マイルストーン（90〜93）" not in previous:
        NOTES.write_text(previous+suffix+"\n",encoding="utf-8")
    print("Full research slides",len(prs.slides),"PDF",len(PdfReader(str(FULL_PDF)).pages))


def make_live():
    prs=Presentation(str(LIVE_PPTX))
    existing_pdf=PdfReader(str(LIVE_PDF))
    if len(prs.slides)!=33 or len(existing_pdf.pages)!=33:
        raise RuntimeError("Expected 33-slide talk; refuse unreviewed build")

    # Remove neuroscience-specific framing, preserve four general elements.
    s6=prs.slides[5]
    swaps={
        "FIELD PRIMER / COMPUTATIONAL NEUROSCIENCE":"FIELD PRIMER / BEHAVIOR & AI FOR EVERYONE",
        "神経科学の言葉に置き換えると、何をモデル化するのか":BEGINNER_TITLE,
        "内部状態・観測・行動・方策・結果を区別すると、分野全体が見えてくる":BEGINNER_SUBTITLE,
        "ただし、脳回路の機序を説明することと、社会・消費・対人行動を予測することは別の検証課題。":
          "行動予測と、介入による因果効果は異なる。証拠がないときは何もしないことも選択肢。",
    }
    replaced=0
    for shape in s6.shapes:
        if shape.has_text_frame:
            for p in shape.text_frame.paragraphs:
                for r in p.runs:
                    new=r.text
                    for x,y in swaps.items():
                        new=new.replace(x,y)
                    if new!=r.text:
                        r.text=new
                        replaced+=1
    if replaced<2:
        raise RuntimeError("Expected to generalize slide 6 labels")
    tf=s6.notes_slide.notes_text_frame
    if tf is not None:
        tf.text="第06枚｜基本概念：状態・観測・選択・結果　目安1.3分\n\n"+BEGINNER_NOTE

    s=base(prs,"MANAGER / THREE PARALLEL TRACKS",
           MILESTONE_TITLE,
           "独自のモデルの重みを待たず、今あるAIと安全な実行基盤で成果を検証する",
           "Conditional roadmap — P05/P06/P07/P08 and model release gates")
    for i,(h,b,c) in enumerate([
      ("会社のEngine","最初はShadow\n→ 1つの可逆な実務操作",TEAL),
      ("モデルの重み","権利とHoldout評価\n→ 実LoRA → Open weight",BLUE),
      ("人への効果","本人の希望と同意\n→ 行動・反すうの比較測定",ORANGE),
    ]):
        card(s,.68+4.22*i,2.42,3.98,2.55,h,b,c,16.2)
    shape_box(s,.84,5.33,11.73,1.03,LIGHT2)
    text(s,1.04,5.52,11.28,.62,
         "現時点：コード・人工テストは成功。実世界の利益・人間の改善は未証明。",
         15.9,TEAL,True,PP_ALIGN.CENTER)

    # Current last slide is the research talk's conclusion. The rollout
    # milestone belongs BEFORE that conclusion, not after the Q&A invitation.
    ids=prs.slides._sldIdLst
    current=list(ids)
    last_old=current[32]
    new_id=current[33]
    ids.remove(new_id)
    ids.insert(32,new_id)
    assert prs.slides[32]._element is s._element
    assert prs.slides[33]._element is not s._element

    for i,slide in enumerate(prs.slides,1):
        update_footer(slide,i,34)
    milestone=prs.slides[32].notes_slide.notes_text_frame
    if milestone is not None:
        milestone.text=("第33枚｜モデル・会社・人への影響の並行ロードマップ"
                        "　目安1.3分\n\n"+MILESTONE_SCRIPT)
    ending=prs.slides[33].notes_slide.notes_text_frame
    if ending is not None:
        ending.text=ending.text.replace("第33枚", "第34枚",1)
    prs.save(str(LIVE_PPTX))
    assert len(Presentation(str(LIVE_PPTX)).slides)==34

    new_page=render_slide(prs.slides[32])
    changed_six=render_slide(prs.slides[5])
    with TemporaryDirectory() as td:
        src=Path(td)/"replacement.pdf"
        changed_six.save(str(src),save_all=True,append_images=[new_page],
                         resolution=180,quality=95)
        two=PdfReader(str(src))
        writer=PdfWriter()
        for k in range(1,35):
            if k==6:page=two.pages[0]
            elif k==33:page=two.pages[1]
            elif k==34:page=existing_pdf.pages[32]
            else:page=existing_pdf.pages[k-1]
            writer.add_page(page)
            add_pdf_footer(writer,writer.pages[-1],k,34,(1,1,1))
        result=Path(td)/"live-34.pdf"
        with result.open("wb") as fp:writer.write(fp)
        LIVE_PDF.write_bytes(result.read_bytes())
    assert len(PdfReader(str(LIVE_PDF)).pages)==34

    script=SCRIPT.read_text(encoding="utf-8")
    if "## 33｜"+MILESTONE_TITLE in script:
        raise RuntimeError("Already updated speaker script")
    # Replace slide6's heading and entire speaking body, leaving next pages intact.
    pat=r"(?ms)^## 06｜.*?(?=^## 07｜)"
    match=re.search(pat,script)
    if not match:raise AssertionError("Slide 6 script not found")
    replacement=(
       f"## 06｜{BEGINNER_TITLE}\n\n"
       "**章：** 入門：何をシミュレーションするのか　"
       "**目安：** 1.3分　**元資料：** 分かりやすい用語説明の新規スライド\n\n"
       "### 読み上げ原稿\n\n"+BEGINNER_NOTE+"\n\n---\n\n")
    script=re.sub(pat,lambda _:replacement,script,count=1)

    pat=r"(?ms)^## 33｜.*?\Z"
    end=re.search(pat,script)
    if not end:raise AssertionError("Last script not found")
    old_final=end.group(0).replace("## 33｜","## 34｜",1)
    milestone_text=(
        f"## 33｜{MILESTONE_TITLE}\n\n"
        "**章：** Manager：現実のモデルと実行のロードマップ　"
        "**目安：** 1.3分　**元資料：** 新規追加（P05-3〜5／研究展開）\n\n"
        "### 読み上げ原稿\n\n"+MILESTONE_SCRIPT+"\n\n---\n\n")
    script=script[:end.start()]+milestone_text+old_final
    script=script.replace("全33枚","全34枚").replace("本編33枚","本編34枚")
    script=script.replace("約41.7分","約43.0分")
    SCRIPT.write_text(script,encoding="utf-8")

    rs=SCHEDULE.read_text(encoding="utf-8")
    rs=rs.replace("発表用33枚","発表用34枚").replace("発表版33枚","発表版34枚")
    rs=rs.replace("13:00–13:42本編（計41.7分）、13:42–13:57質疑15分、13:57–14:00移動・余裕約3分",
                  "13:00–13:43本編（計43.0分）、13:43–13:58質疑15分、13:58–14:00移動・余裕約2分")
    rs=rs.replace("31–33 | 5.0分","31–34 | 6.3分")
    rs=rs.replace("What-if×Executorの研究仮説、製品・流通・心理の実測証拠、公開と検証",
                  "What-if×Executorの仮説、会社/モデル/人への実測、段階的な導入と公開")
    rs=rs.replace("| 6 | 新規（神経科学ブリッジ） | 1.3 | 神経科学の言葉に置き換えると、何をモデル化するのか |",
                  f"| 6 | 新規（共通の基本概念） | 1.3 | {BEGINNER_TITLE} |")
    # Insert a one-row roadmap before previously last slide row, renumber old row.
    lines=rs.splitlines()
    for k,line in enumerate(lines):
        if line.startswith("| 33 | 48 |"):
            old=line.replace("| 33 |","| 34 |",1)
            lines[k]="| 33 | 新規（運用・モデル・行動変容） | 1.3 | "+MILESTONE_TITLE+" |"
            lines.insert(k+1,old)
            break
    else:
        raise AssertionError("Source table 33 not found")
    rs="\n".join(lines)+"\n"
    rs=rs.replace("31–33（Managerと議論）","31–34（Managerと議論）")
    rs=rs.replace("31–33（Manager","31–34（Manager")
    rs+="\n**2026-11-04 P05-3〜P05-5追補**：本編は34枚・43.0分、質疑15分、バッファ2.0分に再調整。6枚目を一般読者向け用語説明に、33枚目にモデル・会社・行動変容の3本並行ロードマップを追加し、旧33枚目の結論は34枚目へ移動。発表者用の全文は`SPEAKER_SCRIPT_60MIN_JA.md`に揃えた。会社/行動変容の実績は未証明と明示。\n"
    SCHEDULE.write_text(rs,encoding="utf-8")
    print("Live presentation",len(prs.slides),"PDF",len(PdfReader(str(LIVE_PDF)).pages),"target talk minutes 43.0")


if __name__=="__main__":
    make_full()
    make_live()
