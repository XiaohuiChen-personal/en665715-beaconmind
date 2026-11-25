"""ffmpeg for the video: where it is, the argument lists (never a shell string), and the pipes.

ffmpeg is looked up in this order: the --ffmpeg option, $BM_FFMPEG, `ffmpeg` on PATH, ~/.local/bin/ffmpeg (the
Spark's static build, plan MD6), and the binary bundled in the imageio-ffmpeg wheel (the Mac has no system ffmpeg;
the wheel ships a static ffmpeg 7.1 with libx264). Nothing is installed system-wide.

Every part is encoded once with the same settings (H.264, yuv420p, 25 fps, 1920 x 1080, CRF 18, "+faststart"), so
the parts and the cards join with the concat demuxer without a second encode (plan M6.T14 pitfall).

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-24: wrote this module.
"""
import os
import re
import shutil
import subprocess

ENCODE = ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart"]


def find_ffmpeg(explicit=None):
    cands = [explicit, os.environ.get("BM_FFMPEG"), shutil.which("ffmpeg"),
             os.path.expanduser("~/.local/bin/ffmpeg")]
    for c in cands:
        if c and os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.isfile(exe):
            return exe
    except Exception:  # noqa: BLE001 - not installed, or no binary for this platform
        pass
    return None


def encode_cmd(ffmpeg, size, fps, out):
    """Raw RGB frames on stdin -> one H.264 file."""
    return [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", "%dx%d" % tuple(size), "-framerate", str(fps), "-i", "-", "-an"] + ENCODE + ["-r", str(fps), out]


class Encoder:
    """with Encoder(ffmpeg, size, fps, out) as enc: enc.write(pil_image) ..."""

    def __init__(self, ffmpeg, size, fps, out):
        self.cmd = encode_cmd(ffmpeg, size, fps, out)
        self.size, self.n = tuple(size), 0
        self.proc = None

    def __enter__(self):
        self.proc = subprocess.Popen(self.cmd, stdin=subprocess.PIPE)
        return self

    def write(self, img, repeat=1):
        if img.size != self.size:
            raise ValueError("frame is %r, the encoder takes %r" % (img.size, self.size))
        data = img.convert("RGB").tobytes()
        for _ in range(repeat):
            self.proc.stdin.write(data)
            self.n += 1

    def __exit__(self, *exc):
        self.proc.stdin.close()
        code = self.proc.wait()
        if code != 0 and exc[0] is None:
            raise RuntimeError("ffmpeg exited with %d: %s" % (code, " ".join(self.cmd)))
        return False


def concat_list_text(paths):
    """The concat demuxer's list: one `file '<absolute path>'` line per part (single quotes escaped)."""
    return "".join("file '%s'\n" % os.path.abspath(p).replace("'", "'\\''") for p in paths)


def concat_cmd(ffmpeg, list_file, out):
    return [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
            "-c", "copy", "-movflags", "+faststart", out]


def mux_cmd(ffmpeg, video, audio, out):
    """Narration under the video. apad pads the audio with silence and -shortest then stops at the video's end, so
    a narration a little shorter than the video never cuts the last card (plan M6.T11)."""
    return [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", video, "-i", audio, "-map", "0:v", "-map", "1:a",
            "-c:v", "copy", "-af", "apad", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out]


def still_cmd(ffmpeg, video, t, out):
    return [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-ss", "%.3f" % t, "-i", video, "-frames:v", "1", out]


def decode_cmd(ffmpeg, video, start_s, dur_s, speed, fps, size, n_frames):
    """Raw RGB frames of video[start_s, start_s + dur_s], played at `speed`, resampled to fps and letterboxed
    into size, exactly n_frames of them (the last one repeats if the clip ends early is the caller's job)."""
    w, h = size
    vf = ("setpts=(PTS-STARTPTS)/%s,fps=%d,scale=%d:%d:force_original_aspect_ratio=decrease,"
          "pad=%d:%d:(ow-iw)/2:(oh-ih)/2" % (repr(float(speed)), fps, w, h, w, h))
    return [ffmpeg, "-hide_banner", "-loglevel", "error", "-ss", "%.3f" % max(0.0, start_s), "-i", video,
            "-t", "%.3f" % max(0.001, dur_s), "-vf", vf, "-frames:v", str(int(n_frames)), "-an",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]


def probe(ffmpeg, path):
    """{duration_s, fps, width, height, frames (counted by decoding), audio (bool)} of a file, from ffmpeg itself
    (the imageio-ffmpeg wheel has no ffprobe)."""
    out = subprocess.run([ffmpeg, "-hide_banner", "-i", path, "-map", "0:v:0", "-c", "copy", "-f", "null", "-"],
                         capture_output=True, text=True)
    err = out.stderr
    info = {"path": path}
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    if m:
        info["duration_s"] = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    m = re.search(r"Video: (\w+).*?, (\d{2,5})x(\d{2,5})", err)
    if m:
        info["codec"], info["width"], info["height"] = m.group(1), int(m.group(2)), int(m.group(3))
    m = re.search(r"(\d+(?:\.\d+)?) fps", err)
    if m:
        info["fps"] = float(m.group(1))
    frames = re.findall(r"frame=\s*(\d+)", err)
    if frames:
        info["frames"] = int(frames[-1])
    info["audio"] = bool(re.search(r"Stream #\d+:\d+.*Audio:", err))
    return info


def run(cmd):
    subprocess.run(cmd, check=True)
