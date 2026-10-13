"""Turn a plain screenshot of the CAMS statement form into the annotated one used on the Home page.

    python scripts/annotate_cams_form.py path/to/screenshot.png

What it does:
  1. Wipes whatever was typed into the email, PAN and password boxes, so no personal
     details end up in the repository.
  2. Draws thin outlines with numbered circles that match the table in Step 2 of the
     checklist: 1 Detailed, 2 From date, 3 Password.
  3. Saves app/assets/cams_form_annotated.png.

The coordinates below are for the 1768 x 950 screenshot of the form. If you take a new
screenshot at a different size, adjust them. Keep the original screenshot out of the repo.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "app" / "assets" / "cams_form_annotated.png"

ACCENT = "#FF4B4B"   # Streamlit's default accent colour, the one the app uses
WHITE = (255, 255, 255)
WIDTH = 1500         # final width in pixels; big enough to read, small enough to load fast

# boxes to empty out: (left, top, right, bottom), just inside each box's border
BLANK = [
    (52, 640, 858, 712),      # email
    (906, 640, 1710, 712),    # PAN
    (52, 808, 700, 880),      # password (keeps the eye icon)
    (906, 808, 1560, 880),    # confirm password
]
# the chat bubble that floated over the page's bottom-right corner when the screenshot was taken:
# its faint shadow is wiped (light pixels only, so the box border and eye icon stay) and the bubble itself painted over
SHADOW = (1600, 760, 1768, 950)
BUBBLE = (1679, 846, 1768, 950)
BOX_BORDER = (1714, 803, 1715, 885)   # the confirm-password box's right edge, redrawn after removing the bubble
BOX_BOTTOM = (1679, 884, 1715, 885)

# what to point at: (number, outline box)
MARKS = [
    (1, (632, 48, 1150, 114)),    # Detailed
    (2, (41, 334, 867, 429)),     # From date
    (3, (41, 797, 867, 892)),     # Password
]


def font(size):
    for name in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                 "/Library/Fonts/Arial Bold.ttf"):
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()


def main(src):
    im = Image.open(src).convert("RGB")
    d = ImageDraw.Draw(im)

    border = im.getpixel((BOX_BORDER[0], 830))
    for box in BLANK:
        d.rectangle(box, fill=WHITE)
    for x in range(SHADOW[0], SHADOW[2]):
        for y in range(SHADOW[1], SHADOW[3]):
            if min(im.getpixel((x, y))) >= 200:
                im.putpixel((x, y), WHITE)
    d.rectangle(BUBBLE, fill=WHITE)
    d.rectangle(BOX_BORDER, fill=border)
    d.rectangle(BOX_BOTTOM, fill=border)

    f = font(30)
    r = 22
    for number, (x0, y0, x1, y1) in MARKS:
        d.rounded_rectangle((x0, y0, x1, y1), radius=10, outline=ACCENT, width=4)
        cx, cy = x1, y0   # circle sits on the outline's top-right corner, clear of the labels
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=ACCENT, outline=WHITE, width=3)
        d.text((cx, cy), str(number), font=f, fill=WHITE, anchor="mm")

    im = im.resize((WIDTH, round(im.height * WIDTH / im.width)), Image.LANCZOS)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    im.save(OUT, optimize=True)
    print(f"saved {OUT} ({OUT.stat().st_size / 1000:.0f} KB)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
