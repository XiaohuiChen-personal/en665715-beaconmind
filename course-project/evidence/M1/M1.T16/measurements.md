# M1.T16 — current-car measurements (power bank, mass, ride height)

Readings are Xiaohui Chen's, sent in chat on 2026-10-29 (22:06 and 22:21 CDT) and copied here as
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
| Front-most point of the camera's USB cable | **pending** | | New since 2026-10-10: the camera is now powered from the bank, and its cable sticks out at the front |

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
  midpoint, inside the 0.140 m sweep radius.
- **The rear cable is outside the sweep radius.** 148 mm > 140 mm (`sweep_radius_m` in `car.json`), even on
  the centre line. This is the M1.T16 stop-and-ask: Xiaohui decides whether the sweep radius changes or
  the cable is rerouted (AGENT-DESIGN §W asks for right-angle USB plugs routed back along the chassis).
- **The bank is the lowest body point.** 17 mm, against 30 mm for the gearbox bottoms (2026-10-10).

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
- **Still open, not for the URDF yet:** the front camera cable's front-most point (unmeasured) and the
  sweep-radius decision (the rear Pico cable reaches 148 mm > 140 mm). Do not change `sweep_radius_m`
  or the front overhang until these are settled.

## Photos

`photos/` holds the six photos sent in chat (no EXIF or location data in the copies):
`bank-side.jpg`, `bank-rear-low.jpg`, `car-from-rear.jpg` (bank under the plate at the breadboard end,
cables behind it), and the three weighing photos named above.

AI-assisted: Claude Opus 5.5 via Cursor, 2026-10-29: wrote this checklist, the checks, the derived
values and the photo notes. Xiaohui Chen took the readings and the photos.
