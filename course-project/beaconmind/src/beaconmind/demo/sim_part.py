"""Part 1 of the video: the simulated closed-loop episode, replayed from its logs, with the car drawn driving.

Sequence (durations from configs/demo_video.json; the thinking time-lapse factor is fitted to the part's target
length): part card -> "how to read the screen" card -> the episode -> result card -> (optional) the validator clip from
the scripted test model, with its own card.

The simulator executes a move in no time. To show the robot running, every executed move is drawn at its commanded
speed limits (bm.move/1 v_max_mps, w_max_dps in the run log: 0.15 m/s, 45 deg/s), the car turning and driving
smoothly between the logged poses (episode.load_episode draw_motion=True); that drawn motion plays at move_speed,
the model's thinking at the fitted factor, one step (detail_step) at detail_speed, with pauses on that step's report
and on the last one. The header shows both speeds and which one is playing; the clock is the harness's own (it stands
still while a drawn move plays) and ends at the summary's total.

Screen layout (1920 x 1080): header (0, 0, 1920 x 84); the room from above (0, 84, 1130 x 860); legend (0, 944,
1130 x 96); a close-up that follows the car (1130, 84, 390 x 292) and the simulated camera view (1530, 84, 390 x 292);
the step panel (1130, 376, 790 x 664); provenance line (0, 1040, 1920 x 40).

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24/25: wrote this part.
"""
import json
import math
import os

from PIL import Image, ImageDraw

from . import cards as C
from . import draw as D
from . import episode as E
from . import panels as P
from . import simcam
from . import timeline as TL
from .topdown import TopDown

SIZE = (1920, 1080)
HEADER = (0, 0, 1920, 84)
TOP = (0, 84, 1130, 860)
LEGEND = (0, 944, 1130, 96)
CLOSE = (1130, 84, 390, 292)
SIMCAM = (1530, 84, 390, 292)
PANEL = (1130, 376, 790, 664)
PROV = (0, 1040, 1920, 40)


def car_wheels(root):
    """The two drive wheels as rectangles in the car's frame, from configs/car.json (diameter, tyre width, outer
    track), on the axle (x = 0, the base_link origin)."""
    with open(os.path.join(root, "configs", "car.json"), encoding="utf-8") as fh:
        v = json.load(fh)["values"]
    d, w, track = v["wheel_diameter_m"]["value"], v["wheel_width_m"]["value"], v["track_outer_m"]["value"]
    yc = (track - w) / 2.0
    return [(-d / 2, yc - w / 2, d / 2, yc + w / 2), (-d / 2, -yc - w / 2, d / 2, -yc + w / 2)]


def load_camera_json(root):
    with open(os.path.join(root, "configs", "camera.json"), encoding="utf-8") as fh:
        return json.load(fh)


def card_from_spec(spec, nums, have_car=False):
    """A card spec with {{key}} filled and conditional lines resolved."""
    out = {}
    for k, v in spec.items():
        if k == "lines":
            lines = []
            for line in v:
                if isinstance(line, dict):
                    if line.get("if") == "car" and not have_car:
                        continue
                    line = line["text"]
                lines.append(nums.fill(line))
            out[k] = lines
        elif k == "rows":
            out[k] = [[nums.fill(a), nums.fill(b)] for a, b in v]
        elif isinstance(v, str):
            out[k] = nums.fill(v)
        else:
            out[k] = v
    return out


class SimPart:
    def __init__(self, root, cfg, nums, ep, card_specs, fps=25, footprint=None, have_car=False):
        self.root, self.cfg, self.nums, self.ep, self.fps = root, cfg, nums, ep, fps
        self.specs, self.have_car = card_specs, have_car
        cam = load_camera_json(root)
        rng = float((ep.run.get("env") or {}).get("max_range") or 3.0)
        self.wheels = car_wheels(root)
        self.cam_kw = dict(footprint=footprint, lens_x_m=float(cam["extrinsics"]["x_m"]),
                           hfov_deg=float(cam["hfov_deg"]), range_m=rng, view_rot_deg=float(cfg.get("view_rot_deg", 180)),
                           wheels=self.wheels)
        self.td = TopDown(ep.scene, ep.tags, TOP[2:], **self.cam_kw)
        from beaconmind.camera_model import load_camera
        self.camera = load_camera(os.path.join(root, "configs", "camera.json"))
        cs = cfg["cards_s"]
        self.val_cfg = cfg.get("validator")
        self.val_seconds = 0.0
        if self.val_cfg:
            self.val_seconds = float(cs["validator"]) + len(self._validator_phases()) * float(self.val_cfg["phase_s"])
        self.fixed_s = float(cs["part"]) + float(cs["legend"]) + float(cs["result"]) + self.val_seconds
        self.target_s = float(cfg["target_s"] if have_car else cfg.get("target_s_without_car", cfg["target_s"]))
        d = cfg.get("detail_step")
        st = ep.steps[d] if d is not None else None
        self.detail = (st.t0, st.t_report) if st else None
        holds = []
        if st and float(cfg.get("detail_hold_s", 0)) > 0:
            holds.append((st.t_report, float(cfg["detail_hold_s"])))
        if float(cfg.get("end_hold_s", 0)) > 0:
            holds.append((ep.total_s, float(cfg["end_hold_s"])))
        self.move_speed = float(cfg.get("move_speed", 1.0))
        self.factor, self.pieces, fits = TL.fit_mixed(0.0, ep.total_s, ep.move_windows, self.target_s - self.fixed_s, fps,
                                                     self.move_speed, self.detail, float(cfg.get("detail_speed", 2.0)),
                                                     holds)
        if not fits:
            raise ValueError("the simulation part does not fit %.0f s: the drawn motion at x%g, the slowed step and the "
                             "pauses alone are longer; raise move_speed or the target" % (self.target_s, self.move_speed))
        self.cues = {}
        self.n_frames = 0

    def badge(self, piece):
        """The header's speed badge: thinking and driving speeds, the playing one filled."""
        if piece.hold_s is not None:
            return [("paused", True, D.BELIEF)]
        if piece.label == "detail":
            return [("thinking %s" % TL.speed_badge(piece.speed), True, D.BELIEF),
                    ("driving %s" % TL.speed_badge(self.move_speed), False, D.OK)]
        return [("thinking %s" % TL.speed_badge(self.factor), piece.label == "think", D.WARN),
                ("driving %s" % TL.speed_badge(self.move_speed), piece.label == "move", D.OK)]

    # -------------------------------------------------------------- one frame of the episode
    def frame(self, t, piece):
        ep = self.ep
        v = E.view_at(ep, t)
        step = ep.steps[v.k]
        img = Image.new("RGB", SIZE, D.BG)
        detected = v.detected if not (v.moving and t > step.move_t0) else ()
        top = self.td.render(truth=v.truth, belief=v.belief, map_entries=v.map_entries, mapped=v.mapped,
                             detected=detected, trail_truth=v.trail_truth, trail_belief=v.trail_belief,
                             start={"x_m": 0.0, "y_m": 0.0})
        img.paste(top, TOP[:2])
        label = piece.label if piece.hold_s is None else "hold"
        if label in ("detail", "hold"):
            dr = ImageDraw.Draw(img)
            if label == "detail":
                msg = "One step slowed to %s: each tool call appears when the model made it" % TL.speed_badge(piece.speed)
            elif t >= ep.total_s:
                msg = "Paused on the last report: the model decided %s" % step.decision
            else:
                msg = "Paused on the step's report and the validator's verdict"
            f = D.sans(24, "bold")
            w = D.text_w(dr, msg, f)
            x0, y0 = TOP[0] + (TOP[2] - w) // 2 - 12, 610
            D.rounded(dr, [x0, y0, x0 + w + 24, y0 + 42], fill=D.BELIEF, radius=8)
            dr.text((x0 + 12, y0 + 6), msg, font=f, fill=(255, 255, 255))
        if v.truth:
            img.paste(self._close_up(v, detected), CLOSE[:2])
            img.paste(simcam.render(SIMCAM[2:], self.camera, v.truth, ep.scene["tags"], ep.scene["walls_polygon"],
                                    detected, "simulated camera view (camera.json)"), SIMCAM[:2])
        err = None
        ref = step.estimate if v.report_shown else step.prior
        if step.truth and ref:
            err = E.pose_error_m(step.truth, ref) * 100
        stats = [("real time", _mmss(ep.logged_time(t))), ("model cost", "US$%.2f" % v.cost),
                 ("tags mapped", "%d of %d" % (len(v.mapped), len(ep.tags)))]
        if err is not None:
            stats.append(("pose error", "%.1f cm" % err))
        hdr = P.header(HEADER[2:], ("SIMULATION", self.cfg.get("label", "")), stats, self.badge(piece),
                       chip_gap=26)
        img.paste(hdr, HEADER[:2])
        slow = label in ("detail", "hold")
        panel = P.step_panel(PANEL[2:], step, len(ep.steps), v.calls, v.report_shown,
                             highlight=("PAUSED" if label == "hold" else "SLOWED DOWN") if slow else None, compact=True)
        img.paste(panel, PANEL[:2])
        dr = ImageDraw.Draw(img)
        dr.line([(PANEL[0], CLOSE[1]), (PANEL[0], PROV[1])], fill=D.RULE, width=2)
        dr.line([(PANEL[0], PANEL[1]), (SIZE[0], PANEL[1])], fill=D.RULE, width=2)
        img.paste(self._legend(), LEGEND[:2])
        img.paste(self._prov(), PROV[:2])
        return img

    def _close_up(self, v, detected):
        px_per_m = float(self.cfg.get("close_up_px_per_m", 380))
        td = TopDown(self.ep.scene, self.ep.tags, CLOSE[2:], center=(v.truth["x_m"], v.truth["y_m"]),
                     px_per_m=px_per_m, tag_labels=False, scale_bar="left", **self.cam_kw)
        img = td.render(truth=v.truth, belief=v.belief, map_entries=v.map_entries, mapped=v.mapped, detected=detected,
                        trail_truth=v.trail_truth, trail_belief=v.trail_belief, start={"x_m": 0.0, "y_m": 0.0})
        dr = ImageDraw.Draw(img)
        cap = "close-up following the car (to scale)"
        f = D.sans(16)
        dr.rectangle([0, 0, D.text_w(dr, cap, f) + 16, 24], fill=(16, 18, 22))
        dr.text((8, 3), cap, font=f, fill=(235, 235, 235))
        return img

    def _legend(self):
        if not hasattr(self, "_legend_img"):
            rows = [[("truth", "true pose"), ("belief", "believed pose"), ("path_truth", "true path"),
                     ("path_belief", "believed path"), ("start", "start"),
                     ("fov", "camera %s°, %s m" % (self.nums["cam.hfov"], self.nums["cl.range-m"]))],
                    [("tag_mapped", "tag mapped by the model"), ("tag_unmapped", "tag not yet mapped"),
                     ("beacon", "model's beacon estimate"), ("seen", "seen this step")]]
            self._legend_img = P.legend(LEGEND[2:], rows)
        return self._legend_img

    def _prov(self):
        if not hasattr(self, "_prov_img"):
            img, dr = D.canvas(PROV[2:], (228, 232, 237))
            text = self.nums.fill(self.cfg["provenance"])
            f = D.sans(19)
            dr.text((22, 9), D.ellipsize(dr, text, f, PROV[2] - 44), font=f, fill=D.MUTED)
            self._prov_img = img
        return self._prov_img

    # -------------------------------------------------------------- the part
    def card(self, name):
        return C.render_card(card_from_spec(self.specs[name], self.nums, self.have_car))

    def legend_card(self):
        spec = card_from_spec(self.specs["sim_legend"], self.nums, self.have_car)
        ep = self.ep
        k = int(self.cfg.get("legend_step", self.cfg.get("detail_step") or 0))
        s = ep.steps[k]
        spec["image"] = self.frame(s.t_report, TL.Piece(s.t0, s.t_report, 2.0, "detail"))
        return C.render_card(spec)

    def layout(self):
        """[(cue, kind, payload, n_frames)] of the whole part, in order; kind card | legend | episode | validator."""
        fps, cs = self.fps, self.cfg["cards_s"]
        out = [("sim.part", "card", "sim_part", _frames(cs["part"], fps)),
               ("sim.legend", "legend", None, _frames(cs["legend"], fps)),
               ("sim.episode", "episode", None, sum(TL.frame_counts(self.pieces, fps))),
               ("sim.result", "card", "sim_result", _frames(cs["result"], fps))]
        if self.val_cfg:
            out.append(("sim.validator", "card", "validator", _frames(cs["validator"], fps)))
            out.append(("sim.validator.clip", "validator", None,
                        len(self._validator_phases()) * _frames(self.val_cfg["phase_s"], fps)))
        return out

    def plan(self):
        """(cues {name: seconds from the part's start}, total frames) without rendering anything."""
        fps, k, cues = self.fps, 0, {}
        for cue, kind, _payload, n in self.layout():
            cues[cue] = k / float(fps)
            if kind == "episode":
                for key, w in self.episode_cues().items():
                    ot = TL.output_time_of(self.pieces, fps, w)
                    if ot is not None:
                        cues[key] = k / float(fps) + ot
            k += n
        cues["sim.end"] = k / float(fps)
        self.cues, self.n_frames = cues, k
        return cues, k

    def render(self, enc):
        """Write every frame of the part into the Encoder, as plan() laid it out; returns the cues."""
        cues, total = self.plan()
        start = enc.n
        for cue, kind, payload, n in self.layout():
            if abs((enc.n - start) / float(self.fps) - cues[cue]) > 1e-9:
                raise RuntimeError("the render left the plan at %s" % cue)
            if kind == "card":
                enc.write(self.card(payload), n)
            elif kind == "legend":
                enc.write(self.legend_card(), n)
            elif kind == "episode":
                for _i, w, j in TL.frame_times(self.pieces, self.fps):
                    enc.write(self.frame(w, self.pieces[j]))
            elif kind == "validator":
                for img, m in self.validator_frames():
                    enc.write(img, m)
        if enc.n - start != total:
            raise RuntimeError("rendered %d frames, planned %d" % (enc.n - start, total))
        return cues

    def episode_cues(self):
        """Source times worth a narration cue: the slowed step, the first position fix, the last tag mapped, the end."""
        ep, out = self.ep, {}
        if self.detail:
            out["sim.detail"] = self.detail[0]
            out["sim.detail.end"] = self.detail[1]
        for s in ep.steps:
            if s.report.get("pose_source") in ("position_fix", "beacon_fix", "relocalised"):
                out["sim.first-fix"] = s.t_report
                break
        final = E.mapped_tags(ep.steps[-1].report.get("map"), ep.tags)
        for s in ep.steps:
            if E.mapped_tags(s.report.get("map"), ep.tags) >= final:
                out["sim.mapped-all"] = s.t_report
                break
        fwd = [s for s in ep.steps if s.move and str(s.move.get("action", "")).startswith("FORWARD")]
        if fwd:
            out["sim.first-leg"] = fwd[0].move_t0
            d = self.cfg.get("detail_step")
            later = [s for s in fwd if d is not None and s.k > d]
            if later:
                out["sim.leg"] = later[0].move_t0
        out["sim.done"] = ep.steps[-1].t_report
        return out

    # -------------------------------------------------------------- the scripted validator clip
    def _validator_phases(self):
        with open(os.path.join(self.root, self.val_cfg["trace"]), encoding="utf-8") as fh:
            tr = json.load(fh)
        self._trace = tr
        phases = []
        for st in tr["steps"]:
            if st["step"] not in self.val_cfg["steps"]:
                continue
            calls = st.get("move_calls") or []
            if st.get("validator", {}).get("latched") and not st.get("latched_seen"):
                phases.append((st, "estop", None))
            for m in calls:
                phases.append((st, "call", m))
        return phases

    def validator_frames(self):
        from beaconmind.envs import kinsim_room as kr
        seed = int(self.val_cfg["seed"])
        scene = dict(kr.study_scene(seed))
        limit = float(self.nums["rule.wall-limit-m"])           # the rule's own constant (kinsim_lite)
        scene["drive_polygon"] = kr.inset_polygon(scene["walls_polygon"], limit)
        tags = [{"tag": t["tag"], "id": t["id"], "x_m": t["x_m"], "y_m": t["y_m"], "normal_deg": t["normal_deg"]}
                for t in scene["tags"]]
        td = TopDown(scene, tags, TOP[2:], footprint=self.td.footprint, view_rot_deg=90.0, margin_px=130,
                     wheels=self.wheels)
        phase_n = _frames(self.val_cfg["phase_s"], self.fps)
        # an accepted move is drawn in real time at the commanded limits of the episode (the trace logs no command)
        v_max, w_max = float(self.nums["sim.v-max"]), float(self.nums["sim.w-max"])
        first = min(self.val_cfg["steps"])
        trail = []
        for s0 in self._trace["steps"]:                    # the path driven before the clip starts
            if s0["step"] <= first:
                x0, y0, th0 = s0["truth_xy_theta"]
                trail.append({"x_m": x0, "y_m": y0, "theta_deg": th0})
        prev_step, done_before = None, []
        for st, kind, m in self._validator_phases():
            if st["step"] != prev_step:
                prev_step, done_before = st["step"], []
            x, y, th = st["truth_xy_theta"]
            pose = {"x_m": x, "y_m": y, "theta_deg": th}
            nxt = self._next_truth(st)
            accepted = kind == "call" and m["tool_result"] == "done" and m.get("validator_ok")
            dur = 0.0
            if accepted and nxt:
                dur = (math.hypot(nxt["x_m"] - pose["x_m"], nxt["y_m"] - pose["y_m"]) / v_max
                       + abs(E.wrap_deg(nxt["theta_deg"] - pose["theta_deg"])) / w_max)
            for i in range(phase_n):
                el = (i + 0.5) / self.fps
                cur = E.interp_pose(pose, nxt, min(1.0, el / dur)) if dur > 0 else pose
                img = Image.new("RGB", SIZE, D.BG)
                top = td.render(truth=cur, trail_truth=trail + [cur], show_fov=False)
                if kind == "call" and not accepted:
                    top = self._ghost(td, top, pose, m["action"])
                img.paste(top, TOP[:2])
                hdr = P.header(HEADER[2:], ("SCRIPTED TEST", "a scripted test model, not a real model"),
                               [("arena", "study square, seed %d" % seed), ("step", str(st["step"]))],
                               "real time", D.BAD)
                img.paste(hdr, HEADER[:2])
                img.paste(self._validator_panel(st, kind, m, done_before), PANEL[:2])
                img.paste(self._val_legend(), LEGEND[:2])
                img.paste(self._prov_val(), PROV[:2])
                yield img, 1
            if accepted and nxt:
                trail.append(pose)
                trail.append(nxt)
            done_before = done_before + [(kind, m)]

    def _next_truth(self, st):
        for s2 in self._trace["steps"]:
            if s2["step"] == st["step"] + 1:
                x, y, th = s2["truth_xy_theta"]
                return {"x_m": x, "y_m": y, "theta_deg": th}
        return None

    def _ghost(self, td, top, pose, action):
        step = {"FORWARD_25": 0.25, "FORWARD_10": 0.10, "BACKWARD_10": -0.10}.get(action)
        turn = {"TURN_LEFT_30": 30.0, "TURN_RIGHT_30": -30.0}.get(action, 0.0)
        th = math.radians(pose["theta_deg"])
        g = {"x_m": pose["x_m"] + (step or 0.0) * math.cos(th), "y_m": pose["y_m"] + (step or 0.0) * math.sin(th),
             "theta_deg": pose["theta_deg"] + turn}
        big = top.resize((td.W, td.H), Image.LANCZOS)
        dr = ImageDraw.Draw(big)
        poly = td.pose_poly(g, td.footprint)
        for a, b in zip(poly, poly[1:] + poly[:1]):
            td._dashed(dr, a, b, D.BAD, 4 * td.ss, 10 * td.ss, 7 * td.ss)
        cx = sum(p[0] for p in poly) / len(poly)
        cy = sum(p[1] for p in poly) / len(poly)
        f = D.sans(24 * td.ss, "bold")
        label = "%s refused" % action
        lx, ly = cx + 70 * td.ss, cy - 4 * td.ss
        w = D.text_w(dr, label, f)
        dr.rounded_rectangle([lx - 10 * td.ss, ly - 6 * td.ss, lx + w + 10 * td.ss, ly + 36 * td.ss],
                             radius=8 * td.ss, fill=(255, 255, 255), outline=D.BAD, width=2 * td.ss)
        dr.text((lx, ly), label, font=f, fill=D.BAD)
        return big.resize(td.size, Image.LANCZOS)

    def _validator_panel(self, st, kind, m, before=()):
        W, H = PANEL[2:]
        img, dr = D.canvas((W, H), D.PANEL)
        pad, y = 26, 20
        f, fb, fs = D.sans(23), D.sans(31, "bold"), D.sans(19, "bold")
        lh = D.line_h(f, 1.25)
        dr.text((pad, y), "Scripted step %d" % st["step"], font=fb, fill=D.INK)
        y += 56
        dr.text((pad, y), "SAFETY FLAGS GIVEN TO THE MODEL", font=fs, fill=D.MUTED)
        y += 32
        sf = st.get("safety") or {}
        for line in ["forward_allowed: [%s]" % ", ".join(sf.get("forward_allowed") or []),
                     "backward_allowed: %s" % str(sf.get("backward_allowed")).lower(),
                     "turn_allowed: %s" % str(sf.get("turn_allowed")).lower()]:
            dr.text((pad + 10, y), line, font=D.mono(21), fill=D.INK)
            y += lh
        y += 16
        dr.text((pad, y), "WHAT THE MODEL ASKED FOR, AND THE ANSWER", font=fs, fill=D.MUTED)
        y += 32
        lines = []
        for k0, m0 in before:                     # what this step already asked for
            if k0 == "estop":
                lines.append((False, "emergency_stop: the episode is latched"))
            else:
                ok0 = m0["tool_result"] == "done" and m0.get("validator_ok")
                lines.append((ok0, "move %s %s" % (m0["action"], "accepted" if ok0 else "refused: %s" % (
                    m0.get("validator_reason") or m0.get("tool_reason")))))
        if kind == "estop":
            lines.append((False, "emergency_stop: the episode is latched"))
            lr = st.get("validator", {}).get("latch_reason")
            if lr:
                lines.append((False, "latch reason: %s" % lr))
        else:
            ok = m["tool_result"] == "done" and m.get("validator_ok")
            if ok:
                lines.append((True, "move %s accepted by both checks and executed" % m["action"]))
            else:
                why = m.get("validator_reason") or m.get("tool_reason")
                lines.append((False, "move %s refused: %s" % (m["action"], why)))
                lines.append((False, "nothing is executed for a refused move"))
        for ok, line in lines:
            cy = y + lh // 2 - 2
            dr.ellipse([pad + 8, cy - 7, pad + 22, cy + 7], fill=D.OK if ok else D.BAD)
            for w in D.wrap(dr, line, f, W - 2 * pad - 40):
                dr.text((pad + 34, y), w, font=f, fill=D.INK)
                y += lh
        end = st.get("episode_end")
        if end and kind != "estop":
            y += 16
            dr.text((pad, y), "Episode ended by: %s (%s)" % (end["ended_by"], end["detail"]), font=f, fill=D.BAD)
        return img

    def _val_legend(self):
        if not hasattr(self, "_val_legend_img"):
            self._val_legend_img = P.legend(LEGEND[2:], [
                [("truth", "car (scripted test)"), ("path_truth", "path driven"), ("tag_unmapped", "tag")],
                [("limit", "forward moves must stop %s m from a wall" % self.nums["rule.wall-limit-m"]),
                 ("refused", "a refused move (not executed)")]])
        return self._val_legend_img

    def _prov_val(self):
        if not hasattr(self, "_prov_val_img"):
            img, dr = D.canvas(PROV[2:], (250, 228, 228))
            text = self.nums.fill(self.cfg["validator"]["provenance"])
            f = D.sans(19)
            dr.text((22, 9), D.ellipsize(dr, text, f, PROV[2] - 44), font=f, fill=D.BAD)
            self._prov_val_img = img
        return self._prov_val_img


def _frames(seconds, fps):
    return max(1, int(math.floor(float(seconds) * fps + 0.5)))


def _mmss(t):
    s = int(t)
    return "%02d:%02d" % (s // 60, s % 60)
