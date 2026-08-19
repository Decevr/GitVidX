"""Create Android launcher icons from the graphical master."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from make_icons import sized

ROOT = Path(__file__).resolve().parent
SIZES = {
    "mipmap-mdpi": 48,
    "mipmap-hdpi": 72,
    "mipmap-xhdpi": 96,
    "mipmap-xxhdpi": 144,
    "mipmap-xxxhdpi": 192,
}

for folder, size in SIZES.items():
    dest = ROOT / "app" / "src" / "main" / "res" / folder
    dest.mkdir(parents=True, exist_ok=True)
    sized(size).save(dest / "ic_launcher.png")

print("Wrote launcher icons")
