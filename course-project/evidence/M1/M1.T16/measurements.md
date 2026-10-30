# M1.T16 — current-car measurements (power bank, mass, ride height)

Readings are Xiaohui Chen's, sent in chat on 2026-10-29 (22:06, 22:21 and 23:45 CDT) and copied here as
given. No reading in this file is estimated by the agent. Derived values and checks are computed
from his readings and labelled as such.

Frame (as `configs/car.json`): x from the drive-wheel axle line, + toward the camera (the front,
caster end); the breadboard end is the back. y + to the robot's left when looking toward the camera.
Heights from the floor.

## Readings

| Quantity | Value | Instrument | Note |
| --- | --- | --- | --- |
| Whole-car mass, staying configuration | **660 g** | Pitney Bowes postal scale, 5 kg × 1 g | `photos/scale-whole-car.jpg`, `photos/scale-whole-car-display.jpg` |
| Two-scale split: front (caster) scale | **58 g** | two Pitney Bowes scales of that model, side by side | `photos/scale-two-scale-split.jpg`. The caster was **not** turned sideways (Xiaohui, 22:28 CDT), unlike the 2026-10-10 method; which way it trailed is unknown |
| Two-scale split: drive-wheel scale | **602 g** | same | same photo |
| Bank alone | **not measured** | | Xiaohui does not want to detach the bank (2026-10-29) |
| Bank vertical dimension | **25 mm** (the bank lies flat; footprint 70 × 70 mm) | | |
| Bank fixing | 3M double-sided tape to the underside of the plate | | |
| Bank bottom above the floor | **17 mm** | not stated | |
| Bank front face | **15 mm behind the axle line** (x = −0.015 m) | not stated | Behind the axle, at the breadboard end |
| Bank rear face | **85 mm behind the axle line** (x = −0.085 m) | not stated | |
| Bank sideways position | centred; **18 mm** from the bank to each tyre | not stated | |
| Rear-most point: the Pico's USB cable | **148 mm behind the axle line** | not stated | y of that point not given |
| Lowest point of any cable | **7 mm** above the floor | not stated | Xiaohui: acceptable, runs are on flat ground |
| Ride height | **unchanged** (Xiaohui) | | URDF heights 30 / 46 / 43 mm stay |
| Front-most point of the camera's USB cable | **40 mm past the 2026-10-10 front-most point** (138 mm, the ESP32-CAM's USB-C side with no cable), so **178 mm ahead of the axle line** | not stated | Xiaohui, 2026-10-29 23:45 CDT: "The cable at the front sticks out 4cm than the original". Asked which "original" he meant, he chose the option "Yes: 40 mm past the original 138 mm front-most point, so 178 mm from the axle". "4cm" is read by the agent as a reading to the nearest centimetre (±5 mm); he did not say how it was measured. y and height of that point not given. New since 2026-10-10: the camera is now powered from the bank |

## Checks on the readings (agent, from the readings above)

- **Weights agree.** 58 + 602 = 660 g, the single-scale reading. All three displays in the photos show
  the stated digits.
- **Bank length.** 85 − 15 = 70 mm, the bank's footprint side.
- **Bank width.** The 2026-10-10 inner gap between the tyres is 107 mm; (107 − 70) / 2 = 18.5 mm, against
  the 18 mm read.
- **Bank height.** 17 + 25 = 42 mm, against the 43 mm plate underside at the breadboard end (2026-10-10,
  ±2 mm): the tape layer sits in that gap.
- **The bank sticks out past the plate.** Its rear face (85 mm) is 8.5 mm behind the plate's rear edge
  (`rear_overhang_m` 0.07649 in `car.json`). Its rear corners are √(85² + 35²) = 91.9 mm from the axle
  midpoint, inside the 0.140 m sweep radius of the time.
- **The rear cable is outside the sweep radius (as it was then).** 148 mm > 140 mm (`sweep_radius_m` in
  `car.json` before the footprint decision below), even on the centre line. This is the M1.T16 stop-and-ask: Xiaohui decides whether the sweep radius changes or
  the cable is rerouted (AGENT-DESIGN §W asks for right-angle USB plugs routed back along the chassis).
- **The bank is the lowest body point.** 17 mm, against 30 mm for the gearbox bottoms (2026-10-10).
- **The front cable is the farthest point of the car (added 23:45 CDT).** 138 + 40 = 178 mm, more than the
  0.140 m sweep radius and more than the rear cable's 148 mm. Taken as wide as the 20 mm ESP32-CAM board
  (its y was not given), the front-most corners are √(178² + 10²) = 178.3 mm from the axle midpoint.

## Derived values (agent; for M2.T4, not written into `car.json` or the xacro by this task)

- Total mass 0.660 kg (was 0.506 kg).
- Centre of mass x = caster contact x × front load / total. The caster was not turned sideways, so its
  contact was not under the swivel (x 0.120 m). The 2026-10-10 notes give the contact at about 0.100 m
  when trailing toward the axle, a trail of about 20 mm. So:
  - trailing toward the axle: 0.100 × 58 / 660 = **0.0088 m**;
  - trailing forward (same 20 mm trail assumed): 0.140 × 58 / 660 = 0.0123 m;
  - turned sideways (the 2026-10-10 method, for comparison): 0.120 × 58 / 660 = 0.0105 m.

  The centre of mass is 9–12 mm ahead of the axle (2026-10-10: 0.0337 m). Re-weighing the split with
  the caster turned sideways removes this spread.
- Load on the caster: 58 / 660 = 8.8 % (was 28 %).
- Chassis leftover with the URDF's unchanged stand-in part masses (2 × 0.030 + 0.010 + 0.010 + 0.005 =
  0.085 kg): 0.660 − 0.085 = 0.575 kg.
- The 154 g increase cannot be given to the bank alone: since 2026-10-10 both motors, the camera's
  power cable and the Pico's cable also changed.

## Decisions for M2.T4 (the URDF update)

- **Centre of mass: use the middle value, x = 0.0105 m ahead of the axle**, with ±0.0018 m as its
  uncertainty from the unknown caster orientation (Xiaohui, 2026-10-29 22:31 CDT).
- **Total mass 0.660 kg.** Chassis leftover 0.575 kg if the stand-in part masses stay as they are.
- **The bank is modelled as geometry only** (a 70 × 70 × 25 mm box on the chassis link, x −0.085 to
  −0.015 m, y ±0.035 m, z 0.017 to 0.042 m above the floor), with no separate mass. Its mass stays inside
  the measured total, because the bank alone was not weighed. Only the inertia spread is affected,
  and the chassis inertia is already a uniform-box approximation (agent decision under Xiaohui's
  delegation, 2026-10-29).
- **Ride height unchanged**: keep 30 / 46 / 43 mm.
- ~~**Still open, not for the URDF yet:** the front camera cable's front-most point (unmeasured) and the
  sweep-radius decision (the rear Pico cable reaches 148 mm > 140 mm). Do not change `sweep_radius_m`
  or the front overhang until these are settled.~~ Settled the same evening, below.
- **Cables: keep them, enlarge the footprint (Xiaohui, 2026-10-29, chat right after 23:45 CDT).** Offered
  three choices (reroute both cables with right-angle plugs and re-measure; keep the cables and update the
  footprint now; undecided), he chose: "Keep the cables as they are: update the footprint now (front overhang
  ~0.178 m, rear ~0.148 m, sweep radius ~0.178 m) in car.json, and add the cables to the URDF in this PR."
  So `front_overhang_m` becomes the camera cable's tip (178 mm), `rear_overhang_m` the Pico cable (148 mm),
  and `corners`, `chassis_length_m` and `sweep_radius_m` follow from them. M2.T4 applied this (PR #1,
  `evidence/M2/M2.T4/2026-10-29-m1t16/`).

## Photos

`photos/` holds the six photos sent in chat (no EXIF or location data in the copies):
`bank-side.jpg`, `bank-rear-low.jpg`, `car-from-rear.jpg` (bank under the plate at the breadboard end,
cables behind it), and the three weighing photos named above.

AI-assisted: Claude Opus 5.5 via Cursor, 2026-10-29: wrote this checklist, the checks, the derived
values and the photo notes. Xiaohui Chen took the readings and the photos.

AI-assisted: Claude Opus 5.5 via Cursor, 2026-10-29 (after 23:45 CDT): added the front-cable reading, its check and
Xiaohui's footprint decision as he gave them in chat.
