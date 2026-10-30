# BeaconMind public-repo migration

Date: 2026-10-29. Student: Xiaohui Chen.

This file is the durable record of the move. The private course repository stays private and keeps its history. This repository is a new git history whose first commit is the public project tree.

## Why

The class-project code-repository item asks for one GitHub repo the instructor can open: a README with the student's name and one or two sentences about the project, at least one commit, and no secrets (`wifi_config.h`, API keys). It also says to ignore `build/` and, only if a depth lab is included, `depth/hf_cache` and `depth/results`. BeaconMind does not include that depth lab. Nothing was submitted to Canvas. Grading for that item is Complete/Incomplete when the instructor can open the link.

The private course repo must not be made public and must not be history-split. Assignment solutions and a few secrets exist in its history and in tracked files outside `course-project/`.

## What was copied

Tracked files from `git ls-files course-project` in the private course repo, placed at `course-project/` so existing path strings keep working. Copy method: `git archive` of that tree (tracked files only). Not `cp -a`, and not `sync_to_spark.sh`.

That excludes gitignored `.venv`, `course-project/report/sources/` (copyrighted papers), both `wifi_config.h` files, `__pycache__`, and `course-project/data/`.

`reference/hardware/` in this repo is a second copy of the notes listed below, scrubbed here only. The private course repo's originals were not edited in that step.

Hardware notes copied, then given a one-line public-copy header:

- `wiring-plan.md`
- `pico-bringup.md`
- `esp32cam-notes.md`
- `car-build-notes.md`
- `wifi-roaming-design-2026-10-23.md`
- `pico2w-pin-map.md`
- `bno055-pin-map.md`
- `tb6612fng-pin-map.md`
- `ams1117-pin-map.md`
- `buck5v-pin-map.md`
- `motor-encoder-cable-map.md`
- `motor-options-2026-10-22.md`

Photos copied so those notes' image links resolve: `esp32cam-board.jpg`, `esp32cam-mb-underside.jpg`, `esp32cam-ov3660.jpg`, `buck5v-front.jpg`, `buck5v-back.jpg`, `motor-plug-a.jpg`, `motor-plug-b.jpg`, `motor-cable-ends.jpg`, `pico2w-underside.jpg`, `ams1117-label-side.jpg`, `ams1117-chip-side.jpg`, `tb6612fng-front.jpg`, `tb6612fng-back.jpg`, `bno055-top.jpg`.

`IEEEtran.cls`, `IEEEtran.bst`, and `IEEEabrv.bib` came with the report. They are the IEEE conference class, not the JHU presentation template.

## What was excluded

- `course-project/beaconmind/tests/fixtures/reference/l2_geometry.py` (byte-identical assignment solution). `test_matches_reference_random` skips when the file is absent. `SOURCES.sha256` no longer lists it. `fewshot-numbers.json` stayed. The geometry library was not rewritten. On 2026-10-29, `pytest tests/test_geometry.py` in this tree: 7 passed, 1 skipped.
- `course-project/Chen-Project-Proposal.pptx` (built from the JHU presentation template).
- `course-project/QuadChart-Template.pptx` (instructor template).
- `reference/templates/` (not copied).
- `reference/hardware/emo-chassis-plate/` (classmate CAD and the classmate's name). Derived sizes stay in `configs/car.json`.
- `reference/hardware/fritzing-setup.md`.
- Anything under `assignments/`, `discussions/`, or `knowledge-points/`.
- No `wifi_config.h` file is on disk in this repo. Confirmed by `find . -name wifi_config.h`.

`build_proposal.py` and `validate_proposal.sh` stayed. They refer to the QuadChart template by path. That template is not in this repo, so those scripts cannot rebuild the proposal here. That is intentional.

## Scrub list (applied to this repo only)

- Wi-Fi SSID and password values: not found in tracked text. The example headers still contain the placeholders `your-ssid`, `your-password`, `YOUR_2_4_GHZ_WIFI_NAME`, and `YOUR_WIFI_PASSWORD`. Those are not credentials.
- Gmail address and a `100.x` Tailscale address on two `ps` lines in `course-project/evidence/M1/M1.T6/usb-and-load.txt`, replaced with `<redacted>`. The address values are not repeated in this file.
- Full MAC printed by esptool in `flash-id.txt`, `dout-write.txt`, and `uxga-write.txt`, replaced with `<redacted>`. The broadcast address `ff:ff:ff:ff:ff:ff` in the Wi-Fi design stayed. It is the hinted-join constant, not a device.
- `cursor.com` address in `plan/M5-report.md`, replaced with `email removed`.
- Classmate's name (`Vincent Hu` and `V. Hu`) in `CONTEXT.md`, `car.json`, evidence, and the measurements CSV, replaced with "a classmate".
- Room-by-room home-mesh map in the public `wifi-roaming-design-2026-10-23.md`: room names, per-node LAN addresses, and the eero-app checklist removed. Firmware decisions stayed (session supervisor, roam thresholds, host node choice, `WIFI_NODE_PRIORS`, why channel 6 stalls matter). Last-three-byte node labels stayed. They are not full MACs. The private original is unchanged.
- Plate-CAD path `reference/hardware/emo-chassis-plate/` in imported project files now says the CAD is not published here. One broken join (`…here)README.md`) in `evidence/M1/M1.T9/plate-cad-2026-10-16/README.md` was rewritten.
- `pico-bringup.md` no longer points at an assignment photo that is not in this repo.
- Maintainer email in `package.xml` and `setup.py`: left as the address `gh api users/XiaohuiChen-personal` returns on the public profile (`email` field, account id 6566440). That is the verified public maintainer address, not a placeholder. No personal address was invented. The GitHub noreply form was not needed.

Home LAN `192.168` addresses that are operational (camera IP, agent IP) stayed. `user: "1000:1000"` in Compose is a uid, not a Tailscale address.

## Evidence images

Looked at every JPEG and PNG under `course-project/evidence` before commit:

| File | Decision |
| --- | --- |
| `evidence/M1/M1.T5/render-d1.0.png`, `render-d2.0.png` | Keep. Simulated AprilTag on a blank wall. |
| `evidence/M1/M1.T6/bm_cam_v02/capture-1.jpg`, `capture-2.jpg`, `capture-3.jpg` | Keep. Blinds and a desk. No face. |
| `evidence/M1/M1.T6/pictures/floor-1.jpg`, `floor-2.jpg`, `floor-3.jpg` | Keep. Floor scene of the home interior from the robot. No face, readable document, account screen, or mail. |
| `evidence/M1/M1.T6/pictures/uxga-1.jpg`, `uxga-2.jpg`, `uxga-3.jpg` | Keep. Wood panel and a desk. Papers in frame are not readable. |

No evidence image was dropped.

Board photos under `reference/hardware/` are close-ups of the kit boards. They were copied because the pin notes link to them.

## Claims checked against the 2026-10-29 handoff

`AGENTS.md`, `README.md`, and the top of `CONTEXT.md` say: the Pico image the docs name is Build K2 and the chip was not re-read that day; `bm_cam-0.2` is flashed and not calibrated; the URDF mass is still the 2026-10-10 car; M1.T7 is not done. Older `CONTEXT.md` entries stay as history. The 2026-10-29 entry is first and wins. The 2026-10-06 M1.T2 note now says `l2_geometry.py` is not in this tree.

## Search before the first push

Run from this repo root, after the tree and this file's earlier sections were written. A second run is recorded at the bottom after this file existed, because this file names the patterns.

```bash
find . -name wifi_config.h -print
# content scan over text files, skipping .git:
# gmail.com, utexas.edu, cursor.com, ts.net, 100.109,
# tailscale-shaped 100.x.x.x, Vincent, "V. Hu", word Hu,
# colon MAC ([0-9a-f]{2}:){5}, QuadChart, JHU-Presentation, .potx,
# l2_geometry.py, and quoted password/SSID assignments
# path scan: a file named l2_geometry.py, assignment7, assignment8,
# .venv, report/sources, .pptx, .potx
```

First-run results (before this file existed):

| Check | Result |
| --- | --- |
| `wifi_config.h` on disk | none |
| file named `l2_geometry.py` | none |
| path containing `assignment7` or `assignment8` | none (prose mentions of the private course repo remain) |
| `.venv`, `report/sources`, `.pptx`, `.potx` | none |
| `gmail.com`, `cursor.com`, `ts.net`, `100.109`, other `100.x.x.x` | 0 |
| `Vincent`, `V. Hu`, word `Hu` | 0 |
| `utexas.edu` | 4, all the public maintainer email in the two packages' `package.xml` and `setup.py` |
| colon MAC | 1, the broadcast hinted-join address in the Wi-Fi design |
| quoted password or SSID assignment | 0 real values; example headers use the placeholders named above |
| `QuadChart`, `JHU-Presentation`, `.potx` | mentions in plans and in the proposal builder only; the files are not in the tree |
| `l2_geometry.py` | mentions in plans, research notes, and the skip comment; the file is not in the tree |

## Deviations

- `gh auth status` labels the keyring login `jack25409440`. `gh auth token` against the API returns `XiaohuiChen-personal` (id 6566440). The repo is created with that token and then checked with `gh repo view`. If the owner were wrong, the private `course-project/` tree would not be removed.
- Last-three-byte node labels stayed in the Wi-Fi design. The room map and full MACs did not.
- The public maintainer email is the public GitHub profile email, which is a utexas.edu address. It was not replaced with the noreply form because a public email exists.
- `build_proposal.py` remains even though the template it reads does not.
- Gitignored local files in the private repo's `course-project/` (if any, such as a local `wifi_config.h`) are left on disk when that tree is replaced by a stub README. They are not committed.

## Second search

Run after this file existed, from the repo root, with the same patterns. Hits inside this file are the search record (the words `gmail.com`, `utexas.edu`, `cursor.com`, `ts.net`, `100.109`, `Vincent`, `V. Hu`, and the broadcast MAC appear here as documentation). They are not credentials.

Outside this file:

| Check | Result |
| --- | --- |
| `wifi_config.h` on disk | none |
| `l2_geometry.py`, `.pptx`, `.potx`, `.venv`, `report/sources/`, `assignment7/` or `assignment8/` directories | none |
| `gmail.com`, `cursor.com`, `ts.net`, `100.109`, other `100.x.x.x` | 0 |
| `Vincent`, `V. Hu`, word `Hu` | 0 |
| `utexas.edu` | 4, the public maintainer email only |
| colon MAC | 1, broadcast `ff:ff:ff:ff:ff:ff` in the Wi-Fi design |
| `wifi_config.h` as text | filename mentions in firmware comments, plans, and `.gitignore`; no credential file |

Geometry tests after the skip: `7 passed, 1 skipped`.

Second search: no unfixed leak. Push may proceed.
