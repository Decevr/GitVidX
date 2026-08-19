"""Create iPhone app icons from the GitVidX master art."""
from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "icon-master.jpg"
IOS = Path(__file__).resolve().parent / "GitVidX" / "Assets.xcassets" / "AppIcon.appiconset"


def sized(size: int) -> Image.Image:
    source = Image.open(MASTER).convert("RGBA")
    return source.resize((size, size), Image.Resampling.LANCZOS)


def main() -> None:
    if not MASTER.exists():
        raise SystemExit(f"Missing {MASTER}")
    IOS.mkdir(parents=True, exist_ok=True)
    sizes = {
        "icon-20@2x.png": 40,
        "icon-20@3x.png": 60,
        "icon-29@2x.png": 58,
        "icon-29@3x.png": 87,
        "icon-40@2x.png": 80,
        "icon-40@3x.png": 120,
        "icon-60@2x.png": 120,
        "icon-60@3x.png": 180,
        "icon-76.png": 76,
        "icon-76@2x.png": 152,
        "icon-83.5@2x.png": 167,
        "icon-1024.png": 1024,
    }
    for name, size in sizes.items():
        sized(size).save(IOS / name, "PNG")
    (IOS / "Contents.json").write_text(
        """{
  "images": [
    { "idiom": "iphone", "size": "20x20", "scale": "2x", "filename": "icon-20@2x.png" },
    { "idiom": "iphone", "size": "20x20", "scale": "3x", "filename": "icon-20@3x.png" },
    { "idiom": "iphone", "size": "29x29", "scale": "2x", "filename": "icon-29@2x.png" },
    { "idiom": "iphone", "size": "29x29", "scale": "3x", "filename": "icon-29@3x.png" },
    { "idiom": "iphone", "size": "40x40", "scale": "2x", "filename": "icon-40@2x.png" },
    { "idiom": "iphone", "size": "40x40", "scale": "3x", "filename": "icon-40@3x.png" },
    { "idiom": "iphone", "size": "60x60", "scale": "2x", "filename": "icon-60@2x.png" },
    { "idiom": "iphone", "size": "60x60", "scale": "3x", "filename": "icon-60@3x.png" },
    { "idiom": "ipad", "size": "20x20", "scale": "1x", "filename": "icon-20@2x.png" },
    { "idiom": "ipad", "size": "20x20", "scale": "2x", "filename": "icon-40@2x.png" },
    { "idiom": "ipad", "size": "29x29", "scale": "1x", "filename": "icon-29@2x.png" },
    { "idiom": "ipad", "size": "29x29", "scale": "2x", "filename": "icon-29@3x.png" },
    { "idiom": "ipad", "size": "40x40", "scale": "1x", "filename": "icon-40@2x.png" },
    { "idiom": "ipad", "size": "40x40", "scale": "2x", "filename": "icon-40@3x.png" },
    { "idiom": "ipad", "size": "76x76", "scale": "1x", "filename": "icon-76.png" },
    { "idiom": "ipad", "size": "76x76", "scale": "2x", "filename": "icon-76@2x.png" },
    { "idiom": "ipad", "size": "83.5x83.5", "scale": "2x", "filename": "icon-83.5@2x.png" },
    { "idiom": "ios-marketing", "size": "1024x1024", "scale": "1x", "filename": "icon-1024.png" }
  ],
  "info": { "version": 1, "author": "xcode" }
}
""",
        encoding="utf-8",
    )
    print(f"Wrote iOS icons to {IOS}")


if __name__ == "__main__":
    main()
