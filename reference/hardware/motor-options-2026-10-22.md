> Public copy for BeaconMind, 2026-10-29; the private course repo holds the unredacted original.

# Replacement gear motors for the car

**Bottom line.** Buy three NULLLAB 1:90 TT encoder motors in the black **"Pro Strength & Metal Gear"** (all-metal gearbox) variant on Amazon. Get the 2-pack, ASIN B0GHYFZ2SQ ($24.99) [1], and one single, ASIN B0G4ZK2BSZ ($13.99) [2]. Both are variations on the same listing, and the three cost about $39 before tax. On 2026-10-22 both were in stock and shipped by Amazon, with delivery quoted for Oct 24-27. Those dates were for Amazon's default ZIP code, so yours may differ. This is the only option that bolts on, plugs in and runs your current firmware unchanged: same TT body, plug, pinout and 4,320 counts per wheel turn. Its metal gears target the jam you just had. Nobody sells speed-matched pairs, so run all three in, keep the closest two and hold the third as a spare. This is not a proven quality upgrade. It is the same brand and the same encoder board as your failed motors, which match the blue half-metal "Low Noise & Hybrid Gear" variant on that listing (don't order that one). It also has only 4 ratings. It is a fast, cheap fix, and none of the TT-format encoder motors found in this research is a proven quality upgrade either. The runner-up has the best documented quality, if you are willing to drill four small holes: the Pololu #5140 150:1 micro metal gearmotor with encoder, about $117 for three with brackets, wheels and cables [3].

## Shortlist

Two terms used below:
- **x4 decoding** counts every rising and falling edge of both encoder channels, so each pulse gives 4 counts. All counts below are x4 counts per wheel turn.
- **Stall current** is what a motor draws when it is powered but cannot turn. The TB6612FNG allows 1.2 A continuous (1.0 A in Toshiba's operating table) and 3.2 A for a single 10 ms pulse [4].

| Product | Drop-in? | Ratio | Counts per wheel turn | Encoder supply | Stall current vs TB6612 | Price (2026-10-22) | Verdict |
|---|---|---|---|---|---|---|---|
| NULLLAB TT encoder motor, all-metal, B0GHYFZ2SQ / B0G4ZK2BSZ [1][2] | Yes: same body, plug, pinout and firmware. Fit judged from photos only; no drawing is published | 1:90 | 4,320 (vendor formula [5]) | 3.3-5 V (HX3144 chips, 3.0 V minimum) | 0.82 A at an unstated voltage, copied from the half-metal listing (unverified for metal): under | $24.99 for 2; $13.99 each | **Top pick**: zero rework; does not fix the encoder design |
| SparkFun Hobby Motor with Encoder, Metal Gear (DG01D-E), ROB-16413 [6][7] | Mechanically yes, per the drawing; needs re-wiring and firmware changes | 1:48 (label) | Not published; 540-1,150 estimated (unverified) | "Generally 3.3V or 5V" [7]; SparkFun's Auto pHAT feeds it 3.3 V [8] | Not published for metal; the plastic sibling is 0.75 A at 6 V [9]: likely under | $12.50 each, sold singly | Acceptable: different maker, far fewer counts, mixed quality reports |
| Pololu #5140 Micro Metal Gearmotor MP 6V 150:1, 12 CPR encoder [3][10] | No: drill the plate, new brackets, 70 mm wheels, new cable | 150.58:1 | 1,807 | 2.7-18 V | 0.67 A at 6 V (Pololu's extrapolation); about 0.8 A at 7.2 V (estimate): under | $29.95 each (32 in stock); about $117 kit | **Runner-up**: best documented quality |
| Pololu #5194 Micro Metal Gearmotor HPCB 6V 210:1, 12 CPR encoder [11] | No (same work as #5140) | 210.59:1 | 2,527 | 2.7-18 V | 1.5 A at 6 V: over the continuous rating, under the peak | $32.45 each (70 in stock); about $124 kit | Acceptable: longer-life carbon brushes, but a jam can exceed the gearbox limit, so it needs a stall cut-off |

**If you pick the DG01D-E anyway:** your old NULLLAB cable may fit its socket, but the pin order is different (Motor1, Motor2, Enc+, A, B, Enc−). If you wire it by the old colours, battery voltage goes onto the encoder. Check every wire with the multimeter first. Buyers have received cables with the colours reversed [12], and SparkFun gives only a 30-day warranty and sells no spare cables [13].

## Why the current motors failed, and what to look for

- **Buzzing but not turning:** current is flowing but the rotor is locked. The buzz is the firmware's 1.2 kHz PWM.
  - Likely causes: a jammed gearbox (a gear off its pin, a chipped tooth, debris, or the housing pinched by over-tightened M3 bolts, which pass right through it [14]) or a seized motor. Pololu staff give the same diagnosis for their own motors [15].
  - Ten-minute test on the dead one: unplug it, loosen the bolts and try again. Then slide the motor out of its plastic strap and run it on its own from two AA cells for 1-2 s.
  - If the bare motor spins, the gearbox failed, and metal gears help. If it doesn't, the motor itself died. That argues for the Pololu runner-up over the same brand.
- **Weak and sticky:** this fits a dead winding or worn brushes (the contacts that feed current to the spinning part). Pololu warns that a stall can damage both "on the order of seconds" [16]. Your firmware keeps a stalled wheel at its commanded duty after the last start-assist try.
- **Lost encoder counts:**
  - The board uses two HX3144 *unipolar* Hall switches [5]. Their duty cycle (the share of time the output is high) depends on magnet strength, the air gap and each chip's threshold. A *latch*-type sensor gives about 50 % regardless [17]. So the problem is the board design, not one bad unit.
  - When one channel's high pulse is shorter than the gap between A and B, plain x4 decoding counts +1 and then −1, and the two cancel. Your edge-count mode avoids this.
- **The HX3144 at 3.3 V:** the datasheet says "Operation down to 3.0V", but every figure in it is measured at 12 V [18]. The board's 50 Ω supply resistor leaves the chip about 3.05-3.18 V. That is within spec by only 0.05-0.2 V, at a voltage nobody has characterized. A genuine Allegro A3144 needs 4.5 V and is discontinued [19], so a "3144" marking alone proves nothing. The supply is marginal, but it does not explain the duty-cycle fault on its own.
- **The 7-18 % speed mismatch is normal.** Adafruit specifies ±10 % for TT motors [20] and Pololu ±20 % [10]. The speed PID is what fixes it.
- **What to look for:** metal gears; an encoder rated for 3.3 V, ideally a latch type; a datasheet that gives stall current and speed at a stated voltage; a stall current under about 1 A. Buy three so you can screen them.

## What changes on the car and in the firmware

### Top pick: NULLLAB all-metal

- **Wiring:** none. Same PH2.0 6-pin plug and pinout (vendor schematic: 1 Motor+, 2 GND, 3 A, 4 B, 5 VCC, 6 Motor− [5]). Before you power anything, run the §5 meter checks in `reference/hardware/motor-encoder-cable-map.md` on each new cable.
- **Encoder supply:** Pico 3V3, as now.
- **Counts per turn:** keep `ENCODER_COUNTS_PER_REV` at 4320, but confirm each motor with 10 hand turns. One earlier unit gave 4,369.
- **Screening:**
  - Run each motor unloaded for a few minutes in each direction, and log counts/s both ways at one duty.
  - Check each channel's duty with the multimeter (DC average ÷ VCC). Aim for 45-55 %.
  - Keep the closest two. On any wheel with a bad channel, set `ENCODER_*_EDGE_MODE` to 1.
  - Return any bad unit within Amazon's 30 days.
- **Speed map:** re-measure `MIN_DUTY` and `MAX_WHEEL_SPEED_MPS` for each wheel.
  - On this battery pack, healthy 1:90 units peaked near 6,000 counts/s with the wheels lifted. That is about 83 rpm, not the listed 113. On the floor they reached 0.18-0.21 m/s, so plan on 0.05-0.20 m/s.
  - The battery tray loses about 0.87 V in its contacts. Fixing it gains more speed than any motor would.
- **PID:** the plant is the same kind, so re-measure each wheel's step response and adjust the gains.
- **Stall cut-off (add this whatever motor you buy):** if duty is above about 0.5 and a wheel shows no encoder edges for about 0.5 s, set that wheel to 0 and flag it. Keep the start-assist kick short.
- **Mounting:** tighten the M3 bolts snugly but don't crank them, and leave a small gap at the wheel hub. The listing's one written review says the gears "may bind" under force on the shaft [1].

### Runner-up: Pololu #5140 (not a drop-in)

- **Chassis:**
  - Replace the TT brackets with Pololu #989 brackets ($2.95 a pair, #2-56 screws included [21]).
  - Drill two 2.3-2.5 mm holes per motor, 18 mm apart, one on each side of the axle line. Use a sharp bit, go slowly and put a backing board underneath, because acrylic cracks.
  - Fit 70 × 8 mm wheels #1425 ($7.45 a pair) [22]. The TT wheels won't fit.
- **Wiring:**
  - The motor has a 1.0 mm JST SH socket and comes with no cable. The easiest route is a #4767 female-female cable [23] into a #4772 breakout [24] with a 6-pin header soldered on, plugged into the breadboard.
  - Pins: 1 GND (green), 2 B (white), 3 A (yellow), 4 Vcc (blue), 5 M2 (black), 6 M1 (red) [3]. Wire by function, not by colour.
- **Encoder supply:** Pico 3V3. The encoder is rated 2.7-18 V, and its 10 kΩ pull-ups go to Vcc, so the outputs stay at 3.3 V [10].
- **Counts per turn:** 1,807 (12 × 150.58).
  - Change `ENCODER_COUNTS_PER_REV`. Scale `STALL_COUNTS` and `RESET_COUNTS` (now 4320/20; becomes about 90).
  - Update `counts_per_rev` in the odometry node and in the host tools that hard-code 4320. Re-check the direction signs.
  - At 0.05 m/s this gives about 8 counts per 20 ms, so measure speed from the time between edges or average over 50-100 ms.
- **Geometry:** re-measure the wheel diameter (about 0.070 m) and the track width (it will no longer be 0.134 m). The plate sits about 3 mm lower. Update the odometry, `car.json` and the shared URDF.
- **Speed map:** 0.25 m/s needs about 45 % of the 150 rpm no-load speed, which leaves headroom. It is a 6 V motor, so cap PWM near 0.85 on fresh cells. Re-measure `MIN_DUTY` and top speed.
- **PID:** retune. The gains scale roughly with 1 / (m/s per unit duty), so re-measure each wheel's response first.
- **Cost and time:**
  - About $117 for 3 motors, 1 bracket pair, 1 wheel pair, 3 cables and 3 breakouts.
  - Pololu ships the same day from Las Vegas; ground delivery takes 1-5 business days, free on orders over $100 of Pololu products [25].
  - Allow an evening to a weekend, plus recalibration.

## Options considered and rejected

- NULLLAB "Low Noise & Hybrid Gear" 1:90 (blue; B0FSZWPNK1, B0GS97898M): the half-metal variant your failed motors match.
- SparkFun DG01D-E plastic pair, ROB-24053 [26]: plastic gears and about 240 rpm at 6 V, too fast for good low-speed control.
- DFRobot FIT0450/FIT0458 1:120 TT [27]: the encoder needs 4.5-7.5 V, 2.8 A stall, plastic gearbox, pinout errors in its docs. Not verified.
- Hiwonder TT 1:42 Hall, 21100132 [28]: probably the same factory motor as the DG01D-E. Its only review (2 stars) measured fewer counts than the spec. Ships from Shenzhen with import duties. Not verified.
- SazkJere TT 1:48, B0GYDM1RKC [29]: probably the same factory motor; half-metal gears, no datasheet, 0-1 reviews. Not verified.
- Yahboom encoder TT [30]: about 355 rpm, far too fast; specs only from a reseller.
- Adafruit 3802 all-metal TT [31]: no encoder. Adafruit 3782 [32] is a single-channel slotted disc that cannot tell direction.
- Pololu Romi 120:1 with encoder kit [33]: plastic gears, rework anyway, lowest resolution here.
- DFRobot FIT0483 N20 [34] and Waveshare N20 12 V [35]: generic motors with no stall or duty-cycle spec. The Waveshare runs at half speed on 6 V.
- DFRobot FIT0522 [36], Pololu 25D #4825 [37], generic JGA25-370: oversized, with stall currents of 2-3 A that exceed the TB6612's continuous rating. The Pololu 25D encoder needs at least 3.5 V.
- SparkFun N20 pair ROB-28633 [38] and Yahboom 310 [39]: 450-500 rpm, far too fast.
- Adafruit N20 encoder motors [40]: out of stock, and only about 200 mA stall (low torque).
- Marketplace TT encoder listings with Nov 5-19 delivery: too slow; not researched.

## Sources

1. https://www.amazon.com/dp/B0GHYFZ2SQ
2. https://www.amazon.com/dp/B0G4ZK2BSZ
3. https://www.pololu.com/product/5140
4. https://toshiba.semicon-storage.com/info/TB6612FNG_datasheet_en_20141001.pdf?did=10660&prodName=TB6612FNG
5. https://github.com/nulllaborg/tt-encoder-motor
6. https://www.sparkfun.com/hobby-motor-with-encoder-metal-gear-dg01d-e.html
7. https://cdn.sparkfun.com/assets/8/3/b/e/4/DS-16413-DG01D-E_Motor_with_Encoder.pdf
8. https://cdn.sparkfun.com/assets/b/c/0/1/4/SparkFun_Auto_pHAT.pdf
9. https://cdn.sparkfun.com/assets/4/b/4/5/4/DG01D-E-sparkfun_Datasheet.pdf
10. https://www.pololu.com/file/0J1487/pololu-micro-metal-gearmotors-rev-6-2.pdf
11. https://www.pololu.com/product/5194
12. https://forum.core-electronics.com.au/t/hobby-motor-with-encoder-metal-gear-dg01d-e-rob-16413/9154
13. https://community.sparkfun.com/t/defective-can-cables-for-the-hobby-motor-with-encoder-metal-gear-dg01d-e-be-ordered-seperately/68325
14. https://newscrewdriver.com/2021/01/24/tt-gear-motor-teardown/
15. https://forum.pololu.com/t/gearmotor-problem/10421
16. https://www.pololu.com/category/60/micro-metal-gearmotors
17. https://www.ti.com/lit/SBOA543
18. https://atta.szlcsc.com/upload/public/pdf/source/20200522/C558879_E12AF4322976E0148F23285B4470E786.pdf
19. https://www.allegromicro.com/-/media/files/datasheets/a3141-2-3-4-datasheet.ashx
20. https://www.adafruit.com/product/3777
21. https://www.pololu.com/product/989
22. https://www.pololu.com/product/1425
23. https://www.pololu.com/product/4767
24. https://www.pololu.com/product/4772
25. https://www.pololu.com/ordering
26. https://www.sparkfun.com/products/24053
27. https://wiki.dfrobot.com/fit0450/
28. https://www.hiwonder.com/products/tt-motor-plastic
29. https://www.amazon.com/dp/B0GYDM1RKC
30. https://www.yahboom.store/products/encoder-tt-motor
31. https://www.adafruit.com/product/3802
32. https://www.adafruit.com/product/3782
33. https://www.pololu.com/product/1520
34. https://www.digikey.com/en/products/detail/dfrobot/FIT0483/7087160
35. https://www.waveshare.com/dcgm-n20-12v-en-200rpm.htm
36. https://wiki.dfrobot.com/fit0522/
37. https://www.pololu.com/product/4825
38. https://www.sparkfun.com/n20-motor-with-encoder-and-cable-pair.html
39. https://www.yahboom.store/products/310motor
40. https://www.adafruit.com/product/4640

AI-assisted: written by Claude Opus 5.5 via Claude Code from a web-research workflow (2026-10-22); prices and stock as seen that day.