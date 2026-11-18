#!/usr/bin/env python3
"""Drive the car one bounded move at a time, read its state, stop it, clear the latch (work list 2.6 and 2.7).

    car_move.py state                                   read the car's telemetry; publishes nothing
    car_move.py move FORWARD_25 --i-am-at-the-car       one C2 move: FORWARD_25, FORWARD_10, BACKWARD_10,
                                                        TURN_LEFT_30, TURN_RIGHT_30
    car_move.py move FORWARD_25 --sim                   the same move on the simulated car, no ROS
    car_move.py stop-key                                the STOP program: SPACE = stop + latch (own terminal, -it)
    car_move.py stop                                    STOP once, now (no keyboard), and latch
    car_move.py clear-latch --operator <name>           remove the latch after checking the car
    car_move.py arm --i-am-at-the-car                   send the firmware's arm marker (after a restart or a link drop)
    car_move.py set-map 0.25 0.33 --i-am-at-the-car     set the firmware's drive map (a restart puts 0.46 / 0.215 back)
    car_move.py sim-car                                 a simulated car on the real topics; refuses ROS_DOMAIN_ID 0

Run it in the beaconmind-ros container through tools/car.sh, which sets the ROS environment. A real move
(ROS_DOMAIN_ID 0) needs, besides the flag: no latch, the recorder running (rule R2: data/real/.active), and the
STOP program running (its heartbeat file data/STOP_ALIVE). Every move writes a JSONL log of each command and
telemetry sample into the recorder's session (moves/), and prints the bm.move_result/1 record.

Exit status: 0 the move ended `done`; 1 any other result; 2 the tool refused before talking to the car.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote this tool.
"""
import argparse
import json
import os
import sys
import time

_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "beaconmind", "src")
if os.path.isdir(_SRC) and os.path.abspath(_SRC) not in [os.path.abspath(p) for p in sys.path]:
    sys.path.insert(0, os.path.abspath(_SRC))

from beaconmind.car import config as C                     # noqa: E402
from beaconmind.car.latch import Latch                     # noqa: E402
from beaconmind.car.moves import ACTIONS, make_move        # noqa: E402
from beaconmind.car.movelog import active_session_dir      # noqa: E402
from beaconmind.car import ros_io                          # noqa: E402

ACK = "--i-am-at-the-car"


def build_parser():
    ap = argparse.ArgumentParser(prog="car_move.py", description=__doc__.split("\n")[0])
    ap.add_argument("--latch", help="latch file (default: course-project/data/LATCH)")
    sub = ap.add_subparsers(dest="command", required=True)

    mv = sub.add_parser("move", help="run one bounded move")
    mv.add_argument("action", choices=sorted(ACTIONS))
    mv.add_argument(ACK, dest="ack", action="store_true",
                    help="you are beside the car, the recorder runs, and a hand is on the motor battery's switch")
    mv.add_argument("--sim", action="store_true", help="simulated car in this process; nothing is published")
    mv.add_argument("--prev-forward", type=float, help="BACKWARD_10 only: what the previous forward move covered, m")
    mv.add_argument("--unstamped", action="store_true",
                    help="send motion commands without the send time (the car then cannot drop late ones)")
    mv.add_argument("--left-gain", type=float, default=1.0, help="--sim only: the left wheel's speed share (0.7 = carpet)")

    sub.add_parser("state", help="print the car's state (read-only)")
    sub.add_parser("stop", help="STOP now and latch")
    sub.add_parser("stop-key", help="the interactive STOP program")

    cl = sub.add_parser("clear-latch", help="remove the STOP latch")
    cl.add_argument("--operator", required=True, help="your name: you checked the car and it may move again")

    arm = sub.add_parser("arm", help="send the arm marker")
    arm.add_argument(ACK, dest="ack", action="store_true")

    sm = sub.add_parser("set-map", help="set the firmware's drive map")
    sm.add_argument("min_duty", type=float)
    sm.add_argument("max_speed_mps", type=float)
    sm.add_argument(ACK, dest="ack", action="store_true")

    sc = sub.add_parser("sim-car", help="simulated car node (never on ROS_DOMAIN_ID 0)")
    sc.add_argument("--seconds", type=float)
    sc.add_argument("--left-gain", type=float, default=1.0)
    sc.add_argument("--ready-file")
    return ap


def preflight_real_move(latch, data_dir, domain, now_unix=None):
    """Why a real move may not start, as a list of sentences (empty = go). On a domain other than 0 only the
    latch counts: nothing there can reach the car."""
    problems = []
    record = latch.read()
    if record is not None:
        problems.append("the STOP latch is set (%s, by %s, %s): check the car, then clear-latch --operator <name>"
                        % (record.get("reason"), record.get("by"), record.get("time_utc")))
    if domain == ros_io.REAL_CAR_DOMAIN:
        if active_session_dir(data_dir) is None:
            problems.append("no recorder session is active (rule R2): bash course-project/tools/record_session.sh "
                            "start <label> first")
        if not ros_io.stop_program_alive(ros_io.stop_heartbeat_path(data_dir), now_unix=now_unix, domain=domain):
            problems.append("no STOP program is running on this ROS domain with the car's /pico/cmd_vel in reach: "
                            "start `car.sh stop-key` in its own terminal first")
    return problems


def _print(obj):
    print(json.dumps(obj, indent=1, default=str))


def cmd_move(args, latch):
    cmd = make_move(args.action, int(time.time()), "cli-%s" % time.strftime("%Y%m%dT%H%M%S", time.gmtime()),
                    prev_forward_m=args.prev_forward)
    if args.sim:
        from beaconmind.car.link import default_sim_link
        link = default_sim_link(latch=latch, left_gain=args.left_gain)
        result = link.execute(cmd)
        _print({"sim": True, "command": cmd, "result": result, "diag": link.last_diag, "truth": link.sim.truth()})
        return 0 if result["result"] == "done" else 1
    if not args.ack:
        print("refused: a real move needs %s (you are beside the car, the recorder runs, a hand is on the motor "
              "battery's switch). Nothing was sent." % ACK, file=sys.stderr)
        return 2
    if args.action == "BACKWARD_10" and args.prev_forward is None:
        print("refused: BACKWARD_10 is only for directly after a forward move (C2); give what that move covered "
              "with --prev-forward <metres>. Nothing was sent.", file=sys.stderr)
        return 2
    domain = ros_io.ros_domain_id()
    problems = preflight_real_move(latch, os.path.dirname(latch.path), domain)
    if problems:
        print("refused, nothing was sent:\n- " + "\n- ".join(problems), file=sys.stderr)
        return 2
    cfg = C.load_config(stamp_commands=not args.unstamped)
    try:
        link = ros_io.RosCarLink(cfg=cfg, latch=latch, log_root=os.path.dirname(latch.path))
    except RuntimeError as exc:
        print("refused, nothing was sent: %s" % exc, file=sys.stderr)
        return 2
    try:
        before = link.car_state()
        result = link.execute(cmd)
        _print({"ros_domain_id": domain, "command": cmd, "car_before": before, "result": result,
                "diag": link.last_diag, "log": link.last_log_path, "log_error": link.last_log_error})
    except KeyboardInterrupt:
        print("interrupted: zeros were sent; the car also stops by itself within 0.5 s", file=sys.stderr)
        return 1
    finally:
        link.close()
    return 0 if result["result"] == "done" else 1


def cmd_state(_args, latch):
    link = ros_io.RosCarLink(latch=latch, wait_telemetry_s=3.0, read_only=True)
    try:
        time.sleep(1.2)     # one /pico/drive/status period
        state = link.car_state()
        state["latch"] = latch.read()
        state["recorder_session"] = active_session_dir(os.path.dirname(latch.path))
        state["stop_program_alive"] = ros_io.stop_program_alive(
            ros_io.stop_heartbeat_path(os.path.dirname(latch.path)), domain=ros_io.ros_domain_id())
        state["commands_published_by_this_tool"] = link.published
        _print(state)
    finally:
        link.close()
    return 0


def cmd_clear(args, latch):
    try:
        record = latch.clear(args.operator)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print("no latch at %s" % latch.path if record is None else
          "latch cleared by %s (it was: %s, by %s, %s)" % (args.operator.strip(), record.get("reason"),
                                                          record.get("by"), record.get("time_utc")))
    return 0


def cmd_operator(args, latch):
    if not args.ack:
        print("refused: this talks to the car and needs %s. Nothing was sent." % ACK, file=sys.stderr)
        return 2
    if latch.is_set():
        print("refused: the STOP latch is set. Nothing was sent.", file=sys.stderr)
        return 2
    try:
        link = ros_io.RosCarLink(latch=latch, log_root=os.path.dirname(latch.path), wait_telemetry_s=3.0)
    except RuntimeError as exc:
        print("refused, nothing was sent: %s" % exc, file=sys.stderr)
        return 2
    try:
        if args.command == "arm":
            ok = link.arm()
            print("armed" if ok else "the car did not report itself armed within 6 s")
            return 0 if ok else 1
        got = link.set_drive_map(args.min_duty, args.max_speed_mps)
        print("the car reports drive map %s" % (got,))
        ok = got is not None and abs(got[0] - args.min_duty) < 0.0015 and abs(got[1] - args.max_speed_mps) < 0.0015
        return 0 if ok else 1
    finally:
        link.close()


def _on_sigterm(_signum, _frame):
    raise KeyboardInterrupt     # `docker stop` ends a move the way Ctrl+C does: zeros first


def main(argv=None):
    args = build_parser().parse_args(argv)
    latch = Latch(args.latch)
    if args.command in ("move", "arm", "set-map"):
        import signal
        signal.signal(signal.SIGTERM, _on_sigterm)
    if args.command == "move":
        return cmd_move(args, latch)
    if args.command == "state":
        return cmd_state(args, latch)
    if args.command == "clear-latch":
        return cmd_clear(args, latch)
    if args.command in ("arm", "set-map"):
        return cmd_operator(args, latch)
    if args.command in ("stop", "stop-key"):
        extra = ["--latch", latch.path] + (["--now"] if args.command == "stop" else [])
        return ros_io.stop_main(extra)
    if args.command == "sim-car":
        from beaconmind.car.simcar import SimCarParams
        ros_io.run_sim_car_node(SimCarParams(left_gain=args.left_gain), duration_s=args.seconds,
                                ready_file=args.ready_file)
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
