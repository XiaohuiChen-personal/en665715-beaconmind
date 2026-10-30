"""BeaconMind is the pure-Python package for the EN.665.715 course project.

An LLM owns landmark SLAM: this package will hold the contracts, geometry, harness,
baselines and metrics. Importing it does not import ROS. course_root() finds the
course-project directory on the Mac, on the Spark mirror and inside a container.

AI-assisted: Grok 4.7 via Cursor, 2026-10-06: wrote the package root and course_root().
"""

__version__ = "0.1.0"

from pathlib import Path
import os


def course_root() -> Path:
    """course-project/ folder: $BM_COURSE_ROOT if set, else the first parent of this file that
    contains configs/ and plan/ (works for the Mac checkout, the Spark mirror and /workspace)."""
    override = os.environ.get("BM_COURSE_ROOT")
    if override:
        root = Path(override).expanduser()
        if not root.is_dir():
            raise FileNotFoundError(
                "BM_COURSE_ROOT is set to {0!r}, which is not an existing directory".format(
                    override
                )
            )
        return root.resolve()
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "configs").is_dir() and (parent / "plan").is_dir():
            return parent
    raise FileNotFoundError(
        "course-project root not found: BM_COURSE_ROOT is unset and no parent of {0} "
        "contains both configs/ and plan/".format(here)
    )
