"""Generate an 82-page PDF: preserve original 74-page PDF; render 8 added PPTX slides.

Existing 74 pages are left graphically unchanged apart from an updated
page-count footer. Extra pages are rasterized from the new slide shapes
with a Mac Japanese font because LibreOffice is unavailable.
"""
from __future__ import annotations

import glob
import re
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, JpegImagePlugin
from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    ArrayObject, DecodedStreamObject, DictionaryObject, NameObject, NumberObject,
)
from pptx import Presentation
from pptx.enum.dml import MSO_FILL

ROOT=Path(__file__).resolve().parent
PDF=ROOT/"AI_BEHAVIOR_JOURNAL_CLUB_JA.pdf"
PPTX=ROOT/"AI_BEHAVIOR_JOURNAL_CLUB_JA.pptx"
DPI=180
W,H=round(13.3333333333*DPI),round(7.5*DPI)
FONT_REGULAR=glob.glob("/System/Library/Fonts/*W3.ttc")
FONT_BOLD=glob.glob("/System/Library/Fonts/*W6.ttc")
if not FONT_REGULAR:
    raise RuntimeError("Japanese font unavailable")


def rgb(color, default=(23,43,62)):
    try:
        value=color.rgb
        return (value[0],value[1],value[2]) if value is not None else default
    except Exception:
        return default


def point(emu):
    return int(round(emu / 914400 * DPI))


def get_font(size, bold):
    file=(FONT_BOLD[0] if bold and FONT_BOLD else FONT_REGULAR[0])
    return ImageFont.truetype(file, max(12, int(round(size * DPI/72))))


def wrap(draw, value, font, max_width):
    lines=[]
    for original in value.split("\n"):
        if not original:
            lines.append("")
            continue
        buf=""
        for char in original:
            maybe=buf+char
            if buf and draw.textbbox((0,0),maybe,font=font)[2] > max_width:
                lines.append(buf)
                buf=char
            else:
                buf=maybe
        if buf:
            lines.append(buf)
    return lines


def render_slide(slide):
    im=Image.new("RGB",(W,H),(255,255,255))
    draw=ImageDraw.Draw(im)
    for shape in slide.shapes:
        x=point(shape.left);y=point(shape.top)
        w=point(shape.width);h=point(shape.height)
        if w<1 or h<1:
            continue
        if shape.shape_type==1:
            try:
                color=rgb(shape.fill.fore_color)
            except Exception:
                color=None
            if color is not None:
                if h < 10 or w < 10:
                    draw.rectangle([x,y,x+w,y+h],fill=color)
                else:
                    draw.rounded_rectangle([x,y,x+w,y+h],
                                           radius=int(min(20,h*.18)),fill=color)
        if not getattr(shape,"has_text_frame",False) or not shape.text.strip():
            continue
        p=shape.text_frame.paragraphs[0]
        run=p.runs[0] if p.runs else None
        size=run.font.size.pt if run and run.font.size else 16
        color=rgb(run.font.color) if run else (23,43,62)
        bold=bool(run.font.bold) if run else False
        fontsize=size
        # Shrink only when the text cannot otherwise fit the shape bounds.
        for trial in range(6):
            font=get_font(fontsize,bold)
            lines=wrap(draw,shape.text,font,max(6,w-5))
            line_height=round(font.size*1.25)
            if len(lines)*line_height <= h-1 or fontsize<=8.5:
                break
            fontsize*=.90
        total=len(lines)*line_height
        line_y=y+max(0,(h-total)//2)
        for line in lines:
            if p.alignment is not None and str(p.alignment) == "CENTER (2)":
                tw=draw.textbbox((0,0),line,font=font)[2]
                line_x=x+max(0,(w-tw)//2)
            else:
                line_x=x+max(1,int(.02*DPI))
            draw.text((line_x,line_y),line,font=font,fill=color)
            line_y+=line_height
    return im


def add_footer_overlay(writer, page, number):
    # Footer coordinates in PDF points, origin is bottom-left.
    resources=page["/Resources"].get_object()
    fonts=resources.get(NameObject("/Font"))
    if fonts is None:
        fonts=DictionaryObject()
        resources[NameObject("/Font")]=fonts
    else:
        fonts=fonts.get_object()
    font=DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
        NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
    })
    font_ref=writer._add_object(font)
    fonts[NameObject("/ManagerFoot")]=font_ref
    # Whiten the original 74-page footer in the same physical location.
    command=(f"q 1 1 1 rg 855 8 97 23 re f Q\n"
             f"BT /ManagerFoot 8 Tf 0.33 0.42 0.49 rg "
             f"866 15 Td ({number} / 82) Tj ET\n")
    stream=DecodedStreamObject()
    stream.set_data(command.encode("ascii"))
    ref=writer._add_object(stream)
    original=page.get(NameObject("/Contents"))
    if original is None:
        page[NameObject("/Contents")]=ref
    elif isinstance(original,ArrayObject):
        original.append(ref)
    else:
        page[NameObject("/Contents")]=ArrayObject([original,ref])


def run():
    deck=Presentation(str(PPTX))
    if len(deck.slides)!=82:
        raise RuntimeError("PPTX should be 82 slides")
    source=PdfReader(str(PDF))
    if len(source.pages)==82:
        print("PDF already 82 pages - refusing append twice")
        return
    if len(source.pages)!=74:
        raise RuntimeError(f"Expected original 74-page PDF, got {len(source.pages)}")
    images=[render_slide(deck.slides[i]) for i in range(74,82)]
    with tempfile.TemporaryDirectory() as tmp:
        temp=Path(tmp)
        appendix=temp/"p04_45_appendix.pdf"
        images[0].save(str(appendix),save_all=True,append_images=images[1:],
                       resolution=DPI,quality=95)
        new_pdf=PdfReader(str(appendix))
        if len(new_pdf.pages)!=8:
            raise AssertionError("Appendix page count")
        writer=PdfWriter()
        for i,p in enumerate(source.pages,1):
            writer.add_page(p)
            add_footer_overlay(writer,writer.pages[-1],i)
        for p in new_pdf.pages:
            writer.add_page(p)
        target=temp/"82pages.pdf"
        with target.open("wb") as f:
            writer.write(f)
        target.replace(PDF)
    final=PdfReader(str(PDF))
    if len(final.pages)!=82:
        raise AssertionError("Final PDF page count")
    print("PPTX",len(deck.slides),"PDF",len(final.pages),
          "82nd page",tuple(float(x) for x in final.pages[-1].mediabox))


if __name__=="__main__":
    run()
