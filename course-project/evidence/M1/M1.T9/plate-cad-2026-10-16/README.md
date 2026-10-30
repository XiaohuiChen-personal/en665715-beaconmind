# 2026-10-16 run logs: car.json and the URDF rebuilt with the plate CAD

What changed and why: `../README.md` (2026-10-16 section). The plate-CAD README stays in the private course repo and is not published here.

| File | What it shows |
| --- | --- |
| `pytest-mac.txt` | `beaconmind` tests on the Mac (Python 3.13 venv): **63 passed** (55 before + 8 new plate-CAD tests in `tests/test_car_model.py`) |
| `pytest-py310.txt` | the same suite in `beaconmind-ros` on spark-2a60 (Python 3.10.12, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`): **63 passed** |
| `colcon-test.txt` | `colcon test --packages-select beaconmind_description` in `beaconmind-ros` (domain 141, localhost only): **21 tests, 0 errors, 0 failures, 1 skipped** (the camera.json test), with the list of tests run; the new one is `test_plate_outline_matches_measurements`. The first run failed `test_chassis_boxes_do_not_overlap` (wing slices 3/4 overlapping by 1 µm); fixed by the 2 µm slice grid, then this run |
| `urdf-named-diff.txt` | the expanded URDF before (`81a7d617…`) and after (`d0b2ffbf…`), compared element by element by name: only the plate boxes and the chassis inertia's iyy/izz differ |

The Spark-side scratch (`course-project/data/m7-plate-cad/` on spark-2a60, git-ignored) holds `urdf_before.urdf`,
`urdf_after.urdf` and the position-based `urdf_compare.txt` (which misaligns once boxes are inserted, hence the
by-name comparison here). No ROS node or daemon was started; the only ROS process in `beaconmind-ros` afterwards was
the old `tf2_echo` zombie (pid 1645) recorded in `course-project/CONTEXT.md` on 2026-10-10.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-10-16: ran the builds and tests and wrote these notes.
