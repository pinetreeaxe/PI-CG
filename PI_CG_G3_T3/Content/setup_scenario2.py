"""
Scenario 2 - "Medium" Setup Script
Run this in Unreal Engine: Tools > Execute Python Script

Requires:
- A Static Mesh asset named "Piplup" already in the Content Browser
- The existing Piplup folder in the Outliner (Piplup, Piplup2, Piplup3, Piplup4 already placed)

This script adds Piplup5, Piplup6, Piplup7 with the correct transforms
for Scenario 2 occlusion distribution.
"""

import unreal

ELL = unreal.EditorLevelLibrary
EAL = unreal.EditorAssetLibrary

# ── Asset paths ─────────────────────────────────────────────────────────────
# Adjust this path to match where your Piplup mesh lives in the Content Browser
PIPLUP_MESH_PATH = "/Game/Piplup/Piplup"

# ── Helper ───────────────────────────────────────────────────────────────────
def spawn_piplup(name, loc, rot, scale=(2.0, 2.0, 2.0)):
    """Spawn a StaticMeshActor with the Piplup mesh."""
    mesh_asset = unreal.load_asset(PIPLUP_MESH_PATH)
    if mesh_asset is None:
        unreal.log_error(f"Could not load mesh at '{PIPLUP_MESH_PATH}'. "
                         "Update PIPLUP_MESH_PATH in the script.")
        return None

    location  = unreal.Vector(*loc)
    rotation  = unreal.Rotator(*rot)   # (pitch, yaw, roll)
    transform = unreal.Transform(location, rotation, unreal.Vector(*scale))

    actor = ELL.spawn_actor_from_class(
        unreal.StaticMeshActor,
        location,
        rotation
    )
    actor.set_actor_label(name)
    actor.set_actor_scale3d(unreal.Vector(*scale))

    smc = actor.get_component_by_class(unreal.StaticMeshComponent)
    smc.set_static_mesh(mesh_asset)

    unreal.log(f"Spawned {name} at {loc}")
    return actor


# ── Move actor into the Piplup folder in the Outliner ────────────────────────
def move_to_folder(actor, folder="Piplup"):
    actor.set_folder_path(folder)


# ════════════════════════════════════════════════════════════════════════════
# NEW INSTANCES
# ════════════════════════════════════════════════════════════════════════════

# Piplup5 — bem visível (<20% oclusão)
# Zona aberta de areia, sem obstáculos à frente
# Rotation: (pitch, yaw, roll)
p5 = spawn_piplup(
    name  = "Piplup5",
    loc   = (800.0, 600.0, 0.0),
    rot   = (0.0, 45.0, 0.0),
    scale = (2.0, 2.0, 2.0)
)

# Piplup6 — oclusão moderada (40–60%)
# Semi-escondido atrás de arbusto / base de árvore
p6 = spawn_piplup(
    name  = "Piplup6",
    loc   = (-200.0, 1200.0, 5.0),
    rot   = (0.0, 200.0, 0.0),
    scale = (2.0, 2.0, 2.0)
)

# Piplup7 — oclusão forte (60–80%)
# Entre rochas empilhadas com folhagem por cima
p7 = spawn_piplup(
    name  = "Piplup7",
    loc   = (1500.0, -800.0, 20.0),
    rot   = (0.0, 315.0, 0.0),
    scale = (2.0, 2.0, 2.0)
)

# Move all to the Piplup outliner folder
for actor in [p5, p6, p7]:
    if actor:
        move_to_folder(actor, "Piplup")

# ════════════════════════════════════════════════════════════════════════════
# SUMMARY CHECK
# ════════════════════════════════════════════════════════════════════════════
unreal.log("=== Scenario 2 additions complete ===")
unreal.log("Piplup5  — well visible    (<20%)  at (800,  600,  0)")
unreal.log("Piplup6  — moderate occl.  (40-60%) at (-200, 1200, 5)")
unreal.log("Piplup7  — strong occl.    (60-80%) at (1500, -800, 20)")
unreal.log("")
unreal.log("Expected final distribution (7 instances):")
unreal.log("  Well visible  (<20%):  Piplup2, Piplup5          → 2 instances ✓")
unreal.log("  Moderate (40-60%):     Piplup4, Piplup6          → 2 instances ✓")
unreal.log("  Strong   (60-80%):     Piplup, Piplup3, Piplup7  → 3 instances ✓")
unreal.log("")
unreal.log("⚠  Adjust positions manually if trees/rocks don't overlap as expected.")
unreal.log("⚠  If PIPLUP_MESH_PATH is wrong, update line 16 and re-run.")
