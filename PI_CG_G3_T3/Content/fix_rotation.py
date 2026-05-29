"""
Fix rotation of Piplup5, Piplup6, Piplup7
Run via: Tools > Execute Python Script

Matches rotation style of Piplup2 (pitch=0, yaw=X, roll=0) — stands upright.
Only the yaw (facing direction) varies between instances.
"""

import unreal

ELL = unreal.EditorLevelLibrary

# Target rotations: (pitch, yaw, roll)
# Piplup2 reference: pitch=0, yaw=90, roll=0 → stands upright facing a direction
ROTATIONS = {
    "Piplup5": (0.0,  60.0, 0.0),   # bem visível, virado ligeiramente
    "Piplup6": (0.0, 220.0, 0.0),   # oclusão moderada
    "Piplup7": (0.0, 150.0, 0.0),   # oclusão forte
}

for actor in ELL.get_all_level_actors():
    label = actor.get_actor_label()
    if label in ROTATIONS:
        p, y, r = ROTATIONS[label]
        actor.set_actor_rotation(unreal.Rotator(p, y, r), False)
        unreal.log(f"Fixed rotation of {label} → pitch={p}, yaw={y}, roll={r}")

unreal.log("=== Rotations fixed ===")
