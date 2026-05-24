#!/usr/bin/env python3
"""Template C JA (10-slide carousel, mantra.app clone) — anicca-mantra-slideshow-ja."""
import os, sys, json, datetime, requests, concurrent.futures
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

if len(sys.argv) < 2:
    print("usage: build-slideshow.py <run_dir>", file=sys.stderr); sys.exit(1)
RUN_DIR = Path(sys.argv[1])
SKILL_DIR = Path(__file__).resolve().parent.parent
W = H = 1080

BG_PROMPTS = [
    "open sky with single yellow wildflower in bottom-right corner, hazy blue, film grain, square 1:1, no text",
    "sunlit ocean wave breaking on shore, soft morning light, square 1:1, no text",
    "new moon over silver clouds, ethereal navy, square 1:1, no text",
    "single dewdrop on emerald leaf, macro soft focus, square 1:1, no text",
    "cream linen flat lay with pale dried wildflower, top-down soft light, square 1:1, no text",
    "sage green soft fog on rolling hills, dawn atmosphere, square 1:1, no text",
    "pale pink dawn sky with one bare branch silhouette, minimal, square 1:1, no text",
    "single red dewy rose petal macro, blurred background, square 1:1, no text",
    "calm shore at golden hour with pale sand and one driftwood, square 1:1, no text",
    "pale dawn sky with thin cloud strands and one yellow flower in bottom corner, square 1:1, no text",
]

CTA_SLIDE = {"id":"cta-ja","text":"Anicca を入れる。iOS 無料。","source":"Anicca brand CTA","source_url":"https://aniccaai.com"}

def pick(run_dir):
    pool = json.loads((SKILL_DIR / "data" / "quotes.json").read_text())
    shorts = [q for q in pool["ja"] if len(q["text"].rstrip("。")) <= 16]
    doy = int(datetime.datetime.now().strftime("%j"))
    start = (doy - 1) % len(shorts)
    picks = [shorts[(start + i) % len(shorts)] for i in range(9)] + [CTA_SLIDE]
    (run_dir / "picks.json").write_text(json.dumps({"picks": picks, "prompts": BG_PROMPTS}, ensure_ascii=False, indent=2))
    return picks

def gen_bg(i, prompt, run_dir):
    r = requests.post("https://fal.run/fal-ai/flux/dev",
        headers={"Authorization": f"Key {os.environ['FAL_API_KEY']}"},
        json={"prompt":prompt + ", soft cinematic editorial photography","image_size":{"width":W,"height":H},"num_inference_steps":28,"guidance_scale":3.5,"num_images":1,"enable_safety_checker":True},
        timeout=180)
    r.raise_for_status()
    img = requests.get(r.json()["images"][0]["url"], timeout=60).content
    out = run_dir / "images" / f"bg_{i:02}.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(img)
    return out

def fal_backgrounds(run_dir):
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
        list(ex.map(lambda i: gen_bg(i+1, BG_PROMPTS[i], run_dir), range(10)))

def wrap_by_width(text, font, max_w):
    out, cur = [], ""
    for c in text:
        if font.getbbox(cur + c)[2] > max_w and cur:
            for sep in ['。','、','し','て','で','に','は','を','の']:
                idx = cur.rfind(sep)
                if idx >= len(cur)//2:
                    out.append(cur[:idx+1]); cur = cur[idx+1:] + c; break
            else:
                out.append(cur); cur = c
        else:
            cur += c
    if cur: out.append(cur)
    return out

def compose_slide(run_dir, i, p):
    bg = Image.open(run_dir / "images" / f"bg_{i:02}.jpg").convert("RGB")
    ratio = max(W/bg.width, H/bg.height)
    bg = bg.resize((int(bg.width*ratio), int(bg.height*ratio)), Image.LANCZOS)
    bg = bg.crop(((bg.width-W)//2, (bg.height-H)//2, (bg.width-W)//2+W, (bg.height-H)//2+H))
    bg = ImageEnhance.Brightness(bg).enhance(0.82)
    canvas = bg.convert("RGBA")

    overlay = Image.new("RGBA",(W,H),(0,0,0,0))
    od = ImageDraw.Draw(overlay)
    for y in range(H):
        if 80<=y<=480: a=85
        elif y<80: a=int(85*y/80)
        elif y<560: a=int(85*(560-y)/80)
        else: a=0
        od.line([(0,y),(W,y)], fill=(20,15,20,a))
    canvas = Image.alpha_composite(canvas, overlay)
    draw = ImageDraw.Draw(canvas)

    body_font = ImageFont.truetype(str(SKILL_DIR / "fonts" / "NotoSansJP-Regular.ttf"), 64)
    wmark_brand_font = ImageFont.truetype(str(SKILL_DIR / "fonts" / "DMSans-Regular.ttf"), 32)
    wmark_handle_font = ImageFont.truetype(str(SKILL_DIR / "fonts" / "DMSans-Regular.ttf"), 16)
    cream = (245, 237, 224, 255)

    lines = wrap_by_width(p["text"], body_font, 940)
    LH = 92
    y = 160
    for ln in lines:
        draw.text((72, y), ln, font=body_font, fill=cream)
        y += LH

    cx, cy, cr = 760, 970, 32
    draw.ellipse([cx-cr,cy-cr,cx+cr,cy+cr], fill=(245,237,224,255))
    draw.ellipse([cx-cr+10,cy-cr+10,cx+cr-10,cy+cr-10], fill=(255,255,255,200))
    draw.line([(cx+cr+12,cy-cr+4),(cx+cr+12,cy+cr-4)], fill=(245,237,224,200), width=2)
    draw.text((cx+cr+24, cy-cr+2), "Anicca", font=wmark_brand_font, fill=cream)
    draw.text((cx+cr+24, cy+8), "@aniccaai", font=wmark_handle_font, fill=(245,237,224,200))

    out = run_dir / "slides" / f"slide_{i:02}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(out, "PNG", optimize=True)

def main():
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    picks = pick(RUN_DIR)
    fal_backgrounds(RUN_DIR)
    for i, p in enumerate(picks, 1):
        compose_slide(RUN_DIR, i, p)
    (RUN_DIR / "first_line.txt").write_text(picks[0]["text"], encoding="utf-8")
    print(f"build OK: 10 slides, first='{picks[0]['text']}'")

if __name__ == "__main__":
    main()
