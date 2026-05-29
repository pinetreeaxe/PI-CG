"""
Scenario 2 — Adjust Piplup5/6/7 positions
Run via: Tools > Execute Python Script

Deletes Piplup5, Piplup6, Piplup7 and re-spawns them
closer to trees/rocks for correct occlusion levels.
"""

import unreal

ELL = unreal.EditorLevelLibrary
PIPLUP_MESH_PATH = "/Game/Piplup/Piplup"

# ── Delete existing Piplup5/6/7 ─────────────────────────────────────────────
to_delete = {"Piplup5", "Piplup6", "Piplup7"}
for actor in ELL.get_all_level_actors():
    if actor.get_actor_label() in to_delete:
        ELL.destroy_actor(actor)
        unreal.log(f"Deleted {actor.get_actor_label()}")

# ── Helper ───────────────────────────────────────────────────────────────────
def spawn_piplup(name, loc, rot, scale=(2.0, 2.0, 2.0)):
    mesh_asset = unreal.load_asset(PIPLUP_MESH_PATH)
    if mesh_asset is None:
        unreal.log_error(f"Could not load mesh at '{PIPLUP_MESH_PATH}'")
        return None
    actor = ELL.spawn_actor_from_class(
        unreal.StaticMeshActor,
        unreal.Vector(*loc),
        unreal.Rotator(*rot)
    )
    actor.set_actor_label(name)
    actor.set_actor_scale3d(unreal.Vector(*scale))
    actor.get_component_by_class(unreal.StaticMeshComponent).set_static_mesh(mesh_asset)
    actor.set_folder_path("Piplup")
    unreal.log(f"Spawned {name} at {loc}")
    return actor

# ════════════════════════════════════════════════════════════════════════════
# ADJUSTED POSITIONS (based on known tree/rock locations in the scene)
#
# Known anchors from existing Piplups:
#   Piplup  → (-478, -386, 23)   near rocks + foliage
#   Piplup2 → (2383, -502, -13)  open sandy area
#   Piplup3 → (-600, 1750, 10)   among ferns
#   Piplup4 → (2187, 1138, 161)  on top of rock
#
# Tree cluster approx. positions (from viewport):
#   Tree A (bottom-left):  (-350, 550)
#   Tree B (top-center):   (1550, -150)
#   Tree C (right):        (2300, -350)
# ════════════════════════════════════════════════════════════════════════════

# Piplup5 — bem visível (<20%)
# Clareira aberta entre Tree B e Tree C, sem cobertura
spawn_piplup(
    name  = "Piplup5",
    loc   = (1900.0, 300.0, 0.0),
    rot   = (0.0, 60.0, 0.0),
    scale = (2.0, 2.0, 2.0)
)

# Piplup6 — oclusão moderada (40–60%)
# Na base de Tree A, com ramos a cobrir metade do modelo
spawn_piplup(
    name  = "Piplup6",
    loc   = (-280.0, 620.0, 5.0),
    rot   = (0.0, 220.0, 0.0),
    scale = (2.0, 2.0, 2.0)
)

# Piplup7 — oclusão forte (60–80%)
# Atrás de Tree B, parcialmente encoberto pelo tronco + sombra
spawn_piplup(
    name  = "Piplup7",
    loc   = (1480.0, -100.0, 5.0),
    rot   = (0.0, 150.0, 0.0),
    scale = (2.0, 2.0, 2.0)
)

unreal.log("=== Adjust complete — verify occlusion visually in viewport ===")
