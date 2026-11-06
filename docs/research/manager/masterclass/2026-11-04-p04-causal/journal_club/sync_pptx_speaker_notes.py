"""Make the PPTX internal speaker notes complete for all 82 slides."""
from pathlib import Path
import re
from pptx import Presentation

ROOT=Path(__file__).resolve().parent
pptx=ROOT/"AI_BEHAVIOR_JOURNAL_CLUB_JA.pptx"
notes=ROOT/"SPEAKER_NOTES_JA.md"

def run():
    text=notes.read_text(encoding="utf-8")
    pattern=r"(?ms)^## (\d{2})｜([^\n]+)\n(.*?)(?=^## |\Z)"
    sections={int(n): title+"\n\n"+body.strip() for n,title,body in re.findall(pattern,text)}
    deck=Presentation(str(pptx))
    if len(deck.slides)!=82 or set(sections)!=set(range(1,83)):
        raise AssertionError(f"Slides={len(deck.slides)} notes={len(sections)}")
    added=[]
    for k,slide in enumerate(deck.slides,1):
        if not slide.has_notes_slide:
            frame=slide.notes_slide.notes_text_frame
            if frame is not None:
                frame.text=sections[k]
                added.append(k)
    deck.save(str(pptx))
    after=Presentation(str(pptx))
    assert sum(s.has_notes_slide for s in after.slides)==82
    print("PPTX notes synchronized",len(after.slides),"added",added)

if __name__=="__main__":
    run()
