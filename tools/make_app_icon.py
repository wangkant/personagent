"""Draw the app icon: the page's speech-bubble mark on a dark tile.

    python tools/make_app_icon.py

Writes persona_agent/static/app.ico (Windows) and app.png (GTK and Qt).
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

STATIC = Path(__file__).resolve().parents[1] / "persona_agent" / "static"
INK, PAPER = (28, 28, 26, 255), (255, 255, 255, 255)
CANVAS = 1024
# The mark is drawn in the favicon's 24-unit box, centred on the tile.
UNIT = CANVAS * 0.70 / 24
CENTRE = (12.0, 12.2)
ICO_SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def _at(x: float, y: float) -> tuple[float, float]:
    return (CANVAS / 2 + (x - CENTRE[0]) * UNIT, CANVAS / 2 + (y - CENTRE[1]) * UNIT)


def _box(x0: float, y0: float, x1: float, y1: float) -> list[float]:
    return [*_at(x0, y0), *_at(x1, y1)]


def draw() -> Image.Image:
    image = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    pen = ImageDraw.Draw(image)
    pen.rounded_rectangle([0, 0, CANVAS - 1, CANVAS - 1], radius=CANVAS * 0.225, fill=INK)
    pen.rounded_rectangle(_box(3, 3.5, 21, 17.5), radius=5.5 * UNIT, fill=PAPER)
    pen.polygon([_at(11.4, 17.2), _at(6.6, 21.0), _at(5.7, 20.5), _at(5.7, 15.5)], fill=PAPER)
    for left in (8.6, 13.4):
        pen.rounded_rectangle(_box(left, 8.6, left + 2, 12.0), radius=UNIT, fill=INK)
    return image


def main() -> None:
    master = draw()
    master.resize((256, 256), Image.LANCZOS).save(STATIC / "app.png", optimize=True)
    master.save(STATIC / "app.ico", sizes=[(size, size) for size in ICO_SIZES])


if __name__ == "__main__":
    main()
