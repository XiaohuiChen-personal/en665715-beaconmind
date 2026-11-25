"""Fonts, colours and text helpers shared by the video's renderers (Pillow).

Fonts are looked up by path, first the Mac's (Helvetica Neue, Menlo), then DejaVu (the Spark), then Pillow's own
default, so the same code renders on both machines; the font used is printed by video_cli (`fonts`).

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24: wrote this module.
"""
import functools
import os

from PIL import Image, ImageDraw, ImageFont

# (path, index of regular, bold, italic) in order of preference
SANS = [("/System/Library/Fonts/HelveticaNeue.ttc", 0, 1, 2),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 0, 0, 0)]
SANS_BOLD_FILE = {"/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"}
MONO = [("/System/Library/Fonts/Menlo.ttc", 0, 1, 2),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 0, 0, 0)]

# colours (RGB)
BG = (244, 245, 247)
PANEL = (255, 255, 255)
INK = (27, 31, 36)
MUTED = (87, 96, 106)
FAINT = (175, 184, 193)
RULE = (208, 215, 222)
JHU_BLUE = (0, 45, 114)
HEADER_BG = (0, 45, 114)
HEADER_INK = (255, 255, 255)
TRUTH = (36, 41, 47)
CAR_BODY = (104, 112, 122)
CAR_WHEEL = (20, 22, 26)
BELIEF = (31, 111, 235)
BELIEF_LIGHT = (160, 196, 250)
MAPPED = (26, 127, 55)
UNMAPPED = (255, 255, 255)
UNMAPPED_EDGE = (110, 119, 129)
SEEN = (212, 135, 0)
SEEN_FILL = (255, 196, 64)
OK = (26, 127, 55)
BAD = (207, 34, 46)
WARN = (191, 135, 0)
WALL = (36, 41, 47)
FLOOR = (255, 255, 255)
DRIVE = (234, 238, 242)
DESK = (200, 205, 211)


@functools.lru_cache(maxsize=None)
def _font(kind, size, style):
    table = SANS if kind == "sans" else MONO
    for path, i_reg, i_bold, i_it in table:
        if not os.path.exists(path):
            continue
        index = {"regular": i_reg, "bold": i_bold, "italic": i_it}[style]
        if style == "bold" and path in SANS_BOLD_FILE and os.path.exists(SANS_BOLD_FILE[path]):
            path, index = SANS_BOLD_FILE[path], 0
        try:
            return ImageFont.truetype(path, size, index=index)
        except OSError:
            continue
    return ImageFont.load_default()


def sans(size, style="regular"):
    return _font("sans", int(size), style)


def mono(size, style="regular"):
    return _font("mono", int(size), style)


def font_names():
    return {"sans": sans(20).getname(), "mono": mono(20).getname()}


def text_w(draw, text, font):
    return draw.textlength(text, font=font)


def wrap(draw, text, font, width):
    """Lines of `text` that each fit in `width` pixels (words never split unless one word is wider)."""
    out = []
    for para in str(text).split("\n"):
        words, line = para.split(" "), ""
        for w in words:
            trial = w if not line else line + " " + w
            if text_w(draw, trial, font) <= width:
                line = trial
                continue
            if line:
                out.append(line)
            while text_w(draw, w, font) > width and len(w) > 1:       # a single over-long token
                cut = len(w)
                while cut > 1 and text_w(draw, w[:cut], font) > width:
                    cut -= 1
                out.append(w[:cut])
                w = w[cut:]
            line = w
        out.append(line)
    return out


def ellipsize(draw, text, font, width):
    if text_w(draw, text, font) <= width:
        return text
    while text and text_w(draw, text + "…", font) > width:
        text = text[:-1]
    return text + "…"


def line_h(font, factor=1.25):
    asc, desc = font.getmetrics()
    return int((asc + desc) * factor)


def canvas(size, colour=BG):
    img = Image.new("RGB", size, colour)
    return img, ImageDraw.Draw(img)


def rounded(draw, box, fill, outline=None, radius=10, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)
