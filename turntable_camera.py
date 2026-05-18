"""
turntable_camera.py  v6  —  SceneCapture2D  (UE5.7)
────────────────────────────────────────────────────────────────
UE5.7 renomeou KismetRenderingLibrary → RenderingLibrary.
Usa SceneCaptureActor2D + RenderTarget síncrono.
────────────────────────────────────────────────────────────────
"""

import unreal
import math
import os
import random

# ═══════════════════════════════════════════════════════════════
#  CONFIGURAÇÃO
# ═══════════════════════════════════════════════════════════════

OBJECT_ACTOR_NAME = "Cube"

NUM_SHOTS  = 100
IMG_WIDTH  = 1920
IMG_HEIGHT = 1080
OUTPUT_DIR = r"C:\Renders\Dataset"

SPAWN_X_MIN = -700.0
SPAWN_X_MAX =  700.0
SPAWN_Y_MIN = -700.0
SPAWN_Y_MAX =  700.0
SPAWN_Z     =    0.0

CAM_RADIUS_MIN =  250.0
CAM_RADIUS_MAX =  500.0
CAM_HEIGHT_MIN =  350.0
CAM_HEIGHT_MAX =  650.0
TARGET_Z_OFFSET =  80.0

ROTATE_OBJECT = True

# Caminho do RenderTarget dentro do projeto UE5
RT_ASSET_PATH = '/Game/DatasetCapture/RT_Dataset'

# ═══════════════════════════════════════════════════════════════
#  UTILITÁRIOS
# ═══════════════════════════════════════════════════════════════

def find_actor(name):
    for actor in unreal.EditorLevelLibrary.get_all_level_actors():
        if actor.get_actor_label() == name:
            return actor
    return None


def get_editor_world():
    """Tenta o subsystem novo; cai no deprecated se necessário."""
    try:
        sub = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        return sub.get_editor_world()
    except Exception:
        return unreal.EditorLevelLibrary.get_editor_world()


def create_or_load_rt(width, height):
    """Cria ou reutiliza o RenderTarget2D como asset do projeto."""
    if unreal.EditorAssetLibrary.does_asset_exist(RT_ASSET_PATH):
        rt = unreal.load_asset(RT_ASSET_PATH)
        unreal.log(f"[OK] RT carregado: {RT_ASSET_PATH}")
        return rt

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    factory = unreal.TextureRenderTarget2DFactoryNew()
    rt = asset_tools.create_asset(
        'RT_Dataset', '/Game/DatasetCapture/',
        unreal.TextureRenderTarget2D, factory
    )
    rt.set_editor_property('size_x', width)
    rt.set_editor_property('size_y', height)
    rt.render_target_format = unreal.TextureRenderTargetFormat.RTF_RGBA8
    unreal.EditorAssetLibrary.save_asset(RT_ASSET_PATH)
    unreal.log(f"[OK] RT criado: {RT_ASSET_PATH}")
    return rt


def export_rt(rt, filepath):
    """Exporta o RenderTarget para PNG via AssetExportTask."""
    task = unreal.AssetExportTask()
    task.object            = rt
    task.filename          = filepath
    task.selected          = False
    task.replace_identical = True
    task.prompt            = False
    task.automated         = True
    return unreal.Exporter.run_asset_export_task(task)


# ═══════════════════════════════════════════════════════════════
#  LÓGICA PRINCIPAL
# ═══════════════════════════════════════════════════════════════

unreal.log("══════════════════════════════════════════")
unreal.log(" Dataset Capture v6 — SceneCapture2D (UE5.7)")
unreal.log(f" Shots : {NUM_SHOTS}  |  Output: {OUTPUT_DIR}")
unreal.log("══════════════════════════════════════════")

# 1. Encontrar o objecto
obj = find_actor(OBJECT_ACTOR_NAME)
if obj is None:
    unreal.log_error(f"[ERRO] Actor '{OBJECT_ACTOR_NAME}' não encontrado!")
    raise SystemExit

original_loc = obj.get_actor_location()
original_rot = obj.get_actor_rotation()
unreal.log(f"[OK] Objecto encontrado em {original_loc}")

# 2. Criar pasta de output
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 3. Obter world
world = get_editor_world()

# 4. Criar Render Target  (RenderingLibrary = novo nome de KismetRenderingLibrary)
rt = unreal.RenderingLibrary.create_render_target2d(
    world,
    IMG_WIDTH,
    IMG_HEIGHT,
    unreal.TextureRenderTargetFormat.RTF_RGBA8,
    unreal.LinearColor(0.0, 0.0, 0.0, 1.0),
    False,
)
unreal.log(f"[OK] Render Target criado ({IMG_WIDTH}x{IMG_HEIGHT})")

# 5. Criar SceneCapture2D
capture_actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
    unreal.SceneCapture2D,
    unreal.Vector(0.0, 0.0, 500.0),
    unreal.Rotator(-90.0, 0.0, 0.0),
)
capture_actor.set_actor_label("DatasetCapture")

comp = capture_actor.capture_component2d
comp.texture_target      = rt
comp.capture_source      = unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
comp.capture_every_frame = False

# Forçar exposição fixa para evitar imagens escuras
try:
    pps = comp.post_process_settings
    pps.override_auto_exposure_bias        = True
    pps.auto_exposure_bias                 = 10.0   # ajusta se continuar escuro/claro
    pps.override_auto_exposure_min_ev100   = True
    pps.override_auto_exposure_max_ev100   = True
    pps.auto_exposure_min_ev100            = 10.0
    pps.auto_exposure_max_ev100            = 10.0
    comp.post_process_settings = pps
    unreal.log("[OK] Exposição fixa aplicada (EV100=10)")
except Exception as e:
    unreal.log_warning(f"[AVISO] Não foi possível forçar exposição: {e}")

unreal.log("[OK] SceneCaptureActor2D criado")

# 6. Loop de captura
errors = 0
for i in range(NUM_SHOTS):

    # Posição aleatória do objecto
    ox    = random.uniform(SPAWN_X_MIN, SPAWN_X_MAX)
    oy    = random.uniform(SPAWN_Y_MIN, SPAWN_Y_MAX)
    o_yaw = random.uniform(0, 360) if ROTATE_OBJECT else 0.0
    obj.set_actor_location_and_rotation(
        unreal.Vector(ox, oy, SPAWN_Z),
        unreal.Rotator(0.0, o_yaw, 0.0),
        False, True,
    )

    # Posição aleatória da câmara
    angle  = random.uniform(0, 2 * math.pi)
    radius = random.uniform(CAM_RADIUS_MIN, CAM_RADIUS_MAX)
    height = random.uniform(CAM_HEIGHT_MIN, CAM_HEIGHT_MAX)
    cam_loc = unreal.Vector(
        ox + radius * math.cos(angle),
        oy + radius * math.sin(angle),
        SPAWN_Z + height,
    )
    aim     = unreal.Vector(ox, oy, SPAWN_Z + TARGET_Z_OFFSET)
    cam_rot = unreal.MathLibrary.find_look_at_rotation(cam_loc, aim)
    capture_actor.set_actor_location_and_rotation(cam_loc, cam_rot, False, True)

    # Capturar frame (SÍNCRONO)
    comp.capture_scene()

    # Guardar PNG
    fname = f"synthetic_{i:04d}"
    try:
        unreal.RenderingLibrary.export_render_target(world, rt, OUTPUT_DIR, fname)
        # export_render_target não adiciona extensão — renomear para .png
        src = os.path.join(OUTPUT_DIR, fname)
        dst = os.path.join(OUTPUT_DIR, fname + ".png")
        if os.path.exists(src):
            if os.path.exists(dst):
                os.remove(dst)
            os.rename(src, dst)
        unreal.log(f"[Dataset] Shot {i + 1}/{NUM_SHOTS} → {fname}.png")
    except Exception as e:
        unreal.log_warning(f"[Dataset] Shot {i + 1} falhou: {e}")
        errors += 1

# 7. Limpeza
capture_actor.destroy_actor()
obj.set_actor_location_and_rotation(original_loc, original_rot, False, True)

unreal.log("══════════════════════════════════════════")
unreal.log(f" Concluído! {NUM_SHOTS - errors}/{NUM_SHOTS} shots em:")
unreal.log(f" {OUTPUT_DIR}")
unreal.log("══════════════════════════════════════════")
