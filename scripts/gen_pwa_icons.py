"""Einmalig ausführen: schreibt static/icon-192.png und static/icon-512.png (PWA-Icons)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "static"


def _draw(size: int) -> Image.Image:
    bg = (7, 10, 18)
    accent = (0, 245, 212)
    img = Image.new("RGB", (size, size), bg)
    draw = ImageDraw.Draw(img)
    margin = int(size * 0.12)
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=int(size * 0.14),
        outline=accent,
        width=max(2, size // 64),
    )
    # simple "document" fold
    fold = int(size * 0.22)
    draw.polygon(
        [(margin, margin + fold), (margin + fold, margin), (margin + fold, margin + fold)],
        fill=accent,
    )
    return img


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    _draw(192).save(OUT / "icon-192.png", format="PNG")
    _draw(512).save(OUT / "icon-512.png", format="PNG")
    print("Written:", OUT / "icon-192.png", OUT / "icon-512.png")


if __name__ == "__main__":
    main()
