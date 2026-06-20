import unreal
import math
import os
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


# ─── CONFIGURAÇÃO ────────────────────────────────────────────────
CENARIO                    = "01"
RAIO                       = 280.0
NUM_ANGULOS                = 60
BBOX_MAX_FRAC              = 0.80
BBOX_MIN_FRAC              = 0.03
MARGEM_BORDA               = 20
FRAMES_ESPERA              = 60
FRAMES_FICHEIRO_MIN        = 90
FRAMES_FICHEIRO_TIMEOUT    = 240
LARGURA_RES                = 1920
ALTURA_RES                 = 1080
CLASSE_ID                  = 0
MIN_PONTOS_VISIVEIS        = 2
TRACE_COMPLEX              = True

MAT_NORMAL_PATH   = "/Game/Piplup/3DModel"
MAT_EMISSIVE_PATH = "/Game/Piplup/3DModel_Emissive"


# ─── PATHS ───────────────────────────────────────────────────────
SCRIPT_PATH = Path(__file__).resolve().parent
REPO_ROOT   = SCRIPT_PATH.parent
BASE_DIR    = REPO_ROOT / "Dataset" / "Synthetic" / f"Cenario_{CENARIO}"
IMAGES_DIR  = str(BASE_DIR / "images")
LABELS_DIR  = str(BASE_DIR / "labels")

PROJECT_DIR     = unreal.Paths.project_dir()
SAVED_DIR       = unreal.Paths.project_saved_dir()
SCREENSHOTS_DIR = unreal.Paths.screen_shot_dir()

os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(LABELS_DIR, exist_ok=True)

SESSAO = datetime.datetime.now().strftime("%Y%m%d_%H%M")

EDITOR_SUBSYSTEM = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
ACTOR_SUBSYSTEM  = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
WORLD = EDITOR_SUBSYSTEM.get_editor_world()


# ── Helpers de paths ─────────────────────────────────────────────
def normalize_path(p):
    return os.path.normpath(str(p))


def log_paths():
    unreal.log(f"  Repo root    -> {normalize_path(REPO_ROOT)}")
    unreal.log(f"  Project dir  -> {normalize_path(PROJECT_DIR)}")
    unreal.log(f"  Saved dir    -> {normalize_path(SAVED_DIR)}")
    unreal.log(f"  Screenshot   -> {normalize_path(SCREENSHOTS_DIR)}")
    unreal.log(f"  Imagens      -> {normalize_path(IMAGES_DIR)}")
    unreal.log(f"  Labels       -> {normalize_path(LABELS_DIR)}")


# ── Modo de renderização ─────────────────────────────────────────
def set_viewmode(mode):
    unreal.SystemLibrary.execute_console_command(WORLD, f"viewmode {mode}")


def set_black_environment(ativo):
    val = 0 if ativo else 1
    for flag in [
        "Atmosphere", "Fog", "Clouds", "Sky",
        "DirectionalLights", "PointLights", "SpotLights", "SkyLighting"
    ]:
        unreal.SystemLibrary.execute_console_command(WORLD, f"show {flag} {val}")


# ── Materiais ────────────────────────────────────────────────────
_mat_normal   = unreal.load_asset(MAT_NORMAL_PATH)
_mat_emissive = unreal.load_asset(MAT_EMISSIVE_PATH)

unreal.log(f"[MAT] Normal: {_mat_normal}")
unreal.log(f"[MAT] Emissive: {_mat_emissive}")

if _mat_normal is None:
    unreal.log_warning(f"[MAT] ERRO: material normal nao encontrado: {MAT_NORMAL_PATH}")
if _mat_emissive is None:
    unreal.log_warning(f"[MAT] ERRO: material emissivo nao encontrado: {MAT_EMISSIVE_PATH}")


def aplicar_material(piplup_actor, mat):
    if mat is None:
        unreal.log_warning("[MAT] aplicar_material: mat e None!")
        return

    comps = piplup_actor.get_components_by_class(unreal.StaticMeshComponent)
    for comp in comps:
        n = comp.get_num_materials()
        for slot in range(n):
            comp.set_material(slot, mat)

    if not comps:
        try:
            comp = piplup_actor.static_mesh_component
            for slot in range(comp.get_num_materials()):
                comp.set_material(slot, mat)
        except Exception as e:
            unreal.log_warning(f"[MAT] fallback falhou: {e}")


# ── Visibilidade dos Piplups ─────────────────────────────────────
def focar_piplup(piplup_alvo, todos_pips):
    for pip in todos_pips:
        pip.set_is_temporarily_hidden_in_editor(pip != piplup_alvo)


def restaurar_todos(todos_pips):
    for pip in todos_pips:
        pip.set_is_temporarily_hidden_in_editor(False)
        aplicar_material(pip, _mat_normal)


# ── Processamento de imagem ──────────────────────────────────────
def calcular_bbox_pixels(img_path):
    try:
        img = Image.open(img_path).convert("RGB")
        arr = np.array(img)
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
    w_frac = (x_max - x_min) / LARGURA_RES
    h_frac = (y_max - y_min) / ALTURA_RES

    if (
        x_min < MARGEM_BORDA or
        y_min < MARGEM_BORDA or
        x_max > LARGURA_RES - MARGEM_BORDA or
        y_max > ALTURA_RES - MARGEM_BORDA
    ):
        return False, f"Piplup cortado ({x_min},{y_min},{x_max},{y_max})"

    if w_frac < BBOX_MIN_FRAC or h_frac < BBOX_MIN_FRAC:
        return False, f"Piplup demasiado pequeno ({w_frac:.1%}x{h_frac:.1%})"

    if w_frac > BBOX_MAX_FRAC or h_frac > BBOX_MAX_FRAC:
        return False, f"Bbox demasiado grande ({w_frac:.1%}x{h_frac:.1%})"

    return True, "ok"


def bbox_pixels_para_yolo(bbox_px):
    x_min, y_min, x_max, y_max = bbox_px
    x_c = ((x_min + x_max) / 2.0) / LARGURA_RES
    y_c = ((y_min + y_max) / 2.0) / ALTURA_RES
    w   = (x_max - x_min) / LARGURA_RES
    h   = (y_max - y_min) / ALTURA_RES
    return (x_c, y_c, w, h)


def guardar_anotacao(fname, bbox_yolo):
    path = os.path.join(LABELS_DIR, fname + ".txt")
    x_c, y_c, w, h = bbox_yolo
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"{CLASSE_ID} {x_c:.6f} {y_c:.6f} {w:.6f} {h:.6f}\n")
    unreal.log(f"    -> label: cx={x_c:.3f} cy={y_c:.3f} w={w:.3f} h={h:.3f}")


# ── Screenshots ──────────────────────────────────────────────────
def caminho_imagem_final(fname):
    return normalize_path(os.path.join(IMAGES_DIR, fname + ".png"))


def screenshot_existe(path):
    return os.path.exists(normalize_path(path))


def capturar_screenshot(path_final):
    path_final = normalize_path(path_final).replace("\\", "/")
    unreal.AutomationLibrary.take_high_res_screenshot(
        LARGURA_RES,
        ALTURA_RES,
        filename=path_final
    )


# ── Oclusão / visibilidade ───────────────────────────────────────
def obter_centro_actor(actor):
    origin, extent = actor.get_actor_bounds(False)
    return origin, extent


def pontos_visados_bbox(actor):
    origin, extent = actor.get_actor_bounds(False)

    ex = extent.x * 0.45
    ey = extent.y * 0.45
    ez_top = extent.z * 0.55
    ez_mid = extent.z * 0.15
    ez_low = extent.z * -0.20

    return [
        unreal.Vector(origin.x,      origin.y,      origin.z + ez_top),
        unreal.Vector(origin.x,      origin.y,      origin.z + ez_mid),
        unreal.Vector(origin.x,      origin.y,      origin.z + ez_low),
        unreal.Vector(origin.x + ex, origin.y,      origin.z + ez_mid),
        unreal.Vector(origin.x - ex, origin.y,      origin.z + ez_mid),
        unreal.Vector(origin.x,      origin.y + ey, origin.z + ez_mid),
        unreal.Vector(origin.x,      origin.y - ey, origin.z + ez_mid),
    ]


def ator_pertence_ao_piplup(hit_actor, piplup_actor):
    if hit_actor is None:
        return False

    if hit_actor == piplup_actor:
        return True

    try:
        owner = hit_actor.get_owner()
        if owner == piplup_actor:
            return True
    except Exception:
        pass

    try:
        if hit_actor.get_actor_label() == piplup_actor.get_actor_label():
            return True
    except Exception:
        pass

    return False


def extrair_hit_info(hit):
    hit_result = None
    hit_success = False

    if isinstance(hit, tuple):
        if len(hit) >= 2:
            hit_success = bool(hit[0])
            hit_result = hit[1]
    else:
        hit_result = hit
        try:
            hit_success = bool(hit_result.blocking_hit)
        except Exception:
            hit_success = False

    hit_actor = None
    if hit_result is not None:
        try:
            hit_actor = hit_result.hit_actor
        except Exception:
            try:
                hit_actor = hit_result.get_actor()
            except Exception:
                hit_actor = None

    return hit_success, hit_result, hit_actor


def esta_ocluido(cam_loc, piplup_actor):
    try:
        pontos = pontos_visados_bbox(piplup_actor)
        bloqueados = []
        visiveis = 0

        for target in pontos:
            hit = unreal.SystemLibrary.line_trace_single(
                WORLD,
                cam_loc,
                target,
                unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
                TRACE_COMPLEX,
                [],
                unreal.DrawDebugTrace.NONE,
                True
            )

            hit_success, hit_result, hit_actor = extrair_hit_info(hit)

            if hit_success and hit_result is not None:
                if ator_pertence_ao_piplup(hit_actor, piplup_actor):
                    visiveis += 1
                    continue

                try:
                    nome_hit = hit_actor.get_actor_label() if hit_actor else "desconhecido"
                except Exception:
                    nome_hit = "desconhecido"

                bloqueados.append(nome_hit)
                continue

            visiveis += 1

        if visiveis >= MIN_PONTOS_VISIVEIS:
            return False

        if bloqueados:
            contagem = {}
            for nome in bloqueados:
                contagem[nome] = contagem.get(nome, 0) + 1
            pior = max(contagem, key=contagem.get)
            return True, f"{pior} ({contagem[pior]}/{len(pontos)} rays bloqueados)"

        return True, "oclusao_total"

    except Exception as e:
        unreal.log_warning(f"[OCLUSAO] Falha no multi-target trace, a ignorar: {e}")
        return False


# ── Calcular posições de câmara ──────────────────────────────────
def calcular_posicoes():
    todos = ACTOR_SUBSYSTEM.get_all_level_actors()
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
        centro, extent = obter_centro_actor(piplup)
        unreal.log(f"  {nome}: centro=({centro.x:.0f},{centro.y:.0f},{centro.z:.0f})")

        for j in range(NUM_ANGULOS):
            a = math.radians(j * 360.0 / NUM_ANGULOS)
            cam_loc = unreal.Vector(
                centro.x + RAIO * math.cos(a),
                centro.y + RAIO * math.sin(a),
                centro.z
            )
            cam_rot = unreal.MathLibrary.find_look_at_rotation(cam_loc, centro)
            fname   = f"Cenario{CENARIO}_{nome}_ang{j+1:02d}_{SESSAO}"

            posicoes.append({
                "loc": cam_loc,
                "rot": cam_rot,
                "fname": fname,
                "nome": nome,
                "piplup": piplup,
            })

    return posicoes, pips


# ── Inicialização ────────────────────────────────────────────────
posicoes, todos_piplups_cena = calcular_posicoes()
total = len(posicoes)

estado = {
    "i": 0,
    "espera": 0,
    "fase": "mover",
    "bbox_emissivo": None,
    "img_emissiva": None,
    "img_normal": None,
    "aguardar_tipo": None,
}

cb_handle = [None]
stats = {
    "ok": 0,
    "rejeitadas": 0,
    "ocluidas": 0,
}


def avancar_para_proxima():
    estado["i"] += 1
    estado["fase"] = "mover"
    estado["espera"] = 0
    estado["bbox_emissivo"] = None
    estado["img_emissiva"] = None
    estado["img_normal"] = None
    estado["aguardar_tipo"] = None


def screenshot_pronto(path):
    return screenshot_existe(path)


# ── Máquina de estados por tick ──────────────────────────────────
def on_tick(dt):
    i = estado["i"]

    if i >= total:
        restaurar_todos(todos_piplups_cena)
        set_viewmode("lit")
        set_black_environment(False)
        unreal.log(
            f"Concluido! {stats['ok']} imagens validas | "
            f"{stats['rejeitadas']} rejeitadas | "
            f"{stats['ocluidas']} ocluidas"
        )
        unreal.unregister_slate_pre_tick_callback(cb_handle[0])
        return

    p = posicoes[i]
    fase = estado["fase"]

    if fase == "mover":
        if i == 0 or posicoes[i]["piplup"] != posicoes[i - 1]["piplup"]:
            focar_piplup(p["piplup"], todos_piplups_cena)
            unreal.log(f"  Focando: {p['nome']} (outros Piplups escondidos)")

        EDITOR_SUBSYSTEM.set_level_viewport_camera_info(p["loc"], p["rot"])

        ocl = esta_ocluido(p["loc"], p["piplup"])
        if isinstance(ocl, tuple) and ocl[0]:
            stats["ocluidas"] += 1
            stats["rejeitadas"] += 1
            unreal.log_warning(f"    Ocluido por: {ocl[1]} — descartada")
            unreal.log(
                f"  [{i+1}/{total}] {p['nome']} ang{(i % NUM_ANGULOS)+1:02d} | "
                f"ok={stats['ok']} rej={stats['rejeitadas']} ocl={stats['ocluidas']}"
            )
            avancar_para_proxima()
            return

        aplicar_material(p["piplup"], _mat_emissive)
        set_black_environment(True)
        set_viewmode("unlit")

        estado["img_emissiva"] = caminho_imagem_final(p["fname"] + "_em")
        estado["img_normal"] = caminho_imagem_final(p["fname"])
        estado["bbox_emissivo"] = None
        estado["espera"] = 0
        estado["aguardar_tipo"] = "emissivo"
        estado["fase"] = "esperar_emissivo"

    elif fase == "esperar_emissivo":
        estado["espera"] += 1
        if estado["espera"] >= FRAMES_ESPERA:
            estado["fase"] = "capturar_emissivo"

    elif fase == "capturar_emissivo":
        capturar_screenshot(estado["img_emissiva"])
        estado["espera"] = 0
        estado["aguardar_tipo"] = "emissivo"
        estado["fase"] = "aguardar_ficheiro_emissivo"

    elif fase == "aguardar_ficheiro_emissivo":
        estado["espera"] += 1

        if estado["espera"] < FRAMES_FICHEIRO_MIN:
            return

        if screenshot_pronto(estado["img_emissiva"]):
            estado["fase"] = "processar_emissivo"
            return

        if estado["espera"] % 30 == 0:
            unreal.log(f"    A aguardar screenshot emissivo no disco... ({estado['espera']} ticks)")

        if estado["espera"] >= FRAMES_FICHEIRO_TIMEOUT:
            unreal.log_warning(f"    Screenshot emissivo nao encontrado: {estado['img_emissiva']}")
            stats["rejeitadas"] += 1
            unreal.log(
                f"  [{i+1}/{total}] {p['nome']} ang{(i % NUM_ANGULOS)+1:02d} | "
                f"ok={stats['ok']} rej={stats['rejeitadas']} ocl={stats['ocluidas']}"
            )
            avancar_para_proxima()
            return

    elif fase == "processar_emissivo":
        img_em = estado["img_emissiva"]

        if not screenshot_pronto(img_em):
            unreal.log_warning(f"    Screenshot emissivo desapareceu antes de processar: {img_em}")
            stats["rejeitadas"] += 1
            unreal.log(
                f"  [{i+1}/{total}] {p['nome']} ang{(i % NUM_ANGULOS)+1:02d} | "
                f"ok={stats['ok']} rej={stats['rejeitadas']} ocl={stats['ocluidas']}"
            )
            avancar_para_proxima()
            return

        bbox_px = calcular_bbox_pixels(img_em)

        try:
            if os.path.exists(img_em):
                os.remove(img_em)
        except Exception as e:
            unreal.log_warning(f"    Nao foi possivel apagar emissiva: {e}")

        if bbox_px is None:
            unreal.log_warning("    Sem pixeis vermelhos — descartada")
            stats["rejeitadas"] += 1
            unreal.log(
                f"  [{i+1}/{total}] {p['nome']} ang{(i % NUM_ANGULOS)+1:02d} | "
                f"ok={stats['ok']} rej={stats['rejeitadas']} ocl={stats['ocluidas']}"
            )
            avancar_para_proxima()
            return

        valida, motivo = validar_bbox(bbox_px)
        if not valida:
            unreal.log_warning(f"    Rejeitada: {motivo}")
            stats["rejeitadas"] += 1
            unreal.log(
                f"  [{i+1}/{total}] {p['nome']} ang{(i % NUM_ANGULOS)+1:02d} | "
                f"ok={stats['ok']} rej={stats['rejeitadas']} ocl={stats['ocluidas']}"
            )
            avancar_para_proxima()
            return

        estado["bbox_emissivo"] = bbox_px
        aplicar_material(p["piplup"], _mat_normal)
        set_black_environment(False)
        set_viewmode("lit")
        estado["espera"] = 0
        estado["aguardar_tipo"] = "normal"
        estado["fase"] = "esperar_normal"

    elif fase == "esperar_normal":
        estado["espera"] += 1
        if estado["espera"] >= FRAMES_ESPERA:
            estado["fase"] = "capturar_normal"

    elif fase == "capturar_normal":
        capturar_screenshot(estado["img_normal"])
        estado["espera"] = 0
        estado["aguardar_tipo"] = "normal"
        estado["fase"] = "aguardar_ficheiro_normal"

    elif fase == "aguardar_ficheiro_normal":
        estado["espera"] += 1

        if estado["espera"] < FRAMES_FICHEIRO_MIN:
            return

        if screenshot_pronto(estado["img_normal"]):
            estado["fase"] = "processar_normal"
            return

        if estado["espera"] % 30 == 0:
            unreal.log(f"    A aguardar screenshot normal no disco... ({estado['espera']} ticks)")

        if estado["espera"] >= FRAMES_FICHEIRO_TIMEOUT:
            unreal.log_warning(f"    Screenshot final nao encontrado: {estado['img_normal']}")
            stats["rejeitadas"] += 1
            unreal.log(
                f"  [{i+1}/{total}] {p['nome']} ang{(i % NUM_ANGULOS)+1:02d} | "
                f"ok={stats['ok']} rej={stats['rejeitadas']} ocl={stats['ocluidas']}"
            )
            avancar_para_proxima()
            return

    elif fase == "processar_normal":
        img_final = estado["img_normal"]

        if not screenshot_pronto(img_final):
            unreal.log_warning(f"    Screenshot final desapareceu antes de processar: {img_final}")
            stats["rejeitadas"] += 1
            unreal.log(
                f"  [{i+1}/{total}] {p['nome']} ang{(i % NUM_ANGULOS)+1:02d} | "
                f"ok={stats['ok']} rej={stats['rejeitadas']} ocl={stats['ocluidas']}"
            )
            avancar_para_proxima()
            return

        guardar_anotacao(p["fname"], bbox_pixels_para_yolo(estado["bbox_emissivo"]))
        stats["ok"] += 1

        unreal.log(
            f"  [{i+1}/{total}] {p['nome']} ang{(i % NUM_ANGULOS)+1:02d} | "
            f"ok={stats['ok']} rej={stats['rejeitadas']} ocl={stats['ocluidas']}"
        )

        avancar_para_proxima()


# ── Arranque ─────────────────────────────────────────────────────
if total > 0:
    unreal.log(f"=== CENARIO {CENARIO} ===")
    unreal.log(f"  {len(todos_piplups_cena)} Piplups x {NUM_ANGULOS} angulos = {total} tentativas")
    unreal.log(f"  Raio: {RAIO}cm | Margem borda: {MARGEM_BORDA}px | Bbox min: {BBOX_MIN_FRAC:.0%}")
    log_paths()
    unreal.log(f"  Min pontos visiveis -> {MIN_PONTOS_VISIVEIS}")
    unreal.log(f"  Espera screenshot min -> {FRAMES_FICHEIRO_MIN} ticks")
    unreal.log(f"  Timeout screenshot    -> {FRAMES_FICHEIRO_TIMEOUT} ticks")

    cb_handle[0] = unreal.register_slate_pre_tick_callback(on_tick)
else:
    unreal.log_warning("Nenhuma posicao calculada — verifica se ha actors 'Piplup' na cena.")