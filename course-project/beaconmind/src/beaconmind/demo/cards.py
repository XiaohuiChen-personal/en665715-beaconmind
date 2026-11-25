"""Full-screen cards (1920 x 1080): title, part, explanation with a picture, results, disclosure.

A card is {"style": "title"|"part"|"text", "kicker", "title", "subtitle", "lines": [...], "rows": [[label, value],
...], "footer", "image": PIL image or None}. Text is wrapped to the card; a line that starts with "!" is drawn in the
warning colour (honesty notes); "{{key}}" fields must already be filled (numbers.Numbers.fill) and a card that still
holds "{{" or "TBD" is refused.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24: wrote these cards.
"""
from PIL import Image

from . import draw as D

SIZE = (1920, 1080)


class UnfilledCard(ValueError):
    pass


def _check(card):
    texts = [card.get(k) or "" for k in ("kicker", "title", "subtitle", "footer")]
    texts += list(card.get("lines") or [])
    texts += [str(x) for row in card.get("rows") or [] for x in row]
    texts += [str(x) for item in card.get("callouts") or [] for x in item[:2]]
    for t in texts:
        if "{{" in t or "}}" in t or "TBD" in t:
            raise UnfilledCard("card %r has an unfilled field: %r" % (card.get("title"), t))


def render_card(card, size=SIZE):
    _check(card)
    style = card.get("style", "text")
    if style == "title":
        return _title(card, size)
    return _text(card, size, dark=(style == "part"))


def _title(card, size):
    W, H = size
    img, dr = D.canvas(size, D.HEADER_BG)
    x = 140
    y = 250
    if card.get("kicker"):
        dr.text((x, y), card["kicker"].upper(), font=D.sans(30, "bold"), fill=(160, 190, 235))
        y += 64
    for line in D.wrap(dr, card["title"], D.sans(96, "bold"), W - 2 * x):
        dr.text((x, y), line, font=D.sans(96, "bold"), fill=(255, 255, 255))
        y += 112
    y += 34
    dr.line([(x, y), (x + 240, y)], fill=(255, 255, 255), width=5)
    y += 40
    if card.get("subtitle"):
        for line in D.wrap(dr, card["subtitle"], D.sans(42), W - 2 * x):
            dr.text((x, y), line, font=D.sans(42), fill=(230, 236, 245))
            y += 56
    y += 30
    for line in card.get("lines") or []:
        for w in D.wrap(dr, line, D.sans(32), W - 2 * x):
            dr.text((x, y), w, font=D.sans(32), fill=(200, 214, 235))
            y += 44
    if card.get("footer"):
        f = D.sans(24)
        for i, line in enumerate(reversed(D.wrap(dr, card["footer"], f, W - 2 * x))):
            dr.text((x, H - 80 - i * 34), line, font=f, fill=(170, 190, 220))
    return img


def _text(card, size, dark=False):
    W, H = size
    bg = D.HEADER_BG if dark else D.BG
    ink = (255, 255, 255) if dark else D.INK
    muted = (190, 205, 230) if dark else D.MUTED
    img, dr = D.canvas(size, bg)
    if not dark:
        dr.rectangle([0, 0, W, 14], fill=D.JHU_BLUE)
    x = 120
    image = card.get("image")
    text_w = W - 2 * x
    if image is not None:
        iw = card.get("image_w", 1000)
        ih = int(image.size[1] * iw / image.size[0])
        text_w = W - x - iw - 60 - 70
    y = 96
    if card.get("kicker"):
        dr.text((x, y), card["kicker"].upper(), font=D.sans(28, "bold"), fill=muted if dark else D.JHU_BLUE)
        y += 52
    f_title = D.sans(66 if dark else 58, "bold")
    for line in D.wrap(dr, card["title"], f_title, text_w):
        dr.text((x, y), line, font=f_title, fill=ink)
        y += int(f_title.size * 1.18)
    if card.get("subtitle"):
        y += 8
        for line in D.wrap(dr, card["subtitle"], D.sans(34), text_w):
            dr.text((x, y), line, font=D.sans(34), fill=muted)
            y += 46
    y += 30
    rows = card.get("rows") or []
    if rows:
        fl, fv = D.sans(31), D.sans(31, "bold")
        lw = max(D.text_w(dr, r[0], fl) for r in rows) + 50
        rh = D.line_h(fl, 1.45)
        for i, (label, value) in enumerate(rows):
            wrapped = D.wrap(dr, value, fv, text_w - lw - 10)
            h = rh + max(0, len(wrapped) - 1) * D.line_h(fv, 1.15)
            if i % 2 == 0 and not dark:
                dr.rectangle([x - 16, y - 6, x + text_w, y + h - 10], fill=(232, 236, 241))
            dr.text((x, y), label, font=fl, fill=muted)
            for j, w in enumerate(wrapped):
                dr.text((x + lw, y + j * D.line_h(fv, 1.15)), w, font=fv, fill=ink)
            y += h
        y += 24
    f = D.sans(card.get("font", 33))
    lh = D.line_h(f, 1.3)
    for line in card.get("lines") or []:
        colour = ink
        bullet = True
        if line.startswith("!"):
            line, colour = line[1:].lstrip(), (D.WARN if not dark else (255, 214, 102))
        if line.startswith("="):
            line, bullet = line[1:].lstrip(), False
        if bullet:
            dr.ellipse([x + 2, y + lh // 2 - 7, x + 14, y + lh // 2 + 5], fill=colour)
        for i, w in enumerate(D.wrap(dr, line, f, text_w - 36)):
            dr.text((x + 36, y), w, font=f, fill=colour)
            y += lh
        y += 10
    if image is not None:
        iw = card.get("image_w", 1000)
        im = image.resize((iw, ih), Image.LANCZOS)
        ix, iy = W - x - iw + 60, card.get("image_y", 150)
        dr.rectangle([ix - 4, iy - 4, ix + iw + 3, iy + ih + 3], fill=D.RULE)
        img.paste(im, (ix, iy))
        for n, (label, (fx, fy)) in enumerate(card.get("callouts") or [], 1):
            cx, cy = ix + fx * iw, iy + fy * ih
            r = 24
            dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=D.WARN, outline=(255, 255, 255), width=3)
            s = str(n)
            fn = D.sans(28, "bold")
            dr.text((cx - D.text_w(dr, s, fn) / 2, cy - 17), s, font=fn, fill=(255, 255, 255))
    if card.get("footer"):
        f = D.sans(24)
        lines = D.wrap(dr, card["footer"], f, W - 2 * x)
        for i, line in enumerate(reversed(lines)):
            dr.text((x, H - 70 - i * 34), line, font=f, fill=muted)
    return img
