#!/usr/bin/env python3
"""Append 16 P09-research slides to the 118-slide canonical research archive.

This is actual PPTX/PDF authoring, not a mere outline. Keeps the 34-slide
journal club presentation untouched. English slides, Japanese speaker notes.
The caller supplies base 118 slide PPTX and original 118 page PDF; never append
to an already 134-slide deck. Machine-generated research numbers are evidence-
labelled, not a claim of a trained behavioral foundation model.
"""
import argparse
import math
import json
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

NAVY=RGBColor(18,42,64)
TEAL=RGBColor(0,124,120)
DARK=RGBColor(34,48,62)
MUTED=RGBColor(83,100,114)
PAPER=RGBColor(248,251,251)
LIGHT=RGBColor(230,245,242)
WHITE=RGBColor(255,255,255)
AMBER=RGBColor(204,130,40)
RED=RGBColor(181,64,67)
FONT="Aptos"
FONT_JA="Hiragino Kaku Gothic ProN"


def textbox(slide,text,x,y,w,h,size=16,bold=False,color=DARK,align=None):
    sh=slide.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h))
    tf=sh.text_frame
    tf.word_wrap=True
    tf.margin_left=Inches(.05)
    tf.margin_right=Inches(.05)
    tf.margin_top=Inches(.02)
    tf.margin_bottom=Inches(.02)
    for i,line in enumerate(text.split("\n")):
        p=tf.paragraphs[0] if i==0 else tf.add_paragraph()
        p.text=line
        p.font.name=FONT
        p.font.size=Pt(size)
        p.font.bold=bold
        p.font.color.rgb=color
        if align is not None:p.alignment=align
    return sh


def rect(slide,x,y,w,h,fill,round=False):
    sh=slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if round else MSO_SHAPE.RECTANGLE,
        Inches(x),Inches(y),Inches(w),Inches(h))
    sh.fill.solid();sh.fill.fore_color.rgb=fill
    sh.line.fill.background()
    return sh


def base_slide(prs,number,kicker,title,subtitle=None):
    slide=prs.slides.add_slide(prs.slide_layouts[0])
    slide.background.fill.solid();slide.background.fill.fore_color.rgb=WHITE
    rect(slide,0,0,13.333,.09,TEAL)
    textbox(slide,"MANAGER RESEARCH  /  PHASE 09",.67,.35,6,.28,10,True,TEAL)
    textbox(slide,f"{kicker}     {number} / 134",8.8,.35,3.9,.28,10,True,MUTED,PP_ALIGN.RIGHT)
    textbox(slide,title,.7,.83,11.95,.76,26,True,NAVY)
    if subtitle:textbox(slide,subtitle,.72,1.65,11.85,.55,13,False,MUTED)
    rect(slide,.68,6.9,11.98,.035,LIGHT)
    return slide


def bullets(slide,items,x=.9,y=2.35,step=.69,size=17):
    for i,item in enumerate(items):
        rect(slide,x,y+i*step,.10,.11,TEAL)
        textbox(slide,item,x+.3,y-.09+i*step,11.0,.56,size,False,DARK)


def fact_box(slide,kicker,value,x,y,w=3.4,h=1.10):
    rect(slide,x,y,w,h,LIGHT,True)
    textbox(slide,kicker,x+.15,y+.09,w-.3,.32,11,True,MUTED)
    textbox(slide,value,x+.15,y+.44,w-.3,.53,25,True,NAVY)


def bar_chart(slide,rows,max_value,title,unit,x=.9,y=2.33):
    textbox(slide,title,x,y-.09,10,.4,14,True,MUTED)
    for i,(label,value,color) in enumerate(rows):
        yy=y+.46+i*.62
        textbox(slide,label,x,yy,4.25,.36,13,False,DARK)
        rect(slide,x+4.35,yy+.02,5.95,.24,LIGHT)
        rect(slide,x+4.35,yy+.02,min(5.95,5.95*value/max_value),.24,color)
        textbox(slide,f"{value:.3f} {unit}",x+10.4,yy-.03,1.85,.33,12,True,NAVY)


def cite(slide,text):
    textbox(slide,text,.74,6.96,11.8,.29,9,False,MUTED)


def add_notes(slide,content):
    tf=slide.notes_slide.notes_text_frame
    tf.text="日本語発表者ノート\n"+content


def create(prs,data):
    index=len(prs.slides)
    assert index==118
    result=data
    few=result["p09_2_fewshot_study_effect_adaptation"]
    cal=result["p09_3_publication_status_shift_and_conformal"]
    forget=result["p09_4_negative_transfer_shared_scalar"]
    meme=result["p09_5_meme_distinct_task_holdout"]
    notes_log=[]
    def push(slide,notes,source):
        add_notes(slide,notes)
        cite(slide,source)
        notes_log.append((len(prs.slides),notes,source))

    s=base_slide(prs,119,"P09-1","Generalization begins with what you hold out.",
                 "Data leakage can look like impressive intelligence.")
    bullets(s,["Held-out person: can we predict a new participant?",
               "Held-out study: can we predict a new experimental design?",
               "Time-forward and domain holdout: can we transfer to the future and a new setting?",
               "For comedy: hold out BOTH audiences and joke families."])
    push(s,"P09-1: train/testランダム行分割だけでは人・研究・同じネタの変形が漏れる。予測時刻を固定し、情報利用可能性も等しくする。","Nature 2026 / Centaur Nature 2025 / Manager P09-1 course")

    s=base_slide(prs,120,"P09-1","A real-data audit: Nature's Figure 1 is not 3,356 studies.",
                 "Published aggregate effects; author's adjusted estimator is a different estimand.")
    fact_box(s,"STUDIES","70",.9,2.3)
    fact_box(s,"DIRECTED CONTRASTS","3,356",4.85,2.3)
    fact_box(s,"REVERSED PAIRS","1,678",8.8,2.3)
    textbox(s,"Unadjusted pooled r = 0.8051    |    RMSE = 11.83 percentage points",.9,4.1,11.7,.55,18,True,NAVY)
    textbox(s,"Original authors' panel B: raw r = 0.8508; adjusted estimate = 0.9151.",.9,4.85,11.7,.45,14,False,MUTED)
    push(s,"今回本当に実行したのは図表panelAの独立再解析。原著のRDS・Rコード完全再現ではない。逆対により比較行が二重になっている。著者の公式評価と混同しない。","Ashokkumar et al., Nature 2026, Source Data Fig.1")

    s=base_slide(prs,121,"P09-2","Few-shot adaptation = common knowledge + local evidence.",
                 "Partial pooling protects against noisy conclusions from one or two examples.")
    bullets(s,["Zero-shot: predict from 69 other studies, with 0 labels from the target study.",
               "Few-shot: use k = 1, 3, or 5 target-study contrasts, not the query labels.",
               "Posterior-style shrinkage: local effect = SUM(residuals) / (k + 5).",
               "More data does not justify pretending a person's mind is fully known."])
    push(s,"P09-2。階層ベイズの概念を説明。個人ではなく研究ごとの実験効果に対するFew-shot校正。事前の研究集合を共有し、k件のターゲット研究ラベルで小さな残差補正を行う。","MAML (ICML 2017); Centaur (Nature 2025); Manager actual Nature test")

    s=base_slide(prs,122,"P09-2","Held-out studies: regularized few-shot helps modestly.",
                 "Nature Fig.1, 36 eligible studies, separate query contrasts, 8 repeat splits.")
    vals=few["results"]
    labels=[("Original stored GPT-4 estimates",vals["raw"]["rmse_micro"]*100,RED),
            ("Zero-shot correction",vals["zero_shot_global"]["rmse_micro"]*100,TEAL),
            ("1-shot partial pooling",vals["partial_pool_k1"]["rmse_micro"]*100,TEAL),
            ("3-shot partial pooling",vals["partial_pool_k3"]["rmse_micro"]*100,TEAL),
            ("5-shot partial pooling",vals["partial_pool_k5"]["rmse_micro"]*100,TEAL),
            ("5-shot without pooling",vals["unpooled_k5"]["rmse_micro"]*100,AMBER)]
    bar_chart(s,labels,13.0,"Micro RMSE on held-out contrasts (lower is better)","pp")
    push(s,"実測。対象36研究（条件比較8組未満の34研究を除外）。k5部分プーリングRMSE約8.026pp、ゼロショット8.154pp、プーリングなし8.478pp。小さい改善で、個人デジタルツインの性能ではない。","Actual Python run; P09-2 Nature experiment; fixed seed 20261106")

    s=base_slide(prs,123,"P09-2","Do not hide who got worse.",
                 "36 eligible studies, paired macro evaluation and study-cluster bootstrap.")
    b=few["paired_study_uncertainty"]
    fact_box(s,"STUDIES IMPROVED",str(b["studies_improved"]),.9,2.35)
    fact_box(s,"STUDIES WORSENED",str(b["studies_worsened"]),4.85,2.35)
    fact_box(s,"EXCLUDED: TOO FEW PAIRS",str(few["excluded_small_studies"]),8.8,2.35)
    lo,hi=b["paired_study_bootstrap_95ci"]
    textbox(s,f"Study-macro RMSE gain vs zero-shot = {b['study_macro_rmse_delta_zero_minus_fewshot5']*100:.3f} pp",.9,4.12,11.8,.5,17,True,NAVY)
    textbox(s,f"Exploratory paired bootstrap 95% interval: [{lo*100:.3f}, {hi*100:.3f}] pp",.9,4.89,11.7,.42,15,False,MUTED)
    push(s,"36研究を一単位とした探索的bootstrap。19研究改善、17悪化。平均改善があっても全研究で勝つわけではない。元LLMの事前学習で研究が既知だったかは未検査。","Actual 36-study grouped experiment; 2,000 study resamples")

    s=base_slide(prs,124,"P09-3","Prediction intervals are useful only when informative.",
                 "Conformal prediction requires calibration data and assumptions.")
    bullets(s,["Measure absolute calibration residuals on held-out studies.",
               "Report both empirical coverage AND interval width.",
               "Under distribution shift, ordinary exchangeability may fail.",
               "Abstain when the validated information is insufficient."])
    textbox(s,"Interval: [ predicted effect - q, predicted effect + q ]",1.0,5.45,11.1,.65,18,True,TEAL)
    push(s,"P09-3。Conformal Predictionの分位点qは訓練から独立なcalibration集合の残差から作る。交換可能性が崩れれば有限標本被覆保証を無条件に主張できない。","Oliveira et al. JMLR 2024; Geifman & El-Yaniv 2017")

    s=base_slide(prs,125,"P09-3","90% target does not mean a useful 90% prediction.",
                 "Nature publication-status group split: published 24 train / 8 calibrate / 8 test.")
    idd=cal["in_domain"];ood=cal["unpublished_group"]
    fact_box(s,"INTERVAL HALF-WIDTH",f"{cal['q90_calibration_error']*100:.2f} pp",.9,2.32)
    fact_box(s,"IN-GROUP COVERAGE",f"{idd['empirical_pair_coverage']*100:.1f}%",4.85,2.32)
    fact_box(s,"UNPUBLISHED COVERAGE",f"{ood['empirical_pair_coverage']*100:.1f}%",8.8,2.32)
    textbox(s,f"RMSE: {idd['rmse']*100:.2f} pp (published) vs {ood['rmse']*100:.2f} pp (unpublished)",.9,4.17,11.7,.55,18,True,NAVY)
    textbox(s,"Wide intervals overcover; publication status is NOT proof of genuine cultural OOD transfer.",.9,5.0,11.65,.63,14,False,RED)
    push(s,"保留された未公表群30研究は純粋な文化OODではない。区間半幅が約24.25ppと極端に広いため、包含率98.5%は高い予測精度を意味しない。","Actual Nature figure-level study split; NOT an exchangeability guarantee")

    s=base_slide(prs,126,"P09-3","Selective prediction: measure risk AND coverage.",
                 "A simple out-of-range threshold, fit using training studies only.")
    rows=[("Published group: all",idd["rmse"]*100,AMBER),
          ("Published: retained",idd["retained_rmse"]*100,TEAL),
          ("Unpublished group: all",ood["rmse"]*100,AMBER),
          ("Unpublished: retained",ood["retained_rmse"]*100,TEAL)]
    bar_chart(s,rows,10,"RMSE on published / unpublished contrasts","pp")
    textbox(s,f"Retained: {idd['retained_fraction']*100:.1f}% (published); {ood['retained_fraction']*100:.1f}% (unpublished).",.85,5.75,11.9,.45,14,True,NAVY)
    push(s,"今回の棄権基準は訓練分布での予測効果の大きさが90%範囲にあるか。モデル不確実性の正確な検知ではない。残したデータのRMSEが下がっても、本番安全の証明ではない。","P09-3 experiment; Conformal / SelectiveNet research")

    s=base_slide(prs,127,"P09-4","Shared weights can learn one task and forget another.",
                 "Compare EWC, replay, distillation, PCGrad — do not assume a universal win.")
    bullets(s,["EWC: regularize parameters important to earlier tasks.",
               "Learning without Forgetting: preserve earlier outputs by distillation.",
               "Replay: reintroduce rights-cleared old-domain examples.",
               "PCGrad / HARPO: manage conflicting or heterogeneous updates."])
    push(s,"P09-4。EWCのFisher正則化、LwF知識蒸留、リプレイ、PCGradの干渉勾配投影、OmniSapiens2.0のHARPO。これらは先行研究であり今回EWC/PCGradの本モデルを実行した結果ではない。","Kirkpatrick 2017; Li & Hoiem 2016; Yu et al. 2020; Ong et al. 2026")

    s=base_slide(prs,128,"P09-4","Real-data negative transfer in a tiny shared calibration head.",
                 "One shared slope across Nature and MaMe-Re: an intentionally weak baseline.")
    frm=forget
    rows=[("Nature-trained slope",frm["before_learning_new_domain"]["source_rmse"]*100,TEAL),
          ("After training on meme ratings",frm["after_naive_shared_finetuning"]["source_rmse"]*100,RED),
          ("Equal-task replay-style slope",frm["after_equal_task_replay"]["source_rmse"]*100,AMBER)]
    bar_chart(s,rows,10,"Nature heldout RMSE after sequential updates","pp")
    textbox(s,"Original Nature task degrades after naive new-domain update.",.9,5.51,11.7,.55,16,True,NAVY)
    push(s,"P09-4実測。Nature側RMSE 4.54pp→8.45pp、バランス再学習後6.02pp。これは共通スカラー係数が両タスクに不足する例であり7B BFMの忘却を証明しない。ミーム側の評価指標とは直接合算しない。","Actual two-data-set scalar transfer probe; NOT a neural behavioral foundation model")

    s=base_slide(prs,129,"P09-4","Negative transfer needs its own regression suite.",
                 "Track every old task after every model revision.")
    bullets(s,["Keep untouched old task, participant and study holdouts.",
               "Report per-task loss, calibration, coverage and safety delta.",
               "A better average score can conceal serious regressions.",
               "Consent, revocation and NO_ACTION remain independent hard constraints."])
    push(s,"P09-4。旧タスク評価器と固定テストのSHAを保存。新しい学習で古い領域の負の転移を検知する。実際の事業で許諾・撤回のソフト契約の退行は他の指標で相殺しない。","ManagerBench regression contract / independent safety layer")

    s=base_slide(prs,130,"P09-5","Two real human-response datasets; two very different targets.",
                 "Prediction is not a single interchangeable number.")
    fact_box(s,"NATURE","70 studies",.9,2.3)
    fact_box(s,"MEME CONTEXTS","250",4.85,2.3)
    fact_box(s,"HUMOR PAIRS","100,000",8.8,2.3)
    textbox(s,"Nature: treatment-effect estimates.   MaMe-Re: aggregate 'funny' vote fraction.",.9,4.22,11.8,.75,17,True,NAVY)
    textbox(s,"Do NOT pool incompatible RMSEs into one leaderboard.",.9,5.2,11.5,.45,16,True,RED)
    push(s,"P09-5。Nature図表の実験効果とMaMe-Reの面白さ評価の単位が異なる。MaMe-Reは100,000組それぞれ5名評価であり100,000人ではない。漫画画像と台詞を学習入力に用いず、権利明確なメタ情報・説明文・評価値のみ。","Nature 2026; CyberAgent AI Lab MaMe-Re CC BY data")

    s=base_slide(prs,131,"P09-5","An extra model can fail to beat a simple prior.",
                 "MaMe-Re: train 160 contexts / validate 40 / test 50, 20k held-out pairs.")
    m=meme["metrics"]
    rows=[("Global human-rating mean",m["global_mean"]["rmse"],AMBER),
          ("Meme's past rating mean",m["image_historical_mean"]["rmse"],TEAL),
          ("Text+description Ridge",m["text_context_description_ridge"]["rmse"],RED)]
    bar_chart(s,rows,.20,"RMSE on unseen Japanese text contexts (lower is better)","")
    lo,hi=meme["paired_context_uncertainty"]["context_cluster_bootstrap_95ci"]
    textbox(s,f"Context-cluster 95% CI of (simple - Ridge) gain: [{lo:.5f}, {hi:.5f}]",.9,5.63,11.7,.45,13,False,MUTED)
    push(s,"P09-5実測。過去平均RMSE0.184605はRidge0.184694よりわずかによい。50文脈単位bootstrapの比較区間は0を跨ぐ。モデルが漫画画像を理解したとか個別の人の笑いを予測したと呼ばない。","Actual 100k aggregate human-rating dataset; unseen 50-context heldout")

    s=base_slide(prs,132,"P09-5","The benchmark must scale before the model does.",
                 "Reuse, validate, then learn a shared representation only where warranted.")
    bullets(s,["Baseline: fixed means, study-balanced GLM / Ridge, per-domain heads.",
               "Reusable benchmarks: Centaur / Psych-101 and HBA / OmniSapiens.",
               "Separate Task A/B/C/D/E/F evidence, rights and held-out data.",
               "Only then test a shared encoder + specialist adapters."])
    push(s,"P09-5のアーキテクチャは共有表現とタスク固有ヘッドの分離。今回実行したのは線形モデルとドメイン横断の一個のスカラー係数であり、学習済み7Bモデルではない。原著の一般化性能をManagerの成果と混同しない。","Centaur Nature 2025; HBA ICLR 2026; OmniSapiens ICML 2026")

    s=base_slide(prs,133,"PHASE 09","What we actually ran — and what remains unproven.",
                 "A reliable research archive contains null results and explicit boundaries.")
    rect(s,.85,2.22,5.65,3.6,LIGHT,True)
    rect(s,6.75,2.22,5.65,3.6,PAPER,True)
    textbox(s,"VERIFIED IN THIS PROJECT",1.2,2.55,4.9,.4,15,True,TEAL)
    textbox(s,"70-study figure-level source\n36-study few-shot evaluation\nPublished/unpublished split\nTwo-domain negative transfer\nMaMe-Re 20k heldout pairs\nOffline tests + source hashes",1.2,3.05,4.9,2.5,15,False,DARK)
    textbox(s,"NOT YET VERIFIED",7.1,2.55,4.9,.4,15,True,RED)
    textbox(s,"Original Nature RDS replay\nNew LLM/7B BFM forward pass\nHuman-level digital twins\nProspective human study\nIntervention benefit / harm\nUniversal shared weights",7.1,3.05,4.9,2.5,15,False,DARK)
    push(s,"今回の実行範囲と未実行を分ける。Nature個人RDSはCode Oceanの正規ダウンロード認証が必要。今後の本番研究では同意・権限・害測定を再検証。","Exact evidence files in repo; p09_2_5 empirical bench; Code Ocean")

    s=base_slide(prs,134,"NEXT","From Phase 9 to an honest product and external replication.",
                 "Learning next: Phase 10. Engineering cursor: preserve the existing BFM-01 / INT-02 gates.")
    bullets(s,["P10: user value, actual revenue, cost, permissions and operations.",
               "P11: network dynamics, model-based RL and justified shared-model upgrades.",
               "P12: open benchmark, external replication, long-term welfare.",
               "No new intervention or commercial model release without rights and evidence."])
    push(s,"正式ロードマップのP10-1から学習を継続。会社の単一SSOTの実装優先順に介入しない。報告・記事・発表スライドは実測と未実測を分け、原著結果と自社の計算を混同しない。","ONE Manager Roadmap P00–P12; BFM-01/INT-02; P09 appendices")

    assert len(prs.slides)==134 and len(notes_log)==16
    return notes_log


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--base",type=Path,required=True)
    parser.add_argument("--results",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--notes",type=Path,required=True)
    parser.add_argument("--source-notes",type=Path)
    args=parser.parse_args()
    old=Presentation(str(args.base))
    assert len(old.slides)==118
    before=[["|".join([sh.text for sh in slide.shapes if sh.has_text_frame]), slide.notes_slide.notes_text_frame.text if slide.has_notes_slide else ""] for slide in old.slides]
    notes=create(old,json.loads(args.results.read_text()))
    after=[["|".join([sh.text for sh in slide.shapes if sh.has_text_frame]), slide.notes_slide.notes_text_frame.text if slide.has_notes_slide else ""] for slide in [old.slides[i] for i in range(118)]]
    assert before==after,"Original slides or notes changed!"
    args.output.parent.mkdir(parents=True,exist_ok=True)
    old.save(str(args.output))
    check=Presentation(str(args.output))
    assert len(check.slides)==134
    assert all(check.slides[i].has_notes_slide for i in range(118,134))
    assert len([i for i in range(118) if check.slides[i].has_notes_slide])==len([i for i in range(118) if before[i][1]])
    if args.source_notes:
        base_notes=args.source_notes.read_text()
    else:
        base_notes=""
    parts=["\n\n# Phase 09: 16 real-data research appendix slides (119–134)\n"]
    for num,text,source in notes:
        parts.append(f"\n## Slide {num}\n{text}\n\n出典: {source}\n")
    args.notes.write_text(base_notes + "".join(parts))
    print(json.dumps({"original_slides":118,"appended":16,"total":len(check.slides),
                      "original_slide_text_and_notes_unchanged":True,
                      "new_notes_count":len(notes),
                      "pptx_bytes":args.output.stat().st_size},ensure_ascii=False))


if __name__=="__main__":
    main()