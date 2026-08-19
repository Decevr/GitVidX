"""Copy the web app into the iOS www folder."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path(__file__).resolve().parent / "GitVidX" / "www"
TARGET.mkdir(parents=True, exist_ok=True)

for name in ("index.html", "styles.css", "app.js", "web-search.js", "manifest.json", "sw.js"):
    source = ROOT / name
    if source.exists():
        shutil.copy2(source, TARGET / name)

for image in list(ROOT.glob("icon-*.png")) + list(ROOT.glob("banner.jpg")):
    shutil.copy2(image, TARGET / image.name)

fonts = ROOT / "fonts"
if fonts.exists():
    dest = TARGET / "fonts"
    dest.mkdir(exist_ok=True)
    for font in fonts.glob("*"):
        shutil.copy2(font, dest / font.name)

print(f"Copied web files to {TARGET}")
