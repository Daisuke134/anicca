#!/usr/bin/env python3
"""Regenerate editable P12-2/3/4 30-slide research deck from canonical slide notes.

Requires python-pptx; no internet, external API, copyrighted research figures,
payments or production side effects. This output is not the 34-slide live talk.
"""
from pathlib import Path
import re
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN

HERE=Path(__file__).resolve().parent
SRC=HERE/"P12-2_TO_P12-4_SLIDES_SOURCE_JA.md"
OUT=HERE/"MANAGER_PHASE12_P12-2_TO_P12-4_RESEARCH_JA.pptx"
NOTE_FILE=HERE/"SPEAKER_NOTES_P12-2_TO_P12-4_JA.md"
NAVY=RGBColor(7,20,36)
PANEL=RGBColor(23,46,66)
CYAN=RGBColor(56,221,203)
WHITE=RGBColor(243,248,254)
MUTED=RGBColor(167,193,205)
AMBER=RGBColor(255,204,120)
FONT="Hiragino Sans"

def shape(s,x,y,w,h,color,rounded=True):
    typ=MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE
    a=s.shapes.add_shape(typ,Inches(x),Inches(y),Inches(w),Inches(h))
    a.fill.solid();a.fill.fore_color.rgb=color
    a.line.fill.background()
    return a

def text(s,txt,x,y,w,h,pts=20,color=WHITE,bold=False):
    a=s.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h))
    a.text_frame.clear();a.text_frame.word_wrap=True
    p=a.text_frame.paragraphs[0]
    p.text=txt;p.font.name=FONT;p.font.size=Pt(pts)
    p.font.bold=bold;p.font.color.rgb=color
    return a

def parse():
    phase=""
    cards=[]
    for line in SRC.read_text("utf8").splitlines():
        if line.startswith("## P12-2｜"):phase="P12-2"
        elif line.startswith("## P12-3｜"):phase="P12-3"
        elif line.startswith("## P12-4｜"):phase="P12-4"
        m=re.match(r"^(\d+)\.\s+\*\*(.+?)\*\*：(.*)$",line)
        if m:
            number,title,content=m.groups()
            if "講演：" not in content:
                raise ValueError("Speaker notes absent: "+line)
            main,speaker=content.split("講演：",1)
            cards.append((int(number),phase,title,main.strip("。 "),speaker.strip()))
    if [n for n,*_ in cards]!=list(range(1,31)):
        raise AssertionError("Expected exactly 30 sequential slide IDs")
    return cards

def main():
    prs=Presentation()
    prs.slide_width=Inches(13.333)
    prs.slide_height=Inches(7.5)
    notes=[]
    for number,phase,title,summary,speaker in parse():
        s=prs.slides.add_slide(prs.slide_layouts[6])
        shape(s,0,0,13.333,7.5,NAVY,False)
        text(s,"ANICCA  /  MANAGER RESEARCH",.6,.28,6,.36,12,CYAN,True)
        text(s,phase,11.52,.29,1.2,.4,13,MUTED,True)
        text(s,title,.72,.9,11.75,.84,31,WHITE,True)
        shape(s,.8,2.03,11.74,3.9,PANEL)
        text(s,summary,1.2,2.42,10.7,1.85,26,WHITE,True)
        shape(s,1.22,4.75,.11,.55,CYAN,False)
        text(s,speaker,1.54,4.79,9.9,.74,19,MUTED)
        shape(s,.8,6.37,11.75,.06,CYAN,False)
        text(s,"SOURCE-BACKED EDUCATION  /  ALL NUMERICAL DEMOS ARE SYNTHETIC",
             .86,6.64,11.05,.3,12,AMBER,True)
        text(s,f"{number:02d} / 30",11.55,7.03,.85,.25,10,MUTED)
        full=f"{title}\n\n要点：{summary}\n\n発表ノート：{speaker}\n\n実人間に対する効果や製品本番受入は未検証。"
        s.notes_slide.notes_text_frame.text=full
        notes.append(f"## Slide {number:02d} | {title}\n\n{full}\n")
    prs.save(OUT)
    NOTE_FILE.write_text("# P12-2〜4｜30枚の日本語発表ノート\n\n"+"\n".join(notes),encoding="utf8")
    print("P12-2/3/4:",len(prs.slides),"editable slides saved",OUT)

if __name__=="__main__":
    main()
