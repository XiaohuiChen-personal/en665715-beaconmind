"""The demo video in one command (plan M6.T11-T16 as re-scoped in plan/README.md section 3.6).

    python3 course-project/tools/demo_video.py all            # numbers, parts, cards, assembly, narration, stills
    python3 course-project/tools/demo_video.py plan           # the edit decision list only (no rendering)
    python3 course-project/tools/demo_video.py numbers        # every on-screen number with its source
    python3 course-project/tools/demo_video.py sim | car | cards | assemble | narration | stills
    python3 course-project/tools/demo_video.py car-test --session data/real/<id>   # the car layout on stand-in data

Settings: configs/demo_video.json (durations, the run folders, the car's inputs once they exist). Card texts:
presentation/demo-cards.json. Narration: presentation/demo-voiceover.template.md -> presentation/demo-voiceover.md.
Outputs (git-ignored): <out_dir>/ = course-project/data/video/: parts/*.mp4, cards/*.png, edl.json, cues.csv,
numbers.txt, BeaconMind-demo-silent.mp4 (and BeaconMind-demo.mp4 with the narration when narration_audio is set),
stills/.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24: wrote this command.
"""
import argparse
import csv
import json
import os
import sys
import time

import beaconmind

from . import episode as E
from . import ffmpeg as F
from . import narration as NR
from . import numbers as N
from . import timeline as TL


def _rel(root, p):
    return p if os.path.isabs(p) else os.path.join(root, p)


class Build:
    def __init__(self, root=None, config="configs/demo_video.json", ffmpeg=None, car_inputs=None):
        self.root = str(root or beaconmind.course_root())
        with open(_rel(self.root, config), encoding="utf-8") as fh:
            self.cfg = json.load(fh)
        self.fps = int(self.cfg["fps"])
        self.size = (int(self.cfg["width"]), int(self.cfg["height"]))
        self.out = _rel(self.root, self.cfg["out_dir"])
        self.ffmpeg_arg = ffmpeg
        self._ffmpeg = None
        with open(_rel(self.root, self.cfg["cards"]), encoding="utf-8") as fh:
            self.cards = json.load(fh)
        self.car_inputs = car_inputs if car_inputs is not None else (self.cfg.get("car") or {}).get("inputs")
        self._sim = self._car = self._nums = None

    # -------------------------------------------------------------- pieces
    @property
    def ffmpeg(self):
        if self._ffmpeg is None:
            self._ffmpeg = F.find_ffmpeg(self.ffmpeg_arg)
            if not self._ffmpeg:
                raise SystemExit("demo_video: no ffmpeg found (PATH, $BM_FFMPEG, ~/.local/bin/ffmpeg or the "
                                 "imageio-ffmpeg wheel); install nothing system-wide, ask first")
        return self._ffmpeg

    def path(self, *parts):
        p = os.path.join(self.out, *parts)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        return p

    @property
    def sim_episode(self):
        if not hasattr(self, "_ep"):
            self._ep = E.load_episode(_rel(self.root, self.cfg["sim"]["run_dir"]))
        return self._ep

    def _base_nums(self):
        """The numbers that do not depend on the video's own fitting (report, logs, scripted trace)."""
        if self._nums is None:
            cwd = os.getcwd()
            os.chdir(self.root)            # the sources are printed relative to course-project/
            try:
                n = N.report_numbers(self.root)
                N.rule_numbers(n)
                N.episode_numbers(n, self.sim_episode, self.cfg["sim"].get("evidence_summary"))
                if self.cfg["sim"].get("validator"):
                    N.scripted_numbers(n, self.cfg["sim"]["validator"]["trace"])
            finally:
                os.chdir(cwd)
            self._nums = n
        return self._nums

    @property
    def nums(self):
        n = self._base_nums()
        if not getattr(self, "_fitted_keys", False):
            sim = self.sim
            n.put("sim.factor", str(sim.factor), "fitted: the smallest whole factor that fits sim.target_s")
            d = self.cfg["sim"].get("detail_step")
            if d is not None:
                n.put("sim.detail-step", str(d), "configs/demo_video.json sim.detail_step")
                n.put("sim.detail-speed", str(int(self.cfg["sim"]["detail_speed"])), "configs/demo_video.json")
                n.put("sim.detail-calls", str(len(self.sim_episode.steps[d].calls)),
                      "seed_%d.jsonl step %d calls, counted" % (self.sim_episode.seed, d))
            self._fitted_keys = True
        return n

    @property
    def sim(self):
        if self._sim is None:
            from beaconmind.envs import kinsim_room as kr

            from .sim_part import SimPart
            self._sim = SimPart(self.root, self.cfg["sim"], self._base_nums(), self.sim_episode, self.cards,
                                self.fps, footprint=kr.default_footprint(), have_car=self.have_car)
        return self._sim

    @property
    def have_car(self):
        return bool(self.car_inputs)

    @property
    def car(self):
        if self._car is None and self.have_car:
            from .car_part import CarPart
            self._car = CarPart(self.root, self.cfg["car"], self.car_inputs, self.nums, self.cards, self.fps)
        return self._car

    # -------------------------------------------------------------- the edit decision list
    def plan(self):
        """Sequence with durations and absolute cue times, computed without rendering."""
        sim_cues, sim_frames = self.sim.plan()
        durations = {"sim": sim_frames / float(self.fps)}
        part_cues = {"sim": sim_cues}
        if self.have_car:
            car_cues, car_frames = self.car.plan()
            durations["car"] = car_frames / float(self.fps)
            part_cues["car"] = car_cues
        items = [it for it in self.cfg["sequence"] if it["kind"] == "card" or it["id"] in durations]
        seq = []
        t = 0
        for it in items:
            if it["kind"] == "card":
                n = max(1, int(float(it["seconds"]) * self.fps + 0.5))
            else:
                n = int(round(durations[it["id"]] * self.fps))
            seq.append({"id": it["id"], "kind": it["kind"], "start_s": t / float(self.fps), "frames": n,
                        "dur_s": n / float(self.fps)})
            t += n
        cues = {}
        for s in seq:
            if s["kind"] == "card":
                cues[s["id"]] = s["start_s"]
            else:
                for k, v in part_cues[s["id"]].items():
                    cues[k] = s["start_s"] + v
        return {"sequence": seq, "cues": cues, "total_s": t / float(self.fps), "total_frames": t,
                "sim": {"factor": self.sim.factor, "detail": self.cfg["sim"].get("detail_step"),
                        "pieces": [{"w0": p.w0, "w1": p.w1, "speed": p.speed, "label": p.label, "hold_s": p.hold_s}
                                   for p in self.sim.pieces],
                        "source_total_s": self.sim_episode.total_s},
                "car": self.car.describe() if self.have_car else None}

    def write_plan(self):
        p = self.plan()
        with open(self.path("edl.json"), "w", encoding="utf-8") as fh:
            json.dump(p, fh, indent=1)
        with open(self.path("cues.csv"), "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["output_s", "cue"])
            for k, v in sorted(p["cues"].items(), key=lambda kv: kv[1]):
                w.writerow(["%.2f" % v, k])
        return p

    # -------------------------------------------------------------- rendering
    def render_sim(self):
        out = self.path("parts", "sim.mp4")
        t = time.time()
        with F.Encoder(self.ffmpeg, self.size, self.fps, out) as enc:
            self.sim.render(enc)
        print("sim part: %s, %d frames, %.1f s of video, rendered in %.0f s" % (
            os.path.relpath(out, self.root), enc.n, enc.n / float(self.fps), time.time() - t))
        return out

    def render_car(self):
        if not self.have_car:
            print("car part: no inputs configured (configs/demo_video.json car.inputs is null): left out")
            return None
        out = self.path("parts", "car.mp4")
        t = time.time()
        with F.Encoder(self.ffmpeg, self.size, self.fps, out) as enc:
            self.car.render(enc, self.ffmpeg)
        print("car part: %s, %d frames, %.1f s, rendered in %.0f s" % (os.path.relpath(out, self.root), enc.n,
                                                                       enc.n / float(self.fps), time.time() - t))
        return out

    def card_image(self, card_id):
        from . import cards as C
        from .sim_part import card_from_spec
        return C.render_card(card_from_spec(self.cards[card_id], self.nums, self.have_car), self.size)

    def render_cards(self):
        outs = {}
        for it in self.cfg["sequence"]:
            if it["kind"] != "card":
                continue
            img = self.card_image(it["id"])
            png = self.path("cards", "%s.png" % it["id"])
            img.save(png)
            mp4 = self.path("parts", "card-%s.mp4" % it["id"])
            with F.Encoder(self.ffmpeg, self.size, self.fps, mp4) as enc:
                enc.write(img, max(1, int(float(it["seconds"]) * self.fps + 0.5)))
            outs[it["id"]] = mp4
        print("cards: %s" % ", ".join(sorted(outs)))
        return outs

    def assemble(self):
        p = self.write_plan()
        files = []
        for s in p["sequence"]:
            f = self.path("parts", ("card-%s.mp4" % s["id"]) if s["kind"] == "card" else ("%s.mp4" % s["id"]))
            if not os.path.exists(f):
                raise SystemExit("demo_video: %s is missing; render it first" % os.path.relpath(f, self.root))
            files.append(f)
        lst = self.path("concat.txt")
        with open(lst, "w", encoding="utf-8") as fh:
            fh.write(F.concat_list_text(files))
        silent = self.path("BeaconMind-demo-silent.mp4")
        F.run(F.concat_cmd(self.ffmpeg, lst, silent))
        info = F.probe(self.ffmpeg, silent)
        print("assembled: %s, %.2f s, %s frames (planned %d)" % (os.path.relpath(silent, self.root),
                                                                info.get("duration_s", -1), info.get("frames"),
                                                                p["total_frames"]))
        audio = self.cfg.get("narration_audio")
        if audio:
            final = self.path("BeaconMind-demo.mp4")
            F.run(F.mux_cmd(self.ffmpeg, silent, _rel(self.root, audio), final))
            print("with narration: %s" % os.path.relpath(final, self.root))
        else:
            print("no narration audio configured (narration_audio is null): the silent video is the output")
        return silent, info, p

    # -------------------------------------------------------------- narration, numbers, stills
    def narration(self):
        p = self.plan()
        with open(_rel(self.root, self.cfg["narration_template"]), encoding="utf-8") as fh:
            blocks = NR.parse_template(fh.read())
        rows, missing = NR.build(blocks, p["cues"], p["total_s"], self.nums, self.cfg.get("words_per_min", 130))
        header = ("# Demo video: narration script\n\n"
                  "Generated by `python3 course-project/tools/demo_video.py narration` from "
                  "`presentation/demo-voiceover.template.md` and the video's edit decision list; do not edit this "
                  "file, edit the template. Times are output times of `BeaconMind-demo-silent.mp4` (m:ss.s). "
                  "Every number in the text comes from the evidence and log files (`demo_video.py numbers`).\n\n"
                  "How to record (Xiaohui): play the silent video in QuickTime Player and, in a second window, File > "
                  "New Audio Recording; read each block from its start time. Save as `narration.m4a` in "
                  "`course-project/data/video/`, set `narration_audio` in `configs/demo_video.json` to "
                  "`data/video/narration.m4a` and run `demo_video.py assemble`. The video also works silent: the "
                  "cards and the on-screen labels carry the story.")
        footer = ("## Generative-AI disclosure\n\n"
                  "AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24: drafted the narration template and wrote "
                  "the generator that times it against the video. Xiaohui Chen records the voice-over and may reword "
                  "any block.")
        md = NR.render_markdown(rows, missing, p["total_s"], header, footer, self.cfg.get("words_per_min", 130))
        out = _rel(self.root, self.cfg["narration_out"])
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(md)
        over = [r["cue"] for r in rows if r["over"]]
        print("narration: %s, %d blocks, over budget: %s" % (os.path.relpath(out, self.root), len(rows),
                                                             ", ".join(over) or "none"))
        return rows, missing

    def write_numbers(self):
        with open(self.path("numbers.txt"), "w", encoding="utf-8") as fh:
            fh.write("# key | value | source. Generated by tools/demo_video.py numbers.\n")
            fh.write(self.nums.manifest())
        return self.path("numbers.txt")

    def stills(self, video=None, times=None):
        video = video or self.path("BeaconMind-demo-silent.mp4")
        p = self.plan()
        if times is None:
            times = {}
            for k, v in p["cues"].items():
                times[k] = v + 0.6
            for s in p["sequence"]:
                times["mid-" + s["id"]] = s["start_s"] + s["dur_s"] / 2
            times["last"] = p["total_s"] - 0.1
        outs = []
        for name, t in sorted(times.items(), key=lambda kv: kv[1]):
            png = self.path("stills", "%07.2f-%s.png" % (t, name))
            F.run(F.still_cmd(self.ffmpeg, video, t, png))
            outs.append(png)
        print("stills: %d in %s" % (len(outs), os.path.relpath(os.path.dirname(outs[0]), self.root)))
        return outs


def main(argv=None):
    ap = argparse.ArgumentParser(prog="demo_video.py", description=__doc__.split("\n\n")[0])
    ap.add_argument("what", choices=["all", "plan", "numbers", "check", "sim", "car", "cards", "assemble",
                                     "narration", "stills", "car-test"])
    ap.add_argument("--config", default="configs/demo_video.json")
    ap.add_argument("--ffmpeg", default=None)
    ap.add_argument("--session", default=None, help="car-test: a recorder session folder")
    ap.add_argument("--no-car", action="store_true", help="leave the car part out even if inputs are configured")
    ap.add_argument("--car-target-s", type=float, default=24.0, help="car-test: length of the test part")
    a = ap.parse_args(argv)
    b = Build(config=a.config, ffmpeg=a.ffmpeg, car_inputs={} if a.no_car else None)
    if a.what == "numbers":
        sys.stdout.write(b.nums.manifest())
        print("written: %s" % os.path.relpath(b.write_numbers(), b.root))
    elif a.what == "check":
        bad = 0
        for what, mine, theirs, ok in E.check_against_summary(b.sim_episode):
            print("%-28s logs %-14s summary %-14s %s" % (what, mine, theirs, "OK" if ok else "DIFFERS"))
            bad += not ok
        return 1 if bad else 0
    elif a.what == "plan":
        p = b.write_plan()
        for s in p["sequence"]:
            print("%7.2f s  %-11s %-5s %6.2f s" % (s["start_s"], s["id"], s["kind"], s["dur_s"]))
        print("total %.2f s (%d frames); simulation time-lapse x%d over %.1f s of logged time" % (
            p["total_s"], p["total_frames"], p["sim"]["factor"], p["sim"]["source_total_s"]))
    elif a.what == "sim":
        b.render_sim()
    elif a.what == "car":
        b.render_car()
    elif a.what == "cards":
        b.render_cards()
    elif a.what == "assemble":
        b.assemble()
    elif a.what == "narration":
        b.narration()
    elif a.what == "stills":
        b.stills()
    elif a.what == "car-test":
        from .car_part import pipeline_test
        pipeline_test(b, a.session, target_s=a.car_target_s)
    elif a.what == "all":
        for what, mine, theirs, ok in E.check_against_summary(b.sim_episode):
            if not ok:
                raise SystemExit("demo_video: the logs disagree with the summary on %s (%s vs %s)" % (what, mine, theirs))
        b.write_numbers()
        b.render_sim()
        b.render_car()
        b.render_cards()
        b.assemble()
        b.narration()
        b.stills()
    return 0


if __name__ == "__main__":
    sys.exit(main())
