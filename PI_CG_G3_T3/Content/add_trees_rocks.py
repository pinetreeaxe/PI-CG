"""
Add more trees and rocks to Scenario 2
Run via: Tools > Execute Python Script

Copies meshes from existing actors in the scene (no hardcoded asset paths needed).
Adds 3 more trees and 4 more rocks at varied positions.
"""

import unreal
import random

ELL = unreal.EditorLevelLibrary

# ── Collect existing tree and rock meshes from the scene ─────────────────────
tree_meshes = []
rock_meshes = []

for actor in ELL.get_all_level_actors():
    label = actor.get_actor_label()
    smc = actor.get_component_by_class(unreal.StaticMeshComponent)
    if smc is None:
        continue
    mesh = smc.static_mesh
    if mesh is None:
        continue
    if any(x in label for x in ["ScotsPine", "Pine", "Tree"]):
        tree_meshes.append(mesh)
    elif any(x in label for x in ["Boulder", "Rock", "Stone"]):
        rock_meshes.append(mesh)

if not tree_meshes:
    unreal.log_error("No tree actors found in scene. Check actor labels contain 'Pine' or 'Tree'.")
if not rock_meshes:
    unreal.log_error("No rock actors found in scene. Check actor labels contain 'Boulder' or 'Rock'.")

unreal.log(f"Found {len(tree_meshes)} tree mesh(es) and {len(rock_meshes)} rock mesh(es) to clone from.")

# ── Helper ───────────────────────────────────────────────────────────────────
def spawn_static(mesh, loc, yaw, scale, folder):
    actor = ELL.spawn_actor_from_class(
        unreal.StaticMeshActor,
        unreal.Vector(*loc),
        unreal.Rotator(0.0, yaw, 0.0)
    )
    actor.set_actor_scale3d(unreal.Vector(*scale))
    actor.get_component_by_class(unreal.StaticMeshComponent).set_static_mesh(mesh)
    actor.set_folder_path(folder)
    unreal.log(f"Spawned at {loc} (folder: {folder})")
    return actor

# ════════════════════════════════════════════════════════════════════════════
# NEW TREES  (4–6 total target — adding 3)
# Spread around the scene to increase canopy density and shadow overlap
# ════════════════════════════════════════════════════════════════════════════
new_trees = [
    # (location,              yaw,   scale)
    ((  300.0, -600.0,  0.0),  30.0, (1.1, 1.1, 1.1)),  # front-left open area
    (( -800.0,  200.0,  0.0), 120.0, (1.0, 1.0, 1.0)),  # far left
    (( 1100.0,  900.0,  0.0), 200.0, (1.2, 1.2, 1.2)),  # centre-right
]

if tree_meshes:
    for i, (loc, yaw, scale) in enumerate(new_trees):
        mesh = tree_meshes[i % len(tree_meshes)]
        spawn_static(mesh, loc, yaw, scale, "Trees")

# ════════════════════════════════════════════════════════════════════════════
# NEW ROCKS  (5–8 total target — adding 4)
# Some clustered near trees, some near Piplup positions for occlusion
# ════════════════════════════════════════════════════════════════════════════
new_rocks = [
    # (location,               yaw,   scale)
    (( -350.0,  400.0,   0.0),  45.0, (1.0, 1.0, 1.0)),  # near Tree A / Piplup6
    (( 1600.0, -300.0,   0.0), 100.0, (1.3, 1.3, 1.0)),  # near Tree B / Piplup7
    (( 2000.0,  600.0,   0.0), 200.0, (0.9, 0.9, 0.9)),  # right side cluster
    ((  700.0,  -50.0,   0.0), 310.0, (1.1, 1.1, 1.1)),  # centre scatter
]

if rock_meshes:
    for i, (loc, yaw, scale) in enumerate(new_rocks):
        mesh = rock_meshes[i % len(rock_meshes)]
        spawn_static(mesh, loc, yaw, scale, "Rocks")

unreal.log("=== Trees and rocks added. Verify placement in viewport. ===")
