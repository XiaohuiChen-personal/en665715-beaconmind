"""Part 2 of the video: a real-car episode, from footage that does not exist yet (input path, layout, time alignment).

Inputs (configs/demo_video.json car.inputs, every path relative to course-project/):

    recorder_session   data/real/<YYYYmmdd-HHMMSS>-<label>/: camera frames (frames_backend/ when the batch backend was
                       the camera's client, else frames/), each folder with index.jsonl (host receive time t_resp_ns,
                       the X-BM headers) - tools/record_session.sh, tools/record_frames.py, car/camera.py
    run_dir            the closed-loop harness's folder for the episode: seed_<n>.jsonl, seed_<n>.moves.jsonl,
                       spend.jsonl (model turns), backend/steps.jsonl (each sensing: host time, frames, detections)
    phone_video        the phone clip; it starts by filming tools/session_clock.py
    clock_readings     ["<seconds into the clip>=<epoch the clock shows>", ...]: one fixes the offset, two or more
                       (one near the start, one near the end) also the rate (timeline.clock_sync)
    world, start_pose_world   the surveyed world file and the episode's start pose in it (the batch's start scan), so
                       the room is drawn in the episode's map frame (kinsim_room.room_scene)
    label, test        the header's label; test=true marks every frame as a pipeline test

Everything is placed on the Spark's epoch clock: harness rows (spend.jsonl, moves.jsonl, backend/steps.jsonl) and
camera frames (t_resp_ns) are stamped by the Spark; the phone clip is mapped onto it by the clock readings. Motion
plays at move_speed (real time by default), the waits are sped up to fit target_s (timeline.fit_think_speed).

Layout (1920 x 1080): header (0, 0, 1920 x 84); phone video (0, 84, 1130 x 636); the car's camera with the fused
detections outlined (0, 720, 427 x 320); the room from above (427, 720, 703 x 320); the step panel (1130, 84,
790 x 956); provenance (0, 1040, 1920 x 40).

pipeline_test() runs the whole path on stand-in data: the camera frames of an existing recorder session, a stand-in
trace (the first steps of the simulated episode re-timed into the session's window) and a stand-in phone clip that
films a fake session clock and carries its own epoch in a bit stripe; the rendered frames are decoded again and the
stripe is compared with the time each frame should show.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24: wrote this part and its pipeline test.
"""
import json
import math
import os
import subprocess

from PIL import Image, ImageDraw

from . import cards as C
from . import draw as D
from . import episode as E
from . import ffmpeg as F
from . import panels as P
from . import timeline as TL
from .topdown import TopDown

SIZE = (1920, 1080)
HEADER = (0, 0, 1920, 84)
PHONE = (0, 84, 1130, 636)
CAM = (0, 720, 427, 320)
TOPV = (427, 720, 703, 320)
PANEL = (1130, 84, 790, 956)
PROV = (0, 1040, 1920, 40)


def _rel(root, p):
    return p if (p is None or os.path.isabs(p)) else os.path.join(root, p)


def _jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def camera_index(session_dir):
    """[(host receive time s, absolute jpeg path)] of a recorder session, sorted; frames_backend/ first."""
    for sub in ("frames_backend", "frames"):
        idx = os.path.join(session_dir, sub, "index.jsonl")
        if os.path.exists(idx):
            out = []
            for r in _jsonl(idx):
                if r.get("file") and not r.get("error"):
                    out.append((r["t_resp_ns"] / 1e9, os.path.join(session_dir, sub, r["file"])))
            return sorted(out)
    return []


def frame_detections(backend_steps):
    """{jpeg file name: (step, fused detections)} from backend/steps.jsonl: every frame a sensing used carries that
    sensing's fused detections (detections_internal with base_xyz_m, joined with the observation's range)."""
    out = {}
    for b in backend_steps or []:
        if b.get("type", "step") != "step":
            continue
        obs = {d["det"]: d for d in (b.get("sense") or {}).get("detections") or []}
        dets = []
        for d in b.get("detections_internal") or []:
            o = obs.get(d.get("det"), {})
            dets.append(dict(d, range_m=o.get("range_m"), bearing_deg=o.get("bearing_deg")))
        for f in b.get("frames") or []:
            if f.get("file"):
                out[f["file"]] = (b.get("step"), dets)
    return out


class CarPart:
    def __init__(self, root, cfg, inputs, nums, card_specs, fps=25):
        self.root, self.cfg, self.inp, self.nums, self.specs, self.fps = root, cfg, inputs, nums, card_specs, fps
        run_dir = _rel(root, inputs["run_dir"])
        bpath = _rel(root, inputs.get("backend_steps") or os.path.join(run_dir, "backend", "steps.jsonl"))
        self.backend = _jsonl(bpath) if os.path.exists(bpath) else []
        self.ep = E.load_episode(run_dir, inputs.get("seed"), time_base="epoch", backend_steps=self.backend)
        self.frames = camera_index(_rel(root, inputs["recorder_session"]))
        self.frame_t = [t for t, _ in self.frames]
        self.dets = frame_detections(self.backend)
        self.sync = TL.clock_sync([TL.parse_reading(r) for r in inputs.get("clock_readings") or []]) \
            if inputs.get("clock_readings") else None
        self.phone = _rel(root, inputs.get("phone_video"))
        from beaconmind.envs import kinsim_room as kr
        start = inputs["start_pose_world"]
        if isinstance(start, str):
            x, y, th = (float(v) for v in start.split(","))
            start = {"x_m": x, "y_m": y, "theta_deg": th}
        scene = kr.room_scene(kr.load_world(_rel(root, inputs["world"])), start,
                              drive_inset_m=float(inputs.get("drive_inset_m", 0.4)))
        self.ep.scene = scene
        self.ep.tags = [{k: t.get(k) for k in ("tag", "id", "x_m", "y_m", "normal_deg", "uid", "wall")}
                        for t in scene["tags"]]
        with open(os.path.join(root, "configs", "camera.json"), encoding="utf-8") as fh:
            camj = json.load(fh)
        self.td = TopDown(scene, self.ep.tags, TOPV[2:], footprint=kr.default_footprint(),
                          lens_x_m=float(camj["extrinsics"]["x_m"]), hfov_deg=float(camj["hfov_deg"]),
                          range_m=float(inputs.get("max_range_m", 3.0)), view_rot_deg=float(cfg.get("view_rot_deg", 180)),
                          margin_px=24)
        try:
            from beaconmind.camera_model import load_camera
            self.camera = load_camera(os.path.join(root, "configs", "camera.json"))
        except Exception:  # noqa: BLE001 - outlines are a drawing aid
            self.camera = None
        self.t0, self.t1 = self.ep.steps[0].t0, self.ep.steps[-1].t1
        self.card_s = float(cfg.get("card_s", 6))
        self.think_speed, self.pieces, self.fits = TL.fit_think_speed(
            self.t0, self.t1, self.ep.move_windows, float(cfg["target_s"]) - self.card_s, fps,
            move_speed=float(cfg.get("move_speed", 1.0)))
        self.test = bool(inputs.get("test"))

    # -------------------------------------------------------------- plan
    def layout(self):
        n_card = max(1, int(self.card_s * self.fps + 0.5))
        return [("car.part", "card", "car_part", n_card),
                ("car.episode", "episode", None, sum(TL.frame_counts(self.pieces, self.fps)))]

    def plan(self):
        k, cues = 0, {}
        for cue, kind, _p, n in self.layout():
            cues[cue] = k / float(self.fps)
            k += n
        cues["car.end"] = k / float(self.fps)
        return cues, k

    def describe(self):
        return {"think_speed": self.think_speed, "fits": self.fits, "t0_epoch": self.t0, "t1_epoch": self.t1,
                "pieces": [{"w0": p.w0, "w1": p.w1, "speed": p.speed, "label": p.label} for p in self.pieces],
                "clock_sync": None if self.sync is None else {"offset": self.sync.offset, "rate": self.sync.rate,
                                                              "residuals_s": self.sync.residuals()},
                "camera_frames": len(self.frames), "test": self.test}

    # -------------------------------------------------------------- frames
    def phone_frames(self, ffmpeg, piece, n):
        """n frames of the phone clip for one piece (black frames where the clip has none)."""
        size = PHONE[2:]
        blank = Image.new("RGB", size, (16, 18, 22))
        if not self.sync or not self.phone or not os.path.exists(self.phone):
            for _ in range(n):
                yield blank
            return
        p0, p1 = self.sync.phone(piece.w0), self.sync.phone(piece.w1)
        span = (p1 - p0)
        # ffmpeg's fps filter keeps, for output frame k, the last input frame before (k + 0.5) output frames: starting
        # the decode at p0 therefore shows p0 + (k + 0.5) * span / n, the same instants as timeline.frame_times
        start = p0
        speed = (span / n) * self.fps if span > 0 else 1.0
        if p1 <= 0:
            for _ in range(n):
                yield blank
            return
        cmd = F.decode_cmd(ffmpeg, self.phone, start, span, speed, self.fps, size, n)
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        bpf = size[0] * size[1] * 3
        got, last = 0, blank
        try:
            while got < n:
                buf = proc.stdout.read(bpf)
                if len(buf) < bpf:
                    break
                last = Image.frombytes("RGB", size, buf)
                got += 1
                yield last
        finally:
            proc.stdout.close()
            proc.wait()
        for _ in range(n - got):
            yield last

    def camera_tile(self, t, step):
        """While a step is being decided: the last frame its detector used, with the fused detections outlined.
        Otherwise (the car moving, or no detector frame logged): the newest frame at t, without detections."""
        if not hasattr(self, "_by_name"):
            self._by_name = {os.path.basename(p): (ft, p) for ft, p in self.frames}
        used = [self._by_name[n] for n, (k, _d) in self.dets.items() if k == step.k and n in self._by_name]
        if used and step.t0 <= t < step.move_t0:
            ft, path = max(used)
            _k, dets = self.dets[os.path.basename(path)]
            cap = "detector input of step %d (frame %s)" % (step.k, os.path.basename(path).split("_")[0].lstrip("0"))
            return P.camera_tile(CAM[2:], path, dets, self.camera, cap)
        i = TL.latest_at(self.frame_t, t)
        if i is None:
            return P.camera_tile(CAM[2:], None)
        ft, path = self.frames[i]
        cap = "live camera, frame %s, %.1f s old" % (os.path.basename(path).split("_")[0].lstrip("0") or "0",
                                                     max(0.0, t - ft))
        return P.camera_tile(CAM[2:], path, (), self.camera, cap)

    def frame(self, t, piece, phone_img):
        ep = self.ep
        v = E.view_at(ep, t, anim_s=0.0)
        step = ep.steps[v.k]
        img = Image.new("RGB", SIZE, D.BG)
        img.paste(phone_img, PHONE[:2])
        dr = ImageDraw.Draw(img)
        label = "phone video" + (" (stand-in clip)" if self.test else "")
        if self.sync:
            label += " · clip time %.1f s" % self.sync.phone(t)
        f = D.sans(20, "bold")
        w = D.text_w(dr, label, f)
        dr.rectangle([PHONE[0] + 12, PHONE[1] + 12, PHONE[0] + 28 + w, PHONE[1] + 46], fill=(0, 0, 0))
        dr.text((PHONE[0] + 20, PHONE[1] + 16), label, font=f, fill=(255, 255, 255))
        img.paste(self.camera_tile(t, step), CAM[:2])
        rays = []
        if v.belief:
            for d in step.observation.get("detections") or []:
                th = math.radians(v.belief["theta_deg"] + d.get("bearing_deg", 0.0))
                rays.append((v.belief["x_m"] + d["range_m"] * math.cos(th), v.belief["y_m"] + d["range_m"] * math.sin(th)))
        top = self.td.render(truth=v.truth, belief=v.belief, map_entries=v.map_entries, mapped=v.mapped,
                             trail_truth=v.trail_truth, trail_belief=v.trail_belief, start={"x_m": 0.0, "y_m": 0.0},
                             show_fov=v.truth is not None)
        if rays and v.belief:
            dt = ImageDraw.Draw(top)
            bx, by = self.td.px_out(v.belief["x_m"], v.belief["y_m"])
            for x, y in rays:
                px, py = self.td.px_out(x, y)
                dt.line([(bx, by), (px, py)], fill=D.SEEN, width=2)
                dt.ellipse([px - 5, py - 5, px + 5, py + 5], fill=D.SEEN_FILL, outline=D.SEEN)
        img.paste(top, TOPV[:2])
        dr.line([(TOPV[0], TOPV[1]), (TOPV[0], TOPV[1] + TOPV[3])], fill=D.RULE, width=2)
        stats = [("real time", "%02d:%02d" % divmod(int(t - self.t0), 60)), ("model cost", "US$%.2f" % v.cost),
                 ("tags mapped", "%d of %d" % (len(v.mapped), len(ep.tags)))]
        badge = TL.piece_badge(piece)
        badge = badge + (" time-lapse" if badge.startswith("×") else "")
        hdr = P.header(HEADER[2:], ("PIPELINE TEST" if self.test else "REAL CAR", self.inp.get("label", "")), stats,
                       badge, D.SEEN if piece.label == "think" else D.OK)
        img.paste(hdr, HEADER[:2])
        img.paste(P.step_panel(PANEL[2:], step, len(ep.steps), v.calls, v.report_shown), PANEL[:2])
        ImageDraw.Draw(img).line([(PANEL[0], PANEL[1]), (PANEL[0], PANEL[1] + PANEL[3])], fill=D.RULE, width=2)
        prov, dp = D.canvas(PROV[2:], (250, 228, 228) if self.test else (228, 232, 237))
        text = self.inp.get("provenance") or ("tags mapped: against the surveyed world file; the true pose (black) is "
                                              "the batch's tag resection when logged; amber rays: this step's detections "
                                              "drawn from the believed pose")
        dp.text((22, 9), D.ellipsize(dp, text, D.sans(19), PROV[2] - 44), font=D.sans(19),
                fill=D.BAD if self.test else D.MUTED)
        img.paste(prov, PROV[:2])
        return img

    def render(self, enc, ffmpeg):
        cues, total = self.plan()
        start = enc.n
        for cue, kind, payload, n in self.layout():
            if kind == "card":
                from .sim_part import card_from_spec
                enc.write(C.render_card(card_from_spec(self.specs[payload], self.nums, True)), n)
            else:
                k = 0
                for piece, m in zip(self.pieces, TL.frame_counts(self.pieces, self.fps)):
                    frames = TL.frame_times([piece], self.fps)
                    for (_i, w, _j), phone in zip(frames, self.phone_frames(ffmpeg, piece, m)):
                        enc.write(self.frame(w, piece, phone))
                        k += 1
        if enc.n - start != total:
            raise RuntimeError("car part: rendered %d frames, planned %d" % (enc.n - start, total))
        return cues


# ---------------------------------------------------------------- the pipeline test on stand-in data

STRIPE_BITS = 24


def stripe_value(epoch, base):
    return int(round((epoch - base) * 100)) % (1 << STRIPE_BITS)


def draw_stripe(dr, value, width, height, y0=0):
    cell = width / float(STRIPE_BITS)
    for b in range(STRIPE_BITS):
        on = (value >> (STRIPE_BITS - 1 - b)) & 1
        dr.rectangle([int(b * cell), y0, int((b + 1) * cell) - 1, y0 + height], fill=(255, 255, 255) if on else (0, 0, 0))


def read_stripe(img, box, y_frac=0.5):
    """Decode the stripe drawn across box = (x, y, w, h) of img (the phone tile's picture area)."""
    x, y, w, h = box
    gray = img.convert("L")
    val = 0
    cell = w / float(STRIPE_BITS)
    for b in range(STRIPE_BITS):
        px = int(x + (b + 0.5) * cell)
        py = int(y + h * y_frac)
        val = (val << 1) | (1 if gray.getpixel((px, py)) > 127 else 0)
    return val


def make_standin_phone(ffmpeg, out, epoch0, seconds, base, fps=30, size=(1280, 720)):
    """A stand-in phone clip whose frame k shows epoch0 + k / fps: a big clock like tools/session_clock.py, and the
    same time as a bit stripe across the top (stripe_value)."""
    with F.Encoder(ffmpeg, size, fps, out) as enc:
        for k in range(int(seconds * fps)):
            e = epoch0 + k / float(fps)
            img, dr = D.canvas(size, (24, 26, 30))
            draw_stripe(dr, stripe_value(e, base), size[0], 90, 0)
            dr.text((60, 150), "STAND-IN PHONE CLIP (pipeline test, not real footage)", font=D.sans(40, "bold"),
                    fill=(255, 196, 64))
            dr.text((60, 230), "fake session clock, epoch", font=D.sans(36), fill=(220, 220, 220))
            dr.text((60, 290), "%.1f" % e, font=D.mono(120, "bold"), fill=(255, 255, 255))
            dr.text((60, 470), "clip time %.2f s" % (k / float(fps)), font=D.sans(40), fill=(160, 200, 255))
            enc.write(img)
    return out


def make_standin_run(src_run, out_dir, t_start, t_end, n_steps, frames, move_s=1.2):
    """Write a stand-in run folder: the first n_steps rows of a simulated run, re-timed into [t_start, t_end] on the
    epoch clock (model turns spread over each step, a move of move_s at its end), and backend/steps.jsonl whose
    sensings point at the recorder session's frames nearest each step's start."""
    src = E.find_seed(src_run)
    rows = _jsonl(os.path.join(src_run, "seed_%d.jsonl" % src))[:n_steps]
    os.makedirs(os.path.join(out_dir, "backend"), exist_ok=True)
    span = (t_end - t_start) / n_steps
    moves, spend, backend = [], [], []
    ft = [t for t, _ in frames]
    for k, r in enumerate(rows):
        s0 = t_start + k * span
        think = span - move_s
        turns = r.get("turns") or []
        tot = sum(float(x.get("seconds") or 0) for x in turns) or 1.0
        acc = s0
        for x in turns:
            x["seconds"] = round(float(x.get("seconds") or 0) / tot * think, 3)
            acc += x["seconds"]
            spend.append({"t": round(acc, 3), "usd": x.get("cost_usd", 0.0)})
        r["seconds"] = round(think, 3)
        if r.get("executed_move"):
            moves.append({"step": k, "obs_id": r["observation"].get("obs_id"), "phase": "commanded",
                          "action": r["executed_move"]["action"], "t": round(acc, 3)})
            moves.append({"step": k, "obs_id": r["observation"].get("obs_id"), "phase": "result",
                          "action": r["executed_move"]["action"], "result": "done", "t": round(acc + move_s, 3)})
        i = TL.latest_at(ft, s0) or 0
        use = frames[max(0, i - 2): i + 1]
        dets = []
        for d in (r.get("raw") or {}).get("detections") or []:
            th = math.radians(d["bearing_deg"])
            dets.append({"det": d["det"], "id": d["id"], "base_xyz_m": [round(d["range_m"] * math.cos(th), 4),
                                                                       round(d["range_m"] * math.sin(th), 4), 0.23],
                         "normal_yaw_deg": None, "frames_seen": len(use)})
        backend.append({"type": "step", "step": k, "t_unix": round(s0, 3),
                        "sense": {"detections": r["observation"].get("detections") or []},
                        "frames": [{"file": os.path.basename(p), "t_resp_ns": int(t * 1e9)} for t, p in use],
                        "detections_internal": dets})
    if rows:
        rows[-1]["episode_end"] = {"ended_by": "test", "detail": "stand-in trace cut after %d steps" % n_steps}
    with open(os.path.join(out_dir, "seed_%d.jsonl" % src), "w", encoding="utf-8") as fh:
        fh.writelines(json.dumps(r) + "\n" for r in rows)
    for name, data in (("seed_%d.moves.jsonl" % src, moves), ("spend.jsonl", spend)):
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as fh:
            fh.writelines(json.dumps(x) + "\n" for x in data)
    with open(os.path.join(out_dir, "backend", "steps.jsonl"), "w", encoding="utf-8") as fh:
        fh.writelines(json.dumps(x) + "\n" for x in backend)
    return out_dir


def pipeline_test(build, session, n_steps=4, target_s=24.0):
    """Render the car layout on stand-in data and check the phone alignment; prints and returns the report."""
    root = build.root
    session = _rel(root, session or "data/real/20261118-015528-calibration-distance-check")
    frames = camera_index(session)
    if len(frames) < 4:
        raise SystemExit("car-test: %s has no camera frames" % session)
    out = build.path("car-test", "x")[:-2]
    t_start, t_end = frames[0][0] + 0.5, frames[-1][0] - 0.2
    run = make_standin_run(_rel(root, build.cfg["sim"]["run_dir"]), os.path.join(out, "run"), t_start, t_end,
                           n_steps, frames)
    base = math.floor(frames[0][0]) - 10
    phone0 = frames[0][0] - 4.0 + 0.137                     # the clip starts 3.863 s before the first frame
    phone = make_standin_phone(build.ffmpeg, os.path.join(out, "phone.mp4"), phone0, (t_end - phone0) + 3.0, base)
    # what a person would read off the clip: the clock at 1.0 s and near the end, to 0.1 s as the clock prints it
    late = round((t_end - phone0) + 1.0, 1)
    readings = ["1.0=%.1f" % (phone0 + 1.0), "%.1f=%.1f" % (late, phone0 + late)]
    inputs = {"recorder_session": os.path.relpath(session, root), "run_dir": os.path.relpath(run, root),
              "phone_video": os.path.relpath(phone, root), "clock_readings": readings,
              "world": "configs/arenas/real-room-plus8-160mm-nominal.json", "start_pose_world": "2.5,1.5,90",
              "label": "stand-in trace on a real recorder session", "test": True,
              "provenance": "PIPELINE TEST: stand-in phone clip and stand-in trace (simulated steps re-timed); camera "
                            "frames from recorder session %s; not a real episode" % os.path.basename(session)}
    cfg = dict(build.cfg["car"], target_s=target_s)
    car = CarPart(root, cfg, inputs, build.nums, build.cards, build.fps)
    mp4 = os.path.join(out, "car-test-%gs.mp4" % target_s)
    with F.Encoder(build.ffmpeg, build.size, build.fps, mp4) as enc:
        car.render(enc, build.ffmpeg)
    n_total = enc.n
    # decode every 5th frame of the episode and compare the stripe with the time that frame should show
    card_n = car.layout()[0][3]
    times = TL.frame_times(car.pieces, build.fps)
    errs = []
    cmd = [build.ffmpeg, "-hide_banner", "-loglevel", "error", "-i", mp4, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    bpf = build.size[0] * build.size[1] * 3
    k = 0
    scale = min(PHONE[2] / 1280.0, PHONE[3] / 720.0)
    pw, ph = int(1280 * scale), int(720 * scale)
    box = (PHONE[0] + (PHONE[2] - pw) // 2, PHONE[1] + (PHONE[3] - ph) // 2, pw, int(90 * scale))
    while True:
        buf = proc.stdout.read(bpf)
        if len(buf) < bpf:
            break
        j = k - card_n
        if j >= 0 and j % 5 == 0 and j < len(times):
            img = Image.frombytes("RGB", build.size, buf)
            got = read_stripe(img, box, 0.85)          # below the clip-time label
            want = stripe_value(times[j][1], base)
            if car.sync.phone(times[j][1]) > 0.1:
                errs.append((abs(got - want) / 100.0, car.pieces[times[j][2]].label))
        k += 1
    proc.wait()
    report = {"session": os.path.relpath(session, root), "camera_frames": len(frames), "output": os.path.relpath(mp4, root),
              "frames": n_total, "think_speed": car.think_speed, "fits": car.fits,
              "clock_readings": readings, "fitted_offset": car.sync.offset, "true_offset": phone0,
              "fitted_rate": car.sync.rate, "checked_frames": len(errs),
              "max_error_s": max(e for e, _ in errs) if errs else None,
              "mean_error_s": (sum(e for e, _ in errs) / len(errs)) if errs else None,
              "max_error_by_piece_s": {lab: max(e for e, l2 in errs if l2 == lab) for lab in {l2 for _, l2 in errs}},
              "pieces": [(round(p.w1 - p.w0, 2), p.label, p.speed) for p in car.pieces]}
    with open(os.path.join(out, "report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
    for k2, v in report.items():
        print("%-16s %s" % (k2, v))
    return report
