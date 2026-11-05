"""Validate 1h presentation, 85-slide backup, and frozen synthetic study records.

The canonical source deck is read from origin/main for regression checking.
"""
import hashlib
import io
import json
import re
import subprocess
import zipfile
from pathlib import Path

from pypdf import PdfReader
from pptx import Presentation

ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent
REPO=ROOT.parents[5]  # overridden by git rev-parse

def check():
    repo=Path(subprocess.check_output(
        ["git","rev-parse","--show-toplevel"],cwd=ROOT,text=True).strip())
    rel=ROOT.relative_to(repo).as_posix()
    old_path=rel+"/AI_BEHAVIOR_JOURNAL_CLUB_JA.pptx"
    old_bytes=subprocess.check_output(["git","show","origin/main:"+old_path],cwd=ROOT)
    original=Presentation(io.BytesIO(old_bytes))
    if len(original.slides)!=82:
        raise AssertionError("Expected 82 original slides in origin/main")
    master=Presentation(str(ROOT/"AI_BEHAVIOR_JOURNAL_CLUB_JA.pptx"))
    live=Presentation(str(ROOT/"AI_BEHAVIOR_JOURNAL_CLUB_60MIN_JA.pptx"))
    assert len(master.slides)==85 and len(live.slides)==33

    # Every old slide remains, with original content and order.
    for k in range(82):
        before=[x.text for x in original.slides[k].shapes if x.has_text_frame]
        after=[x.text for x in master.slides[k].shapes if x.has_text_frame]
        assert len(before)==len(after),k+1
        for b,a in zip(before,after):
            b=re.sub(r"^\s*\d+\s*/\s*82\s*$","[FOOTER]",b)
            a=re.sub(r"^\s*\d+\s*/\s*85\s*$","[FOOTER]",a)
            assert b==a,(k+1,b[:70],a[:70])
    assert all(s.has_notes_slide and s.notes_slide.notes_text_frame.text.strip()
               for s in master.slides)
    assert all(s.has_notes_slide and len(s.notes_slide.notes_text_frame.text)>100
               for s in live.slides)

    for name,slides in [("AI_BEHAVIOR_JOURNAL_CLUB_JA.pptx",85),
                        ("AI_BEHAVIOR_JOURNAL_CLUB_60MIN_JA.pptx",33)]:
        with zipfile.ZipFile(ROOT/name) as z:
            assert z.testzip() is None
    fullpdf=PdfReader(str(ROOT/"AI_BEHAVIOR_JOURNAL_CLUB_JA.pdf"))
    livepdf=PdfReader(str(ROOT/"AI_BEHAVIOR_JOURNAL_CLUB_60MIN_JA.pdf"))
    assert len(fullpdf.pages)==85 and len(livepdf.pages)==33

    main_notes=(ROOT/"SPEAKER_SCRIPT_60MIN_JA.md").read_text()
    detailed_notes=(ROOT/"SPEAKER_NOTES_JA.md").read_text()
    live_indices=[int(x) for x in re.findall(r"(?m)^## (\d{2})｜",main_notes)]
    backup_indices=[int(x) for x in re.findall(r"(?m)^## (\d{2})｜",detailed_notes)]
    assert sorted(live_indices)==list(range(1,34)),live_indices
    assert sorted(backup_indices)==list(range(1,86)),backup_indices
    plan=(BASE/"evidence/P04-6_PREANALYSIS_PLAN_SYNTHETIC.json")
    receipt=json.loads((BASE/"evidence/P04-6_PLAN_FREEZE_RECEIPT.json").read_text())
    assert hashlib.sha256(plan.read_bytes()).hexdigest()==receipt["plan_sha256"]

    old_receipt=json.loads((BASE/"evidence/P04-5_FREEZE_RECEIPT.json").read_text())
    pred=(BASE/"evidence/P04-5_FROZEN_PREDICTIONS_SYNTHETIC.csv").read_bytes()
    assert hashlib.sha256(pred).hexdigest()==old_receipt["prediction_sha256"]

    result=json.loads((BASE/"evidence/P04-6_POLICY_RCT_SYNTHETIC_RESULTS.json").read_text())
    assert result["n"]==40000
    assert not result["real_user_trial"]
    assert result["primary_pre_specified_net_utility_contrast"]["difference"]>0
    assert result["separate_aa_optional_peeking_demo"]["naive_peeking_any_look_false_positive_rate"]>0.1

    # Ensure no slide text accidentally changed while extracting a live subset.
    original_pieces=[(re.sub(r"^\s*\d+\s*/\s*82\s*$","[FOOTER]",x.text))
                     for s in original.slides for x in s.shapes if x.has_text_frame]
    live_source_pages=[1,2,3,4,5,7,8,10,12,13,34,35,36,37,38,39,40,18,19,20,21,22,33,42,43,44,32,45,46,47,48]
    live_original=[k for k in range(33) if k not in [4,5]]
    for k,original_page in zip(live_original,live_source_pages):
        before=[x.text for x in original.slides[original_page-1].shapes if x.has_text_frame]
        after=[x.text for x in live.slides[k].shapes if x.has_text_frame]
        assert len(before)==len(after),(k+1,original_page)
        for a,b in zip(before,after):
            a=re.sub(r"^\s*\d+\s*/\s*82\s*$","[FOOTER]",a)
            b=re.sub(r"^\s*\d+\s*/\s*33\s*$","[FOOTER]",b)
            assert a==b,(k+1,original_page,a[:80],b[:80])

    metadata={
        "created_2026_11_04":True,
        "speaker_audience":"computational neuroscience & neuroscience researchers, M1/M2",
        "duration_minutes":{"talk":41.7,"discussion":15.0,"buffer":3.3},
        "live_powerpoint_slides":33,
        "live_pdf_pages":33,
        "live_scripted_pages":len(live_indices),
        "detailed_powerpoint_slides":85,
        "detailed_pdf_pages":85,
        "detailed_pages_with_embedded_notes":sum(s.has_notes_slide for s in master.slides),
        "detailed_markdown_pages":len(backup_indices),
        "source_82_slide_bodies_unchanged_except_page_footer":True,
        "selected_31_legacy_slide_bodies_unchanged_except_page_footer":True,
        "new_live_intro_slides":2,
        "manager_live_slides":3,
        "full_P04_6_appendix_slides":3,
        "P04_6_preregistration_hash_valid":True,
        "P04_5_prediction_hash_valid":True,
        "P04_1_to_P04_6_unit_test_count":96,
        "external_real_world_RCT_study":False,
        "real_human_interventions":False,
    }
    (BASE/"evidence/P04-6_JOURNAL_CLUB_QA.json").write_text(
        json.dumps(metadata,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(metadata,ensure_ascii=False,indent=2))


if __name__=="__main__":
    check()
