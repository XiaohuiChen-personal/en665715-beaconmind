# AprilTag render attempts (not a pass yet)

## Attempt 1 — `data/renders/spike-20261007-000650`

`simulation_app.update()` for the warm-up. `READY 11.3`. Material source `asset-server`. Intrinsics fx=fy=1385.641, cx=800, cy=600. First `grab` raised `RuntimeError: annotator shape (0,)`. The process then segfaulted in `libomni.syntheticdata.plugin.so` while shutting down. `exit=1`.

## Attempt 2 — `data/renders/spike-20261007-000901`

`world.step(render=True)` for 30 steps, the `render_carter.py` step. `READY 6.7`. Same material source and intrinsics. Log lines:

```
step d=0.5 n=10 frame=False
step d=0.5 n=20 frame=False
step d=0.5 n=30 frame=False
Error annotator empty after 30 rendered steps at d=0.5
```

`simulation_app.close()` ended the process before the `SystemExit`, so the wrapper recorded `exit=0`. No PNG was written.

Attempt 3 uses `rep.orchestrator.step`, which is what `standalone_examples/api/isaacsim.replicator.examples/multi_camera.py` uses to fill an RGB annotator. That run is `data/renders/spike-20261007-001032`. It wrote four PNGs and printed `DONE`, but every frame was the same grey vertical split (mean about 209, std about 21 at every distance). `detect_tags_offline.py` printed an empty id on all four. The camera quaternion was not aimed at the quad.

## Attempt 4 — `data/renders/spike-20261007-001302` (the kept render)

The camera xform was replaced with the inverse of `Gf.Matrix4d.SetLookAt` (eye `(0, 0, 0.12)`, target `(1, 0, 0.12)`, up `(0, 0, 1)`). `READY 6.8`. `MATERIAL_SOURCE asset-server`. `DONE`. `exit=0`. Four PNGs. Offline decode and `apriltag_ros` both returned id 3. See `detect-offline.csv` and `apriltag-ros-on-render.txt`.

AI-assisted: Grok 4.7 via Cursor, 2026-10-06: recorded the Qwen3.8 pin, deferred Bonsai, and started M1.T5.
