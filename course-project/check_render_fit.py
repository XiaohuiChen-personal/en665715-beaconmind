#!/usr/bin/env python3
"""Check that a rendered PDF of the proposal deck keeps every word inside its text shape.

Usage: python3 check_render_fit.py DECK.pptx RENDER.pdf

For each slide it flags (1) rendered words that fall outside every text-bearing shape,
and (2) shapes whose last word is not rendered inside their own box. A shape whose
text overflows its box, or that pushes text into a neighbour, fails one of the two.
"""

# Generative-AI disclosure: Claude Opus 5.5 in Cursor wrote this check for the
# October 2026 proposal revision. Xiaohui Chen reviewed it.

from __future__ import annotations

import html
import re
import subprocess
import sys

from pptx import Presentation

EMU_PER_PT = 12700
TOLERANCE_PT = 1.5


def page_words(pdf: str) -> dict[int, list[tuple[float, float, float, float, str]]]:
    output = subprocess.run(
        ["pdftotext", "-bbox", pdf, "-"], check=True, capture_output=True, text=True
    ).stdout
    pages: dict[int, list] = {}
    for number, page in enumerate(re.findall(r"<page[^>]*>(.*?)</page>", output, re.S), 1):
        pages[number] = [
            (float(a), float(b), float(c), float(d), html.unescape(word))
            for a, b, c, d, word in re.findall(
                r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">'
                r"(.*?)</word>",
                page,
            )
        ]
    return pages


def inside(word, box) -> bool:
    x0, y0, x1, y1, _ = word
    left, top, right, bottom = box
    t = TOLERANCE_PT
    return x0 >= left - t and x1 <= right + t and y0 >= top - t and y1 <= bottom + t


def main(deck: str, pdf: str) -> int:
    presentation = Presentation(deck)
    words = page_words(pdf)
    failures = 0
    for number, slide in enumerate(presentation.slides, 1):
        boxes = []
        for shape in slide.shapes:
            if not getattr(shape, "has_text_frame", False) or not shape.text.strip():
                continue
            box = (
                shape.left / EMU_PER_PT,
                shape.top / EMU_PER_PT,
                (shape.left + shape.width) / EMU_PER_PT,
                (shape.top + shape.height) / EMU_PER_PT,
            )
            boxes.append((shape, box))
        stray = [w for w in words.get(number, []) if not any(inside(w, b) for _, b in boxes)]
        for word in stray:
            failures += 1
            print(f"slide {number}: word {word[4]!r} at y={word[1]:.1f}-{word[3]:.1f} pt "
                  "lies outside every text shape")
        for shape, box in boxes:
            last = shape.text.split()[-1]
            hits = [w for w in words.get(number, []) if w[4] == last and inside(w, box)]
            if not hits:
                failures += 1
                print(f"slide {number}: last word {last!r} of {shape.name!r} is not rendered "
                      f"inside its box (bottom {box[3]:.1f} pt)")
            else:
                slack = box[3] - max(w[3] for w in hits)
                print(f"slide {number}: {shape.name:28} ok, {slack:5.1f} pt to spare below")
    print("FAIL" if failures else "PASS: every rendered word lies inside its text shape")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
