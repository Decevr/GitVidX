"""Generate GitVidX icons from the graphical master."""
from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
MASTER = ROOT / "icon-master.jpg"
BG = (16, 8, 13, 255)


def sized(size: int) -> Image.Image:
    source = Image.open(MASTER).convert("RGBA")
    return source.resize((size, size), Image.Resampling.LANCZOS)


def main() -> None:
    if not MASTER.exists():
        raise SystemExit(f"Missing {MASTER}")
    sized(180).save(ROOT / "icon-180.png")
    sized(192).save(ROOT / "icon-192.png")
    sized(512).save(ROOT / "icon-512.png")
    print("Wrote GitVidX icons")


if __name__ == "__main__":
    main()
