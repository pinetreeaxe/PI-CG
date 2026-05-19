"""
turntable_camera.py v7 — SceneCapture2D Dataset Capture (UE5.x)
----------------------------------------------------------------
Fixes:
- safer logging
- UE5 EditorActorSubsystem usage
- manual exposure on SceneCapture2D
- optional line-of-sight rejection
- retries when shot is blocked
----------------------------------------------------------------
Run this INSIDE Unreal Editor Python, not system Python.
"""

import unreal
import math
import os
import random

# ═══════════════════════════════════════════════════════════════
# CONFIGURAÇÃO
# ═══════════════════════════════════════════════════════════════

OBJECT_ACTOR_NAME = "Cube"

NUM_SHOTS = 100
MAX_ATTEMPTS_PER_SHOT = 30

IMG_WIDTH = 1920
IMG_HEIGHT = 1080
OUTPUT_DIR = r"C:\Renders\Dataset"

SPAWN_X_MIN = -700.0
SPAWN_X_MAX = 700.0
SPAWN_Y_MIN = -700.0
SPAWN_Y_MAX = 700.0
SPAWN_Z = 0.0

CAM_RADIUS_MIN = 350.0
CAM_RADIUS_MAX = 650.0
CAM_HEIGHT_MIN = 450.0
CAM_HEIGHT_MAX = 850.0
TARGET_Z_OFFSET = 80.0

ROTATE_OBJECT = True
REJECT_OCCLUDED_SHOTS = True

# Exposure
MANUAL_EXPOSURE_BIAS = 3.0

# UE5 render target asset path if you later want to persist one
RT_ASSET_PATH = "/Game/DatasetCapture/RT_Dataset"


# ═══════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════

def ulog(msg):
    if hasattr(unreal, "log"):
        unreal.log(str(msg))
    else:
        print(str(msg))

def uwarn(msg):
    if hasattr(unreal, "log_warning"):
        unreal.log_warning(str(msg))
    else:
        print("[WARNING]", str(msg))

def uerr(msg):
    if hasattr(unreal, "log_error"):
        unreal.log_error(str(msg))
    else:
        print("[ERROR]", str(msg))


# ═══════════════════════════════════════════════════════════════
# UTILITÁRIOS
# ═══════════════════════════════════════════════════════════════

def get_editor_world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()

def get_actor_subsystem():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

def find_actor(name):
    actor_subsystem = get_actor_subsystem()
    for actor in actor_subsystem.get_all_level_actors():
        if actor.get_actor_label() == name:
            return actor
    return None

def spawn_capture_actor(location, rotation):
    actor_subsystem = get_actor_subsystem()
    try:
        return actor_subsystem.spawn_actor_from_class(unreal.SceneCapture2D, location, rotation)
    except Exception:
        return unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.SceneCapture2D, location, rotation
        )

def is_view_occluded(world, start, end, ignored_actors=None):
    if ignored_actors is None:
        ignored_actors = []

    try:
        hit_result = unreal.SystemLibrary.line_trace_single(
            world,
            start,
            end,
            unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
            False,
            ignored_actors,
            unreal.DrawDebugTrace.NONE,
            True
        )
        return bool(hit_result[0])
    except Exception as e:
        uwarn(f"[AVISO] Falha no line trace, a ignorar oclusão: {e}")
        return False

def ensure_png_extension(output_dir, base_name):
    src = os.path.join(output_dir, base_name)
    dst_png = os.path.join(output_dir, base_name + ".png")
    dst_jpg = os.path.join(output_dir, base_name + ".jpg")

    if os.path.exists(src):
        if os.path.exists(dst_png):
            os.remove(dst_png)
        os.rename(src, dst_png)
        return dst_png

    if os.path.exists(dst_png):
        return dst_png

    if os.path.exists(dst_jpg):
        return dst_jpg

    return None


# ═══════════════════════════════════════════════════════════════
# INÍCIO
# ═══════════════════════════════════════════════════════════════

ulog("══════════════════════════════════════════════════════════")
ulog(" Dataset Capture v7 — SceneCapture2D (UE5.x)")
ulog(f" Shots : {NUM_SHOTS} | Output: {OUTPUT_DIR}")
ulog("══════════════════════════════════════════════════════════")

world = get_editor_world()
if world is None:
    uerr("[ERRO] Não foi possível obter o editor world.")
    raise SystemExit

obj = find_actor(OBJECT_ACTOR_NAME)
if obj is None:
    uerr(f"[ERRO] Actor '{OBJECT_ACTOR_NAME}' não encontrado!")
    raise SystemExit

original_loc = obj.get_actor_location()
original_rot = obj.get_actor_rotation()
ulog(f"[OK] Objecto encontrado em {original_loc}")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ═══════════════════════════════════════════════════════════════
# RENDER TARGET
# ═══════════════════════════════════════════════════════════════

rt = unreal.RenderingLibrary.create_render_target2d(
    world,
    IMG_WIDTH,
    IMG_HEIGHT,
    unreal.TextureRenderTargetFormat.RTF_RGBA8,
    unreal.LinearColor(0.0, 0.0, 0.0, 1.0),
    False,
)
ulog(f"[OK] Render Target criado ({IMG_WIDTH}x{IMG_HEIGHT})")

# ═══════════════════════════════════════════════════════════════
# SCENE CAPTURE
# ═══════════════════════════════════════════════════════════════

capture_actor = spawn_capture_actor(
    unreal.Vector(0.0, 0.0, 500.0),
    unreal.Rotator(-45.0, 0.0, 0.0),
)

if capture_actor is None:
    uerr("[ERRO] Não foi possível criar SceneCapture2D.")
    raise SystemExit

capture_actor.set_actor_label("DatasetCapture")

comp = capture_actor.capture_component2d
comp.texture_target = rt
comp.capture_source = unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
comp.capture_every_frame = False
comp.capture_on_movement = False
comp.post_process_blend_weight = 1.0

# Optional quality / consistency flags if available
for prop_name, value in [
    ("always_persist_rendering_state", True),
    ("use_ray_tracing_if_enabled", True),
]:
    try:
        comp.set_editor_property(prop_name, value)
    except Exception:
        pass

# Manual exposure setup
try:
    pps = comp.post_process_settings

    if hasattr(pps, "override_auto_exposure_method"):
        pps.override_auto_exposure_method = True
    if hasattr(unreal, "AutoExposureMethod") and hasattr(pps, "auto_exposure_method"):
        try:
            pps.auto_exposure_method = unreal.AutoExposureMethod.AEM_MANUAL
        except Exception:
            pass

    if hasattr(pps, "override_auto_exposure_bias"):
        pps.override_auto_exposure_bias = True
        pps.auto_exposure_bias = MANUAL_EXPOSURE_BIAS

    if hasattr(pps, "override_auto_exposure_apply_physical_camera_exposure"):
        pps.override_auto_exposure_apply_physical_camera_exposure = True
        pps.auto_exposure_apply_physical_camera_exposure = False

    if hasattr(pps, "override_motion_blur_amount"):
        pps.override_motion_blur_amount = True
        pps.motion_blur_amount = 0.0

    if hasattr(pps, "override_bloom_intensity"):
        pps.override_bloom_intensity = True
        pps.bloom_intensity = 0.0

    comp.post_process_settings = pps
    ulog(f"[OK] Exposição manual aplicada (bias={MANUAL_EXPOSURE_BIAS})")
except Exception as e:
    uwarn(f"[AVISO] Não foi possível configurar exposição manual: {e}")

ulog("[OK] SceneCaptureActor2D criado")

# ═══════════════════════════════════════════════════════════════
# LOOP DE CAPTURA
# ═══════════════════════════════════════════════════════════════

saved = 0
errors = 0

for i in range(NUM_SHOTS):
    shot_saved = False

    for attempt in range(MAX_ATTEMPTS_PER_SHOT):
        ox = random.uniform(SPAWN_X_MIN, SPAWN_X_MAX)
        oy = random.uniform(SPAWN_Y_MIN, SPAWN_Y_MAX)
        o_yaw = random.uniform(0.0, 360.0) if ROTATE_OBJECT else 0.0

        obj.set_actor_location_and_rotation(
            unreal.Vector(ox, oy, SPAWN_Z),
            unreal.Rotator(0.0, o_yaw, 0.0),
            False,
            True,
        )

        angle = random.uniform(0.0, 2.0 * math.pi)
        radius = random.uniform(CAM_RADIUS_MIN, CAM_RADIUS_MAX)
        height = random.uniform(CAM_HEIGHT_MIN, CAM_HEIGHT_MAX)

        cam_loc = unreal.Vector(
            ox + radius * math.cos(angle),
            oy + radius * math.sin(angle),
            SPAWN_Z + height,
        )
        aim = unreal.Vector(ox, oy, SPAWN_Z + TARGET_Z_OFFSET)
        cam_rot = unreal.MathLibrary.find_look_at_rotation(cam_loc, aim)

        capture_actor.set_actor_location_and_rotation(cam_loc, cam_rot, False, True)

        if REJECT_OCCLUDED_SHOTS:
            blocked = is_view_occluded(world, cam_loc, aim, ignored_actors=[capture_actor, obj])
            if blocked:
                continue

        try:
            comp.capture_scene()
        except Exception as e:
            uwarn(f"[AVISO] capture_scene falhou no shot {i+1}: {e}")
            continue

        fname = f"synthetic_{i:04d}"

        try:
            unreal.RenderingLibrary.export_render_target(world, rt, OUTPUT_DIR, fname)
            out_path = ensure_png_extension(OUTPUT_DIR, fname)

            if out_path is None:
                raise RuntimeError("Ficheiro exportado não encontrado após export_render_target().")

            saved += 1
            shot_saved = True
            ulog(f"[Dataset] Shot {i + 1}/{NUM_SHOTS} guardado → {out_path}")
            break

        except Exception as e:
            uwarn(f"[Dataset] Shot {i + 1} tentativa {attempt + 1} falhou: {e}")

    if not shot_saved:
        errors += 1
        uwarn(f"[Dataset] Shot {i + 1}/{NUM_SHOTS} falhou após {MAX_ATTEMPTS_PER_SHOT} tentativas")

# ═══════════════════════════════════════════════════════════════
# LIMPEZA
# ═══════════════════════════════════════════════════════════════

try:
    capture_actor.destroy_actor()
except Exception:
    pass

obj.set_actor_location_and_rotation(original_loc, original_rot, False, True)

ulog("══════════════════════════════════════════════════════════")
ulog(f" Concluído! {saved}/{NUM_SHOTS} shots guardados")
ulog(f" Falhas: {errors}")
ulog(f" Output: {OUTPUT_DIR}")
ulog("══════════════════════════════════════════════════════════")