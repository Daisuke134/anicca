#!/usr/bin/env python3
"""Render the deterministic bilingual body diagram for the frozen repair run."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


WIDTH = 1200
HEIGHT = 675
FONT = Path("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc")
LABELS = (
    "TRIGGER / 起動",
    "WORK / 実行",
    "VERIFY / 検証",
    "SAFE RETRY / 安全な再試行",
)


def _font(size: int) -> ImageFont.FreeTypeFont:
    if not FONT.is_file():
        raise RuntimeError(f"required bilingual font is missing: {FONT}")
    return ImageFont.truetype(str(FONT), size=size)


def _centered(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: str,
) -> None:
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    width = right - left
    height = bottom - top
    x = box[0] + (box[2] - box[0] - width) / 2
    y = box[1] + (box[3] - box[1] - height) / 2 - top
    draw.text((x, y), text, font=font, fill=fill)


def _arrow(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[int, int]],
    *,
    fill: str,
    width: int = 14,
) -> None:
    draw.line(points, fill=fill, width=width, joint="curve")
    x1, y1 = points[-2]
    x2, y2 = points[-1]
    if abs(x2 - x1) >= abs(y2 - y1):
        direction = 1 if x2 > x1 else -1
        head = [(x2, y2), (x2 - 24 * direction, y2 - 17), (x2 - 24 * direction, y2 + 17)]
    else:
        direction = 1 if y2 > y1 else -1
        head = [(x2, y2), (x2 - 17, y2 - 24 * direction), (x2 + 17, y2 - 24 * direction)]
    draw.polygon(head, fill=fill)


def render_loop_diagram(output: Path) -> dict[str, Any]:
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (WIDTH, HEIGHT), "#F7F2E8")
    draw = ImageDraw.Draw(image)
    navy = "#12304A"
    orange = "#E66A2C"
    sage = "#7A9275"
    muted = "#60727F"
    card = "#FFFCF6"

    title_font = _font(42)
    subtitle_font = _font(24)
    label_font = _font(25)
    small_font = _font(20)
    draw.text(
        (70, 45),
        "A LOOP THAT KNOWS WHEN IT IS DONE",
        font=title_font,
        fill=navy,
    )
    draw.text(
        (72, 101),
        "外から検証できる完了条件で、自走と安全な再試行をつなぐ",
        font=subtitle_font,
        fill=muted,
    )

    boxes = {
        LABELS[0]: (70, 245, 310, 365),
        LABELS[1]: (390, 175, 650, 295),
        LABELS[2]: (790, 245, 1050, 365),
        LABELS[3]: (350, 455, 750, 575),
    }
    accents = {
        LABELS[0]: orange,
        LABELS[1]: navy,
        LABELS[2]: sage,
        LABELS[3]: muted,
    }
    for label, box in boxes.items():
        shadow = (box[0] + 8, box[1] + 10, box[2] + 8, box[3] + 10)
        draw.rounded_rectangle(shadow, radius=24, fill="#DED7CA")
        draw.rounded_rectangle(box, radius=24, fill=card, outline=accents[label], width=5)
        draw.rounded_rectangle(
            (box[0], box[1], box[0] + 18, box[3]),
            radius=9,
            fill=accents[label],
        )
        _centered(draw, box, label, label_font, navy)

    _arrow(draw, [(310, 305), (350, 305), (350, 235), (390, 235)], fill=navy)
    _arrow(draw, [(650, 235), (720, 235), (720, 305), (790, 305)], fill=navy)
    _arrow(draw, [(920, 365), (920, 515), (750, 515)], fill=navy)
    _arrow(draw, [(350, 515), (195, 515), (195, 365)], fill=navy)

    draw.rounded_rectangle((1065, 258, 1170, 352), radius=22, fill="#E8F0E5", outline=sage, width=4)
    _centered(draw, (1065, 258, 1170, 314), "PASS", small_font, navy)
    _centered(draw, (1065, 304, 1170, 352), "DONE", small_font, sage)
    _arrow(draw, [(1050, 305), (1065, 305)], fill=sage, width=10)

    draw.ellipse((40, 286, 68, 314), fill=orange)
    _arrow(draw, [(68, 300), (70, 300)], fill=orange, width=10)
    draw.text(
        (72, 615),
        "Failure never becomes a guess: verify, then retry the same work.",
        font=small_font,
        fill=muted,
    )

    temporary = output.with_name(f".{output.name}.{os.getpid()}.tmp")
    image.save(temporary, format="PNG", optimize=True)
    os.replace(temporary, output)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    return {
        "path": str(output.resolve()),
        "sha256": digest,
        "width": WIDTH,
        "height": HEIGHT,
        "labels": list(LABELS),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(
        json.dumps(
            render_loop_diagram(args.output),
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
