"""Frames from the car's camera, and the detection pipeline of contract C3 on top of the perception module.

The camera (firmware bm_cam-0.2) answers one HTTP request at a time and takes each /capture frame after the
request arrives (firmware/esp32cam/bm_cam_v02/bm_cam_v02.ino, take_fresh_frame), so a frame asked for after the car
has stopped shows the car stopped. It boots at VGA; the calibrated size is XGA at JPEG quality 12
(configs/camera.json), set through /control?framesize=xga&quality=12. From a container the camera is reached
through the relay on the Spark (http://172.17.0.1:18080, tools/camera_relay.py).

Only one program may be the camera's client. When the backend captures, the recorder runs with `--camera off`, and
HttpCamera saves every frame it receives, with the request and response times and the X-BM-* headers, in the same
layout as tools/record_frames.py (frames/<n>_<host time ns>.jpg and frames/index.jsonl), so rule R2 still holds.

The perception module (beaconmind.perception.tags, written in parallel) is imported only when a detector is built.

AI-assisted: Claude Fable 5.2 via Claude Code, 2026-11-18: wrote the camera client and the detector adapter.
"""
import hashlib
import json
import os
import time
import urllib.error
import urllib.request

RELAY_URL = "http://172.17.0.1:18080"       # tools/camera_relay.py on the Spark, as seen from a container
FRAME_SIZE = "xga"                          # configs/camera.json frame_size / jpeg_quality (work list 2.2)
JPEG_QUALITY = 12


def http_grab(url, timeout):
    """(status, headers, body) of one GET."""
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.status, dict(resp.headers.items()), resp.read()


def bm_headers(headers):
    """The camera's X-BM-* headers, lower-cased, numbers as int where they parse."""
    out = {}
    for key, value in headers.items():
        k = str(key).lower()
        if k.startswith("x-bm-"):
            try:
                out[k] = int(value)
            except (TypeError, ValueError):
                out[k] = value
    return out


def is_jpeg(body):
    return len(body) > 4 and body[:2] == b"\xff\xd8" and body[-2:] == b"\xff\xd9"


class CameraError(RuntimeError):
    pass


class HttpCamera:
    """The camera over HTTP. grab() returns (jpeg bytes, record); every frame is saved under save_dir when given."""

    def __init__(self, base_url=RELAY_URL, timeout_s=5.0, save_dir=None, grabber=http_grab, clock_ns=time.time_ns,
                 expected_size=(1024, 768)):
        self.base = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self.save_dir = save_dir
        self.grabber = grabber
        self.clock_ns = clock_ns
        self.expected_size = expected_size
        self.n = 0
        self.last_ok_ns = None
        self.errors = 0

    def configure(self, framesize=FRAME_SIZE, quality=JPEG_QUALITY):
        """Put the camera in its calibrated mode. Returns the camera's answer."""
        url = "%s/control?framesize=%s&quality=%d" % (self.base, framesize, quality)
        try:
            status, _headers, body = self.grabber(url, self.timeout_s)
        except (OSError, urllib.error.URLError) as exc:
            raise CameraError("camera /control failed: %s: %s" % (type(exc).__name__, exc)) from exc
        if status != 200:
            raise CameraError("camera /control answered %s" % status)
        return body.decode("utf-8", "replace").strip()

    def grab(self):
        self.n += 1
        t_req = self.clock_ns()
        rec = {"n": self.n, "t_req_ns": t_req}
        try:
            status, headers, body = self.grabber(self.base + "/capture", self.timeout_s)
            t_resp = self.clock_ns()
            hdr = bm_headers(headers)
            rec.update({"t_resp_ns": t_resp, "latency_ms": round((t_resp - t_req) / 1e6, 1), "http": status,
                        "bytes": len(body), "sha12": hashlib.sha256(body).hexdigest()[:12], "headers": hdr})
            if status != 200 or not is_jpeg(body):
                raise CameraError("camera /capture answered %s with %d bytes that are not a JPEG" % (status, len(body)))
            size = (hdr.get("x-bm-width"), hdr.get("x-bm-height"))
            if self.expected_size and None not in size and tuple(size) != tuple(self.expected_size):
                raise CameraError("the camera sent %sx%s; the calibration is for %sx%s (run configure())"
                                  % (size[0], size[1], self.expected_size[0], self.expected_size[1]))
            if self.save_dir:
                os.makedirs(self.save_dir, exist_ok=True)
                rec["file"] = "%06d_%d.jpg" % (self.n, t_resp)
                with open(os.path.join(self.save_dir, rec["file"]), "wb") as handle:
                    handle.write(body)
            self.last_ok_ns = t_resp
            return body, rec
        except (OSError, urllib.error.URLError, CameraError) as exc:
            self.errors += 1
            rec.setdefault("t_resp_ns", self.clock_ns())
            rec["error"] = "%s: %s" % (type(exc).__name__, exc)
            raise CameraError(rec["error"]) from exc
        finally:
            if self.save_dir:
                try:
                    os.makedirs(self.save_dir, exist_ok=True)
                    with open(os.path.join(self.save_dir, "index.jsonl"), "a", encoding="utf-8") as handle:
                        handle.write(json.dumps(rec) + "\n")
                except OSError:
                    pass


class FakeCamera:
    """A camera for tests: frame_fn(n) -> bytes (anything the paired detector understands), or a CameraError."""

    def __init__(self, frame_fn=None):
        self.frame_fn = frame_fn or (lambda n: b"\xff\xd8fake%d\xff\xd9" % n)
        self.n = 0
        self.configured = None
        self.last_ok_ns = None
        self.errors = 0

    def configure(self, framesize=FRAME_SIZE, quality=JPEG_QUALITY):
        self.configured = (framesize, quality)
        return "ok"

    def grab(self):
        self.n += 1
        try:
            body = self.frame_fn(self.n)
        except CameraError:
            self.errors += 1
            raise
        self.last_ok_ns = time.time_ns()
        return body, {"n": self.n, "file": None, "bytes": len(body)}


def camera_status(camera, frames_wanted, frames_got):
    """sensors.camera of contract C3: "ok", "stale" (some frames of this stop are missing) or "down" (none came)."""
    if frames_got >= frames_wanted:
        return "ok"
    return "down" if frames_got == 0 else "stale"


def capture_frames(camera, n_frames, max_failures=2):
    """Up to n_frames frames, one after another. A failed request is retried until max_failures have failed.
    Returns ([jpeg bytes], [record per request])."""
    frames, records, failures = [], [], 0
    while len(frames) < n_frames and failures <= max_failures:
        try:
            body, rec = camera.grab()
            frames.append(body)
            records.append(rec)
        except CameraError as exc:
            failures += 1
            records.append({"error": str(exc)})
    return frames, records


def perception_detector(camera_path=None, tag_size_m=0.16, obs_min_frames=3, tag_center_height_m=None, **settings):
    """The real detector: a callable (list of JPEG bytes, frames wanted) -> {"detections", "internal", "per_frame"}.

    Each frame goes through beaconmind.perception.tags.detect_tags with the calibrated camera of
    configs/camera.json; fuse_frames applies contract C3 (tags seen in at least obs_min_frames frames, median
    position in base_link, quality = frames seen / frames taken). "detections" is the observation's list (det, id,
    range_m, bearing_deg, quality); "internal" is detections_internal (run log only); "per_frame" lists what each
    frame gave. Needs numpy and OpenCV (the beaconmind-ros container has both)."""
    import cv2
    import numpy as np

    from beaconmind.camera_model import load_camera
    from beaconmind.perception import tags

    camera = load_camera(camera_path)

    def detect(jpegs, frames_wanted=None):
        per_frame, lists = [], []
        for body in jpegs:
            image = cv2.imdecode(np.frombuffer(body, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
            if image is None:
                per_frame.append({"error": "not decodable"})
                lists.append([])
                continue
            try:
                found = tags.detect_tags(image, camera, tag_size_m, tag_center_height_m=tag_center_height_m, **settings)
            except ValueError as exc:       # a frame of another size: the intrinsics do not apply
                per_frame.append({"error": str(exc)})
                lists.append([])
                continue
            lists.append(found)
            per_frame.append({"detections": [{"id": int(d["id"]), "range_m": round(float(d["range_m"]), 3),
                                              "bearing_deg": round(float(d["bearing_deg"]), 2),
                                              "quality": round(float(d["quality"]), 3)} for d in found]})
        fused = tags.fuse_frames(lists, obs_frames=frames_wanted or len(lists), obs_min_frames=obs_min_frames)
        return {"detections": tags.to_observation_detections(fused),
                "internal": tags.to_internal_detections(fused), "per_frame": per_frame}

    return detect


def fake_detector(detections_fn):
    """A detector for tests: detections_fn(jpegs) -> the observation's detections list."""
    def detect(jpegs, frames_wanted=None):
        dets = [dict(d) for d in detections_fn(jpegs)]
        dets.sort(key=lambda d: -d["bearing_deg"])
        for i, d in enumerate(dets):
            d["det"] = i
        return {"detections": dets, "internal": [], "per_frame": [{"n": i} for i in range(len(jpegs))]}
    return detect
