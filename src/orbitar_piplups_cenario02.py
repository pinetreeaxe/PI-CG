import unreal
import math
import os
import shutil
import datetime
import subprocess
import sys
from pathlib import Path

# ── Instalar dependências ────────────────────────────────────────
def pip_install(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "--quiet"])

try:
    from PIL import Image
except ImportError:
    pip_install("Pillow")
    from PIL import Image

try:
    import numpy as np
except ImportError:
    pip_install("numpy")
    import numpy as np

# ─── CONFIGURAÇÃO ─────────────────────────────────────────────
CENARIO            = "03"
RAIO               = 480.0
CAM_ALTURA_OFFSET  = 150.0  # Altura extra da câmara (em cm) para evitar clipping
NUM_ANGULOS        = 60
BBOX_MAX_FRAC      = 0.80
BBOX_MIN_FRAC      = 0.03
MARGEM_BORDA       = 20
FOV_H              = 90.0
FRAMES_ESPERA      = 60
FRAMES_FICHEIRO    = 90
LARGURA            = 1920
ALTURA_RES         = 1080
CLASSE_ID          = 0
ESPESSURA_BBOX     = 3

# Paths dos materiais
MAT_NORMAL_PATH   = "/Game/Piplup/3DModel"
MAT_EMISSIVE_PATH = "/Game/Piplup/3DModel_Emissive"

# ─── PATHS DINÂMICOS ───────────────────────────────────────────
# Deteta o caminho dinamicamente com base na localização deste script Python
SCRIPT_PATH     = Path(__file__).resolve().parent
REPO_ROOT       = SCRIPT_PATH.parent
BASE_DIR        = REPO_ROOT / "Dataset" / "Synthetic" / f"Cenario_{CENARIO}"
IMAGES_DIR      = str(BASE_DIR / "images")
LABELS_DIR      = str(BASE_DIR / "labels")

# Caminho nativo de screenshots do Unreal Engine
SCREENSHOTS_DIR = unreal.Paths.screen_shot_dir()
# ──────────────────────────────────────────────────────────────

os.makedirs(IMAGES_DIR,  exist_ok=True)
os.makedirs(LABELS_DIR,  exist_ok=True)
SESSAO = datetime.datetime.now().strftime("%Y%m%d_%H%M")
WORLD  = unreal.EditorLevelLibrary.get_editor_world()


# ── Modo de renderização ─────────────────────────────────────────
def set_viewmode(mode):
    unreal.SystemLibrary.execute_console_command(WORLD, f"viewmode {mode}")

def set_black_environment(ativo):
    val = 0 if ativo else 1
    for flag in ["Atmosphere", "Fog", "Clouds", "Sky", "DirectionalLights",
                 "PointLights", "SpotLights", "SkyLighting"]:
        unreal.SystemLibrary.execute_console_command(WORLD, f"show {flag} {val}")


# ── Materiais ────────────────────────────────────────────────────
_mat_normal   = unreal.load_asset(MAT_NORMAL_PATH)
_mat_emissive = unreal.load_asset(MAT_EMISSIVE_PATH)

if _mat_normal is None:
    unreal.log_warning(f"[MAT] ERRO: material normal nao encontrado: {MAT_NORMAL_PATH}")
if _mat_emissive is None:
    unreal.log_warning(f"[MAT] ERRO: material emissivo nao encontrado: {MAT_EMISSIVE_PATH}")

def aplicar_material(piplup_actor, mat):
    if mat is None:
        return
    comps = piplup_actor.get_components_by_class(unreal.StaticMeshComponent)
    for comp in comps:
        for slot in range(comp.get_num_materials()):
            comp.set_material(slot, mat)
    if not comps:
        try:
            comp = piplup_actor.static_mesh_component
            for slot in range(comp.get_num_materials()):
                comp.set_material(slot, mat)
        except Exception as e:
            unreal.log_warning(f"[MAT] fallback falhou: {e}")


# ── Visibilidade de Piplups ──────────────────────────────────────
def focar_piplup(piplup_alvo, todos_pips):
    for pip in todos_pips:
        pip.set_is_temporarily_hidden_in_editor(pip != piplup_alvo)

def restaurar_todos(todos_pips):
    for pip in todos_pips:
        pip.set_is_temporarily_hidden_in_editor(False)
        aplicar_material(pip, _mat_normal)


# ── Processamento de imagem com PIL ─────────────────────────────
def calcular_bbox_pixels(img_path):
    """Detecta pixeis vermelhos do emissivo: R>=240, G<130, B<120."""
    try:
        # Uso do 'with' para garantir o fecho correto do ficheiro e libertar memória
        with Image.open(img_path) as img:
            img_rgb = img.convert("RGB")
            arr = np.array(img_rgb)
            
        mask = (arr[:, :, 0] >= 240) & (arr[:, :, 1] < 130) & (arr[:, :, 2] < 120)
        rows = np.where(mask.any(axis=1))[0]
        cols = np.where(mask.any(axis=0))[0]
        if len(rows) == 0 or len(cols) == 0:
            return None
        return (int(cols[0]), int(rows[0]), int(cols[-1]), int(rows[-1]))
    except Exception as e:
        unreal.log_warning(f"Erro bbox pixels: {e}")
        return None


def validar_bbox(bbox_px):
    x_min, y_min, x_max, y_max = bbox_px
    w_frac = (x_max - x_min) / LARGURA
    h_frac = (y_max - y_min) / ALTURA_RES

    if (x_min < MARGEM_BORDA or y_min < MARGEM_BORDA or
            x_max > LARGURA - MARGEM_BORDA or y_max > ALTURA_RES - MARGEM_BORDA):
        return False, f"Piplup cortado ({x_min},{y_min},{x_max},{y_max})"

    if w_frac < BBOX_MIN_FRAC or h_frac < BBOX_MIN_FRAC:
        return False, f"Piplup demasiado pequeno ({w_frac:.1%}x{h_frac:.1%})"

    if w_frac > BBOX_MAX_FRAC or h_frac > BBOX_MAX_FRAC:
        return False, f"Bbox demasiado grande ({w_frac:.1%}x{h_frac:.1%})"

    return True, "ok"


def bbox_pixels_para_yolo(bbox_px):
    x_min, y_min, x_max, y_max = bbox_px
    x_c = ((x_min + x_max) / 2.0) / LARGURA
    y_c = ((y_min + y_max) / 2.0) / ALTURA_RES
    w   = (x_max - x_min) / LARGURA
    h   = (y_max - y_min) / ALTURA_RES
    return (x_c, y_c, w, h)


def guardar_anotacao(fname, bbox_yolo):
    path = os.path.join(LABELS_DIR, fname + ".txt")
    x_c, y_c, w, h = bbox_yolo
    with open(path, "w") as f:
        f.write(f"{CLASSE_ID} {x_c:.6f} {y_c:.6f} {w:.6f} {h:.6f}\n")
    unreal.log(f"    -> label: cx={x_c:.3f} cy={y_c:.3f} w={w:.3f} h={h:.3f}")


def mover_imagem(fname):
    src = os.path.join(SCREENSHOTS_DIR, fname + ".png")
    dst = os.path.join(IMAGES_DIR,      fname + ".png")
    try:
        if os.path.exists(src):
            shutil.move(src, dst)
        else:
            unreal.log_warning(f"    Imagem nao encontrada: {src}")
    except Exception as e:
        unreal.log_warning(f"    Erro ao mover imagem: {e}")


# ── Calcular posições de câmara ─────────────────────────────────
def calcular_posicoes():
    todos = unreal.EditorLevelLibrary.get_all_level_actors()
    pips = sorted(
        [a for a in todos if "Piplup" in a.get_actor_label() and "Extra" not in a.get_actor_label()],
        key=lambda a: a.get_actor_label()
    )

    if not pips:
        unreal.log_warning("Nenhum actor 'Piplup' encontrado!")
        return [], []

    unreal.log(f"Piplups encontrados: {[p.get_actor_label() for p in pips]}")

    posicoes = []
    for piplup in pips:
        nome = piplup.get_actor_label()
        origin, extent = piplup.get_actor_bounds(False)
        centro = origin

        unreal.log(f"  {nome}: centro=({centro.x:.0f},{centro.y:.0f},{centro.z:.0f})")

        for j in range(NUM_ANGULOS):
            a = math.radians(j * 360.0 / NUM_ANGULOS)
            # Incorporação da variável CAM_ALTURA_OFFSET no eixo Z
            cam_loc = unreal.Vector(
                centro.x + RAIO * math.cos(a),
                centro.y + RAIO * math.sin(a),
                centro.z + CAM_ALTURA_OFFSET
            )
            cam_rot = unreal.MathLibrary.find_look_at_rotation(cam_loc, centro)
            fname   = f"Cenario{CENARIO}_{nome}_ang{j+1:02d}_{SESSAO}"
            posicoes.append({
                "loc":    cam_loc,
                "rot":    cam_rot,
                "fname":  fname,
                "nome":   nome,
                "piplup": piplup,
            })

    return posicoes, pips


# ── Inicialização ────────────────────────────────────────────────
posicoes, todos_piplups_cena = calcular_posicoes()
total  = len(posicoes)
estado = {"i": 0, "espera": 0, "fase": "mover", "bbox_emissivo": None}
cb_handle = [None]
stats  = {"ok": 0, "rejeitadas": 0}


# ── Máquina de estados por tick ─────────────────────────────────
def on_tick(dt):
    i = estado["i"]

    if i >= total:
        restaurar_todos(todos_piplups_cena)
        set_viewmode("lit")
        set_black_environment(False)
        unreal.log(f"Concluido! {stats['ok']} imagens validas | {stats['rejeitadas']} rejeitadas")
        unreal.unregister_slate_pre_tick_callback(cb_handle[0])
        return

    p    = posicoes[i]
    fase = estado["fase"]

    if fase == "mover":
        if i == 0 or posicoes[i]["piplup"] != posicoes[i - 1]["piplup"]:
            focar_piplup(p["piplup"], todos_piplups_cena)
            unreal.log(f"  Focando: {p['nome']} (outros Piplups escondidos)")

        aplicar_material(p["piplup"], _mat_emissive)
        set_black_environment(True)
        set_viewmode("unlit")
        unreal.EditorLevelLibrary.set_level_viewport_camera_info(p["loc"], p["rot"])
        estado["espera"] = 0
        estado["fase"]   = "esperar_emissivo"

    elif fase == "esperar_emissivo":
        estado["espera"] += 1
        if estado["espera"] >= FRAMES_ESPERA:
            estado["fase"] = "capturar_emissivo"

    elif fase == "capturar_emissivo":
        fname_em = p["fname"] + "_em"
        unreal.AutomationLibrary.take_high_res_screenshot(LARGURA, ALTURA_RES, fname_em)
        estado["espera"] = 0
        estado["fase"]   = "processar_emissivo"

    elif fase == "processar_emissivo":
        estado["espera"] += 1
        if estado["espera"] >= FRAMES_FICHEIRO:
            fname_em = p["fname"] + "_em"
            mover_imagem(fname_em)
            img_em = os.path.join(IMAGES_DIR, fname_em + ".png")

            bbox_px = calcular_bbox_pixels(img_em)

            if os.path.exists(img_em):
                os.remove(img_em)

            if bbox_px is None:
                unreal.log_warning(f"    Sem pixeis vermelhos — descartada")
                stats["rejeitadas"] += 1
                unreal.log(f"  [{i+1}/{total}] {p['nome']} ang{(i % NUM_ANGULOS)+1:02d} | ok={stats['ok']} rej={stats['rejeitadas']}")
                estado["i"]   += 1
                estado["fase"] = "mover"
                return

            valida, motivo = validar_bbox(bbox_px)
            if not valida:
                unreal.log_warning(f"    Rejeitada: {motivo}")
                stats["rejeitadas"] += 1
                unreal.log(f"  [{i+1}/{total}] {p['nome']} ang{(i % NUM_ANGULOS)+1:02d} | ok={stats['ok']} rej={stats['rejeitadas']}")
                estado["i"]   += 1
                estado["fase"] = "mover"
                return

            estado["bbox_emissivo"] = bbox_px
            aplicar_material(p["piplup"], _mat_normal)
            set_black_environment(False)
            set_viewmode("lit")
            estado["espera"] = 0
            estado["fase"]   = "esperar_normal"

    elif fase == "esperar_normal":
        estado["espera"] += 1
        if estado["espera"] >= FRAMES_ESPERA:
            estado["fase"] = "capturar_normal"

    elif fase == "capturar_normal":
        unreal.AutomationLibrary.take_high_res_screenshot(LARGURA, ALTURA_RES, p["fname"])
        estado["espera"] = 0
        estado["fase"]   = "processar_normal"

    elif fase == "processar_normal":
        estado["espera"] += 1
        if estado["espera"] >= FRAMES_FICHEIRO:
            mover_imagem(p["fname"])
            guardar_anotacao(p["fname"], bbox_pixels_para_yolo(estado["bbox_emissivo"]))
            stats["ok"] += 1
            unreal.log(f"  [{i+1}/{total}] {p['nome']} ang{(i % NUM_ANGULOS)+1:02d} | ok={stats['ok']} rej={stats['rejeitadas']}")
            estado["i"]   += 1
            estado["fase"] = "mover"


if total > 0:
    unreal.log(f"=== CENARIO {CENARIO} ===")
    unreal.log(f"  {len(todos_piplups_cena)} Piplups x {NUM_ANGULOS} angulos = {total} tentativas")
    unreal.log(f"  Raio: {RAIO}cm | Offset Altura: {CAM_ALTURA_OFFSET}cm | Margem borda: {MARGEM_BORDA}px")
    unreal.log(f"  Imagens -> {IMAGES_DIR}")
    unreal.log(f"  Labels  -> {LABELS_DIR}")
    cb_handle[0] = unreal.register_slate_pre_tick_callback(on_tick)
else:
    unreal.log_warning("Nenhuma posicao calculada — verifica se ha actors 'Piplup' na cena.")