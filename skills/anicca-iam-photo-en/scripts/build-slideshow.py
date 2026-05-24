#!/usr/bin/env python3
"""Template A (photo+serif 5-line) — anicca-iam-photo-en.
Usage: build-slideshow.py <run_dir>
Produces:  run_dir/images/bg.jpg + run_dir/slides/slide_01.png + run_dir/picks.json
"""
import os, sys, json, datetime, requests
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

if len(sys.argv) < 2:
    print("usage: build-slideshow.py <run_dir>", file=sys.stderr); sys.exit(1)
RUN_DIR = Path(sys.argv[1])
SKILL_DIR = Path(__file__).resolve().parent.parent
LANG = "en"
TEMPLATE = "A"
HEADER_EN = "Repeat with me:"
HEADER_JA = "繰り返してね。"
W, H = 1080, 1350

# Backgrounds rotation by day-of-year (extend later)
BG_PROMPTS = [
    "soft pastel tulips and white roses on crumpled blush silk fabric, dreamy soft golden hour light, muted dusty pink and cream palette, cinematic film grain, 4:5 portrait, no text, no logo, no watermark, romantic editorial photography",
    "close-up macro of dew on a single pale rose petal, soft morning light, beige tones, 4:5 portrait, romantic editorial",
    "flat lay of dried wildflowers on linen, neutral beige, top-down, soft window light, 4:5 portrait, no text",
    "pale cherry blossom branches against cream silk, soft pastel pink, dreamy mood, 4:5 portrait, no text",
    "white peonies on rumpled silk, golden hour, muted blush palette, 4:5 portrait, editorial",
    "sunlit eucalyptus leaves on cream linen, soft botanical, 4:5 portrait, editorial",
    "single dried rose on aged paper, warm muted tones, 4:5 portrait, no text",
]

def pick_quotes(run_dir: Path):
    """Pick 5 EN affirmations by day-of-year."""
    pool = json.loads((SKILL_DIR / "data" / "quotes.json").read_text())
    doy = int(datetime.datetime.now().strftime("%j"))
    start = (doy - 1) % 100
    items = [pool[LANG][(start + i) % 100] for i in range(5)]
    (run_dir / "picks.json").write_text(json.dumps(items, ensure_ascii=False, indent=2))
    return items

def fal_background(run_dir: Path):
    """Pool-first rotation (Dais 2026-05-14): use SKILL_DIR/pool/bg_*.jpg by day-of-year,
    only call fal.ai if pool is empty (fallback). Pool refilled by monthly cron."""
    import shutil, random
    pool_dir = SKILL_DIR / 'pool'
    pool_dir.mkdir(exist_ok=True)
    pool_imgs = sorted(pool_dir.glob('bg_*.jpg'))
    out = run_dir / 'images' / 'bg.jpg'
    out.parent.mkdir(parents=True, exist_ok=True)
    if pool_imgs:
        doy = int(datetime.datetime.now().strftime('%j'))
        chosen = pool_imgs[doy % len(pool_imgs)]
        shutil.copy(chosen, out)
        print(f'[pool] using {chosen.name} (pool size={len(pool_imgs)})')
        return out
    # Fallback: generate fresh via fal.ai
    print(f'[pool] empty, generating fresh via fal.ai...')
    doy = int(datetime.datetime.now().strftime('%j'))
    prompt = BG_PROMPTS[(doy - 1) % len(BG_PROMPTS)]
    headers = {'Authorization': f"Key {os.environ['FAL_API_KEY']}"}
    r = requests.post('https://fal.run/fal-ai/flux/dev', headers=headers,
        json={'prompt': prompt, 'image_size':{'width':W,'height':H},'num_inference_steps':28,'guidance_scale':3.5,'num_images':1,'enable_safety_checker':True},
        timeout=180)
    r.raise_for_status()
    url = r.json()['images'][0]['url']
    img = requests.get(url, timeout=60).content
    out.write_bytes(img)
    # Save into pool so next time we don't pay fal again
    next_idx = len(pool_imgs) + 1
    shutil.copy(out, pool_dir / f'bg_{next_idx}.jpg')
    return out


def compose(run_dir: Path, picks):
    """Pillow compose 1080×1350 slide."""
    bg_path = run_dir / "images" / "bg.jpg"
    bg = Image.open(bg_path).convert("RGB")
    ratio = max(W/bg.width, H/bg.height)
    bg = bg.resize((int(bg.width*ratio), int(bg.height*ratio)), Image.LANCZOS)
    x0, y0 = (bg.width-W)//2, (bg.height-H)//2
    bg = bg.crop((x0, y0, x0+W, y0+H))
    bg = ImageEnhance.Brightness(bg).enhance(0.85)
    canvas = bg.convert("RGBA")

    overlay = Image.new("RGBA", (W, H), (0,0,0,0))
    od = ImageDraw.Draw(overlay)
    for y in range(H):
        if 360 <= y <= 1040: a = 70
        elif 200 <= y < 360: a = int(70*(y-200)/160)
        elif 1040 < y <= 1200: a = int(70*(1200-y)/160)
        else: a = 0
        od.line([(0,y),(W,y)], fill=(20,10,15,a))
    canvas = Image.alpha_composite(canvas, overlay)
    draw = ImageDraw.Draw(canvas)

    font_path = str(SKILL_DIR / "fonts" / "DMSerifDisplay-Regular.ttf")
    header_font = ImageFont.truetype(font_path, 64)
    body_font = ImageFont.truetype(font_path, 36)
    wmark_font = ImageFont.truetype(font_path, 22)

    hdr = HEADER_EN if LANG == "en" else HEADER_JA
    bb = draw.textbbox((0,0), hdr, font=header_font); hw = bb[2]-bb[0]
    draw.text(((W-hw)//2, 420), hdr, font=header_font, fill=(255,255,255,240))

    y = 560
    for p in picks:
        line = p["text"]
        bb = draw.textbbox((0,0), line, font=body_font); lw = bb[2]-bb[0]
        draw.text(((W-lw)//2, y), line, font=body_font, fill=(255,255,255,240))
        y += 64

    wm = "aniccaai.com"
    bb = draw.textbbox((0,0), wm, font=wmark_font); ww = bb[2]-bb[0]
    draw.text(((W-ww)//2, 1270), wm, font=wmark_font, fill=(255,255,255,160))

    out = run_dir / "slides" / "slide_01.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(out, "PNG", optimize=True)
    return out

def main():
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    picks = pick_quotes(RUN_DIR)
    fal_background(RUN_DIR)
    compose(RUN_DIR, picks)
    # First line summary
    first = picks[0]["text"]
    (RUN_DIR / "first_line.txt").write_text(first)
    print(f"build OK: 1 slide composed, header='{HEADER_EN}' first='{first}'")

if __name__ == "__main__":
    main()
