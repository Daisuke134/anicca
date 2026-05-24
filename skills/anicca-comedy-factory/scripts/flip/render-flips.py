#!/usr/bin/env python3
"""
v2: 本物のフリップ芸仕様 (IPPON 観察ベース)。
- 1 ネタ = 1 フリップ = 1 スライド
- 真っ白背景 + Klee One SemiBold 手書きフォント
- 装飾ゼロ (縦罫線・朱印・お経の紙風・イラスト全削除)
- 1〜3 行、各行 ±3〜5° 斜め、左右オフセット
- お題 / 〆 のみ IPPON 風黄色テロップ

Output: ~/Desktop/anicca-flip-v2-2026-05-14/
"""
import math
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ── Setup ─────────────────────────────────────────────────────────
random.seed(20260514)
OUT = Path.home() / "Desktop" / "anicca-flip-v2-2026-05-14"
OUT.mkdir(parents=True, exist_ok=True)

W = H = 1080  # 1:1 正方 (Google スライド + Instagram + TikTok 共用)

FONT_DIR = Path.home() / ".openclaw/skills/anicca-comedy-factory/fonts"
F_KLEE     = str(FONT_DIR / "KleeOne-SemiBold.ttf")
F_KLEE_REG = str(FONT_DIR / "KleeOne-Regular.ttf")
F_YUJI_MAI = str(FONT_DIR / "YujiMai-Regular.ttf")
F_REGGAE   = str(FONT_DIR / "ReggaeOne-Regular.ttf")

# ── Color palette (FLIP_DESIGN_RULES.md §6) ───────────────────────
PAPER     = (255, 255, 255)      # フリップ本体 = 真っ白
INK       = (26, 26, 26)         # 文字 = 黒
RED       = (199, 37, 37)        # 赤ハイライト (1ワード限定)
TELOP_BG  = (255, 199, 0)        # IPPON お題テロップ黄色
SHIME_BG  = (24, 24, 24)         # 〆スライド黒


def font(path, size):
    return ImageFont.truetype(path, size)


def draw_rotated_text(img, x, y, text, fnt, color, angle_deg):
    """テキストを angle 回転して img に貼る。x,y = 中心座標"""
    d_tmp = ImageDraw.Draw(img)
    bbox = d_tmp.textbbox((0, 0), text, font=fnt)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad = 30
    txt_img = Image.new("RGBA", (tw + pad * 2, th + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(txt_img)
    d.text((pad - bbox[0], pad - bbox[1]), text, font=fnt, fill=color)
    rotated = txt_img.rotate(angle_deg, resample=Image.BICUBIC, expand=True)
    rw, rh = rotated.size
    img.alpha_composite(rotated, (int(x - rw / 2), int(y - rh / 2)))


def paper_canvas(rgb=PAPER):
    """Return RGBA canvas for alpha_composite"""
    return Image.new("RGBA", (W, H), rgb + (255,))


def add_paper_grain(img, intensity=4, dots=400):
    """微小ノイズで紙感"""
    d = ImageDraw.Draw(img)
    for _ in range(dots):
        x = random.randint(0, W - 1)
        y = random.randint(0, H - 1)
        a = random.randint(8, intensity + 14)
        d.point((x, y), fill=(180, 175, 165, a))


# ── 0. 共通: 「{{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}}」サインを右下に小さく ───────────────────
def sign(img):
    f = font(F_KLEE_REG, 34)
    d = ImageDraw.Draw(img)
    text = "── {{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}}"
    bbox = d.textbbox((0, 0), text, font=f)
    tw = bbox[2] - bbox[0]
    d.text((W - tw - 60, H - 75), text, font=f, fill=(140, 140, 140, 220))


# ── Slide 1: お題テロップ (IPPON 風) ─────────────────────────────
def slide_1():
    img = paper_canvas(TELOP_BG)
    # 大きく中央に黒太字でお題
    d = ImageDraw.Draw(img)
    lines = ["「これは無常すぎる」", "と感じるものは?"]
    fnt = font(F_REGGAE, 92)
    line_h = 130
    total = len(lines) * line_h
    y0 = (H - total) // 2 - 40
    for i, ln in enumerate(lines):
        bbox = d.textbbox((0, 0), ln, font=fnt)
        tw = bbox[2] - bbox[0]
        x = (W - tw) // 2
        y = y0 + i * line_h - bbox[1]
        d.text((x, y), ln, font=fnt, fill=INK)
    # 下に小さく
    fnt2 = font(F_KLEE, 40)
    bbox = d.textbbox((0, 0), "ANICCA GRAND PRIX", font=fnt2)
    tw = bbox[2] - bbox[0]
    # 黒帯
    d.rectangle([(W // 2 - tw // 2 - 30, H - 160), (W // 2 + tw // 2 + 30, H - 90)], fill=INK)
    d.text((W // 2 - tw // 2, H - 152 - bbox[1]), "ANICCA GRAND PRIX", font=fnt2, fill=TELOP_BG)
    img.convert("RGB").save(OUT / "01_odai.png", "PNG", optimize=True)


# ── Slide 2-4: フリップ ① ② ③ ────────────────────────────────────
def flip_slide(filename, lines_with_meta, base_size=200, line_gap=18):
    """
    lines_with_meta = [(text, angle, x_offset, color), ...]
    """
    img = paper_canvas(PAPER)
    add_paper_grain(img)
    # 各行のサイズを動的に決定 (画面幅に収める)
    d_tmp = ImageDraw.Draw(img)

    # 各行 font + 自動縮小
    rendered = []
    for text, angle, dx, color in lines_with_meta:
        sz = base_size
        while sz > 90:
            f = font(F_KLEE, sz)
            bbox = d_tmp.textbbox((0, 0), text, font=f)
            if bbox[2] - bbox[0] <= W - 200:
                break
            sz -= 8
        rendered.append((text, angle, dx, color, font(F_KLEE, sz), sz))

    # 行の高さ計算 → 中央に積む
    total_h = sum(r[5] + line_gap for r in rendered) - line_gap
    y = (H - total_h) // 2 + rendered[0][5] // 2

    for text, angle, dx, color, fnt, sz in rendered:
        draw_rotated_text(img, W // 2 + dx, y, text, fnt, color, angle)
        y += sz + line_gap

    sign(img)
    img.convert("RGB").save(OUT / filename, "PNG", optimize=True)


# ── Slide 5: 〆テロップ ─────────────────────────────────────────
def slide_5():
    img = paper_canvas(SHIME_BG)
    d = ImageDraw.Draw(img)
    # 中央巨大「南無」
    fnt = font(F_YUJI_MAI, 480)
    text = "南 無"
    bbox = d.textbbox((0, 0), text, font=fnt)
    tw = bbox[2] - bbox[0]
    d.text(((W - tw) // 2, (H - 480) // 2 - 60 - bbox[1]), text, font=fnt, fill=TELOP_BG)
    # 下に
    fnt2 = font(F_KLEE, 64)
    bbox = d.textbbox((0, 0), "全部、消えます。", font=fnt2)
    tw = bbox[2] - bbox[0]
    d.text(((W - tw) // 2, H - 280 - bbox[1]), "全部、消えます。", font=fnt2, fill=TELOP_BG)

    fnt3 = font(F_KLEE_REG, 42)
    bbox = d.textbbox((0, 0), "{{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}}  @aniccaai", font=fnt3)
    tw = bbox[2] - bbox[0]
    d.text(((W - tw) // 2, H - 150 - bbox[1]), "{{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}}  @aniccaai", font=fnt3, fill=(190, 190, 190))
    img.convert("RGB").save(OUT / "05_shime.png", "PNG", optimize=True)


# ── Run ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    slide_1()

    # フリップ ①: 永代供養の有効期限 (2 行、軽い斜め)
    flip_slide("02_flip_eitai.png", [
        ("永代供養の", -3, -12, INK),
        ("有効期限", 4, 28, INK),
    ], base_size=240)

    # フリップ ②: 天井した翌日 推し卒業 (3 行)
    flip_slide("03_flip_oshi.png", [
        ("天井した", -2, -30, INK),
        ("翌日", 5, 80, INK),
        ("推し卒業", -4, -10, RED),
    ], base_size=220)

    # フリップ ③: 火葬場のスタンプカード (3 行、最後赤強調)
    flip_slide("04_flip_kasou.png", [
        ("火葬場の", -3, -20, INK),
        ("スタンプカード", 2, 10, INK),
        ("あと2回で1回無料", -5, 0, RED),
    ], base_size=180)

    slide_5()

    print(f"OK: 5 slides at {OUT}")
    for p in sorted(OUT.glob("*.png")):
        size_kb = p.stat().st_size // 1024
        print(f"  - {p.name}  {size_kb} KB")
