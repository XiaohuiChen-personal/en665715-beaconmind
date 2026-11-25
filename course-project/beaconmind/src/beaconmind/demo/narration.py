"""The narration script: a template of blocks, each tied to a cue of the edit decision list, filled with the cue
times and the numbers (standard library only).

Template syntax (presentation/demo-voiceover.template.md): everything before the first block is a comment for the
editor and is not copied. A block starts with a line `@@ <cue>` (a cue of the video: a card's id such as `title`, or a
part's cue such as `sim.detail`); its text runs to the next `@@` line. A block runs from its cue's time to the next
block's cue time (blocks are put in time order); its word budget is that duration at words_per_min. `{{key}}` is
replaced by a number from numbers.Numbers. A block whose cue is not in the video (the car part before it exists) is
left out and listed as such.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24: wrote this generator.
"""
import re

from . import timeline as TL

WORD_RE = re.compile(r"\S+")


def parse_template(text):
    """[(cue, text)] in template order."""
    blocks, cue, buf = [], None, []
    for line in text.splitlines():
        m = re.match(r"^@@\s+([A-Za-z0-9._-]+)\s*$", line)
        if m:
            if cue is not None:
                blocks.append((cue, "\n".join(buf).strip()))
            cue, buf = m.group(1), []
        elif cue is not None:
            buf.append(line)
    if cue is not None:
        blocks.append((cue, "\n".join(buf).strip()))
    return blocks


def words(text):
    return len(WORD_RE.findall(text))


def mmss(t):
    s = int(round(t * 10)) / 10.0
    return "%d:%04.1f" % (int(s // 60), s - 60 * int(s // 60))


def build(blocks, cues, video_end_s, nums, words_per_min=130):
    """[{cue, start_s, end_s, seconds, budget, words, text, over}] for the blocks whose cue exists, in time order;
    and the cues left out."""
    present = [(cues[c], c, t) for c, t in blocks if c in cues]
    missing = [c for c, _ in blocks if c not in cues]
    present.sort(key=lambda x: x[0])
    out = []
    for i, (t0, cue, text) in enumerate(present):
        t1 = present[i + 1][0] if i + 1 < len(present) else video_end_s
        filled = nums.fill(text)
        budget = TL.word_budget(t1 - t0, words_per_min)
        n = words(filled)
        out.append({"cue": cue, "start_s": t0, "end_s": t1, "seconds": t1 - t0, "budget": budget, "words": n,
                    "text": filled, "over": n > budget})
    return out, missing


def render_markdown(rows, missing, video_end_s, header, footer, words_per_min=130):
    lines = [header.rstrip(), ""]
    lines.append("Video length %s (m:ss.s); %d blocks; read at about %d words a minute. A block's budget is what fits "
                 "between its cue and the next one." % (mmss(video_end_s), len(rows), words_per_min))
    if missing:
        lines.append("")
        lines.append("Left out because the video has no such cue yet: %s." % ", ".join("`%s`" % m for m in missing))
    over = [r for r in rows if r["over"]]
    lines.append("")
    lines.append("Blocks over their word budget: %s." % (", ".join("`%s`" % r["cue"] for r in over) if over else "none"))
    lines.append("")
    lines.append("| Start | End | Cue | Seconds | Words / budget |")
    lines.append("| --- | --- | --- | --- | --- |")
    for r in rows:
        lines.append("| %s | %s | `%s` | %.1f | %d / %d%s |" % (mmss(r["start_s"]), mmss(r["end_s"]), r["cue"],
                                                             r["seconds"], r["words"], r["budget"],
                                                             " (over)" if r["over"] else ""))
    lines.append("")
    for r in rows:
        lines.append("### %s to %s · `%s` · %.1f s, %d words (budget %d)" % (
            mmss(r["start_s"]), mmss(r["end_s"]), r["cue"], r["seconds"], r["words"], r["budget"]))
        lines.append("")
        lines.append(r["text"])
        lines.append("")
    lines.append(footer.rstrip())
    lines.append("")
    return "\n".join(lines)
