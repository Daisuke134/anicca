#!/usr/bin/env python3
"""Template A JA (photo+serif 5-line) — anicca-iam-photo-ja."""
import os, sys, json, datetime, requests
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

if len(sys.argv) < 2:
    print("usage: build-slideshow.py <run_dir>", file=sys.stderr); sys.exit(1)
RUN_DIR = Path(sys.argv[1])
SKILL_DIR = Path(__file__).resolve().parent.parent
LANG = "ja"
HEADER = "繰り返してね。"
W, H = 1080, 1350

BG_PROMPTS = [
    "soft pastel cherry blossoms and pale plum branches on cream silk fabric, dreamy soft golden hour light, muted dusty pink and cream palette, cinematic film grain, 4:5 portrait, no text, no logo, no watermark, romantic editorial photography",
    "white sakura petals scattered on cream linen, soft natural light, 4:5 portrait, no text",
    "pale pink magnolia branches against cream silk, dreamy mood, 4:5 portrait, no text",
    "single dewy white peony on rumpled silk, soft golden hour, 4:5 portrait, no text",
    "soft pastel hydrangea on cream fabric, dreamy editorial, 4:5 portrait, no text",
    "cherry blossom petals floating on still water, soft pink, 4:5 portrait, no text",
    "single dried white rose on pale linen, warm muted tones, 4:5 portrait, no text",
]

def pick_quotes(run_dir):
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


def wrap_ja(text, font, max_w):
    out, cur = [], ""
    for c in text:
        if font.getbbox(cur + c)[2] > max_w and cur:
            for sep in ['、','。','し','て','で','に','は','を','の']:
                idx = cur.rfind(sep)
                if idx >= len(cur)//2:
                    out.append(cur[:idx+1]); cur = cur[idx+1:] + c; break
            else:
                out.append(cur); cur = c
        else:
            cur += c
    if cur: out.append(cur)
    return out

def compose(run_dir, picks):
    bg = Image.open(run_dir / "images" / "bg.jpg").convert("RGB")
    ratio = max(W/bg.width, H/bg.height)
    bg = bg.resize((int(bg.width*ratio), int(bg.height*ratio)), Image.LANCZOS)
    x0, y0 = (bg.width-W)//2, (bg.height-H)//2
    bg = bg.crop((x0,y0,x0+W,y0+H))
    bg = ImageEnhance.Brightness(bg).enhance(0.82)
    canvas = bg.convert("RGBA")

    overlay = Image.new("RGBA",(W,H),(0,0,0,0))
    od = ImageDraw.Draw(overlay)
    for y in range(H):
        if 360<=y<=1040: a=80
        elif 200<=y<360: a=int(80*(y-200)/160)
        elif 1040<y<=1200: a=int(80*(1200-y)/160)
        else: a=0
        od.line([(0,y),(W,y)], fill=(20,10,15,a))
    canvas = Image.alpha_composite(canvas, overlay)
    draw = ImageDraw.Draw(canvas)

    font_path = str(SKILL_DIR / "fonts" / "NotoSerifJP-Regular.otf")
    header_font = ImageFont.truetype(font_path, 56)
    body_font = ImageFont.truetype(font_path, 28)
    wmark_font = ImageFont.truetype(font_path, 20)

    bb = draw.textbbox((0,0), HEADER, font=header_font); hw = bb[2]-bb[0]
    draw.text(((W-hw)//2, 420), HEADER, font=header_font, fill=(255,255,255,240))

    y = 560
    for p in picks:
        lines = wrap_ja(p["text"], body_font, W - 160)
        for ln in lines:
            bb = draw.textbbox((0,0), ln, font=body_font); lw = bb[2]-bb[0]
            draw.text(((W-lw)//2, y), ln, font=body_font, fill=(255,255,255,240))
            y += 48
        y += 12

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
    (RUN_DIR / "first_line.txt").write_text(picks[0]["text"], encoding="utf-8")
    print(f"build OK: 1 slide first='{picks[0]['text']}'")

if __name__ == "__main__":
    main()
