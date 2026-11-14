"""
prepare_assets.py - turns downloaded pictures into ready-to-use files in the assets/ folder.

Put this file in the project root (next to app.py) and run it from there:

    python prepare_assets.py --astronaut "C:/Users/me/Downloads/astronaut.jpg"
    python prepare_assets.py --nasa "C:/Users/me/Downloads/NASA_logo.svg"
    python prepare_assets.py --flare "C:/Users/me/Downloads/flare.png"
    python prepare_assets.py --check          # shows what the app will find

You can combine the options in one command. Needs Pillow (it is installed together with Streamlit).

What it does
  --astronaut  crops the photo to the banner shape (keeps the right side), shrinks it so the page stays
               fast, saves assets/astronaut.jpg
  --nasa / --flare
               svg files are copied as they are; png/jpg files get their plain background removed,
               the empty border trimmed, and are saved as assets/nasa_logo.png / assets/flare_logo.png
  Old files with the same name (for example the placeholder circles) are removed first.
"""
import argparse
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ASSETS = Path(__file__).resolve().parent / "assets"
EXTS = (".png", ".jpg", ".jpeg", ".webp", ".svg")
BANNER_RATIO = 3.6          # width / height of the crop that is kept
ASTRONAUT_WIDTH = 1800      # px, enough for a wide screen and still light
LOGO_HEIGHT = 320           # px


def remove_old(stem: str) -> None:
    ASSETS.mkdir(exist_ok=True)
    for f in ASSETS.iterdir():
        if f.is_file() and f.stem.lower() == stem.lower() and f.suffix.lower() in EXTS:
            f.unlink()
            print(f"  removed old file: {f.name}")


def prepare_astronaut(src: Path, focus: float) -> None:
    img = Image.open(src).convert("RGB")
    w, h = img.size
    if w / h > BANNER_RATIO:                       # too wide: cut the left side, keep the right side
        new_w = int(h * BANNER_RATIO)
        img = img.crop((w - new_w, 0, w, h))
    else:                                          # too tall: cut top and bottom around the focus line
        new_h = int(w / BANNER_RATIO)
        top = int(min(max(h * focus - new_h / 2, 0), h - new_h))
        img = img.crop((0, top, w, top + new_h))
    if img.width > ASTRONAUT_WIDTH:
        img = img.resize((ASTRONAUT_WIDTH, int(ASTRONAUT_WIDTH / BANNER_RATIO)), Image.LANCZOS)
    remove_old("astronaut")
    out = ASSETS / "astronaut.jpg"
    img.save(out, quality=86, optimize=True)
    print(f"  saved {out.name}: {img.width}x{img.height}px, {out.stat().st_size // 1024} KB")


def prepare_logo(src: Path, stem: str) -> None:
    remove_old(stem)
    if src.suffix.lower() == ".svg":
        out = ASSETS / f"{stem}.svg"
        shutil.copyfile(src, out)
        print(f"  copied {out.name} (vector, as it is)")
        return
    img = Image.open(src).convert("RGBA")
    w, h = img.size
    # remove a plain light background that touches the picture edges (letters inside the logo stay)
    if min(img.getpixel(p)[3] for p in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]) > 200:
        for corner in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
            r, g, b, a = img.getpixel(corner)
            if min(r, g, b) > 225:
                ImageDraw.floodfill(img, corner, (255, 255, 255, 0), thresh=40)
    box = img.getchannel("A").point(lambda v: 255 if v > 10 else 0).getbbox()
    if box:
        pad = int(max(box[2] - box[0], box[3] - box[1]) * 0.03)
        img = img.crop((max(box[0] - pad, 0), max(box[1] - pad, 0),
                        min(box[2] + pad, w), min(box[3] + pad, h)))
    if img.height > LOGO_HEIGHT:
        img = img.resize((int(img.width * LOGO_HEIGHT / img.height), LOGO_HEIGHT), Image.LANCZOS)
    out = ASSETS / f"{stem}.png"
    img.save(out, optimize=True)
    print(f"  saved {out.name}: {img.width}x{img.height}px, {out.stat().st_size // 1024} KB")


def check() -> None:
    print(f"Project folder : {ASSETS.parent}")
    print(f"Assets folder  : {ASSETS}  ({'found' if ASSETS.is_dir() else 'MISSING - it will be created'})")
    files = [f for f in ASSETS.iterdir() if f.is_file()] if ASSETS.is_dir() else []
    wanted = [("flare_logo", "FLARE logo (sidebar top)"), ("nasa_logo", "NASA logo (sidebar bottom)"),
              ("astronaut", "banner picture (Overview)")]
    for stem, label in wanted:
        match = [f for f in files if f.stem.lower() == stem and f.suffix.lower() in EXTS]
        if not match:
            print(f"  [ -- ] {stem:<11} {label}: not found -> built-in default is shown")
            continue
        f = match[0]
        kb = f.stat().st_size / 1024
        note = ""
        if kb < 4 and f.suffix.lower() != ".svg":
            note = "  <- very small, looks like a placeholder. Replace it."
        elif stem == "astronaut" and kb > 1500:
            note = "  <- big file, the page will load slowly. Run --astronaut to shrink it."
        print(f"  [ OK ] {stem:<11} {label}: {f.name} ({kb:.0f} KB){note}")
    odd = [f.name for f in files if f.suffix.lower() in EXTS
           and f.stem.lower() not in {s for s, _ in wanted}]
    for name in odd:
        print(f"  [ ?? ] {name}: not used by the app. Names must be flare_logo / nasa_logo / astronaut.")


def main() -> int:
    ap = argparse.ArgumentParser(description="Prepare the pictures in assets/ for the FLARE app.")
    ap.add_argument("--astronaut", type=Path, help="wide photo with the astronaut on the right")
    ap.add_argument("--nasa", type=Path, help="NASA logo (svg, png or jpg)")
    ap.add_argument("--flare", type=Path, help="FLARE logo (svg, png or jpg)")
    ap.add_argument("--focus", type=float, default=0.45,
                    help="only for tall photos: 0 = keep the top, 1 = keep the bottom (default 0.45)")
    ap.add_argument("--check", action="store_true", help="show what the app will find in assets/")
    a = ap.parse_args()

    if not (a.astronaut or a.nasa or a.flare or a.check):
        ap.print_help()
        return 1
    for label, p in (("astronaut", a.astronaut), ("nasa", a.nasa), ("flare", a.flare)):
        if p and not p.is_file():
            print(f"File not found for --{label}: {p}")
            return 2
    if a.astronaut:
        print("Astronaut banner:")
        prepare_astronaut(a.astronaut, a.focus)
    if a.nasa:
        print("NASA logo:")
        prepare_logo(a.nasa, "nasa_logo")
    if a.flare:
        print("FLARE logo:")
        prepare_logo(a.flare, "flare_logo")
    print()
    check()
    return 0


if __name__ == "__main__":
    sys.exit(main())
