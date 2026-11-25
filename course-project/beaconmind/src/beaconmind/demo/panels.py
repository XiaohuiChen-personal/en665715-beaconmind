"""The header bar, the step panel (observation, tool calls, report, validator), the legend and the camera tile.

The step panel is the harness's own record of one step, in plain words: what the model was given (the
observation), the tool calls it made in order with each tool's answer, the report it wrote, and what the two move
checks (the tool dispatcher and validator.check_move) did with its move. Nothing is paraphrased from hidden
reasoning: the logs do not hold it (evidence/M2/M2.T7/closed-loop/README.md); the quoted note is the report's
one-sentence `note` field, which the model writes for the operator.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24: wrote these panels.
"""
import math

from PIL import Image, ImageDraw

from . import draw as D

POSE_SOURCE = {"odometry": "odometry only", "position_fix": "a position fix (one tag)",
               "beacon_fix": "a full fix (two tags or more)", "relocalised": "relocalisation"}


def fmt_num(v, nd=2):
    s = "%.*f" % (nd, float(v))
    if float(s) == 0:
        s = s.lstrip("-")
    return s.replace("-", "−")


def fmt_pose(p):
    if not p:
        return "?"
    return "(%s, %s, %s°)" % (fmt_num(p["x_m"]), fmt_num(p["y_m"]), fmt_num(p["theta_deg"], 1))


def fmt_xy(p):
    return "(%s, %s)" % (fmt_num(p["x_m"]), fmt_num(p["y_m"]))


def _det_label(det, obs):
    for d in (obs or {}).get("detections") or []:
        if d.get("det") == det:
            return "ID %s" % d.get("id")
    return "tag #%s" % det


def call_text(c, obs=None):
    """(tool label, one-line answer) for one tool call, from its arguments and result (`obs`: the step's
    observation, to name a detection by its tag ID)."""
    a, r = c.args or {}, c.result
    if isinstance(r, dict) and r.get("status") == "error":
        return c.tool, "error: " + str(r.get("error", "")).split(".")[0]
    t = c.tool
    try:
        if t == "compose_odometry":
            return t, "prior pose " + fmt_pose(r)
        if t == "gate_detection":
            cands = (r or {}).get("candidates") or []
            inside = [x for x in cands if x.get("in_gate")]
            who = _det_label(a.get("det"), obs)
            if not cands:
                return t, "%s: no mapped beacon to compare" % who
            if inside:
                best = min(inside, key=lambda x: x.get("point_distance_m", 9))
                return t, "%s \u2248 %s (%s m apart): match" % (who, best["beacon"],
                                                                fmt_num(best.get("point_distance_m", 0)))
            return t, "%s vs %s: outside the gate" % (who, ", ".join(x["beacon"] for x in cands))
        if t == "fix_pose":
            if (r or {}).get("full"):
                return t, "full fix: " + fmt_pose(r["full"])
            if (r or {}).get("position"):
                p = r["position"]
                return t, "position fix, moved %s m" % fmt_num(p.get("delta_m", 0))
            return t, "no fix"
        if t == "map_point":
            return t, "%s placed at %s" % (_det_label(a.get("det"), obs), fmt_xy(r))
        if t == "update_beacon":
            return t, "%s now at %s, seen %s\u00d7" % (a.get("beacon"), fmt_xy(r), r.get("n_obs"))
        if t == "exploration_summary":
            return t, "new place: %s" % ("yes" if (r or {}).get("new_place") else "no")
        if t == "move":
            res = (r or {}).get("result")
            why = (r or {}).get("reason")
            return t, "%s: %s%s" % (a.get("action"), res, (" (%s)" % why) if why else "")
        if t == "emergency_stop":
            return t, "STOP: latched"
    except (KeyError, TypeError, ValueError):
        pass
    return t, "answered"


def obs_lines(obs):
    dets = obs.get("detections") or []
    if dets:
        shown = ", ".join("ID %s at %s m" % (d.get("id"), fmt_num(d.get("range_m", 0))) for d in dets[:4])
        more = " and %d more" % (len(dets) - 4) if len(dets) > 4 else ""
        first = "%d tag%s in view: %s%s" % (len(dets), "" if len(dets) == 1 else "s", shown, more)
    else:
        first = "no tag in view"
    odo = obs.get("odometry")
    if odo:
        if abs(odo.get("forward_m", 0)) > 0.005:
            second = "odometry since the last step: %s m forward, %s°" % (fmt_num(odo["forward_m"]),
                                                                                fmt_num(odo.get("dtheta_deg", 0), 1))
        else:
            second = "odometry since the last step: turned %s°" % fmt_num(odo.get("dtheta_deg", 0), 1)
    else:
        second = "first step: no odometry yet"
    return [first, second]


def validator_lines(step):
    out = []
    for m in step.move_calls:
        ok = m.get("tool_result") == "done" and m.get("validator_ok")
        if ok:
            out.append((True, "%s allowed by both checks" % m.get("action")))
        else:
            why = m.get("validator_reason") or m.get("tool_reason") or m.get("tool_result")
            out.append((False, "%s refused: %s" % (m.get("action"), why)))
    if step.move:
        res = step.move.get("result")
        out.append((res == "done", "executed %s: %s" % (step.move.get("action"), res)))
    elif not step.move_calls:
        out.append((True, "no move: the model decided %s" % step.decision))
    return out


# ---------------------------------------------------------------- header

def header(size, left, stats, badge, badge_colour=D.WARN, chip_gap=34):
    """The top bar: a pill and a label on the left, stat chips (small label over a bold value), the speed badge on
    the right. A chip that does not fit is left out, from the last one backwards."""
    img, dr = D.canvas(size, D.HEADER_BG)
    W, H = size
    x = 24
    pill_f = D.sans(22, "bold")
    tag, label = left
    w = D.text_w(dr, tag, pill_f) + 28
    D.rounded(dr, [x, (H - 42) // 2, x + w, (H + 42) // 2], fill=(255, 255, 255), radius=8)
    dr.text((x + 14, (H - 42) // 2 + 8), tag, font=pill_f, fill=D.HEADER_BG)
    x += w + 16
    f_label = D.sans(26)
    if label:
        dr.text((x, (H - 32) // 2), label, font=f_label, fill=D.HEADER_INK)
        x += D.text_w(dr, label, f_label) + 34
    # the badge: one text, or segments [(text, active, colour)] with the active one filled
    segs = [(badge, True, badge_colour)] if isinstance(badge, str) else list(badge)
    f_badge = D.sans(26, "bold")
    xr = W - 24
    for text, active, colour in reversed(segs):
        bw = D.text_w(dr, text, f_badge) + 30
        box = [xr - bw, (H - 48) // 2, xr, (H + 48) // 2]
        if active:
            D.rounded(dr, box, fill=colour, radius=10)
            dr.text((xr - bw + 15, (H - 34) // 2), text, font=f_badge, fill=(255, 255, 255))
        else:
            D.rounded(dr, box, fill=None, outline=(120, 145, 190), radius=10, width=2)
            dr.text((xr - bw + 15, (H - 34) // 2), text, font=f_badge, fill=(140, 165, 205))
        xr -= bw + 10
    right_edge = xr - 20
    f_small, f_val = D.sans(16, "bold"), D.sans(28, "bold")
    chips = []
    for name, value in stats:
        cw = max(D.text_w(dr, name.upper(), f_small), D.text_w(dr, value, f_val))
        chips.append((name.upper(), value, cw))
    gap = chip_gap
    while chips and sum(c[2] for c in chips) + gap * (len(chips) - 1) > right_edge - x:
        chips.pop()
    total = sum(c[2] for c in chips) + gap * max(0, len(chips) - 1)
    cx = x + max(0, (right_edge - x - total) / 2)
    for name, value, cw in chips:
        dr.text((cx, 10), name, font=f_small, fill=(160, 190, 235))
        dr.text((cx, 32), value, font=f_val, fill=D.HEADER_INK)
        cx += cw + gap
    return img


# ---------------------------------------------------------------- the step panel

def step_panel(size, step, n_steps, view_calls, report_shown, highlight=False, compact=False):
    W, H = size
    img, dr = D.canvas(size, D.PANEL)
    pad, y = 26, (12 if compact else 20)
    f_title = D.sans(30 if compact else 34, "bold")
    f_sec = D.sans(18 if compact else 20, "bold")
    f = D.sans(20 if compact else 24)
    f_mono = D.mono(18 if compact else 22)
    f_it = D.sans(19 if compact else 23, "italic")
    lh = D.line_h(f, 1.12 if compact else 1.22)
    note_max = 3 if compact else 5
    title = "Step %d" % step.k
    dr.text((pad, y), title, font=f_title, fill=D.INK)
    tw = D.text_w(dr, title, f_title)
    sub = "of steps 0 to %d" % (n_steps - 1)
    dr.text((pad + tw + 12, y + 12), sub, font=D.sans(22), fill=D.MUTED)
    tw += 12 + D.text_w(dr, sub, D.sans(22))
    if highlight:
        fh = D.sans(20, "bold")
        hw = D.text_w(dr, highlight, fh) + 28
        D.rounded(dr, [pad + tw + 18, y + 5, pad + tw + 18 + hw, y + 41], fill=D.BELIEF, radius=8)
        dr.text((pad + tw + 32, y + 11), highlight, font=fh, fill=(255, 255, 255))
    y += 46 if compact else 56
    gap = 4 if compact else 10

    def section(title):
        nonlocal y
        dr.text((pad, y), title.upper(), font=f_sec, fill=D.MUTED)
        y += 26 if compact else 29
        dr.line([(pad, y - 3), (W - pad, y - 3)], fill=D.RULE, width=1)
        y += 4 if compact else 6

    section("1  Observation given to the model")
    for line in obs_lines(step.observation):
        for w in D.wrap(dr, line, f, W - 2 * pad - 10):
            dr.text((pad + 10, y), w, font=f, fill=D.INK)
            y += lh
    y += gap
    section("2  Tool calls the model made")
    name_w = D.text_w(dr, "exploration_summary", f_mono) + 16
    shown = view_calls
    max_rows = 8 if compact else 9
    if len(shown) > max_rows:
        dr.text((pad + 10, y), "… %d earlier calls" % (len(shown) - max_rows + 1), font=f, fill=D.MUTED)
        y += lh
        shown = shown[-(max_rows - 1):]
    for c in shown:
        name, ans = call_text(c, step.observation)
        colour = D.OK if c.ok else D.BAD
        cy = y + lh // 2 - 2
        dr.ellipse([pad + 8, cy - 6, pad + 20, cy + 6], fill=colour)
        dr.text((pad + 30, y + 2), name, font=f_mono, fill=D.INK)
        ans = D.ellipsize(dr, ans, f, W - pad - (pad + 30 + name_w))
        dr.text((pad + 30 + name_w, y), ans, font=f, fill=D.INK if c.ok else D.BAD)
        y += lh
    if not view_calls:
        dr.text((pad + 10, y), "thinking …", font=f_it, fill=D.MUTED)
        y += lh
    y += gap
    section("3  Report the model wrote")
    if report_shown:
        rep = step.report
        src = POSE_SOURCE.get(rep.get("pose_source"), str(rep.get("pose_source")))
        entries = rep.get("map") or []
        conf = sum(1 for b in entries if isinstance(b, dict) and b.get("state") == "confirmed")
        lines = ["decision: %s" % step.decision,
                 "pose %s, from %s" % (fmt_pose(rep.get("pose")), src),
                 "beacon map: %d beacon%s, %d confirmed" % (len(entries), "" if len(entries) == 1 else "s", conf)]
        if step.fallback:
            lines.append("the report was invalid: the harness's fallback was used")
        for line in lines:
            for w in D.wrap(dr, line, f, W - 2 * pad - 10):
                dr.text((pad + 10, y), w, font=f, fill=D.INK)
                y += lh
        if step.note:
            y += 4
            note = D.wrap(dr, "“" + step.note + "”", f_it, W - 2 * pad - 24)
            if len(note) > note_max:
                note = note[:note_max]
                note[-1] = D.ellipsize(dr, note[-1] + " …", f_it, W - 2 * pad - 24)
            dr.line([(pad + 10, y + 2), (pad + 10, y + len(note) * lh - 4)], fill=D.BELIEF, width=4)
            for w in note:
                dr.text((pad + 24, y), w, font=f_it, fill=D.MUTED)
                y += lh
    else:
        dr.text((pad + 10, y), "not written yet", font=f_it, fill=D.MUTED)
        y += lh
    y += gap
    section("4  Validator and move")
    if report_shown:
        for ok, line in validator_lines(step):
            cy = y + lh // 2 - 2
            dr.ellipse([pad + 8, cy - 6, pad + 20, cy + 6], fill=D.OK if ok else D.BAD)
            for w in D.wrap(dr, line, f, W - 2 * pad - 40):
                dr.text((pad + 30, y), w, font=f, fill=D.INK)
                y += lh
    else:
        dr.text((pad + 10, y), "waiting for the report", font=f_it, fill=D.MUTED)
    return img


# ---------------------------------------------------------------- legend

def legend(size, rows):
    """rows: [[(kind, label), ...], ...]; kind in truth, belief, path_truth, path_belief, fov, tag_mapped,
    tag_unmapped, beacon, seen, start. Each row is spread over the width."""
    img, dr = D.canvas(size, D.BG)
    W, H = size
    f = D.sans(20)
    row_h = (H - 8) // max(1, len(rows))
    for r, items in enumerate(rows):
        widths = [44 + D.text_w(dr, label, f) for _, label in items]
        gap = max(18, (W - 44 - sum(widths)) / max(1, len(items) - 1)) if len(items) > 1 else 0
        gap = min(gap, 48)
        x, y = 22, 4 + r * row_h + (row_h - 28) // 2
        for (kind, label), w in zip(items, widths):
            _icon(dr, kind, x, y)
            dr.text((x + 42, y + 2), label, font=f, fill=D.INK)
            x += w + gap
    return img


def _icon(dr, kind, x, y):
    if kind == "truth":
        dr.polygon([(x, y + 4), (x + 30, y + 13), (x, y + 22)], fill=D.CAR_BODY)
    elif kind == "belief":
        dr.polygon([(x, y + 4), (x + 30, y + 13), (x, y + 22)], outline=D.BELIEF, width=3)
    elif kind == "path_truth":
        dr.line([(x, y + 13), (x + 32, y + 13)], fill=D.TRUTH, width=3)
    elif kind == "path_belief":
        for a in range(0, 32, 10):
            dr.line([(x + a, y + 13), (x + a + 6, y + 13)], fill=D.BELIEF, width=3)
    elif kind == "fov":
        dr.polygon([(x, y + 13), (x + 32, y + 1), (x + 32, y + 25)], fill=D.SEEN_FILL)
    elif kind == "tag_mapped":
        dr.rectangle([x + 7, y + 4, x + 25, y + 22], fill=D.MAPPED)
    elif kind == "tag_unmapped":
        dr.rectangle([x + 7, y + 4, x + 25, y + 22], fill=D.UNMAPPED, outline=D.UNMAPPED_EDGE, width=2)
    elif kind == "beacon":
        dr.ellipse([x + 3, y, x + 29, y + 26], outline=D.BELIEF, width=4)
    elif kind == "seen":
        dr.ellipse([x + 3, y, x + 29, y + 26], fill=D.SEEN_FILL, outline=D.SEEN, width=2)
    elif kind == "limit":
        for a in range(0, 32, 10):
            dr.line([(x + a, y + 13), (x + a + 6, y + 13)], fill=D.FAINT, width=3)
    elif kind == "refused":
        for a in range(0, 32, 10):
            dr.line([(x + a, y + 4), (x + a + 6, y + 4)], fill=D.BAD, width=3)
            dr.line([(x + a, y + 22), (x + a + 6, y + 22)], fill=D.BAD, width=3)
    elif kind == "start":
        dr.ellipse([x + 8, y + 5, x + 24, y + 21], outline=D.INK, width=3)
        dr.line([(x + 16, y + 1), (x + 16, y + 25)], fill=D.INK, width=2)
        dr.line([(x + 4, y + 13), (x + 28, y + 13)], fill=D.INK, width=2)


# ---------------------------------------------------------------- the car's camera tile

def camera_tile(size, jpeg_path, detections=(), camera=None, caption=None):
    """One camera frame letterboxed into `size`, each detection outlined (the tag square projected from its
    base_link position with camera_model, when `camera` is given) and labelled with its ID and range."""
    W, H = size
    img, dr = D.canvas(size, (16, 18, 22))
    if jpeg_path:
        try:
            src = Image.open(jpeg_path).convert("RGB")
        except OSError:
            src = None
    else:
        src = None
    if src is None:
        f = D.sans(24)
        msg = "no camera frame"
        dr.text(((W - D.text_w(dr, msg, f)) / 2, H / 2 - 12), msg, font=f, fill=(200, 200, 200))
        return img
    sw, sh = src.size
    s = min(W / sw, (H - 36) / sh)
    nw, nh = int(sw * s), int(sh * s)
    ox, oy = (W - nw) // 2, (H - 36 - nh) // 2
    img.paste(src.resize((nw, nh), Image.LANCZOS), (ox, oy))
    f = D.sans(20, "bold")
    for d in detections:
        poly = None
        if camera is not None and d.get("base_xyz_m"):
            poly = _tag_outline(camera, d)
        label = "ID %s  %s m" % (d.get("id"), fmt_num(d.get("range_m", 0)))
        if poly:
            pts = [(ox + u * s, oy + v * s) for u, v in poly]
            dr.polygon(pts, outline=D.SEEN_FILL, width=3)
            lx, ly = min(p[0] for p in pts), min(p[1] for p in pts) - 28
        else:
            bearing = math.radians(d.get("bearing_deg", 0.0))
            u = sw / 2 - (camera.fx if camera else sw) * math.tan(bearing) if camera else sw / 2 * (1 - bearing / 0.41)
            lx, ly = ox + u * s - 40, oy + 10
            dr.line([(ox + u * s, oy), (ox + u * s, oy + nh)], fill=D.SEEN_FILL, width=2)
        tw = D.text_w(dr, label, f)
        dr.rectangle([lx - 4, ly - 2, lx + tw + 6, ly + 26], fill=(0, 0, 0))
        dr.text((lx, ly), label, font=f, fill=D.SEEN_FILL)
    if caption:
        dr.text((12, H - 30), caption, font=D.sans(18), fill=(220, 220, 220))
    return img


def _tag_outline(camera, d):
    try:
        from beaconmind.camera_model import square_corners_base
        yaw = d.get("normal_yaw_deg")
        x, y, z = d["base_xyz_m"]
        facing = (yaw if yaw is not None else math.degrees(math.atan2(-y, -x)))
        corners = square_corners_base((x, y, z), facing, 0.08)
        uv = [camera.project_base(p) for p in corners]
        if any(u is None for u in uv):
            return None
        return [(float(u), float(v)) for u, v in uv]
    except Exception:  # noqa: BLE001 - an outline is a drawing aid; the label is drawn either way
        return None
