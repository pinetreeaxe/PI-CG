import unreal
import math
import os
import shutil
import datetime

# ─── CONFIGURAÇÃO ─────────────────────────────────────────────
RAIO            = 350.0   # distância orbital (cm) — maior para Cenário 3 (oclusão 70–90%)
NUM_ANGULOS     = 15      # ângulos por Piplup
FOV_H           = 90.0    # FOV horizontal do viewport UE5 (graus)
FRAMES_ESPERA   = 40      # frames para o viewport renderizar
FRAMES_FICHEIRO = 15      # frames para o ficheiro ser escrito em disco
LARGURA         = 1920
ALTURA_RES      = 1080
CLASSE_ID       = 0       # ID da classe no YOLO (0 = Piplup)

BASE_DIR    = r"C:\Users\Filipa Rebelo\OneDrive - Cachapuz - Bilanciai Group\Ambiente de Trabalho\PI-CG\Dataset\Synthetic\Cenario_03"
IMAGES_DIR  = os.path.join(BASE_DIR, "images")
LABELS_DIR  = os.path.join(BASE_DIR, "labels")
SCREENSHOTS_DIR = r"C:\Users\Filipa Rebelo\OneDrive - Cachapuz - Bilanciai Group\Ambiente de Trabalho\PI-CG\PI_CG_G3_T3\Saved\Screenshots\WindowsEditor"
# ──────────────────────────────────────────────────────────────

os.makedirs(IMAGES_DIR,  exist_ok=True)
os.makedirs(LABELS_DIR,  exist_ok=True)
SESSAO = datetime.datetime.now().strftime("%Y%m%d_%H%M")


# ── Projeção 3D → 2D ────────────────────────────────────────────
def projeto_3d_2d(world_pt, cam_loc, cam_rot):
    P = math.radians(cam_rot.pitch)
    Y = math.radians(cam_rot.yaw)

    F = (math.cos(P)*math.cos(Y),  math.cos(P)*math.sin(Y),  math.sin(P))
    R = (-math.sin(Y),              math.cos(Y),               0.0)
    U = (-math.sin(P)*math.cos(Y), -math.sin(P)*math.sin(Y),  math.cos(P))

    dx = world_pt.x - cam_loc.x
    dy = world_pt.y - cam_loc.y
    dz = world_pt.z - cam_loc.z

    cam_x = dx*R[0] + dy*R[1] + dz*R[2]
    cam_y = dx*U[0] + dy*U[1] + dz*U[2]
    cam_z = dx*F[0] + dy*F[1] + dz*F[2]

    if cam_z <= 0.001:
        return None

    half_h_fov = math.tan(math.radians(FOV_H / 2.0))
    half_v_fov = half_h_fov * (ALTURA_RES / LARGURA)

    nx =  cam_x / (cam_z * half_h_fov)
    ny = -cam_y / (cam_z * half_v_fov)

    u = (nx + 1.0) / 2.0
    v = (ny + 1.0) / 2.0
    return (u, v)


def calcular_bbox_yolo(piplup, cam_loc, cam_rot):
    origin, extent = piplup.get_actor_bounds(False)

    cantos = [
        unreal.Vector(origin.x + sx*extent.x,
                      origin.y + sy*extent.y,
                      origin.z + sz*extent.z)
        for sx in (-1, 1)
        for sy in (-1, 1)
        for sz in (-1, 1)
    ]

    pts = [projeto_3d_2d(c, cam_loc, cam_rot) for c in cantos]
    pts = [p for p in pts if p is not None]

    if not pts:
        return None

    us = [p[0] for p in pts]
    vs = [p[1] for p in pts]

    u_min, u_max = max(0.0, min(us)), min(1.0, max(us))
    v_min, v_max = max(0.0, min(vs)), min(1.0, max(vs))

    if u_max <= u_min or v_max <= v_min:
        return None

    x_c = (u_min + u_max) / 2.0
    y_c = (v_min + v_max) / 2.0
    w   = u_max - u_min
    h   = v_max - v_min

    return (x_c, y_c, w, h)


def guardar_anotacao(fname, bbox):
    path = os.path.join(LABELS_DIR, fname + ".txt")
    x_c, y_c, w, h = bbox
    with open(path, "w") as f:
        f.write(f"{CLASSE_ID} {x_c:.6f} {y_c:.6f} {w:.6f} {h:.6f}\n")
    unreal.log(f"    -> anotacao: classe={CLASSE_ID} cx={x_c:.3f} cy={y_c:.3f} w={w:.3f} h={h:.3f}")


# ── Calcular posições de câmara ─────────────────────────────────
def calcular_posicoes():
    todos = unreal.EditorLevelLibrary.get_all_level_actors()
    pips  = sorted([a for a in todos if "Piplup" in a.get_actor_label()],
                   key=lambda a: a.get_actor_label())

    if not pips:
        unreal.log_warning("Nenhum actor 'Piplup' encontrado!")
        return []

    unreal.log(f"Piplups detetados: {[p.get_actor_label() for p in pips]}")
    posicoes = []

    for piplup in pips:
        nome = piplup.get_actor_label()

        origin, extent = piplup.get_actor_bounds(False)
        centro = origin

        unreal.log(f"  {nome}: centro=({centro.x:.0f},{centro.y:.0f},{centro.z:.0f})")

        for j in range(NUM_ANGULOS):
            a = math.radians(j * 360.0 / NUM_ANGULOS)

            cam_loc = unreal.Vector(
                centro.x + RAIO * math.cos(a),
                centro.y + RAIO * math.sin(a),
                centro.z
            )
            cam_rot = unreal.MathLibrary.find_look_at_rotation(cam_loc, centro)
            fname   = f"Cenario03_{nome}_ang{j+1:02d}_{SESSAO}"

            posicoes.append({
                "loc":    cam_loc,
                "rot":    cam_rot,
                "fname":  fname,
                "nome":   nome,
                "piplup": piplup,
            })

    return posicoes


def mover_imagem(fname):
    src = os.path.join(SCREENSHOTS_DIR, fname + ".png")
    dst = os.path.join(IMAGES_DIR,      fname + ".png")
    try:
        if os.path.exists(src):
            shutil.move(src, dst)
            unreal.log(f"    -> imagem guardada: images/{fname}.png")
        else:
            unreal.log_warning(f"    Imagem nao encontrada: {src}")
    except Exception as e:
        unreal.log_warning(f"    Erro ao mover imagem: {e}")


# ── Máquina de estados por tick ─────────────────────────────────
posicoes  = calcular_posicoes()
total     = len(posicoes)
estado    = {"i": 0, "espera": 0, "fase": "mover"}
cb_handle = [None]


def on_tick(dt):
    i = estado["i"]
    if i >= total:
        unreal.log(f"Concluido! {total} imagens em images/  |  {total} anotacoes em labels/")
        unreal.unregister_slate_pre_tick_callback(cb_handle[0])
        return

    p    = posicoes[i]
    fase = estado["fase"]

    if fase == "mover":
        unreal.EditorLevelLibrary.set_level_viewport_camera_info(p["loc"], p["rot"])
        estado["espera"] = 0
        estado["fase"]   = "esperar"

    elif fase == "esperar":
        estado["espera"] += 1
        if estado["espera"] >= FRAMES_ESPERA:
            estado["fase"] = "capturar"

    elif fase == "capturar":
        unreal.AutomationLibrary.take_high_res_screenshot(LARGURA, ALTURA_RES, p["fname"])
        estado["espera"] = 0
        estado["fase"]   = "mover_ficheiro"

    elif fase == "mover_ficheiro":
        estado["espera"] += 1
        if estado["espera"] >= FRAMES_FICHEIRO:
            mover_imagem(p["fname"])

            bbox = calcular_bbox_yolo(p["piplup"], p["loc"], p["rot"])
            if bbox:
                guardar_anotacao(p["fname"], bbox)
            else:
                unreal.log_warning(f"    Piplup fora do ecra — anotacao ignorada")

            unreal.log(f"  [{i+1}/{total}] {p['nome']} ang{(i % NUM_ANGULOS)+1:02d}")
            estado["i"]   += 1
            estado["fase"] = "mover"


if total > 0:
    unreal.log(f"A iniciar: {total} fotos | {total//NUM_ANGULOS} Piplups x {NUM_ANGULOS} angulos | {SESSAO}")
    unreal.log(f"Imagens  -> {IMAGES_DIR}")
    unreal.log(f"Labels   -> {LABELS_DIR}")
    cb_handle[0] = unreal.register_slate_pre_tick_callback(on_tick)
