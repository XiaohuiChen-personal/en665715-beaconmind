# OD7 — Isaac Sim version (approved)

Date of the evidence: 2026-10-07. Xiaohui approved this version on 2026-10-07, 00:51 CT.

## Approval

Date: 2026-10-07, 00:51 CT.

Xiaohui's words: "Yes, keep 5.1 for the simulator work."

Approved version: Isaac Sim **5.1.0-rc.19** (`5.1.0-rc.19+main.0.aa503a9b.local`), already installed. Isaac 6.0 stays unbuilt.

## Recommendation

Use Isaac Sim **5.1.0-rc.19** (`5.1.0-rc.19+main.0.aa503a9b.local`) for M2. Isaac 6.0 stays a later option: evaluated for availability only, and not built, because 5.1 meets the W1 render-and-decode requirement and both 900 s kit-lifetime runs reached `DONE`. Tag `v6.0.1` is on GitHub (`isaac6-tags.txt`). `/home` had 2.2T free when the tags were listed.

## What passed

Kept render `data/renders/spike-20261007-001302` (asset-server AprilTag MDL, UXGA 1600×1200, HFOV 60°).

- `detect-offline.csv`: id 3 in 4 of 4 images. Ranges 0.5020, 1.0032, 1.5129, 2.0340 m against 0.5, 1.0, 1.5, 2.0 m. Each is within 5 percent.
- `apriltag-ros-on-render.txt`: the 1.0 m frame, id 3, family `tag36h11`, hamming 0.
- `kit-lifetime.md`: the base kit and the ROS-bridge kit each stayed in the update loop for 900.0 s after `READY`, then printed `DONE` with exit 0. Launch-to-READY was 6.7 s and 7.1 s.

## Generative-AI disclosure

AI-assisted: Grok 4.7 via Cursor, 2026-10-06: recorded the Qwen3.8 pin, deferred Bonsai, and started M1.T5.
AI-assisted: Grok 4.7 via Cursor, 2026-10-07: added the kit-lifetime results to this proposal. The model did not record Xiaohui's approval.
AI-assisted: Grok 4.7 via Cursor, 2026-10-07: recorded the Isaac 5.1 approval.
