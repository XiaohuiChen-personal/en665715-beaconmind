#!/usr/bin/env python3
"""Run a batch of real-car episodes with nobody at the car (plan/README.md section 3.6 "Unattended batches").

    car_batch.py run --world course-project/configs/arenas/<world>.json --scenarios course-project/configs/arenas/real-room-scenarios.json \
        --initial-pose 2.5,1.5,90 --episodes 10 --policy b2 [--out DIR] [--max-range 2.0] [--dry-run]
    car_batch.py record-pass --operator <name> --stand-session <session> --floor-session <session> [--notes TEXT]
    car_batch.py clear-halt --out DIR --operator <name>
    car_batch.py status --out DIR

`run` on the real car (tools/car_batch.sh starts the recorder and the container) refuses to start unless:
- the pass marker data/real/ATTENDED_PASS.json exists, is under 7 days old, and the car's constants and the
  executor's code have not changed since it was written. The marker is written by `record-pass`, which a person runs
  after the attended stand test and floor check of evidence/M3/M3.T6/README.md section 5 have passed, naming the two
  recorded sessions;
- the R2 recorder is recording (data/real/.active); it must stay active for the whole batch (a stopped recorder halts);
- the project latch data/LATCH is clear and no HALT.LATCH is left in the batch folder.
It then sets the drive map and reads it back, finds the car from the surveyed tags (a full circle), drives to each
episode's start pose, runs the episode through harness/closed_loop.py, and measures the end pose. Every move is checked
against the room first. Any health problem ends the whole batch: nothing is retried; an operator looks at the car,
clears the halt (and the latch) by name, and runs the same command again, which skips the finished episodes.

--dry-run does all of it on the simulated car in the simulated room (no ROS, no camera, no marker, no recorder).
--policy: b2 (the coded procedure, free) or a model key of configs/providers*.json (needs --cap-usd > 0).
The world file, the start poses and the range limit are parameters: the tag configuration decides them.
--detector-noise configs/detector_noise.json (bm.detector_noise/1, written by tools/tag_pilot.py analyze): the
per-tag fix sigma from the tag pilot's measured range and bearing errors (batch.fix_sigma_from_detector_noise).
Without it the assumed 0.03 m + 0.04 x range. The manifest's params.fix_sigma_source says which (configs/dv.json,
the frozen study's design values, is not read for this and not changed).
--dv configs/dv-real.json (tools/real_dv.py, after the pilot): the design values the agent's tools and the car code
read during the batch (beaconmind/dv_real.py); default for a dry run: the frozen configs/dv.json. A real batch needs
both --detector-noise and a --dv made from that same detector-noise file (sha256), whose range limit is --max-range:
the agent's sigmas and the batch's fix sigma then come from one measurement (the lead's decision, 2026-11-25). The
manifest records params.dv_file (file, sha12) and params.sigma_sources (whether the two agree, with the sha256).

Exit status: 0 the batch is complete; 3 it halted; 2 it refused to start.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote this tool.
AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25: the range check's bias and window from --detector-noise.
AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24: --detector-noise; only the first of several stop signals
counts; --dv.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "beaconmind" / "src"))

from beaconmind import dv_real                              # noqa: E402
from beaconmind.car import batch as B                      # noqa: E402
from beaconmind.car.latch import Latch                     # noqa: E402
from beaconmind.car.movelog import active_session_dir      # noqa: E402

DEFAULT_PROMPT = ROOT / "prompts" / "robot_system_prompt_v3.3.txt"
MARKER = ROOT / "data" / "real" / "ATTENDED_PASS.json"


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def pose_arg(text):
    try:
        x, y, th = (float(v) for v in text.split(","))
    except ValueError:
        raise argparse.ArgumentTypeError("a pose is x,y,theta_deg (arena frame), got %r" % text)
    return {"x_m": x, "y_m": y, "theta_deg": th}


def start_poses(args):
    poses = []
    if args.scenarios:
        doc = json.loads(pathlib.Path(args.scenarios).read_text(encoding="utf-8"))
        wanted = args.scenario_ids.split(",") if args.scenario_ids else None
        for sc in doc["scenarios"]:
            if wanted is None or sc["id"] in wanted:
                poses.append(dict(sc["start_pose"], id=sc["id"]))
        if wanted and len(poses) != len(wanted):
            sys.exit("--scenario-ids: not all of %s are in %s" % (wanted, args.scenarios))
    for i, text in enumerate(args.start or []):
        name, _, rest = text.rpartition(":")
        poses.append(dict(pose_arg(rest), id=name or "start%d" % (i + 1)))
    if not poses:
        sys.exit("give --scenarios FILE or at least one --start [id:]x,y,theta_deg")
    return poses


def recorder_silent(session, max_age_s=120.0, now=None):
    """None while the recorder is writing: some file under the session's logs/ changed in the last two minutes (its
    ping and Wi-Fi logs are written every few seconds). A recorder that crashed leaves data/real/.active behind; this
    is how the batch notices."""
    newest = 0.0
    logs = os.path.join(session, "logs")
    try:
        for name in os.listdir(logs):
            newest = max(newest, os.path.getmtime(os.path.join(logs, name)))
    except OSError:
        return "the recorder's logs folder %s cannot be read" % logs
    age = (time.time() if now is None else now) - newest
    return None if age <= max_age_s else "the recorder has written nothing for %.0f s" % age


INTERRUPTS = ("SIGINT", "SIGTERM", "SIGHUP")


def make_recorder_check(session, data_dir=None):
    """The batch's recorder check: None while `session` is the active recorder session and writing, else why not.
    A function of its own, so nothing in cmd_run can rebind what it compares: the first real batch (2026-11-25) halted
    before any move with "the recorder session SIGHUP is no longer active" because the closure read a variable that
    the signal loop reused (fixed in 07dd34f; AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-25)."""
    name = os.path.basename(os.path.normpath(session))
    data = str(data_dir or ROOT / "data")

    def check():
        now = active_session_dir(data)
        if not now or os.path.basename(os.path.normpath(now)) != name:
            return "the recorder session %s is no longer active" % name
        return recorder_silent(session)
    return check


def _later_signal(_signum, _frame):
    """A stop signal after the first: nothing to do, the stop is under way. (A Python handler rather than SIG_IGN: a
    signal already pending when the handler changes would otherwise be reported as "ignored due to race condition".)"""


def _as_interrupt(_signum, _frame):
    """docker stop, a closed terminal, kill, Ctrl+C: end as Ctrl+C does, with a halt record. Only the first signal
    counts: the later ones are ignored, so a second Ctrl+C (or docker's proxy repeating one) cannot break off the
    move's stop or the halt record half written. (docker stop's SIGKILL after its grace period still ends a hang.)"""
    import signal
    for name in INTERRUPTS:
        signal.signal(getattr(signal, name), _later_signal)
    raise KeyboardInterrupt


def load_runner_tool():
    """tools/closed_loop_run.py as a module: its driver builder and its list of hashed harness files."""
    spec = importlib.util.spec_from_file_location("closed_loop_run", ROOT / "tools" / "closed_loop_run.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_parser():
    ap = argparse.ArgumentParser(prog="car_batch.py", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--world", required=True, help="bm.world/1 file with the surveyed tags and the driving area")
    run.add_argument("--scenarios", help="file with start poses (configs/arenas/real-room-scenarios.json)")
    run.add_argument("--scenario-ids", help="comma-separated ids of --scenarios to use, in this order of the file")
    run.add_argument("--start", action="append", help="[id:]x,y,theta_deg, arena frame; repeatable")
    run.add_argument("--initial-pose", required=True,
                     help="where the car stands now (tape): x,y,theta_deg; or `last` on a rerun when nobody moved the car "
                          "since the batch stopped (the pose the batch last tracked is used)")
    run.add_argument("--episodes", type=int, default=1)
    run.add_argument("--policy", default="b2")
    run.add_argument("--label", help="the batch's name: its folder is course-project/data/batches/<label>, which every "
                                      "rerun of the batch finds again (halt, manifest and spend live there)")
    run.add_argument("--out", help="batch folder instead of data/batches/<label> (required with --dry-run)")
    run.add_argument("--max-steps", type=int, default=150)
    run.add_argument("--max-range", type=float, default=2.0, help="detections beyond this range are not used, m")
    run.add_argument("--seed0", type=int, default=1)
    run.add_argument("--cap-usd", type=float, default=0.0, help="hard spend cap of the batch; required > 0 for a model")
    run.add_argument("--start-tol-m", type=float, default=0.20)
    run.add_argument("--start-tol-deg", type=float, default=20.0)
    run.add_argument("--start-attempts", type=int, default=3)
    run.add_argument("--wall-margin", type=float, default=0.15, help="smallest distance of the footprint to the edge of the driving area, m")
    run.add_argument("--no-fix-steps", type=int, default=24)
    run.add_argument("--min-vsys-mv", type=int, default=4300, help="the Pico's supply below this halts (not the motor battery)")
    run.add_argument("--min-forward-speed", type=float, default=0.0, help="a FORWARD_25 peaking below this halts, m/s; 0 = off")
    run.add_argument("--episode-minutes", type=float, default=60.0)
    run.add_argument("--batch-hours", type=float, default=6.0)
    run.add_argument("--batch-steps", type=int, default=2500)
    run.add_argument("--drive-map", default="0.25,0.33")
    run.add_argument("--prompt", default=str(DEFAULT_PROMPT))
    run.add_argument("--latch", help="project latch file (default course-project/data/LATCH)")
    run.add_argument("--camera-url", help="camera base URL (default: the relay, car/camera.py RELAY_URL)")
    run.add_argument("--tag-size", type=float, default=0.16)
    run.add_argument("--tag-height", type=float, default=0.23, help="tag centre height for the detector's height rule, m")
    run.add_argument("--dry-run", action="store_true", help="simulated car in the simulated room; no ROS")
    run.add_argument("--dry-seed", type=int, default=1)
    run.add_argument("--detector-noise", help="bm.detector_noise/1 file of the tag pilot (configs/detector_noise.json): "
                                              "the fix sigma from its measured errors; default: the assumed "
                                              "0.03 m + 0.04 x range")
    run.add_argument("--dv", help="design-values file: configs/dv-real.json (tools/real_dv.py) or configs/dv.json; "
                                   "required for a real batch, default for a dry run: the frozen configs/dv.json")
    run.add_argument("--marker", default=str(MARKER))

    rp_ = sub.add_parser("record-pass")
    rp_.add_argument("--operator", required=True)
    rp_.add_argument("--stand-session", required=True)
    rp_.add_argument("--floor-session", required=True)
    rp_.add_argument("--world", required=True, help="the world file (surveyed tag centres) the batches will use")
    rp_.add_argument("--notes", default="")
    rp_.add_argument("--marker", default=str(MARKER))

    ch = sub.add_parser("clear-halt")
    ch.add_argument("--out", required=True)
    ch.add_argument("--operator", required=True)
    st = sub.add_parser("status")
    st.add_argument("--out", required=True)
    return ap


def dv_file_problems(args):
    """A --dv file that cannot be used at all (refused before anything else)."""
    path = dv_real.resolve_arg(args.dv)
    return [] if path is None else dv_real.check_file(path)


def noise_agreement(args):
    """(text for the manifest, problems): do the agent's sigmas (--dv) and the batch's fix sigma (--detector-noise)
    come from one and the same detector-noise file (sha256)? A real batch must have both, from the same file, and the
    --dv file's range limit must be --max-range (the lead's decision of 2026-11-25: real batches run with the pilot's
    file); a dry run is only refused when two given files disagree."""
    path = dv_real.resolve_arg(args.dv)
    frozen = path is None or dv_real.record(path)["frozen"]
    noise_sha = dv_real.sha256(args.detector_noise) if args.detector_noise else None
    dv_sha = None if frozen else dv_real.noise_source(path)
    problems = []
    if not frozen:
        limit = float(json.loads(pathlib.Path(path).read_text(encoding="utf-8"))["values"]["reject_range_above_m"]["value"])
        if abs(limit - args.max_range) > 1e-9:
            problems.append("--dv %s has the range limit %.2f m, --max-range is %.2f m: give the same"
                            % (path, limit, args.max_range))
    if noise_sha and not frozen and dv_sha != noise_sha:
        problems.append("--dv %s was not made from --detector-noise %s (its sigmas name %s): make it again with "
                        "tools/real_dv.py" % (path, args.detector_noise, "sha256 %s" % dv_sha if dv_sha else "no file"))
    if not args.dry_run:
        if not args.dv:
            problems.append("a real batch needs --dv course-project/configs/dv-real.json (tools/real_dv.py, after the tag "
                            "pilot)")
        if not noise_sha:
            problems.append("a real batch needs --detector-noise course-project/configs/detector_noise.json (the tag "
                            "pilot's file; the batch's fix sigma and the agent's sigmas both come from it)")
        if args.dv and frozen:
            problems.append("a real batch needs --dv made from its --detector-noise (configs/dv-real.json), not the "
                            "frozen configs/dv.json: the agent's sigmas and the batch's fix sigma must come from one file")
    if noise_sha and dv_sha == noise_sha:
        text = "agree: the agent's sigmas (--dv) and the batch's fix sigma come from the same detector-noise file (sha256 %s)" % noise_sha
    else:
        text = "not the same file: the agent's sigmas are %s, the batch's fix sigma %s" % (
            "the frozen study's" if frozen else ("from sha256 %s" % dv_sha if dv_sha else "from no named file"),
            "from sha256 %s" % noise_sha if noise_sha else "the assumed 0.03 + 0.04 r")
    return text, problems


def fix_sigma(args):
    """(fix_sigma_a_m, fix_sigma_b, source text) from --detector-noise, or the assumed values."""
    defaults = B.BatchParams(world_path="", start_poses=[], initial_pose={})
    if not args.detector_noise:
        return defaults.fix_sigma_a_m, defaults.fix_sigma_b, defaults.fix_sigma_source
    path = pathlib.Path(args.detector_noise)
    try:
        raw = path.read_bytes()
        model = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError) as exc:
        sys.exit("--detector-noise %s cannot be read: %s" % (path, exc))
    try:
        from beaconmind.schemas import validate
        errors = validate("detector_noise", model)
    except ImportError:
        errors = []             # (no jsonschema here: the checks of fix_sigma_from_detector_noise still apply)
    if errors:
        sys.exit("--detector-noise %s is not a valid bm.detector_noise/1 document: %s" % (path, "; ".join(errors[:3])))
    try:
        a, b, text = B.fix_sigma_from_detector_noise(model, args.max_range)
    except ValueError as exc:
        sys.exit("--detector-noise %s: %s" % (path, exc))
    if model.get("max_range_m") is not None and args.max_range > float(model["max_range_m"]) + 1e-9:
        log("WARNING: --max-range %.2f m is beyond the %.2f m the tag pilot found reliable (%s)"
            % (args.max_range, float(model["max_range_m"]), path))
        text += "; WARNING: --max-range above the pilot's reliable range"
    rel = os.path.relpath(path.resolve(), ROOT)
    return a, b, "%s sha256:%s: %s" % (rel, hashlib.sha256(raw).hexdigest()[:12], text)


def range_model(args):
    """{range_bias_a_m, range_bias_b, range_min_m} for the batch's range check from --detector-noise (the tag pilot's
    range bias, measured - true = a + b x range, and the near end of its reliable window), or {} for the defaults
    (no bias, 0.3 m). The file was read and checked by fix_sigma already."""
    if not args.detector_noise:
        return {}
    model = json.loads(pathlib.Path(args.detector_noise).read_text(encoding="utf-8"))
    bias = model.get("range_bias_m") or {}
    out = {"range_bias_a_m": float(bias.get("a", 0.0)), "range_bias_b": float(bias.get("b", 0.0))}
    if model.get("min_range_m") is not None:
        out["range_min_m"] = float(model["min_range_m"])
    return out


def params_from(args, world_path, agreement=""):
    duty, speed = (float(v) for v in args.drive_map.split(","))
    sigma_a, sigma_b, source = fix_sigma(args)
    rec = dv_real.record(dv_real.resolve_arg(args.dv))
    dv_text = "%s sha12 %s%s" % (rec["file"], rec["sha12"], " (frozen)" if rec["frozen"] else
                                 " (differs from the frozen file in %s)" % ", ".join(sorted(rec["differs_from_frozen"])))
    return B.BatchParams(
        world_path=os.path.relpath(world_path, ROOT), start_poses=start_poses(args), initial_pose=args.initial_pose,
        episodes=args.episodes, policy=args.policy, max_steps=args.max_steps, max_range_m=args.max_range,
        seed0=args.seed0, start_tol_m=args.start_tol_m, start_tol_deg=args.start_tol_deg,
        start_attempts=args.start_attempts, wall_margin_m=args.wall_margin, no_fix_steps=args.no_fix_steps,
        min_vsys_mv=args.min_vsys_mv, min_forward_speed_mps=args.min_forward_speed,
        episode_wall_s=args.episode_minutes * 60.0, batch_wall_s=args.batch_hours * 3600.0,
        batch_steps=args.batch_steps, cap_usd=args.cap_usd, drive_map=(duty, speed), fix_sigma_a_m=sigma_a,
        fix_sigma_b=sigma_b, fix_sigma_source=source, dv_file=dv_text, sigma_sources=agreement, **range_model(args))


def cmd_run(args):
    from beaconmind import dv as dvmod
    from beaconmind.harness import closed_loop as cl
    from beaconmind.harness import replay as rp

    world_path = pathlib.Path(args.world).resolve()
    world = json.loads(world_path.read_text(encoding="utf-8"))
    if not args.out and not args.label:
        sys.exit("give --label (or --out)")
    if args.label and ("/" in args.label or args.label.startswith(".")):
        sys.exit("--label is a name, not a path")
    out = pathlib.Path(args.out) if args.out else ROOT / "data" / "batches" / args.label
    if args.initial_pose == "last":
        try:
            last = json.loads((out / "manifest.json").read_text(encoding="utf-8"))["last_tracked_pose_world"]
            args.initial_pose = dict(last["pose"])
        except (OSError, ValueError, KeyError):
            sys.exit("--initial-pose last: %s has no tracked pose; give the taped pose" % (out / "manifest.json"))
    else:
        args.initial_pose = pose_arg(args.initial_pose)
    if not 1 <= args.max_steps <= cl.STEPS_BUDGET or args.episodes < 1:
        sys.exit("--max-steps must be 1..%d and --episodes at least 1" % cl.STEPS_BUDGET)
    problems = dv_file_problems(args)
    if not problems:
        agreement, sources = noise_agreement(args)
        problems = sources if args.dry_run else []
    if problems:
        print("refused, nothing was sent:\n- " + "\n- ".join(problems), file=sys.stderr)
        return 2
    params = params_from(args, world_path, agreement)
    missing_dv = [] if args.dry_run else sources         # (listed with the pass marker's refusals)
    tool = load_runner_tool()
    driver, cfg, cfg_path, sdk = tool.build_driver(args.policy)
    if cfg is not None and args.cap_usd <= 0:
        sys.exit("a model policy needs a positive --cap-usd (the hard spend cap of the batch)")
    latch = Latch(args.latch)
    session = None
    if args.dry_run:
        if not args.out:
            sys.exit("--dry-run needs --out")
        dry_latch = Latch(out / "DRY_LATCH")           # a dry run never touches the project latch
        rig = B.dry_rig(world, args.initial_pose, latch=dry_latch, seed=args.dry_seed, max_range_m=args.max_range)
        recorder_check, marker_path = None, None
    else:
        problems = B.check_pass_marker(args.marker, str(ROOT), world_path=str(world_path)) + missing_dv
        session = active_session_dir(str(ROOT / "data"))
        if session is None:
            problems.append("no recorder session is active (rule R2): start through tools/car_batch.sh, or "
                            "record_session.sh start <label> --camera off")
        if latch.is_set():
            problems.append("the project latch is set: %s" % (latch.read() or {}).get("reason"))
        if problems:
            print("refused, nothing was sent:\n- " + "\n- ".join(problems), file=sys.stderr)
            return 2
        from beaconmind.car import camera, ros_io
        try:
            link = ros_io.RosCarLink(latch=latch, log_root=os.path.dirname(latch.path))
        except RuntimeError as exc:
            print("refused, nothing was sent: %s" % exc, file=sys.stderr)
            return 2
        cam = camera.HttpCamera(args.camera_url or camera.RELAY_URL, save_dir=os.path.join(session, "frames_backend"))
        detect = camera.perception_detector(tag_size_m=args.tag_size, tag_center_height_m=args.tag_height,
                                            max_range_m=args.max_range)
        rig = B.Rig(link, cam, detect, latch=latch, real=True, notes={"session": os.path.basename(session)})
        recorder_check = make_recorder_check(session)
        marker_path = os.path.join(session, "batch_markers.jsonl")

    out.mkdir(parents=True, exist_ok=True)
    spend = out / "spend.jsonl"
    budget = rp.Budget(args.cap_usd if args.cap_usd > 0 else float("inf"), rp.spent_in(spend), path=spend)
    dv = dvmod.load_dv()
    extra = {"prompt": tool.sha12(args.prompt), "dv": tool.sha12(ROOT / "configs" / "dv.json"),
             "dv_file": params.dv_file,
             "world": hashlib.sha256(world_path.read_bytes()).hexdigest()[:12], "provider_entry": cfg,
             "agent": driver.header(), "harness": {f: tool.sha12(tool.SRC / f) for f in tool.HASHED},
             "batch_code": tool.sha12(ROOT / "beaconmind" / "src" / "beaconmind" / "car" / "batch.py"),
             "dry_run": bool(args.dry_run), "dry_seed": args.dry_seed if args.dry_run else None}
    runner = B.BatchRunner(params, rig, world, out, driver=driver,
                           system_text=pathlib.Path(args.prompt).read_text(encoding="utf-8"), budget=budget, log=log,
                           run_episode=cl.run_episode, autolatch_contacts=int(dv["autolatch_contacts"]),
                           config_extra=extra, recorder_check=recorder_check, marker_path=marker_path)
    import signal
    before = {name: signal.getsignal(getattr(signal, name)) for name in INTERRUPTS}
    for name in INTERRUPTS:
        signal.signal(getattr(signal, name), _as_interrupt)
    log("batch %s: %d episodes of %s on %s, world %s, out %s" % (
        runner.config, params.episodes, params.policy, "the simulated car (dry run)" if args.dry_run else "THE REAL CAR",
        world.get("world_id"), out))
    log("fix sigma %.4f + %.4f x range m: %s" % (params.fix_sigma_a_m, params.fix_sigma_b, params.fix_sigma_source))
    log("range check: tags %.2f to %.2f m, range bias %+.4f %+.4f x range m removed" % (
        params.range_min_m, params.max_range_m, params.range_bias_a_m, params.range_bias_b))
    log("design values: %s" % params.dv_file)
    try:
        with dv_real.use_dv(dv_real.resolve_arg(args.dv)):     # what the agent's tools and the car code read
            result = runner.run()
    finally:
        try:
            rig.link.close()
        except Exception as exc:    # noqa: BLE001
            log("closing the car link: %s" % exc)
        for name, handler in before.items():        # no signal came: give a caller in this process its handlers back
            if handler is not None and signal.getsignal(getattr(signal, name)) is _as_interrupt:
                signal.signal(getattr(signal, name), handler)
    print(open(out / "summary.txt", encoding="utf-8").read() if (out / "summary.txt").exists() else result)
    return {"complete": 0, "halted": 3}.get(result["status"], 2)


def cmd_record_pass(args):
    try:
        if B.file_sha12(args.world) is None:
            raise ValueError("the world file %s cannot be read" % args.world)
        record = B.write_pass_marker(args.marker, str(ROOT), args.operator, args.stand_session, args.floor_session,
                                     args.notes, world_path=args.world)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print("pass recorded by %s: stand %s, floor %s -> %s" % (record["operator"], record["stand_session"],
                                                           record["floor_session"], args.marker))
    return 0


def cmd_clear_halt(args):
    from beaconmind.harness import validator as vd
    path = os.path.join(args.out, "HALT.LATCH")
    try:
        cleared = vd.clear_latch_file(path, args.operator)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    manifest = os.path.join(args.out, "manifest.json")
    try:        # the operator has looked at the car: a run that died without a record may be resumed now
        with open(manifest, encoding="utf-8") as handle:
            m = json.load(handle)
        if m.get("status") in ("running", "halted"):
            m["status"] = "cleared"
            m.setdefault("cleared", []).append({"operator": args.operator.strip(), "time_utc": B.utc()})
            B.write_json(manifest, m)
    except (OSError, ValueError):
        pass
    print("halt cleared by %s" % args.operator.strip() if cleared else "no HALT.LATCH in %s" % args.out)
    return 0


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.command == "run":
        return cmd_run(args)
    if args.command == "record-pass":
        return cmd_record_pass(args)
    if args.command == "clear-halt":
        return cmd_clear_halt(args)
    path = os.path.join(args.out, "summary.txt")
    print(open(path, encoding="utf-8").read() if os.path.exists(path) else "no batch in %s" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
