"""Unattended batches of real-car episodes (plan/README.md section 3.6 "Unattended batches", approved 2026-11-18).

With nobody at the car the motor battery stays on between episodes. This module is what stands in for the person:

    PoseTracker   the car's pose in the arena frame: odometry between fixes, tag resection when tags are in view
    MoveGuard     refuses a move whose swept footprint would come nearer than a margin to the edge of the known
                  driving area (walls, the desk box, the drive-area edge), or when the pose is too uncertain
    Monitor       the health halts. A halt ends the WHOLE batch, never only the episode, and is never retried:
                  it writes <batch>/HALT.LATCH (which the closed-loop harness obeys) and, for anything that
                  questions the car itself, the project latch data/LATCH. An operator clears both by name.
    BatchEnv      the environment the harness drives: RealCarEnv plus tracker, guard and monitor on every step
    BatchRunner   the batch: drive map, localisation scan, transit to the start pose, start scan, the episode, end
                  scan, manifest and summary; resumable (finished episodes are skipped; an unfinished episode on a
                  real car is never replayed, it gets a new attempt)

Everything is in the ARENA frame of the world file (bm.world/1) except what the harness sees, which is the map
frame of the episode's start pose as the start scan measured it (contract C1).

Ground truth (plan 3.6): the pose from the surveyed tags, by a full circle at each episode's start and end and by
the tags in view at each step (resection.py), each with its uncertainty; a step with no fix says so and carries
the pose tracked from the last fix. This replaces tape for unattended runs; tape bounds it at the batch's first
start, its last end and one spot check.

Nothing here imports ROS. The same code runs on the simulated car (dry_rig): that is the --dry-run and the tests.

A tag whose surveyed centre is wrong (a number misread on the mounting sheet) would pull the tracked pose with it.
TagCheck compares every tag with the others in each fit of four tags or more (resection.check_tags), adds the
comparisons up over the batch, halts on a tag that keeps disagreeing (`tag_survey`), and lets a tag steer a step's
fix only once it has been compared closely enough that an error which could still hide in it stays inside the guard's
margin.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote the batch runner.
AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24: added TagCheck, the `tag_survey` halt and the trusted-tag
rule for a step's fix (conflicts still judged on every tag), and the fix sigma from the tag pilot's detector-noise file
(fix_sigma_from_detector_noise, fix_sigma_source). 2026-11-25: the odometry-bias halt weighs each fix by its noise
and asks for significance (a false halt of the first real practice batch); the scale is checked by the ranges along
each straight move (range_scale_of_move), which the camera measures well, and over each episode between its circles.
"""
import hashlib
import json
import math
import os
import time
from dataclasses import asdict, dataclass, field

from .backend import RealCarEnv, compose
from .moves import ACTIONS
from .odometry import wrap_deg
from .resection import position_fix, resect, usable_detection

ASSUMED_FIX_SIGMA = "assumed: 0.03 m + 0.04 x range (plan 3.6; the tag pilot's figures are to replace it)"

FORWARD_STEPS = (("FORWARD_25", 0.25), ("FORWARD_10", 0.10))
TURN_DEG = 30.0
MANIFEST_SCHEMA = "bm.car_batch/1"
# halts that question the car or its surroundings also set the project latch; the others only stop the batch
SAFETY_HALTS = ("telemetry_stale", "command_timeout", "link_lost", "car_restart", "car_disarmed", "imu", "camera",
                "supply_low", "stall", "move_timeout", "slow", "no_fix", "fix_conflict", "outside_drive_area",
                "executor_refused", "guard_blocked", "start_pose", "drive_map", "harness_latch", "error", "pose_uncertain",
                "odometry_scale",
                "episode_wall_clock", "detector", "recorder", "tag_survey")


@dataclass
class BatchParams:
    """Everything that defines a batch. The tag configuration is still being chosen, so the world file, the start
    poses and the range limit are parameters, never constants."""
    world_path: str
    start_poses: list                   # [{"id", "x_m", "y_m", "theta_deg"}] in the arena frame; used in turn
    initial_pose: dict                  # where the operator put the car (tape), arena frame
    episodes: int = 1
    policy: str = "b2"
    max_steps: int = 150
    max_range_m: float = 2.0            # detections beyond it are not used for fixes
    seed0: int = 1
    # start pose
    start_tol_m: float = 0.20
    start_tol_deg: float = 20.0
    start_attempts: int = 3
    scan_attempts: int = 2
    scan_sigma_max_m: float = 0.15      # a full-circle fix less certain than this is not taken as a pose
    scan_rms_max_m: float = 0.08        # nor one whose tags disagree by more than this (a tag surveyed wrongly)
    fix_floor_m: float = 0.05           # no fix makes the position more certain than this: fixes of one tag repeat
                                        # its survey and range-scale error, they do not average it away
    camera_probe_after_s: float = 3.0   # a move after this long without a frame asks the camera for one first
    odometry_bias_max: float = 0.12     # fixes that keep landing ahead of (or behind) the odometry by more than this
                                        # share of the distance driven halt the batch (a wrong encoder scale)
    max_blind_travel_m: float = 0.75    # no straight move may take the distance driven since the last tag fix past
                                        # this: whatever the odometer's error, it then stays inside the wall margin
    transit_scale_tol: float = 0.10     # the transit between two full-circle fixes must measure the same length by
    transit_scale_min_m: float = 0.30   # odometry and by the tags within this share, when it is at least this long
    range_scale_tol: float = 0.12       # the ranges to the tags seen before and after each straight move must change
                                        # by what the odometry says within this share (median over the moves so far)
    range_scale_move_sigma: float = 0.05    # one move's scatter (the real car: 0.92 to 1.03 over six moves): with n
                                        # moves the limit is at least 3 x this / sqrt(n), so one move alone needs 15 %
    # guard
    wall_margin_m: float = 0.15
    sigma_block_m: float = 0.25
    initial_sigma_m: float = 0.10
    initial_sigma_deg: float = 10.0
    initial_gate_m: float = 0.5         # the first circle's fix may differ from the taped pose by at most this
    initial_gate_deg: float = 30.0
    # the noise one tag's position is assumed to have in a fix: sigma = fix_sigma_a_m + fix_sigma_b x range. These
    # set every stated uncertainty and through it the guard's margin; the tag pilot (work list 2.4) should replace them
    fix_sigma_a_m: float = 0.03
    fix_sigma_b: float = 0.04
    fix_sigma_source: str = ASSUMED_FIX_SIGMA   # where the two numbers above came from (recorded in the manifest)
    dv_file: str = "configs/dv.json (frozen)"   # the design values the agent's tools read (car_batch.py --dv)
    sigma_sources: str = ""             # whether --dv's sigmas and the fix sigma come from one detector-noise file
    # the check of the surveyed tags against each other (TagCheck): a tag is halted on when the other tags put it,
    # over all the batch's fits so far, farther from its surveyed centre than max(tag_check_min_m, tag_check_k sigma);
    # it may steer a step's fix by itself only while that distance is at most max(tag_check_min_m, tag_trust_k sigma)
    # and that bound is at most tag_trust_max_m: a tag more than 0.30 m wrong is never trusted. 0.30 m: a tag 0.3 m
    # wrong gave the review's probe 4 cm of wall clearance, no contact.
    tag_check_k: float = 4.0
    tag_trust_k: float = 3.0
    tag_check_min_m: float = 0.15
    tag_trust_max_m: float = 0.30
    tag_trust: bool = True              # False: every tag steers fixes as before 2026-11-24 (tests and comparison only)
    # health
    telemetry_max_age_s: float = 1.0
    min_vsys_mv: int = 4300
    no_fix_steps: int = 24              # two full circles of views without one tag fix
    fix_conflicts: int = 3
    camera_stale_steps: int = 2
    min_forward_speed_mps: float = 0.0  # 0 = off: a FORWARD_25 slower than this at its peak halts (fading batteries)
    # caps
    episode_wall_s: float = 3600.0
    batch_wall_s: float = 6 * 3600.0
    batch_steps: int = 2500
    cap_usd: float = 0.0
    drive_map: tuple = (0.25, 0.33)

    def digest(self):
        """What makes two runs the same batch. The initial pose is left out: after a halt the car stands somewhere
        else, and the operator who clears the halt gives its new taped pose to the resumed run."""
        d = asdict(self)
        d.pop("initial_pose")
        return hashlib.sha256(json.dumps(d, sort_keys=True, default=str).encode()).hexdigest()[:12]


def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def write_json(path, obj):
    tmp = "%s.tmp.%d" % (path, os.getpid())
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(obj, handle, indent=1, default=str)
        handle.write("\n")
    os.replace(tmp, path)


def to_map_pose(start, pose):
    """An arena-frame pose in the map frame of `start` (plan C1)."""
    th = math.radians(start["theta_deg"])
    dx, dy = pose["x_m"] - start["x_m"], pose["y_m"] - start["y_m"]
    return {"x_m": dx * math.cos(th) + dy * math.sin(th), "y_m": -dx * math.sin(th) + dy * math.cos(th),
            "theta_deg": wrap_deg(pose["theta_deg"] - start["theta_deg"])}


# ---------------------------------------------------------------- pose tracking

class PoseTracker:
    """The car's pose in the arena frame with a one-number uncertainty for position and one for heading.
    Odometry moves the pose and grows the uncertainty; a fix is blended in by inverse variance."""

    def __init__(self, pose, sigma_xy_m, sigma_theta_deg, floor_m=0.05):
        self.pose = {k: float(pose[k]) for k in ("x_m", "y_m", "theta_deg")}
        self.sigma_xy_m, self.sigma_theta_deg = float(sigma_xy_m), float(sigma_theta_deg)
        self.floor_m = floor_m
        self.rejected = 0               # fixes not taken because they disagreed with the tracked pose
        self._leg = [0.0, 0.0]          # displacement by odometry since the last fix, arena frame
        self.bias_sum = 0.0             # sum over fixes of (fix - tracked) along the leg driven
        self.bias_travel = 0.0          # sum of the legs' lengths
        self.bias_fixes = 0
        self.bias_sxy = 0.0             # weighted least squares of (innovation along the leg) = scale x leg, weights
        self.bias_sxx = 0.0             # 1 / (fix sigma^2 + tracked sigma^2): see odometry_bias()
        self.dead_reckoned = None       # the pose by odometry alone since mark_dead_reckoning()
        self.range_moves = []           # (tags over odometry, range pairs) of each straight move: range_scale()
        self.travel_since_fix_m = 0.0   # distance driven by odometry since the last fix that was taken
        self.last_tags = None           # the tags of the last fix taken
        self.steps_since_fix = 0
        self.conflicts = 0
        self.fixes = 0

    def predict(self, odo):
        dist = math.hypot(odo["forward_m"], odo["left_m"])
        before = self.pose
        self.pose = compose(self.pose, odo)
        self._leg[0] += self.pose["x_m"] - before["x_m"]
        self._leg[1] += self.pose["y_m"] - before["y_m"]
        if self.dead_reckoned is not None:
            self.dead_reckoned = compose(self.dead_reckoned, odo)
        self.travel_since_fix_m += dist
        # errors of separate moves add in quadrature: 5 % of the distance plus 2 mm, the heading uncertainty swung
        # over the distance; for the heading 2 % of the turn plus 0.05 degrees (the gyro)
        self.sigma_xy_m = math.sqrt(self.sigma_xy_m ** 2 + (0.002 + 0.05 * dist) ** 2
                                    + (math.radians(self.sigma_theta_deg) * dist) ** 2)
        self.sigma_theta_deg = math.hypot(self.sigma_theta_deg, 0.05 + 0.02 * abs(odo["dtheta_deg"]))
        self.steps_since_fix += 1

    def disagrees(self, fix):
        """True when a fix is farther from the tracked position than the two uncertainties explain (three combined
        sigmas plus 5 cm). Such a fix is not blended in: either it or the tracked pose is wrong, and repeating it
        halts the batch (fix_conflict)."""
        d = math.hypot(fix["pose"]["x_m"] - self.pose["x_m"], fix["pose"]["y_m"] - self.pose["y_m"])
        return d > 3.0 * math.hypot(self.sigma_xy_m, fix["sigma_xy_m"]) + 0.05

    def _note_innovation(self, fix):
        """Before a fix is taken: how far it is from the tracked position ALONG the leg driven since the last fix.
        Noise averages out over fixes; an odometer that reads short or long does not."""
        leg = math.hypot(self._leg[0], self._leg[1])
        if leg >= 0.05:
            ux, uy = self._leg[0] / leg, self._leg[1] / leg
            innovation = (fix["pose"]["x_m"] - self.pose["x_m"]) * ux + (fix["pose"]["y_m"] - self.pose["y_m"]) * uy
            self.bias_sum += innovation
            self.bias_travel += leg
            self.bias_fixes += 1
            var = max(float(fix.get("sigma_xy_m") or 0.05), 0.01) ** 2 + self.sigma_xy_m ** 2
            self.bias_sxy += leg * innovation / var
            self.bias_sxx += leg * leg / var
        self._leg = [0.0, 0.0]
        self.travel_since_fix_m = 0.0

    def range_scale(self, min_moves=1):
        """(median over the straight moves of the distance by the tags' ranges over the distance by odometry, moves,
        range pairs), or None while fewer than min_moves straight moves had a tag in view before and after."""
        if len(self.range_moves) < max(1, min_moves):
            return None
        scales = sorted(m[0] for m in self.range_moves)
        n = len(scales)
        median = scales[n // 2] if n % 2 else 0.5 * (scales[n // 2 - 1] + scales[n // 2])
        return median, n, sum(m[1] for m in self.range_moves)

    def mark_dead_reckoning(self):
        """From here on also keep the pose that odometry alone gives (no fix blended in)."""
        self.dead_reckoned = dict(self.pose)
        return dict(self.pose)

    def odometry_bias(self):
        """(scale error: the share of the driven distance by which fixes land ahead of the odometry, metres driven,
        fixes, its standard error), or None while there is too little to judge (under 1 m or 5 fixes).

        Each fix's innovation along the leg driven since the fix before is modelled as scale x leg + noise of variance
        (fix sigma^2 + tracked sigma^2), and the scale is the weighted least-squares estimate. (Until 2026-11-25 it was
        the sum of the innovations over the sum of the legs, which treats a fix 3 m away after a 5 cm leg like one
        after 25 cm: on the real car one single-tag fix 0.21 m off, after five turns had moved the axle 5 cm, took that
        number from +5 % to -24 % and halted the practice batch, while the transit check between two full circles
        read the scale as 1.008.)"""
        if self.bias_travel < 1.0 or self.bias_fixes < 5 or self.bias_sxx <= 0:
            return None
        return self.bias_sxy / self.bias_sxx, self.bias_travel, self.bias_fixes, 1.0 / math.sqrt(self.bias_sxx)

    def set(self, pose, sigma_xy_m, sigma_theta_deg):
        self._note_innovation({"pose": pose, "sigma_xy_m": sigma_xy_m})
        self.last_tags = None
        self.pose = {k: float(pose[k]) for k in ("x_m", "y_m", "theta_deg")}
        self.sigma_xy_m, self.sigma_theta_deg = max(float(sigma_xy_m), self.floor_m), float(sigma_theta_deg)
        self.steps_since_fix, self.conflicts = 0, 0
        self.fixes += 1

    def _same_tags(self, fix):
        """True when this fix rests on exactly the tags of the last one taken. It then repeats that fix's survey
        and range-scale error: the pose may follow it, the uncertainty may not shrink on it."""
        tags = sorted(str(t) for t in fix.get("tags") or [])
        same = bool(tags) and tags == self.last_tags
        self.last_tags = tags or None
        return same

    def correct(self, fix):
        self._note_innovation(fix)
        same = self._same_tags(fix)
        a, b = self.sigma_xy_m ** 2, max(fix["sigma_xy_m"], 0.01) ** 2
        w = a / (a + b)
        self.pose["x_m"] += w * (fix["pose"]["x_m"] - self.pose["x_m"])
        self.pose["y_m"] += w * (fix["pose"]["y_m"] - self.pose["y_m"])
        if not same:
            self.sigma_xy_m = max(math.sqrt(a * b / (a + b)), self.floor_m)
        c, d = self.sigma_theta_deg ** 2, max(fix["sigma_theta_deg"], 0.2) ** 2
        w = c / (c + d)
        self.pose["theta_deg"] = wrap_deg(self.pose["theta_deg"] + w * wrap_deg(fix["pose"]["theta_deg"] - self.pose["theta_deg"]))
        self.sigma_theta_deg = math.sqrt(c * d / (c + d))
        self.steps_since_fix, self.conflicts = 0, 0
        self.fixes += 1

    def correct_position(self, fix):
        """A position-only fix (one tag and the tracked heading): the heading and its uncertainty stay."""
        self._note_innovation(fix)
        same = self._same_tags(fix)
        a, b = self.sigma_xy_m ** 2, max(fix["sigma_xy_m"], 0.01) ** 2
        w = a / (a + b)
        self.pose["x_m"] += w * (fix["pose"]["x_m"] - self.pose["x_m"])
        self.pose["y_m"] += w * (fix["pose"]["y_m"] - self.pose["y_m"])
        if not same:
            self.sigma_xy_m = max(math.sqrt(a * b / (a + b)), self.floor_m)
        self.steps_since_fix, self.conflicts = 0, 0
        self.fixes += 1

    def snapshot(self):
        return {"pose": dict(self.pose), "sigma_xy_m": round(self.sigma_xy_m, 4),
                "sigma_theta_deg": round(self.sigma_theta_deg, 2), "steps_since_fix": self.steps_since_fix}


class TagCheck:
    """Per surveyed tag, the evidence that it is where the world file says: every comparison with the other tags of
    a fit (resection.check_tags) is added as a vector with weight 1/sigma^2. The weighted mean m is where the other
    tags put this tag, relative to its survey, sigma_m its uncertainty.

    flagged: |m| > max(min_m, k sigma_m): the tag is not where the world file says (or not flat, or covered) -> the
    batch halts (`tag_survey`). trusted: compared at least once and |m| <= t = max(min_m, trust_k sigma_m) <=
    trust_max_m. So a tag whose mean says it is more than trust_max_m off is never trusted, and one that has not been
    compared closely enough (t above trust_max_m) is not trusted yet. The halt asks for more (k > trust_k): a tag
    between the two is set aside without stopping the batch. Only trusted tags steer a step's fix (two tags, or one tag
    and the tracked heading); full circles use every tag, and that is how tags are checked. The evidence lives in this
    process: a resumed batch checks again from its first circle."""

    def __init__(self, k=4.0, min_m=0.15, trust_max_m=0.30, trust_k=3.0):
        self.k, self.min_m, self.trust_max_m, self.trust_k = k, min_m, trust_max_m, trust_k
        self.stats = {}                 # uid -> {"id", "sw", "swx", "swy", "n", "worst"}

    def add(self, check, where=""):
        """Add one fit's comparisons. Returns the tags flagged now (uids). An unresolved check (four or fewer tags
        that disagree, no clean reference) adds nothing."""
        if not check or not check.get("resolved", False):
            return []
        for row in check["tags"]:
            if not (row["sigma_m"] > 0 and math.isfinite(row["sigma_m"])):
                continue
            st = self.stats.setdefault(str(row["tag"]), {"id": row["id"], "sw": 0.0, "swx": 0.0, "swy": 0.0, "n": 0,
                                                         "worst": None})
            w = 1.0 / row["sigma_m"] ** 2
            st["sw"] += w
            st["swx"] += w * row["dx_m"]
            st["swy"] += w * row["dy_m"]
            st["n"] += 1
            if st["worst"] is None or row["residual_m"] > st["worst"]["residual_m"]:
                st["worst"] = dict(row, where=where)
        return self.flagged()

    def verdict(self, uid):
        st = self.stats.get(str(uid))
        if not st or st["sw"] <= 0:
            return None
        sigma = 1.0 / math.sqrt(st["sw"])
        mx, my = st["swx"] / st["sw"], st["swy"] / st["sw"]
        limit = max(self.min_m, self.k * sigma)
        trust = max(self.min_m, self.trust_k * sigma)
        offset = math.hypot(mx, my)
        return {"tag": str(uid), "id": st["id"], "n": st["n"], "dx_m": round(mx, 4), "dy_m": round(my, 4),
                "offset_m": round(offset, 4), "sigma_m": round(sigma, 4), "limit_m": round(limit, 4),
                "trust_limit_m": round(trust, 4), "flagged": offset > limit,
                "trusted": offset <= trust <= self.trust_max_m}

    def flagged(self):
        return [uid for uid in self.stats if self.verdict(uid)["flagged"]]

    def trusted(self):
        return {uid for uid in self.stats if self.verdict(uid)["trusted"]}

    def snapshot(self):
        return {uid: dict(self.verdict(uid), worst=self.stats[uid]["worst"]) for uid in sorted(self.stats)}


def tag_survey_detail(tagcheck, uid, tags):
    """The halt's text for a tag that disagrees with the others."""
    v = tagcheck.verdict(uid)
    survey = next((t for t in tags if str(t.get("uid", t["id"])) == str(uid)), None)
    where = ""
    if survey is not None:
        where = " (%.2f, %.2f); the other tags put it at (%.2f, %.2f)" % (
            survey["x_m"], survey["y_m"], survey["x_m"] + v["dx_m"], survey["y_m"] + v["dy_m"])
    return ("tag %s (id %s) is %.2f m from its surveyed centre%s, over %d comparisons (limit %.2f m). Look at the "
            "tag (flat, uncovered, not moved), measure its centre again, correct the world file and record-pass "
            "--world with it; then run the batch under a new label" % (uid, v["id"], v["offset_m"], where, v["n"],
                                                                       v["limit_m"]))


def fix_sigma_from_detector_noise(model, max_range_m):
    """(fix_sigma_a_m, fix_sigma_b, description) from the tag pilot's bm.detector_noise/1 model (tools/tag_pilot.py
    analyze writes configs/detector_noise.json). The batch's per-tag sigma is one isotropic number, a + b x range,
    and must cover both of the pilot's error directions up to max_range_m:
      along the line of sight: |range bias| + range sigma = (|ba| + sa) + (|bb| + sb) r  (the bias is not corrected
        by the detector, so it is counted as error);
      across it: r x (|bearing bias| + bearing sigma at max_range_m) in radians = c r.
    The length of the two-vector (a1 + b1 r, c r) is at most a1 + hypot(b1, c) r, which is what is returned.
    ValueError when the model is not a usable bm.detector_noise/1 document."""
    if not isinstance(model, dict) or model.get("schema") != "bm.detector_noise/1":
        raise ValueError("not a bm.detector_noise/1 document")
    try:
        rb, rs, bs = model["range_bias_m"], model["range_sigma_m"], model["bearing_sigma_deg"]
        nums = [float(rb["a"]), float(rb["b"]), float(rs["a"]), float(rs["b"]), float(model["bearing_bias_deg"]),
                float(bs["a"]), float(bs["b"]), float(max_range_m)]
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("the detector-noise model lacks a number: %s" % exc)
    if not all(math.isfinite(v) for v in nums) or nums[2] < 0 or nums[3] < 0 or nums[5] < 0 or nums[6] < 0:
        raise ValueError("the detector-noise model has a sigma that is negative or not a number")
    rba, rbb, rsa, rsb, bb, bsa, bsb, r_max = nums
    across = math.radians(abs(bb) + bsa + bsb * r_max)
    a = max(abs(rba) + rsa, 0.005)
    b = math.hypot(abs(rbb) + rsb, across)
    source = model.get("source") or {}
    text = ("tag pilot %s (%s, %s frames, %s placements): range bias %+.4f %+.4f r, range sigma %.4f + %.4f r m, "
            "bearing bias %+.2f deg, bearing sigma %.3f + %.3f r deg, reliable to %s m -> %.4f + %.4f x range m up to "
            "%.2f m" % (source.get("log"), source.get("date"), source.get("n_frames"), source.get("n_placements"),
                        rba, rbb, rsa, rsb, bb, bsa, bsb, model.get("max_range_m"), a, b, r_max))
    return a, b, text


# ---------------------------------------------------------------- the move guard

def _inside_depth(poly, p):
    """Distance of p inside the convex counter-clockwise polygon (negative: outside)."""
    depth = float("inf")
    n = len(poly)
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        ex, ey = x2 - x1, y2 - y1
        length = math.hypot(ex, ey)
        depth = min(depth, (ex * (p[1] - y1) - ey * (p[0] - x1)) / length)
    return depth


def _outside_distance(poly, p):
    """Distance from p to a convex polygon it is outside of; negative (minus its depth) when it is inside."""
    inside = _inside_depth(poly, p) if _signed_area(poly) > 0 else _inside_depth(poly[::-1], p)
    if inside >= 0:
        return -inside
    best = float("inf")
    n = len(poly)
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        ex, ey = x2 - x1, y2 - y1
        t = max(0.0, min(1.0, ((p[0] - x1) * ex + (p[1] - y1) * ey) / (ex * ex + ey * ey)))
        best = min(best, math.hypot(p[0] - (x1 + t * ex), p[1] - (y1 + t * ey)))
    return best


def _signed_area(poly):
    return 0.5 * sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
                     for i in range(len(poly)))


class MoveGuard:
    """Blocks a move whose footprint would end nearer than a margin to the edge of the driving area.

    The driving area (the world file's arena.drive_polygon_m: inside the walls, in front of the desk) is convex, so
    a straight move whose end pose keeps every footprint corner inside the shrunken area stays inside all the way.
    Outside the driving area everything is treated as a wall, known or not. The margin grows with the pose's
    uncertainty (two sigma, at most 0.15 m more); beyond sigma_block_m the pose counts as unknown and every move is
    blocked. A straight move is checked 4 cm longer and at +-5 degrees of heading.

    A turn in place does not carry the car anywhere, so it needs less: the sweep circle (the farthest footprint
    corner about the axle midpoint) must stay turn_margin_m plus one sigma (at most 0.10 m) inside the area. A
    straight move must also end where a turn is still allowed with 5 cm to spare, so the car is never driven to a
    spot it cannot turn away from."""

    turn_margin_m = 0.03

    def __init__(self, world, footprint, sweep_radius_m, margin_m, sigma_block_m):
        arena = world["arena"]
        self.drive = [tuple(p) for p in arena.get("drive_polygon_m") or arena["polygon_m"]]
        if _signed_area(self.drive) <= 0:
            raise ValueError("the driving area must be a counter-clockwise polygon")
        self.obstacles = [[tuple(p) for p in o["polygon_m"]] for o in arena.get("obstacles") or []]
        self.footprint = [tuple(p) for p in footprint]
        self.sweep_radius_m, self.margin_m, self.sigma_block_m = sweep_radius_m, margin_m, sigma_block_m

    def point_depth(self, p):
        """How far a point is inside the free area: inside the driving area AND outside every obstacle box (the
        obstacles count even when a world file gives no separate driving area). Negative: not free."""
        depth = _inside_depth(self.drive, p)
        for box in self.obstacles:
            depth = min(depth, _outside_distance(box, p))
        return depth

    def axle_depth(self, pose):
        return self.point_depth((pose["x_m"], pose["y_m"]))

    def footprint_depth(self, pose):
        th = math.radians(pose["theta_deg"])
        c, s = math.cos(th), math.sin(th)
        return min(self.point_depth((pose["x_m"] + x * c - y * s, pose["y_m"] + x * s + y * c))
                   for x, y in self.footprint)

    def need(self, sigma_xy_m):
        return self.margin_m + min(2.0 * sigma_xy_m, 0.15)

    def check(self, action, pose, sigma_xy_m, distance_m=None):
        """None when the move may run, else the reason it is blocked."""
        if action not in ACTIONS:
            return "not a move"
        if not all(math.isfinite(pose[k]) for k in ("x_m", "y_m", "theta_deg")) or not math.isfinite(sigma_xy_m):
            return "pose unknown"
        if sigma_xy_m > self.sigma_block_m:
            return "pose uncertain (sigma %.2f m above %.2f m)" % (sigma_xy_m, self.sigma_block_m)
        need = self.need(sigma_xy_m)
        kind, table_distance, _angle = ACTIONS[action]
        turn_need = self.turn_margin_m + min(sigma_xy_m, 0.10)
        if kind == "turn":
            room = self.axle_depth(pose) - self.sweep_radius_m
            return None if room >= turn_need else \
                "turn: the sweep circle is %.2f m from the edge of the driving area, need %.2f m" % (room, turn_need)
        distance = (table_distance if distance_m is None else abs(distance_m)) + 0.04
        signed = distance if kind == "forward" else -distance
        worst = turn_room = float("inf")
        for bend in (-5.0, 0.0, 5.0):
            heading = math.radians(pose["theta_deg"] + bend)
            end = {"x_m": pose["x_m"] + signed * math.cos(heading), "y_m": pose["y_m"] + signed * math.sin(heading),
                   "theta_deg": pose["theta_deg"] + bend}
            worst = min(worst, self.footprint_depth(end))
            turn_room = min(turn_room, self.axle_depth(end) - self.sweep_radius_m)
        if worst < need:
            return "%s would end %.2f m from the edge of the driving area, need %.2f m" % (action, worst, need)
        if turn_room < turn_need + 0.05:
            return "%s would end where the car cannot turn (%.2f m of room, need %.2f m)" % (action, turn_room, turn_need + 0.05)
        return None

    def forward_allowed(self, pose, sigma_xy_m):
        return [name for name, _ in FORWARD_STEPS if self.check(name, pose, sigma_xy_m) is None]


# ---------------------------------------------------------------- health halts

class Monitor:
    """The batch's health state. halt() is one-way: the first cause is kept, HALT.LATCH is written, and for a
    safety halt the project latch is set too. Nothing in this module moves the car once halted."""

    def __init__(self, params, halt_path, latch=None, clock=time.monotonic, log=print, recorder_check=None):
        """recorder_check: a callable returning None while the R2 recorder is recording this batch, else why not."""
        self.params, self.halt_path, self.latch, self.clock, self.log = params, str(halt_path), latch, clock, log
        self.recorder_check = recorder_check
        self.halted = None
        self.t_batch = clock()
        self.t_episode = None
        self.steps = 0                  # moves sent by this process
        self.steps_before = 0           # moves sent by earlier runs of the same batch (the cap counts both)
        self.elapsed_before = 0.0       # seconds the earlier runs of the same batch were running
        self.boots = None
        self.camera_stale = 0
        self.latch_error = None

    def halt(self, code, detail, safety=None):
        if self.halted is not None:
            return self.halted
        safety = code in SAFETY_HALTS if safety is None else safety
        self.halted = {"code": code, "detail": str(detail), "time_utc": utc(), "safety": safety}
        reason = "batch halt: %s: %s" % (code, detail)
        try:
            os.makedirs(os.path.dirname(self.halt_path) or ".", exist_ok=True)
            with open(self.halt_path, "w", encoding="utf-8") as handle:
                json.dump({"latched": True, "reason": reason, "by": "car_batch", "t": utc(), "code": code}, handle)
                handle.write("\n")
        except OSError as exc:
            self.latch_error = "%s: %s" % (type(exc).__name__, exc)
            safety = True               # the halt could not be written where a rerun looks: use the project latch
            self.halted["safety"] = True
        if safety and self.latch is not None:
            try:
                self.latch.set(reason, "car_batch")
            except OSError as exc:
                self.latch_error = "%s: %s" % (type(exc).__name__, exc)
        self.log("HALT %s: %s" % (code, detail))
        return self.halted

    def halt_file_present(self):
        try:
            os.lstat(self.halt_path)
            return True
        except FileNotFoundError:
            return False
        except OSError:
            return True

    def check_latch(self):
        if self.latch is not None and self.latch.is_set():
            record = self.latch.read() or {}
            reason, by = str(record.get("reason")), record.get("by")
            # the executor latches by itself on a lost link or a restart of the car: name that cause, not "latch"
            code = "latch"
            if by == "executor":
                code = "car_restart" if "restarted" in reason else "link_lost"
            self.halt(code, "%s (by %s)" % (reason, by), safety=False)      # the project latch is already set
        elif self.halted is None and self.halt_file_present():
            self.halt("latch", "%s exists" % self.halt_path, safety=False)
        if self.halted is None and self.recorder_check is not None:
            why = self.recorder_check()
            if why:
                self.halt("recorder", why)      # rule R2: the car is never driven without the recorder

    def check_clocks(self):
        now, p = self.clock(), self.params
        if self.t_episode is not None and now - self.t_episode > p.episode_wall_s:
            self.halt("episode_wall_clock", "episode running %.0f s, cap %.0f s" % (now - self.t_episode, p.episode_wall_s))
        elapsed = self.elapsed_before + now - self.t_batch
        if elapsed > p.batch_wall_s:
            self.halt("batch_wall_clock", "batch running %.0f s over all its runs, cap %.0f s" % (elapsed, p.batch_wall_s))
        if self.steps_before + self.steps >= p.batch_steps:
            self.halt("batch_steps", "%d moves sent, cap %d" % (self.steps_before + self.steps, p.batch_steps))

    def check_car(self, state):
        p = self.params
        age = state.get("telemetry_age_s")
        if age is None or age > p.telemetry_max_age_s:
            return self.halt("telemetry_stale", "last telemetry %s s ago (limit %.1f s)" % (age, p.telemetry_max_age_s))
        if self.boots is None:
            self.boots = state.get("boots")
        elif state.get("boots") != self.boots:
            return self.halt("car_restart", "the car restarted (%s restarts seen)" % state.get("boots"))
        if state.get("drive_status") == 2:
            return self.halt("command_timeout", "the car reports a command-timeout stop")
        if state.get("armed") is False:
            return self.halt("car_disarmed", "the car reports itself disarmed")
        if state.get("imu_ready") is False:
            return self.halt("imu", "the car reports its IMU not ready")
        vsys = state.get("vsys_min_mv")
        if vsys is not None and 0 < vsys < p.min_vsys_mv:
            return self.halt("supply_low", "the Pico's supply fell to %d mV (limit %d mV)" % (vsys, p.min_vsys_mv))
        return None

    def check_sense(self, sense, record, is_first):
        """Everything one sensing can show. `record` is RealCarEnv.last_step."""
        self.check_car(record.get("car_state") or {})
        camera = ((sense.get("status") or {}).get("sensors") or {}).get("camera")
        if camera == "down":
            self.halt("camera", (sense["status"].get("error") or "no camera frame"))
        elif camera == "stale":
            self.camera_stale += 1
            if self.camera_stale >= self.params.camera_stale_steps:
                self.halt("camera", "frames missing in %d stops in a row" % self.camera_stale)
        else:
            self.camera_stale = 0
        if sense.get("odometry") is None and not is_first:
            self.halt("car_restart", "no odometry for this step (the car's counts started again)")
        move = sense.get("move")
        if move:
            result, reason = move["result"], move.get("reason") or ""
            if result == "link_lost":
                self.halt("link_lost", reason)
            elif result == "stalled":
                self.halt("stall", "%s: %s" % (move["action"], reason))
            elif result == "timeout":
                self.halt("move_timeout", "%s did not finish in time (blocked, or fading batteries)" % move["action"])
            elif result == "refused" and reason.startswith("no_telemetry"):
                self.halt("telemetry_stale", "%s refused by the executor: no fresh telemetry" % move["action"])
            elif result == "refused" and not reason.startswith(("executor: no forward move", "batch guard", "batch halted")):
                self.halt("executor_refused", "%s: %s" % (move["action"], reason))
            diag = (record.get("executed") or {}).get("diag") or {}
            if (result == "done" and move["action"] == "FORWARD_25" and self.params.min_forward_speed_mps > 0
                    and diag.get("peak_speed_mps") is not None
                    and diag["peak_speed_mps"] < self.params.min_forward_speed_mps):
                self.halt("slow", "FORWARD_25 peaked at %.3f m/s (limit %.3f): fading batteries?" % (
                    diag["peak_speed_mps"], self.params.min_forward_speed_mps))


# ---------------------------------------------------------------- the environment the harness drives

def range_scale_of_move(before, after, odo, min_info=0.5, gate_m=0.10):
    """The encoder scale from one straight move: (distance by the tags over distance by odometry, range pairs) or None.

    For every tag id seen exactly once before the move and once after it: its position before, in the car frame
    (range from the axle midpoint, bearing), and the odometry's displacement u predict the range after it; the scale
    s solves |tag - s u| = the range measured after. Only ranges enter, which the camera measures to millimetres (the
    tag pilot); a bearing error moves the prediction little for a tag near the line of motion. The pairs of one move
    are weighted by how much the range says about s (d range / d s; a tag abeam says nothing and is left out below
    min_info of it). A pair farther off than half the move plus gate_m is another tag of the same id, not a scale.
    2026-11-25, after a false odometry_scale halt of the first real practice batch: see odometry_bias()."""
    ux, uy = float(odo["forward_m"]), float(odo["left_m"])
    uu = ux * ux + uy * uy
    if uu <= 0.0:
        return None
    move = math.sqrt(uu)

    def once(dets):
        seen = {}
        for d in dets:
            if d.get("id") is not None and usable_detection(d):
                seen.setdefault(int(d["id"]), []).append((float(d["range_m"]), math.radians(float(d["bearing_deg"]))))
        return {k: v[0] for k, v in seen.items() if len(v) == 1}
    a, b = once(before), once(after)
    num = den = 0.0
    pairs = 0
    for tid, (r1, b1) in a.items():
        if tid not in b:
            continue
        r2 = b[tid][0]
        tx, ty = r1 * math.cos(b1), r1 * math.sin(b1)
        tu = tx * ux + ty * uy
        predicted = math.hypot(tx - ux, ty - uy)
        info = abs(tu - uu) / max(predicted, 1e-6)
        if info < min_info * move or abs(r2 - predicted) > 0.5 * move + gate_m:
            continue
        disc = tu * tu - uu * (r1 * r1 - r2 * r2)
        if disc < 0.0:
            continue
        root = math.sqrt(disc)
        s = min(((tu - root) / uu, (tu + root) / uu), key=lambda v: abs(v - 1.0))
        num += info * info * s
        den += info * info
        pairs += 1
    return None if pairs == 0 else (num / den, pairs)


def range_scale_halt(tracker, params):
    """Why the ranges along the straight moves so far say the encoder scale is wrong (the halt's detail), or None.
    The limit is range_scale_tol, and at least three times one move's scatter over the root of the moves."""
    ranges = tracker.range_scale()
    if ranges is None:
        return None
    limit = max(params.range_scale_tol, 3.0 * params.range_scale_move_sigma / math.sqrt(ranges[1]))
    if abs(ranges[0] - 1.0) <= limit:
        return None
    return ("over %d straight moves the ranges to the tags in view changed %.2f times the distance the odometry "
            "reports (median, %d range pairs; limit 1 +- %.2f): the encoder scale in configs/car.json is wrong, or the "
            "tags are" % (ranges[1], ranges[0], ranges[2], limit))


class BatchEnv:
    """RealCarEnv with the tracker, the guard and the monitor on every step. Implements the closed-loop harness's
    environment protocol. `start` is the arena-frame pose that is the origin of the map frame the harness sees."""

    def __init__(self, inner, tracker, guard, monitor, tags, params, start, truth_path=None, sim_truth_fn=None,
                 tagcheck=None):
        self.inner, self.tracker, self.guard, self.monitor = inner, tracker, guard, monitor
        self.tagcheck = tagcheck        # TagCheck, or None: then every surveyed tag steers fixes
        self.tags, self.params, self.start = tags, params, dict(start)
        self.truth_path, self.sim_truth_fn = truth_path, sim_truth_fn
        self.source = inner.source
        self.last_fix = None
        self.blocked = 0
        self.rows = 0
        self.t_frame = monitor.clock()  # when the camera last answered
        self.range_before = None        # the last sensing's detections, for the range check of the next straight move
        self.in_scan = False            # True while BatchRunner.scan turns a full circle (the circle is the fix)
        self.use_views = True           # False until a full circle has confirmed the pose: a view fix judged against
                                        # an unconfirmed (taped) pose says nothing, in either direction

    def describe(self):
        d = self.inner.describe()
        d.update({"batch": True, "start_pose_world": self.start, "wall_margin_m": self.params.wall_margin_m,
                  "max_range_m": self.params.max_range_m,
                  "ground_truth": "tag resection (per-step view fixes blended with odometry); see truth.jsonl"})
        return d

    def reset(self, seed):
        self.monitor.check_latch()
        return self._post(self.inner.reset(seed), None, first=True)

    def step(self, action):
        if action is not None and action not in ACTIONS:
            raise ValueError("not a move: %r" % (action,))
        self.monitor.check_latch()
        self.monitor.check_clocks()
        if action is None:
            return self._post(self.inner.step(None), None)
        if self.monitor.halted is None:
            self._before_move()
        if self.monitor.halted is not None:
            return self._refuse(action, "batch halted: %s" % self.monitor.halted["code"])
        distance = self.inner._last_forward if ACTIONS[action][0] == "backward" else None
        why = self._blind(action, distance) or self.guard.check(action, self.tracker.pose, self.tracker.sigma_xy_m, distance)
        if why is not None:
            self.blocked += 1
            return self._refuse(action, "batch guard: " + why)
        sense = self.inner.step(action)
        if (sense.get("move") or {}).get("result") != "refused":
            self.monitor.steps += 1         # moves that were sent to the car (a refusal by the executor sends none)
        return self._post(sense, action)

    def _blind(self, action, distance=None):
        """Why a straight move would take the car too far from its last tag fix, or None. Turns are always allowed
        by this rule: turning is how the next tag comes into view."""
        kind, table_distance, _angle = ACTIONS[action]
        if kind == "turn":
            return None
        d = table_distance if distance is None else abs(distance)
        total = self.tracker.travel_since_fix_m + d
        if total > self.params.max_blind_travel_m + 1e-9:
            return "%s would make %.2f m driven since the last tag fix (limit %.2f m): turn until a tag is seen" % (
                action, total, self.params.max_blind_travel_m)
        return None

    def _before_move(self):
        """The car as it is NOW, not as the last sensing saw it: an agent may have thought for a long time since.
        Fresh telemetry is checked, and if the camera has not answered for camera_probe_after_s it is asked for one
        frame first, so no move starts on a car that cannot be seen."""
        try:
            self.monitor.check_car(self.inner.link.car_state())
        except Exception as exc:    # noqa: BLE001
            self.monitor.halt("error", "reading the car's state: %s: %s" % (type(exc).__name__, exc))
        if self.monitor.halted is None and self.monitor.clock() - self.t_frame > self.params.camera_probe_after_s:
            try:
                self.inner.camera.grab()
                self.t_frame = self.monitor.clock()
            except Exception as exc:    # noqa: BLE001
                self.monitor.halt("camera", "no frame before the move: %s" % exc)

    def _range_check(self, exact, sense, record, first):
        """Note the encoder scale the ranges give over a straight move (range_scale_of_move) with the tracker. The
        observation's ranges are rounded to the centimetre; where the detector's own record has the tag's position
        to the millimetre (detections_internal, the real camera), that is taken for the same tag."""
        now = []
        precise = {}
        for d in record.get("detections_internal") or []:
            xyz = d.get("base_xyz_m")
            if d.get("id") is not None and xyz and len(xyz) >= 2:
                precise.setdefault(int(d["id"]), []).append((float(xyz[0]), float(xyz[1])))
        for d in sense.get("detections") or []:
            if d.get("id") is None or not usable_detection(d):
                continue
            exact_xy = precise.get(int(d["id"])) or []
            if len(exact_xy) == 1:
                r = math.hypot(*exact_xy[0])
                if abs(r - float(d["range_m"])) < 0.05:
                    d = {"id": d["id"], "range_m": r,
                         "bearing_deg": math.degrees(math.atan2(exact_xy[0][1], exact_xy[0][0]))}
            now.append(d)
        before, self.range_before = self.range_before, now
        if first or exact is None or before is None or abs(exact["forward_m"]) < 0.05:
            return
        est = range_scale_of_move(before, now, exact)
        if est is not None:
            self.tracker.range_moves.append(est)

    def _refuse(self, action, reason):
        sense = self.inner.step(None)           # sense again; nothing moves
        sense = self._post(sense, None)
        sense["move"] = {"action": action, "result": "refused", "reason": reason}
        return sense

    def _post(self, sense, action, first=False):
        self.monitor.check_latch()      # first: a STOP during the move is the operator's halt, not a lost link
        record = self.inner.last_step or {}
        exact = record.get("odometry_exact")
        if exact is not None:
            self.tracker.predict(exact)
        self._range_check(exact, sense, record, first)
        self.monitor.check_sense(sense, record, first)
        if ((sense.get("status") or {}).get("sensors") or {}).get("camera") == "ok":
            self.t_frame = self.monitor.clock()
        fix = None
        usable = [d for d in sense["detections"] if d.get("id") is not None and usable_detection(d)]
        broken = [d for d in sense["detections"] if not usable_detection(d)]
        if broken:
            # never used for a pose, and never ignored: the detector is not to be trusted for the rest of the batch
            self.monitor.halt("detector", "a detection with a range or bearing that is not a number: %r" % (broken[0],))
        if not all(math.isfinite(v) for v in self.tracker.pose.values()) or not math.isfinite(self.tracker.sigma_xy_m):
            self.monitor.halt("pose_uncertain", "the tracked pose is not a number")
        if usable and not self.use_views:
            self.tracker.steps_since_fix = 0        # (the circle in progress is the fix; these steps are not "no fix")
        elif usable:
            noise = {"sigma_a_m": self.params.fix_sigma_a_m, "sigma_b": self.params.fix_sigma_b}
            trusted = self.tagcheck.trusted() if (self.tagcheck is not None and self.params.tag_trust) else None
            # judged with every surveyed tag, exactly as before the trust rule: a view that disagrees with the
            # tracked pose is a conflict whether or not its tags are trusted yet (the fix_conflict halt is unchanged)
            fix = resect([{"pose": None, "detections": usable}], self.tags, prior=self.tracker.pose,
                         max_range_m=self.params.max_range_m,
                         tag_check={"k": self.params.tag_check_k, "min_m": self.params.tag_check_min_m}, **noise)
            self._check_tags(fix.get("check"), "a step's view")
            if fix["ok"] and self.tracker.disagrees(fix):
                fix = dict(fix, ok=False, why="far_from_prior", rejected="disagrees with the tracked pose")
                self.tracker.conflicts += 1
                self.tracker.rejected += 1
            elif fix["ok"]:
                # it agrees: only the trusted tags of it move the pose (two of them; else one and the heading)
                fix = self._trusted_fix(usable, fix, trusted, noise)
            else:
                # fewer than two tags, or an unusable pair: one tag and the tracked heading still give a position
                one = position_fix(usable, self.tags, self.tracker.pose, self.tracker.sigma_theta_deg,
                                   max_range_m=self.params.max_range_m, **noise)
                if one["ok"] and self.tracker.disagrees(one):
                    self.tracker.conflicts += 1
                    self.tracker.rejected += 1
                    fix = dict(one, ok=False, why="far_from_prior", rejected="disagrees with the tracked pose")
                elif one["ok"]:
                    fix = self._trusted_fix(usable, None, trusted, noise, one=one)
                elif "far_from_prior" in (fix.get("why"), one.get("why")):
                    self.tracker.conflicts += 1
                    fix = dict(fix, position_fix=one.get("why"))
        if (usable and self.use_views and self.in_scan and fix and not fix.get("ok") and fix.get("untrusted")
                and not fix.get("rejected") and fix.get("why") != "far_from_prior" and self.tracker.steps_since_fix):
            # tags in view inside a full circle whose own fix cannot use them (not yet trusted): the circle in
            # progress is the fix, as on the first circle, so this step does not count toward no_fix (it would
            # otherwise halt a circle of unchecked tags before the circle could check them)
            self.tracker.steps_since_fix -= 1
        self.last_fix = fix
        p = self.params
        if self.tracker.steps_since_fix >= p.no_fix_steps:
            self.monitor.halt("no_fix", "%d steps without a tag fix (limit %d)" % (self.tracker.steps_since_fix, p.no_fix_steps))
        if self.tracker.conflicts >= p.fix_conflicts:
            self.monitor.halt("fix_conflict", "%d tag fixes in a row far from the tracked pose" % self.tracker.conflicts)
        wrong_scale = range_scale_halt(self.tracker, p)
        if wrong_scale:
            self.monitor.halt("odometry_scale", wrong_scale)
        bias = self.tracker.odometry_bias()
        # the scale is off by more than the limit AND the fixes say so beyond their own noise (three standard errors)
        if bias is not None and abs(bias[0]) > p.odometry_bias_max and abs(bias[0]) > 3.0 * bias[3]:
            self.monitor.halt("odometry_scale", "tag fixes land %+.0f %% (+-%.0f %%) of the distance from where the "
                              "odometry puts the car (%.1f m driven, %d fixes; limit %.0f %%): the encoder scale is "
                              "wrong, or the tags are" % (100 * bias[0], 100 * bias[3], bias[1], bias[2],
                                                          100 * p.odometry_bias_max))
        if self.tracker.sigma_xy_m > p.sigma_block_m:
            self.monitor.halt("pose_uncertain", "position uncertainty %.2f m above %.2f m" % (self.tracker.sigma_xy_m, p.sigma_block_m))
        if self.guard.axle_depth(self.tracker.pose) < 0:
            self.monitor.halt("outside_drive_area", "tracked pose (%.2f, %.2f) is outside the driving area" % (
                self.tracker.pose["x_m"], self.tracker.pose["y_m"]))
        halted = self.monitor.halted is not None
        inner_safety = sense["safety"]
        pose, sigma = self.tracker.pose, self.tracker.sigma_xy_m
        forward = [] if halted else [m for m in self.guard.forward_allowed(pose, sigma)
                                     if m in inner_safety["forward_allowed"] and self._blind(m) is None]
        turn = (not halted) and self.guard.check("TURN_LEFT_30", pose, sigma) is None
        back = (not halted) and inner_safety.get("backward_allowed", False) and \
            self._blind("BACKWARD_10", self.inner._last_forward) is None and \
            self.guard.check("BACKWARD_10", pose, sigma, self.inner._last_forward) is None
        sense["safety"] = {"forward_allowed": forward, "backward_allowed": bool(back),
                           "turn_allowed": bool(turn and inner_safety.get("turn_allowed", True)),
                           "scan_allowed": bool(turn and inner_safety.get("scan_allowed", True))}
        self._write_truth(sense, fix, action)
        return sense

    def _trusted_fix(self, usable, pose_fix, trusted, noise, one=None):
        """Blend in the part of an agreeing view that rests on trusted tags (TagCheck), and return what was used.
        pose_fix: the view's two-tag fix over all tags, or None; one: its one-tag position fix over all tags. With
        trusted None (no TagCheck, or tag_trust off) the fix is used as it is, as before 2026-11-24."""
        if pose_fix is not None:
            use = pose_fix if trusted is None else resect(
                [{"pose": None, "detections": usable}], self.tags, prior=self.tracker.pose,
                max_range_m=self.params.max_range_m, trusted=trusted, **noise)
            if use["ok"] and not self.tracker.disagrees(use):
                use["kind"] = "pose"
                self.tracker.correct(use)
                return use
            one = None
        if one is None or trusted is not None:
            one = position_fix(usable, self.tags, self.tracker.pose, self.tracker.sigma_theta_deg,
                               max_range_m=self.params.max_range_m, trusted=trusted, **noise)
        if one["ok"] and not self.tracker.disagrees(one):
            self.tracker.correct_position(one)
            return one
        # the tags that agree are not checked yet: no fix this step (and no conflict: the view agreed)
        return dict(one, ok=False, why=one.get("why") if not one["ok"] else "disagrees with the tracked pose",
                    untrusted=sorted({str(u) for u in (one.get("untrusted") or []) + ((pose_fix or {}).get("untrusted") or [])}))

    def _check_tags(self, check, where):
        """Add a fit's tag comparisons; a tag that keeps disagreeing with the others halts the batch."""
        if self.tagcheck is None or not check:
            return
        flagged = self.tagcheck.add(check, where)
        if flagged:
            self.monitor.halt("tag_survey", tag_survey_detail(self.tagcheck, flagged[0], self.tags))

    def truth(self):
        """The best pose the batch has, in the map frame, with what it rests on. Not tape: see the module text."""
        t = self.tracker
        out = to_map_pose(self.start, t.pose)
        out.update({"source": "tag_fix" if t.steps_since_fix == 0 and t.fixes else "tracked_since_fix",
                    "fix": bool(t.steps_since_fix == 0 and t.fixes), "sigma_xy_m": round(t.sigma_xy_m, 4),
                    "sigma_theta_deg": round(t.sigma_theta_deg, 2), "steps_since_fix": t.steps_since_fix})
        return out

    def _write_truth(self, sense, fix, action):
        if not self.truth_path:
            return
        row = {"row": self.rows, "time_utc": utc(), "action": action, "tracked_world": self.tracker.snapshot(),
               "truth_map": self.truth(), "view_fix": fix, "no_fix": not (fix and fix.get("ok")),
               "detections": len(sense["detections"]), "halted": self.monitor.halted,
               "sim_truth_world": self.sim_truth_fn() if self.sim_truth_fn else None}
        self.rows += 1
        try:
            with open(self.truth_path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, default=str) + "\n")
        except OSError:
            pass


# ---------------------------------------------------------------- the rig: one car, real or simulated

@dataclass
class Rig:
    """What a batch drives: a car link, a camera, a detector, the latch. make_env builds a RealCarEnv on them.
    sim_truth_fn (simulated car only) gives the true arena-frame pose, for the dry run's own checks."""
    link: object
    camera: object
    detector: object
    latch: object = None
    clock: object = time.monotonic
    sim_truth_fn: object = None
    real: bool = True
    notes: dict = field(default_factory=dict)

    def make_env(self, episode, scene=None, log_dir=None):
        return RealCarEnv(self.link, self.camera, self.detector, scene=scene, log_dir=log_dir, unknown_wall="block",
                          episode=episode)


def dry_rig(world, place_pose, latch=None, seed=1, preset="camera", max_range_m=2.0, sim_params=None, cfg=None,
            collide=True):
    """The simulated car placed at place_pose (arena frame) in the room of `world`, with detections drawn by the
    room simulator (envs/kinsim_room.py: visibility, range window, noise). With collide, a footprint corner past a
    wall or inside the desk box blocks both wheels, as a wall would."""
    import random

    from beaconmind.envs import kinsim_room as kr

    from . import config as C
    from .camera import FakeCamera, fake_detector
    from .link import SimLink
    from .simcar import SimCar, SimCarParams

    scene = kr.room_scene(world, start_pose=place_pose)        # its map frame is the simulated car's own frame
    link = SimLink(cfg or C.load_config(), SimCar(SimCarParams(**(sim_params or {}))), latch=latch)
    rng = random.Random("dry-%s" % seed)
    noise = kr.preset(preset, max_range_m=max_range_m)
    footprint = kr.default_footprint() or [(0.0, 0.0)]

    def sim_pose():
        t = link.sim.truth()
        return {"x_m": t["x_m"], "y_m": t["y_m"], "theta_deg": wrap_deg(t["theta_deg"])}

    def truth_world():
        return kr.to_world(place_pose, sim_pose())

    def detections(_jpegs):
        return kr.detect(scene, sim_pose(), rng, noise)

    if collide:
        count = {"n": 0}

        def walls(l):
            count["n"] += 1
            if count["n"] % 20:
                return
            c = kr.clearance(scene, sim_pose(), footprint)
            hit = c["wall_m"] < 0 or (c["obstacle_m"] is not None and c["obstacle_m"] <= 0)
            if hit:
                l.sim.p.blocked_left = l.sim.p.blocked_right = True
        link.on_step = walls
    return Rig(link, FakeCamera(), fake_detector(detections), latch=latch, clock=lambda: link.t,
               sim_truth_fn=truth_world, real=False, notes={"place_pose": dict(place_pose), "seed": seed})


# ---------------------------------------------------------------- the pass marker of the attended tests

MARKER_FILES = ("configs/car.json", "configs/dv.json") + tuple(
    "beaconmind/src/beaconmind/car/%s.py" % name for name in (
        "config", "executor", "ros_io", "telemetry", "odometry", "moves", "latch", "link", "camera", "backend",
        "resection", "batch"))


def marker_fingerprint(root):
    """Hashes of the car's constants, the design values and every module of the car package: what moves the car in
    a batch. (The firmware on the car and the world file are not in it: the first is checked through telemetry's
    layout and drive map at the start, the second is a parameter of each batch.)"""
    out = {}
    for rel in MARKER_FILES:
        try:
            with open(os.path.join(root, rel), "rb") as handle:
                out[rel] = hashlib.sha256(handle.read()).hexdigest()[:12]
        except OSError:
            out[rel] = None
    return out


def file_sha12(path):
    try:
        with open(path, "rb") as handle:
            return hashlib.sha256(handle.read()).hexdigest()[:12]
    except OSError:
        return None


def write_pass_marker(path, root, operator, stand_session, floor_session, notes="", now_unix=None, world_path=None):
    """Record that the attended stand test and floor check passed (evidence/M3/M3.T6/README.md section 5). Called
    only by `car_batch.py record-pass`, which a person runs after reading both sessions' results."""
    name = str(operator or "").strip()
    if not name:
        raise ValueError("the pass marker needs the operator's name")
    if str(stand_session) == str(floor_session):
        raise ValueError("the stand test and the floor check are two recorded sessions; one name was given for both")
    for label, session, least in (("stand", stand_session, 5), ("floor", floor_session, 10)):
        folder = os.path.join(root, "data", "real", str(session), "moves")
        if not session or "/" in str(session) or not os.path.isdir(folder):
            raise ValueError("%s session %r has no recorded moves under data/real/" % (label, session))
        done = _moves_done(folder)
        if done < least:
            raise ValueError("%s session %r has %d moves that ended `done`; the procedure makes at least %d"
                             % (label, session, done, least))
    record = {"schema": "bm.attended_pass/1", "operator": name, "stand_session": stand_session,
              "floor_session": floor_session, "notes": notes, "time_utc": utc(),
              "world_file": None if world_path is None else os.path.basename(str(world_path)),
              "world_sha12": None if world_path is None else file_sha12(world_path),
              "t_unix": time.time() if now_unix is None else now_unix, "fingerprint": marker_fingerprint(root)}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    write_json(path, record)
    return record


def _moves_done(folder):
    """How many move logs in a session's moves/ folder end with a result `done`."""
    count = 0
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".jsonl"):
            continue
        try:
            with open(os.path.join(folder, name), encoding="utf-8") as handle:
                last = None
                for line in handle:
                    if '"ev": "result"' in line:
                        last = json.loads(line)
            if last and (last.get("result") or {}).get("result") == "done":
                count += 1
        except (OSError, ValueError):
            continue
    return count


def check_pass_marker(path, root, max_age_days=7.0, now_unix=None, world_path=None):
    """Why the marker does not allow a batch, as a list of sentences (empty: go)."""
    try:
        with open(path, encoding="utf-8") as handle:
            record = json.load(handle)
    except FileNotFoundError:
        return ["no pass marker at %s: the attended stand test and floor check must pass first "
                "(car_batch.py record-pass)" % path]
    except (OSError, ValueError) as exc:
        return ["the pass marker %s cannot be read (%s)" % (path, exc)]
    problems = []
    if not isinstance(record, dict) or record.get("schema") != "bm.attended_pass/1" or not record.get("operator"):
        return ["the pass marker %s is not a bm.attended_pass/1 record" % path]
    try:
        age_days = ((time.time() if now_unix is None else now_unix) - float(record["t_unix"])) / 86400.0
    except (KeyError, TypeError, ValueError):
        return ["the pass marker %s has no time" % path]
    if age_days > max_age_days or age_days < -0.01:
        problems.append("the pass marker is %.1f days old (limit %.0f): repeat the attended tests" % (age_days, max_age_days))
    now, then = marker_fingerprint(root), record.get("fingerprint")
    if not isinstance(then, dict):
        then = {}
    # every file of TODAY's list must be in the marker with today's hash: a marker cannot choose what is compared
    changed = [rel for rel, digest in now.items() if digest is None or then.get(rel) != digest]
    if changed:
        problems.append("changed since the attended tests passed (or missing from the marker): %s: repeat them and "
                        "record a new marker" % ", ".join(changed))
    if world_path is not None:
        now_world = file_sha12(world_path)
        if not record.get("world_sha12") or now_world is None or record["world_sha12"] != now_world:
            problems.append("the world file %s is not the one the pass was recorded for (%s): record-pass --world "
                            "with the surveyed file, after checking it against the room"
                            % (world_path, record.get("world_file")))
    return problems


# ---------------------------------------------------------------- the runner

class HaltAwareDriver:
    """The agent as the harness calls it, with one more look at the car before every request. When the batch is
    halted (or halts on that look) no request is sent: the harness is given its own "budget cap reached" answer,
    which makes it stop the episode without writing the step, without a paid call and without a move."""

    def __init__(self, driver, monitor, link):
        self._driver, self._monitor, self._link = driver, monitor, link
        self.requests_refused = 0

    def __getattr__(self, name):
        return getattr(self._driver, name)

    def step(self, system_text, obs, prev, budget, log, sample_key=None):
        m = self._monitor
        if m.halted is None:
            m.check_latch()
            m.check_clocks()
        if m.halted is None:
            try:
                m.check_car(self._link.car_state())
            except Exception as exc:    # noqa: BLE001
                m.halt("error", "reading the car's state: %s: %s" % (type(exc).__name__, exc))
        if m.halted is not None:
            self.requests_refused += 1
            return {"final_text": None, "calls": [], "turns": [], "state": {"moved": None, "estop": False},
                    "error": "budget cap reached", "seconds": 0.0, "cost_usd": 0.0}
        return self._driver.step(system_text, obs, prev, budget, log, sample_key=sample_key)


class BatchStop(Exception):
    """The batch cannot go on (the monitor holds the reason)."""


class BatchRunner:
    def __init__(self, params, rig, world, out_dir, driver=None, system_text="", budget=None, log=print,
                 run_episode=None, footprint=None, sweep_radius_m=None, autolatch_contacts=2, config_extra=None,
                 recorder_check=None, marker_path=None):
        """rig: Rig. world: the bm.world/1 document. driver: a closed-loop driver (harness/closed_loop.py).
        run_episode: harness.closed_loop.run_episode (injectable for tests)."""
        from beaconmind.envs import kinsim_room as kr
        from .config import load_car
        self.kr = kr
        self.params, self.rig, self.world, self.out = params, rig, world, str(out_dir)
        self.driver, self.system_text, self.budget, self.log = driver, system_text, budget, log
        self.run_episode = run_episode
        self.autolatch_contacts = autolatch_contacts
        car = load_car()
        self.footprint = footprint or [tuple(p) for p in car["corners"]]
        self.sweep = sweep_radius_m or float(car["sweep_radius_m"])
        self.tags = [{"id": t["id"], "uid": t.get("uid"), "x_m": t["x_m"], "y_m": t["y_m"]} for t in world["tags"]]
        os.makedirs(self.out, exist_ok=True)
        self.halt_path = os.path.join(self.out, "HALT.LATCH")
        self.manifest_path = os.path.join(self.out, "manifest.json")
        self.monitor = Monitor(params, self.halt_path, rig.latch, rig.clock, log, recorder_check)
        self.marker_path = marker_path          # episode markers inside the recorder's session
        self.guard = MoveGuard(world, self.footprint, self.sweep, params.wall_margin_m, params.sigma_block_m)
        self.tracker = PoseTracker(params.initial_pose, params.initial_sigma_m, params.initial_sigma_deg,
                                   params.fix_floor_m)
        self.tagcheck = TagCheck(params.tag_check_k, params.tag_check_min_m, params.tag_trust_max_m, params.tag_trust_k)
        self.config = hashlib.sha256(json.dumps([params.digest(), config_extra], sort_keys=True, default=str).encode()).hexdigest()[:12]
        self.manifest = None
        self.localised = False          # no full-circle fix yet in this process: the taped pose is all there is

    # ------------------------------------------------------------ manifest

    def _load_manifest(self):
        if os.path.exists(self.manifest_path):
            with open(self.manifest_path, encoding="utf-8") as handle:
                m = json.load(handle)
            if m.get("config") != self.config:
                raise BatchStop("%s belongs to another batch configuration (%s, now %s): use a new label or --out"
                                % (self.manifest_path, m.get("config"), self.config))
            if m.get("status") == "running":
                # the earlier run ended without recording why (killed, power, a crash): nobody knows the car's state
                self.monitor.halt("error", "the earlier run of this batch ended without a record (manifest still "
                                  "`running`): look at the car, then clear-halt", safety=False)
                raise BatchStop("the earlier run of this batch ended without a record; HALT.LATCH written: an "
                                "operator looks at the car and clears it (car_batch.py clear-halt)")
            m["resumes"] = m.get("resumes", 0) + 1
            m["halt"] = None
            for e in m["episodes"]:
                if e.get("status") == "running":        # the process died inside it: never replayed, never "done"
                    e["status"] = "abandoned"
            m.setdefault("initial_poses", []).append({"time_utc": utc(), "pose": dict(self.params.initial_pose)})
            return m
        return {"schema": MANIFEST_SCHEMA, "config": self.config, "params": asdict(self.params), "created": utc(),
                "world_id": self.world.get("world_id"), "real_car": self.rig.real, "resumes": 0, "episodes": [],
                "halt": None, "status": "running", "moves_sent": 0, "spent_usd": 0.0, "rig": self.rig.notes,
                "initial_poses": [{"time_utc": utc(), "pose": dict(self.params.initial_pose)}]}

    def _save(self, status=None):
        m = self.manifest
        if status:
            m["status"] = status
        m["updated"] = utc()
        m["halt"] = self.monitor.halted
        m["moves_sent"] = m.get("moves_base", 0) + self.monitor.steps
        m["elapsed_s"] = round(m.get("elapsed_base", 0.0) + self.monitor.clock() - self.monitor.t_batch, 1)
        m["last_tracked_pose_world"] = dict(self.tracker.snapshot(), confirmed_by_a_circle=self.localised)
        m["latch_error"] = self.monitor.latch_error
        m["tag_check"] = {"this_run": self.tagcheck.snapshot(), "flagged": self.tagcheck.flagged(),
                          "trusted": sorted(self.tagcheck.trusted())}
        if self.budget is not None:
            m["spent_usd"] = round(self.budget.spent, 5)
        try:
            write_json(self.manifest_path, m)
            with open(os.path.join(self.out, "summary.txt"), "w", encoding="utf-8") as handle:
                handle.write(summary_text(m))
        except OSError as exc:
            # a batch that cannot write its own record must not go on, and a rerun must not find a clean folder
            self.log("cannot write the manifest: %s" % exc)
            self.monitor.halt("error", "cannot write the manifest: %s: %s" % (type(exc).__name__, exc), safety=True)

    def _mark(self, event, entry=None):
        if not self.marker_path:
            return
        try:
            with open(self.marker_path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps({"event": event, "time_utc": utc(), "t_unix": round(time.time(), 3),
                                         "batch": self.config, "episode": entry and entry.get("id"),
                                         "status": entry and entry.get("status"), "halt": self.monitor.halted}) + "\n")
        except OSError:
            pass

    # ------------------------------------------------------------ building blocks

    def _service_env(self, label, log_dir):
        inner = self.rig.make_env(label, scene=None, log_dir=log_dir)
        env = BatchEnv(inner, self.tracker, self.guard, self.monitor, self.tags, self.params, self.tracker.pose,
                       truth_path=os.path.join(log_dir, "truth.jsonl"), sim_truth_fn=self.rig.sim_truth_fn,
                       tagcheck=self.tagcheck)
        env.use_views = self.localised
        return env

    def _must(self, env, action, what):
        """One move of the runner's own (a scan turn, a transit move): it runs or the batch halts."""
        sense = env.step(action)
        move = sense.get("move") or {}
        if self.monitor.halted is None and move.get("result") != "done":
            self.monitor.halt("guard_blocked" if str(move.get("reason", "")).startswith("batch guard") else "executor_refused",
                              "%s: %s %s (%s)" % (what, action, move.get("result"), move.get("reason")))
        if self.monitor.halted is not None:
            raise BatchStop(what)
        return sense

    def scan(self, env, what):
        """A full circle of 12 left turns with a view at each heading; the tracker is set from the fix. Returns the
        fix record (ok or not) with the pose NOW (after the circle) in the arena frame."""
        steps = int(round(360.0 / TURN_DEG))
        rel = {"x_m": 0.0, "y_m": 0.0, "theta_deg": 0.0}
        env.in_scan = True
        try:
            return self._scan(env, what, steps, rel)
        finally:
            env.in_scan = False

    def _scan(self, env, what, steps, rel):
        sense = env.step(None)
        if self.monitor.halted is not None:
            raise BatchStop(what)
        views = [{"pose": dict(rel), "detections": sense["detections"]}]
        for _ in range(steps):
            sense = self._must(env, "TURN_LEFT_30", what)
            exact = env.inner.last_step.get("odometry_exact")
            if exact is None:
                self.monitor.halt("car_restart", "%s: no odometry during the scan" % what)
                raise BatchStop(what)
            rel = compose(rel, exact)
            if len(views) < steps:              # the last view repeats the first heading
                views.append({"pose": dict(rel), "detections": sense["detections"]})
        p = self.params
        noise = {"max_range_m": p.max_range_m, "sigma_a_m": p.fix_sigma_a_m, "sigma_b": p.fix_sigma_b,
                 "rms_max_m": p.scan_rms_max_m, "tag_check": {"k": p.tag_check_k, "min_m": p.tag_check_min_m}}
        if self.localised:
            fix = resect(views, self.tags, prior=self.tracker.pose, prior_gate_m=1.0, prior_gate_deg=45.0, **noise)
        else:
            # the pose is only a tape reading so far: let the tags speak without it, then compare. A circle that
            # disagrees with the tape is not a fix: one of the two is wrong and a person has to say which.
            fix = resect(views, self.tags, prior=None, **noise)
            if fix["ok"]:
                start = self.tracker.pose
                # the tracker has turned with the circle; compare where the circle began: positions, and headings
                off_m = math.hypot(fix["pose"]["x_m"] - start["x_m"], fix["pose"]["y_m"] - start["y_m"])
                off_deg = abs(wrap_deg(fix["pose"]["theta_deg"] + rel["theta_deg"] - start["theta_deg"]))
                if off_m > p.initial_gate_m or off_deg > p.initial_gate_deg:
                    fix = {"ok": False, "why": "the tags put the car %.2f m and %.0f degrees from the taped pose "
                           "(limits %.2f m, %.0f degrees)" % (off_m, off_deg, p.initial_gate_m, p.initial_gate_deg),
                           "n_tags": fix["n_tags"], "pose": fix["pose"], "disagrees_with_tape": True,
                           "check": fix.get("check")}
        # every tag of the circle against the others: one that keeps disagreeing halts the batch (tag_survey). (The
        # comparison is among the tags themselves, so it counts whether or not the circle became a fix.)
        env._check_tags(fix.get("check"), what)
        if self.monitor.halted is not None:
            raise BatchStop(what)
        blended = False
        if fix["ok"] and fix["sigma_xy_m"] > self.params.scan_sigma_max_m:
            # few tags, or far ones: not good enough to replace the pose. When a circle has confirmed the pose
            # before, this one is still information: blend it with the tracked pose (as any fix), and take the
            # result if THAT is certain enough and the two did not disagree.
            now = dict(fix, pose=compose(fix["pose"], {"forward_m": rel["x_m"], "left_m": rel["y_m"],
                                                       "dtheta_deg": rel["theta_deg"]}))
            if self.localised and not self.tracker.disagrees(now):
                self.tracker.correct(now)
                blended = self.tracker.sigma_xy_m <= self.params.scan_sigma_max_m
            if blended:
                fix = dict(fix, blended_with_tracked_pose=True, circle_sigma_xy_m=fix["sigma_xy_m"],
                           sigma_xy_m=self.tracker.sigma_xy_m, sigma_theta_deg=self.tracker.sigma_theta_deg,
                           pose_now=dict(self.tracker.pose), closure_deg=round(wrap_deg(rel["theta_deg"]), 2))
            else:
                fix = {"ok": False, "why": "poorly conditioned: sigma %.2f m above %.2f m" % (
                    fix["sigma_xy_m"], self.params.scan_sigma_max_m), "n_tags": fix["n_tags"], "rms_m": fix["rms_m"]}
        if fix["ok"] and not blended:
            now = compose(fix["pose"], {"forward_m": rel["x_m"], "left_m": rel["y_m"], "dtheta_deg": rel["theta_deg"]})
            self.tracker.set(now, fix["sigma_xy_m"], fix["sigma_theta_deg"] + 0.3 * steps ** 0.5)
            fix = dict(fix, pose_now=dict(self.tracker.pose), closure_deg=round(wrap_deg(rel["theta_deg"]), 2))
        fix["what"], fix["time_utc"] = what, utc()
        fix["sim_truth_world"] = self.rig.sim_truth_fn() if self.rig.sim_truth_fn else None
        return fix

    def localise(self, env, what, required=True):
        """Full circles until one gives a pose fix. required: a start pose must be fixed, so no fix halts the
        batch. Otherwise (where the car is before a transit, an episode's end pose) the record says "no full fix"
        and carries the tracked pose with its uncertainty; the guard still stops everything once that is too large."""
        last = None
        for attempt in range(self.params.scan_attempts):
            last = self.scan(env, "%s (scan %d)" % (what, attempt + 1))
            if last["ok"]:
                return last
        if required:
            self.monitor.halt("no_fix", "%s: no tag fix from %d full circles (%s)" % (
                what, self.params.scan_attempts, last.get("why")))
            raise BatchStop(what)
        return dict(last, pose_now=dict(self.tracker.pose), sigma_xy_m=self.tracker.sigma_xy_m,
                    sigma_theta_deg=self.tracker.sigma_theta_deg, tracked_only=True)

    def _turn_to(self, env, heading_deg, what):
        n = int(round(wrap_deg(heading_deg - self.tracker.pose["theta_deg"]) / TURN_DEG))
        for _ in range(abs(n)):
            self._must(env, "TURN_LEFT_30" if n > 0 else "TURN_RIGHT_30", what)

    def go_to(self, env, target, what):
        """Drive to the target pose with C2 moves: face it, go, look again. Bounded; halts when not reached."""
        p = self.params
        for attempt in range(p.start_attempts + int(2.0 / p.max_blind_travel_m)):
            pose = self.tracker.pose
            dx, dy = target["x_m"] - pose["x_m"], target["y_m"] - pose["y_m"]
            dist = math.hypot(dx, dy)
            if dist > p.start_tol_m:
                self._turn_to(env, math.degrees(math.atan2(dy, dx)), what)
                for _ in range(int(dist / 0.10) + 2):
                    pose = self.tracker.pose
                    along = ((target["x_m"] - pose["x_m"]) * math.cos(math.radians(pose["theta_deg"]))
                             + (target["y_m"] - pose["y_m"]) * math.sin(math.radians(pose["theta_deg"])))
                    if along < 0.07:
                        break
                    move = "FORWARD_25" if along >= 0.20 else "FORWARD_10"
                    if env._blind(move):
                        # far enough since the last tag fix: look around before going on
                        self.localise(env, "%s: a look around on the way" % what, required=False)
                        if env._blind(move):
                            self.monitor.halt("no_fix", "%s: no tag fix on the way after %.2f m" % (
                                what, self.tracker.travel_since_fix_m))
                            raise BatchStop(what)
                        break               # the circle may have moved the pose estimate: aim again
                    self._must(env, move, what)
            self._turn_to(env, target["theta_deg"], what)
            fix = self.localise(env, "%s, attempt %d" % (what, attempt + 1))
            pose = self.tracker.pose
            miss = math.hypot(target["x_m"] - pose["x_m"], target["y_m"] - pose["y_m"])
            turn = abs(wrap_deg(target["theta_deg"] - pose["theta_deg"]))
            if miss <= p.start_tol_m and turn <= p.start_tol_deg:
                return dict(fix, miss_m=round(miss, 3), miss_deg=round(turn, 1), attempts=attempt + 1)
        self.monitor.halt("start_pose", "%s: %.2f m and %.0f degrees from the start pose after %d attempts (tolerance "
                          "%.2f m, %.0f degrees)" % (what, miss, turn, attempt + 1, p.start_tol_m, p.start_tol_deg))
        raise BatchStop(what)

    def _scale_check(self, origin, fix_sigmas=None, what="transit"):
        """The transit from one full-circle fix to the next, measured twice: by odometry alone and by the tags. A
        wrong encoder scale (a wrong car.json) shows here, in the first minute, before any episode. fix_sigmas: the
        two circles' own position sigmas (the episode check); without them the tracked sigma and the floor are taken,
        as the transit always has."""
        t, p = self.tracker, self.params
        dr = t.dead_reckoned
        t.dead_reckoned = None
        if origin is None or dr is None:
            return {"checked": False, "why": "no full-circle fix before the transit"}
        by_odometry = math.hypot(dr["x_m"] - origin["x_m"], dr["y_m"] - origin["y_m"])
        by_tags = math.hypot(t.pose["x_m"] - origin["x_m"], t.pose["y_m"] - origin["y_m"])
        out = {"checked": False, "by_odometry_m": round(by_odometry, 3), "by_tags_m": round(by_tags, 3)}
        if by_odometry < p.transit_scale_min_m or by_tags < p.transit_scale_min_m:
            return dict(out, why="transit shorter than %.2f m" % p.transit_scale_min_m)
        ratio = by_tags / by_odometry
        if fix_sigmas:
            slack = 2.0 * math.hypot(*fix_sigmas) / by_tags            # the two circles' own uncertainty
        else:
            slack = 2.0 * (t.sigma_xy_m + p.fix_floor_m) / by_tags      # what the two fixes' own uncertainty allows
        out.update(checked=True, tags_over_odometry=round(ratio, 3), limit=round(p.transit_scale_tol + slack, 3))
        if abs(ratio - 1.0) > p.transit_scale_tol + slack:
            self.monitor.halt("odometry_scale", "the %s measures %.2f m by odometry and %.2f m by the tags (ratio "
                              "%.2f, limit 1 +- %.2f): the encoder scale in configs/car.json is wrong, or the tags are"
                              % (what, by_odometry, by_tags, ratio, p.transit_scale_tol + slack))
        return out

    # ------------------------------------------------------------ the batch

    def preflight(self):
        """Before anything moves: latch clear, the drive map applied and read back."""
        self.monitor.check_latch()
        if self.monitor.halted is not None:
            raise BatchStop("latch")
        want = tuple(self.params.drive_map)
        got = self.rig.link.set_drive_map(*want)
        state = self.rig.link.car_state()
        self.monitor.check_car(state)
        if self.monitor.halted is not None:
            raise BatchStop("car")
        got = state.get("drive_map") or got
        if got is None or abs(got[0] - want[0]) > 0.0015 or abs(got[1] - want[1]) > 0.0015:
            self.monitor.halt("drive_map", "the car reports drive map %s after setting %s" % (got, list(want)))
            raise BatchStop("drive map")
        # the first circle turns on a pose nobody has confirmed: it needs room for the tape being wrong by the gate
        room = self.guard.axle_depth(self.tracker.pose) - self.sweep
        need = self.params.wall_margin_m + (0.0 if self.localised else self.params.initial_gate_m)
        if room < need:
            self.monitor.halt("guard_blocked", "the taped pose leaves %.2f m around the car's sweep circle; the first "
                              "circle needs %.2f m (put the car nearer the middle)" % (room, need))
            raise BatchStop("initial pose")
        return {"drive_map": list(got)}

    def run(self):
        try:
            self.manifest = self._load_manifest()
        except BatchStop as exc:
            self.log(str(exc))
            return {"status": "refused", "detail": str(exc)}
        m = self.manifest
        m["moves_base"] = m.get("moves_sent", 0)
        m["elapsed_base"] = m.get("elapsed_s", 0.0)
        self.monitor.steps_before = m["moves_base"]
        self.monitor.elapsed_before = m["elapsed_base"]
        if self.monitor.halt_file_present():
            self.log("%s exists: an operator clears it first (car_batch.py clear-halt --operator <name>)" % self.halt_path)
            return {"status": "refused", "detail": "HALT.LATCH exists"}
        self._save("running")
        try:
            m["preflight"] = self.preflight()
            done = {e["index"] for e in m["episodes"] if e["status"] == "done"}
            for index in range(self.params.episodes):
                if index in done:
                    continue
                self.monitor.check_latch()
                self.monitor.check_clocks()
                if self.budget is not None and self.budget.exceeded():
                    self.monitor.halt("usd_cap", "spent $%.2f of $%.2f" % (self.budget.spent, self.budget.cap), safety=False)
                if self.monitor.halted is not None:
                    raise BatchStop("before episode %d" % index)
                self._episode(index)
                if self.monitor.halted is not None:
                    raise BatchStop("episode %d" % index)
            # the last look: a fault after the last move must not leave a batch called complete
            self.monitor.check_latch()
            self.monitor.check_car(self.rig.link.car_state())
            if self.monitor.halted is not None:
                raise BatchStop("after the last episode")
            self._save("complete")
        except BatchStop:
            self._save("halted")
        except KeyboardInterrupt:
            self.monitor.halt("interrupted", "interrupted by the operator", safety=False)
            self._save("halted")
        except Exception as exc:    # noqa: BLE001 - anything unexpected halts the batch; nothing is retried
            self.monitor.halt("error", "%s: %s" % (type(exc).__name__, str(exc)[:300]))
            self._save("halted")
        return {"status": self.manifest["status"], "halt": self.monitor.halted}

    def _episode(self, index):
        m, p = self.manifest, self.params
        target = p.start_poses[index % len(p.start_poses)]
        attempt = 1 + sum(1 for e in m["episodes"] if e["index"] == index)
        ep_id = "ep%02d-a%d" % (index + 1, attempt)
        ep_dir = os.path.join(self.out, "episodes", ep_id)
        os.makedirs(ep_dir, exist_ok=True)
        entry = {"index": index, "id": ep_id, "attempt": attempt, "scenario": target.get("id"), "policy": p.policy,
                 "seed": p.seed0 + index, "status": "running", "started": utc(), "target_start": dict(target)}
        m["episodes"].append(entry)
        self.monitor.t_episode = self.monitor.clock()
        self._save()
        self._mark("episode_start", entry)
        try:
            pre = self._service_env(ep_id + "-pre", os.path.join(ep_dir, "pre"))
            pre.reset(entry["seed"])
            if self.monitor.halted is not None:
                raise BatchStop("first sensing")
            # the first circle of a process must give a fix: until it does, the guard rests on a taped pose alone
            entry["first_fix"] = self.localise(pre, "%s: where the car is" % ep_id, required=not self.localised)
            self.localised = True
            pre.use_views = True
            origin = self.tracker.mark_dead_reckoning() if entry["first_fix"]["ok"] else None
            entry["start_fix"] = self.go_to(pre, target, "%s: to the start pose" % ep_id)
            entry["odometry_scale_check"] = self._scale_check(origin)
            if self.monitor.halted is not None:
                raise BatchStop("odometry scale")
            start = dict(self.tracker.pose)
            entry["start_pose_world"] = start
            # the episode itself is checked like the transit: odometry alone from this circle to the end circle
            # against the two circles' fixes (2026-11-25; the per-step statistic alone was too noisy on the car)
            episode_origin = self.tracker.mark_dead_reckoning()
            scene = self.kr.room_scene(self.world, start_pose=start)
            inner = self.rig.make_env(ep_id, scene=scene, log_dir=os.path.join(ep_dir, "backend"))
            env = BatchEnv(inner, self.tracker, self.guard, self.monitor, self.tags, p, start,
                           truth_path=os.path.join(ep_dir, "truth.jsonl"), sim_truth_fn=self.rig.sim_truth_fn,
                           tagcheck=self.tagcheck)
            path = os.path.join(ep_dir, "seed_%d.jsonl" % entry["seed"])
            watch = [self.halt_path] + ([self.rig.latch.path] if self.rig.latch is not None else [])
            agent = HaltAwareDriver(self.driver, self.monitor, self.rig.link)
            res = self.run_episode(agent, self.system_text, env, entry["seed"], path, self.budget, p.max_steps,
                                   self.log, config=self.config, autolatch_contacts=self.autolatch_contacts,
                                   watch_latch_paths=watch)
            entry["result"] = res
            entry["guard_blocked_moves"] = env.blocked
            entry["requests_not_sent_after_halt"] = agent.requests_refused
            if agent.requests_refused and self.monitor.halted is not None and not res.get("complete"):
                # the harness reports the wrapper's refusal as its spend cap; say what it really was
                entry["result"] = dict(res, ended_by="halt", detail="batch halt: %s (no request was sent; the harness "
                                       "saw this as its cap answer)" % self.monitor.halted["code"])
            if not res.get("complete"):
                self.monitor.halt("usd_cap", "the spend cap stopped the episode at step %s" % res.get("steps"), safety=False)
            elif res.get("ended_by") == "latch" and self.monitor.halted is None:
                self.monitor.check_latch()
                self.monitor.halt("harness_latch", res.get("detail"))
            elif res.get("ended_by") == "error" and not str(res.get("detail")).startswith(("no_progress", "driver stopped")):
                self.monitor.halt("harness_error", res.get("detail"), safety=False)
            # (no_progress, driver stopped: the agent stopped deciding moves that are allowed, or the coded procedure
            # met a branch it does not implement. That is the agent's result, recorded in the episode; the car is
            # healthy, and the next episode starts with a transit elsewhere.)
            if self.monitor.halted is not None:
                raise BatchStop("episode")
            before = dict(self.tracker.pose)
            post = self._service_env(ep_id + "-post", os.path.join(ep_dir, "post"))
            post.reset(entry["seed"])
            entry["end_fix"] = self.localise(post, "%s: end pose" % ep_id, required=False)
            if entry["end_fix"].get("ok") and not entry["end_fix"].get("tracked_only"):
                sigmas = (float(entry["start_fix"].get("circle_sigma_xy_m") or entry["start_fix"]["sigma_xy_m"]),
                          float(entry["end_fix"].get("circle_sigma_xy_m") or entry["end_fix"]["sigma_xy_m"]))
                entry["odometry_scale_check_episode"] = self._scale_check(episode_origin, fix_sigmas=sigmas,
                                                                          what="episode (start circle to end circle)")
                if self.monitor.halted is not None:
                    raise BatchStop("odometry scale over the episode")
            else:
                self.tracker.dead_reckoned = None
                entry["odometry_scale_check_episode"] = {"checked": False, "why": "no full-circle fix at the end"}
            ranges = self.tracker.range_scale(1)
            entry["odometry_range_scale"] = None if ranges is None else {
                "tags_over_odometry_median": round(ranges[0], 3), "straight_moves": ranges[1], "range_pairs": ranges[2],
                "note": "the whole batch so far"}
            entry["end_pose_world"] = dict(self.tracker.pose)
            entry["end_pose_map"] = to_map_pose(start, self.tracker.pose)
            # how far the pose tracked through the episode was from what the end circle then measured
            entry["tracked_minus_end_scan"] = {
                "m": round(math.hypot(before["x_m"] - self.tracker.pose["x_m"], before["y_m"] - self.tracker.pose["y_m"]), 3),
                "deg": round(abs(wrap_deg(before["theta_deg"] - self.tracker.pose["theta_deg"])), 1),
                "end_scan_is_a_full_fix": bool(entry["end_fix"]["ok"])}
            agent, truth = _last_report(path)
            entry["agent_final_pose_map"], entry["truth_at_that_step_map"] = agent, truth
            if agent and truth:
                # the agent's last report against the batch's pose AT THAT OBSERVATION (the move decided in that
                # step runs afterwards, so the end circle measures a later pose)
                entry["final_pose_error"] = {"m": round(math.hypot(agent["x_m"] - truth["x_m"], agent["y_m"] - truth["y_m"]), 3),
                                             "deg": round(abs(wrap_deg(agent["theta_deg"] - truth["theta_deg"])), 1),
                                             "truth_sigma_xy_m": truth.get("sigma_xy_m"),
                                             "truth_is_a_tag_fix": bool(truth.get("fix"))}
            entry["status"] = "done"
        except BatchStop:
            entry["status"] = "halted"
            raise
        except Exception:
            entry["status"] = "failed"
            raise
        finally:
            if entry["status"] == "running":    # an interrupt: neither done nor to be replayed
                entry["status"] = "halted"
            entry["ended"] = utc()
            entry["halt"] = self.monitor.halted
            self.monitor.t_episode = None
            self._save()
            self._mark("episode_end", entry)


def _last_report(path):
    """(pose of the last valid report, the environment's truth of that row), both in the map frame, or (None, None)."""
    pose = truth = None
    try:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                report = row.get("report")
                if isinstance(report, dict) and isinstance(report.get("pose"), dict) and isinstance(row.get("truth"), dict):
                    try:
                        pose = {k: float(report["pose"][k]) for k in ("x_m", "y_m", "theta_deg")}
                        truth = dict(row["truth"])
                    except (KeyError, TypeError, ValueError):
                        continue
    except OSError:
        pass
    return pose, truth


def summary_text(m):
    """The manifest as plain text for a person."""
    lines = ["Car batch %s (%s)" % (m.get("config"), "real car" if m.get("real_car") else "simulated car, dry run"),
             "status: %s   updated: %s   resumes: %s" % (m.get("status"), m.get("updated"), m.get("resumes")),
             "world: %s   policy: %s   episodes asked: %s   moves sent: %s   spent: US$%.2f" % (
                 m.get("world_id"), m["params"]["policy"], m["params"]["episodes"], m.get("moves_sent"),
                 m.get("spent_usd") or 0.0)]
    halt = m.get("halt")
    if halt:
        lines.append("HALTED: %s: %s (%s)%s" % (halt["code"], halt["detail"], halt["time_utc"],
                                               "; the project latch was set" if halt.get("safety") else ""))
        lines.append("Nothing is retried. Look at the car, then: car_batch.py clear-halt --out <this folder> "
                     "--operator <name> (and car_move.py clear-latch if the project latch is set), then run again.")
    tc = m.get("tag_check") or {}
    if tc.get("this_run"):
        lines.append("tags checked against each other in this run: %d, trusted to steer a step's fix: %d%s" % (
            len(tc["this_run"]), len(tc.get("trusted") or []),
            "; DISAGREEING: %s" % ", ".join(tc["flagged"]) if tc.get("flagged") else ""))
    lines.append("fix sigma: %s" % m["params"].get("fix_sigma_source", ASSUMED_FIX_SIGMA))
    lines.append("design values: %s" % m["params"].get("dv_file", "configs/dv.json (frozen)"))
    if m["params"].get("sigma_sources"):
        lines.append("sigma sources: %s" % m["params"]["sigma_sources"])
    lines.append("")
    for e in m.get("episodes", []):
        res = e.get("result") or {}
        err = e.get("final_pose_error")
        lines.append("%s  %-7s scenario %s  start miss %s  ended_by %s (%s) after %s steps%s%s" % (
            e["id"], e["status"], e.get("scenario"),
            "%.2f m / %.0f deg" % (e["start_fix"]["miss_m"], e["start_fix"]["miss_deg"]) if e.get("start_fix") else "-",
            res.get("ended_by"), res.get("detail"), res.get("steps"),
            "  final pose error %.2f m / %.0f deg (truth sigma %.2f m, %s)" % (
                err["m"], err["deg"], err["truth_sigma_xy_m"] or 0.0,
                "tag fix at that step" if err.get("truth_is_a_tag_fix") else "tracked since the last fix") if err else "",
            "  HALT %s" % e["halt"]["code"] if e.get("halt") else ""))
    return "\n".join(lines) + "\n"
