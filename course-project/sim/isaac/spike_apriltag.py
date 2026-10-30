#!/usr/bin/env python3
"""Render one tag36h11 on a vertical quad with Isaac Sim's AprilTag MDL.

Run with Isaac's python.sh. Arguments are parsed before SimulationApp.

AI-assisted: Grok 4.7 via Cursor, 2026-10-06: recorded the Qwen3.8 pin, deferred Bonsai, and started M1.T5.
Derived from: discussions/module2/sim/render_carter.py (headless SimulationApp + Replicator pattern; reimplemented).
The AprilTag material call follows isaacsim.gui.menu create_menu.py:create_apriltag and
test_menu.py BindMaterial (reimplemented, not copied).
"""

import argparse
import json
import math
import sys
import time
from pathlib import Path

parser = argparse.ArgumentParser(description="Render an Isaac AprilTag quad at several distances.")
parser.add_argument("--out", required=True)
parser.add_argument("--tag-id", type=int, default=3)
parser.add_argument("--distances", type=float, nargs="+", default=[0.5, 1.0, 1.5, 2.0])
parser.add_argument("--width", type=int, default=1600)
parser.add_argument("--height", type=int, default=1200)
parser.add_argument("--hfov-deg", type=float, default=60.0)
parser.add_argument("--black-m", type=float, default=0.16)
parser.add_argument("--border-m", type=float, default=0.02)
parser.add_argument("--camera-json", default="")
parser.add_argument("--warmup", type=int, default=30)
parser.add_argument("--z-lens", type=float, default=0.12)
args, _unknown = parser.parse_known_args()
# Kit forwards leftover argv into the base app. Drop the script flags after parsing.
sys.argv = [sys.argv[0]]

T0 = time.time()


def mark(msg):
    print(msg, flush=True)


if args.camera_json:
    with open(args.camera_json, encoding="utf-8") as handle:
        camera_doc = json.load(handle)
    args.width = int(camera_doc["image_width"])
    args.height = int(camera_doc["image_height"])
    fx_json = float(camera_doc["camera_matrix"][0])
    # HFOV from fx: fx = width / (2 * tan(hfov/2))
    args.hfov_deg = math.degrees(2.0 * math.atan(args.width / (2.0 * fx_json)))

from isaacsim import SimulationApp

simulation_app = SimulationApp(
    {
        "headless": True,
        "hide_ui": True,
        "width": args.width,
        "height": args.height,
        "renderer": "RaytracedLighting",
        "anti_aliasing": 3,
        "active_gpu": 0,
        "physics_gpu": 0,
        "multi_gpu": False,
        "sync_loads": True,
        "disable_viewport_updates": False,
    }
)
mark("READY {0:.1f}".format(time.time() - T0))

import carb
import numpy as np
import omni.kit.commands
import omni.replicator.core as rep
import omni.usd
from isaacsim.core.api import World
from isaacsim.core.api.objects import GroundPlane
from isaacsim.sensors.camera import Camera
from isaacsim.storage.native import get_assets_root_path
from PIL import Image
from pxr import Gf, Sdf, UsdGeom, UsdLux, UsdShade

settings = carb.settings.get_settings()
for key, value in {
    "/omni/replicator/asyncRendering": False,
    "/app/asyncRendering": False,
    "/omni/replicator/captureOnPlay": False,
    "/app/renderer/waitIdle": True,
    "/app/hydraEngine/waitIdle": True,
    "/renderer/multiGpu/maxGpuCount": 1,
    "/rtx/post/dlss/execMode": 0,
    "/rtx/translucency/enabled": False,
    "/rtx/reflections/enabled": False,
    "/rtx/indirectDiffuse/enabled": False,
    "/rtx/ambientOcclusion/enabled": False,
}.items():
    settings.set(key, value)

# MDL defaults read from AprilTag.mdl (M1.T5 step 2). Not display names.
TAG_SIZE = 10
TAGS_PER_ROW = 24
SPACING = 1
# Camera -Z along world +X, camera +Y along world +Z. Checked offline.
LOOK_PLUS_X = np.array([0.5, 0.5, -0.5, -0.5])


def shader_input(prim, name, type_name, value):
    shader = UsdShade.Shader(prim)
    shader.CreateInput(name, type_name).Set(value)


def bind_apriltag(stage, tag_id):
    """Create the AprilTag MDL and point tag_mosaic at tag36h11. Asset server first."""
    assets = get_assets_root_path()
    local_root = Path.home() / "Projects/EN.665.715/course-project/data/renders/apriltag-assets"
    if assets:
        mdl_url = assets + "/Isaac/Materials/AprilTag/AprilTag.mdl"
        tex_url = assets + "/Isaac/Materials/AprilTag/Textures/tag36h11.png"
        source = "asset-server"
    else:
        mdl_url = str(local_root / "AprilTag.mdl")
        tex_url = str(local_root / "tag36h11.png")
        source = "local"
    mark("MATERIAL_SOURCE {0} mdl={1}".format(source, mdl_url))
    omni.kit.commands.execute(
        "CreateMdlMaterialPrim",
        mtl_url=mdl_url,
        mtl_name="AprilTag",
        mtl_path="/Looks/AprilTag",
        select_new_prim=False,
    )
    for _ in range(5):
        simulation_app.update()
    shader = stage.GetPrimAtPath("/Looks/AprilTag/Shader")
    if not shader.IsValid() and source == "asset-server":
        mark("MATERIAL_SOURCE local-fallback")
        omni.kit.commands.execute(
            "CreateMdlMaterialPrim",
            mtl_url=str(local_root / "AprilTag.mdl"),
            mtl_name="AprilTag",
            mtl_path="/Looks/AprilTag",
            select_new_prim=False,
        )
        tex_url = str(local_root / "tag36h11.png")
        source = "local-fallback"
        for _ in range(5):
            simulation_app.update()
        shader = stage.GetPrimAtPath("/Looks/AprilTag/Shader")
    if not shader.IsValid():
        raise RuntimeError("AprilTag shader prim was not created")
    shader_input(shader, "tag_mosaic", Sdf.ValueTypeNames.Asset, Sdf.AssetPath(tex_url))
    shader_input(shader, "tag_id", Sdf.ValueTypeNames.Int, int(tag_id))
    shader_input(shader, "tag_size", Sdf.ValueTypeNames.Int, TAG_SIZE)
    shader_input(shader, "tags_per_row", Sdf.ValueTypeNames.Int, TAGS_PER_ROW)
    shader_input(shader, "spacing", Sdf.ValueTypeNames.Int, SPACING)
    return source


def make_quad(stage, side_m):
    half = side_m / 2.0
    mesh = UsdGeom.Mesh.Define(stage, "/World/Tag")
    # Viewed from -X (the camera looks along +X): CCW is left-bottom, right-bottom, right-top, left-top.
    mesh.CreatePointsAttr(
        [
            Gf.Vec3f(0.0, half, -half),
            Gf.Vec3f(0.0, -half, -half),
            Gf.Vec3f(0.0, -half, half),
            Gf.Vec3f(0.0, half, half),
        ]
    )
    mesh.CreateFaceVertexCountsAttr([4])
    mesh.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
    mesh.CreateSubdivisionSchemeAttr("none")
    mesh.CreateDoubleSidedAttr(True)
    primvar = UsdGeom.PrimvarsAPI(mesh).CreatePrimvar(
        "st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.vertex
    )
    primvar.Set([Gf.Vec2f(0, 0), Gf.Vec2f(1, 0), Gf.Vec2f(1, 1), Gf.Vec2f(0, 1)])
    xform = UsdGeom.Xformable(mesh.GetPrim())
    translate = xform.AddTranslateOp()
    return translate


def grab(annotator):
    """Return an RGB uint8 image, or None when the annotator has not written a frame yet."""
    data = annotator.get_data()
    image = np.asarray(data)
    if image.ndim != 3 or image.shape[0] < 1 or image.shape[1] < 1 or image.shape[-1] < 3:
        return None
    rgb = np.ascontiguousarray(image[:, :, :3])
    if rgb.dtype != np.uint8:
        rgb = np.clip(rgb, 0, 255).astype(np.uint8)
    return rgb


context = omni.usd.get_context()
if context.get_stage() is None:
    context.new_stage()
stage = context.get_stage()
UsdGeom.SetStageMetersPerUnit(stage, 1.0)
UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
world = World(stage_units_in_meters=1.0, physics_dt=1.0 / 50.0, rendering_dt=1.0 / 50.0)

GroundPlane(prim_path="/World/GroundPlane", z_position=0.0, size=20.0)
dome = UsdLux.DomeLight.Define(stage, "/World/DomeLight")
dome.CreateIntensityAttr(1000.0)
distant = UsdLux.DistantLight.Define(stage, "/World/DistantLight")
distant.CreateIntensityAttr(3000.0)
distant.CreateAngleAttr(1.0)
UsdGeom.Xformable(distant.GetPrim()).AddOrientOp().Set(Gf.Quatf(0.5, Gf.Vec3f(0.5, -0.5, -0.5)))

side_m = args.black_m + 2.0 * args.border_m
translate = make_quad(stage, side_m)
material_source = bind_apriltag(stage, args.tag_id)
omni.kit.commands.execute(
    "BindMaterial",
    material_path="/Looks/AprilTag",
    prim_path=["/World/Tag"],
    strength=["weakerThanDescendants"],
)

aperture_m = 20.955 / 10.0
focal_m = aperture_m / (2.0 * math.tan(math.radians(args.hfov_deg) / 2.0))
camera = Camera(
    prim_path="/World/Camera",
    name="spike_camera",
    resolution=(args.width, args.height),
    position=np.array([0.0, 0.0, args.z_lens]),
    orientation=LOOK_PLUS_X,
)
camera.set_focal_length(focal_m)
camera.set_horizontal_aperture(aperture_m, maintain_square_pixels=True)
camera.set_clipping_range(near_distance=0.01, far_distance=100.0)
fx = args.width * camera.get_focal_length() / camera.get_horizontal_aperture()
fy = args.height * camera.get_focal_length() / camera.get_vertical_aperture()
intrinsics = {
    "fx": fx,
    "fy": fy,
    "cx": args.width / 2.0,
    "cy": args.height / 2.0,
    "width": args.width,
    "height": args.height,
    "hfov_deg": args.hfov_deg,
    "black_m": args.black_m,
    "border_m": args.border_m,
    "quad_side_m": side_m,
    "z_lens_m": args.z_lens,
    "tag_id": args.tag_id,
    "material_source": material_source,
    "tag_size": TAG_SIZE,
    "tags_per_row": TAGS_PER_ROW,
    "spacing": SPACING,
}

out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
with open(out / "intrinsics.json", "w", encoding="utf-8") as handle:
    json.dump(intrinsics, handle, indent=2)
    handle.write("\n")
mark("intrinsics fx={0:.3f} fy={1:.3f} cx={2:.1f} cy={3:.1f}".format(fx, fy, intrinsics["cx"], intrinsics["cy"]))

def aim_camera(prim, z_lens):
    """Place the USD camera at (0, 0, z) looking along +X with +Z up.

    Gf.Matrix4d.SetLookAt returns a world-to-camera view matrix. The camera
    prim stores the inverse. This replaces the quaternion from attempt 2,
    whose frames did not change with tag distance.
    """
    xform = UsdGeom.Xformable(prim)
    xform.ClearXformOpOrder()
    view = Gf.Matrix4d(1.0)
    view.SetLookAt(Gf.Vec3d(0.0, 0.0, z_lens), Gf.Vec3d(1.0, 0.0, z_lens), Gf.Vec3d(0.0, 0.0, 1.0))
    xform.AddTransformOp().Set(view.GetInverse())


world.reset()
aim_camera(camera.prim, args.z_lens)
render_product = rep.create.render_product("/World/Camera", (args.width, args.height))
annotator = rep.AnnotatorRegistry.get_annotator("rgb", device="cpu")
annotator.attach([render_product])
# multi_camera.py steps the replicator graph; world.step alone left this annotator empty.
rep.orchestrator.set_capture_on_play(False)
rep.orchestrator.preview()

for distance in args.distances:
    translate.Set(Gf.Vec3d(float(distance), 0.0, args.z_lens))
    image = None
    for step_index in range(args.warmup):
        rep.orchestrator.step(rt_subframes=1)
        image = grab(annotator)
        if (step_index + 1) % 10 == 0:
            mark("step d={0} n={1} frame={2}".format(distance, step_index + 1, image is not None))
        if image is not None and step_index + 1 >= args.warmup:
            break
    if image is None:
        mark("Error annotator empty after {0} rendered steps at d={1}".format(args.warmup, distance))
        simulation_app.close()
        raise SystemExit(1)
    path = out / "tag{0}_d{1:.1f}.png".format(args.tag_id, distance)
    Image.fromarray(image).save(path)
    mark(
        "png {0} mean={1:.1f} std={2:.1f}".format(
            path, float(image.mean()), float(image.std())
        )
    )

mark("DONE")
simulation_app.close()
