"""
preparar_dataset.py
-------------------
Corre este script UMA VEZ depois de teres todas as imagens e labels geradas.
Faz:
  1. Cria classes.txt e dataset.yaml
  2. Divide imagens + labels em train (80%) e val (20%) aleatoriamente
  3. Mostra resumo final

Como correr (fora do UE5, no terminal normal):
    python preparar_dataset.py
"""

import os
import shutil
import random
import glob

# ─── CONFIGURAÇÃO ─────────────────────────────────────────────
BASE_DIR   = r"C:\Users\Filipa Rebelo\OneDrive - Cachapuz - Bilanciai Group\Ambiente de Trabalho\PI-CG\Dataset\Synthetic"
CENARIO    = "Cenario_01"
RATIO_VAL  = 0.20        # 20% para validação, 80% para treino
SEED       = 42
CLASSES    = ["Piplup"]  # adiciona mais classes aqui se necessário
# ──────────────────────────────────────────────────────────────

SRC_IMAGES = os.path.join(BASE_DIR, CENARIO, "images")
SRC_LABELS = os.path.join(BASE_DIR, CENARIO, "labels")

TRAIN_IMAGES = os.path.join(BASE_DIR, "train", "images")
TRAIN_LABELS = os.path.join(BASE_DIR, "train", "labels")
VAL_IMAGES   = os.path.join(BASE_DIR, "val",   "images")
VAL_LABELS   = os.path.join(BASE_DIR, "val",   "labels")

for d in [TRAIN_IMAGES, TRAIN_LABELS, VAL_IMAGES, VAL_LABELS]:
    os.makedirs(d, exist_ok=True)


# ── 1. classes.txt ────────────────────────────────────────────
classes_path = os.path.join(BASE_DIR, "classes.txt")
with open(classes_path, "w") as f:
    f.write("\n".join(CLASSES) + "\n")
print(f"[OK] classes.txt  →  {classes_path}")


# ── 2. dataset.yaml (formato YOLOv8) ─────────────────────────
yaml_path = os.path.join(BASE_DIR, "dataset.yaml")
yaml_content = f"""# Dataset YOLOv8 — Piplup Sintético
path: {BASE_DIR}
train: train/images
val:   val/images

nc: {len(CLASSES)}
names: {CLASSES}
"""
with open(yaml_path, "w") as f:
    f.write(yaml_content)
print(f"[OK] dataset.yaml  →  {yaml_path}")


# ── 3. Split train / val ──────────────────────────────────────
imagens = sorted(glob.glob(os.path.join(SRC_IMAGES, "*.png")))

if not imagens:
    print(f"\n[AVISO] Nenhuma imagem encontrada em:\n  {SRC_IMAGES}")
    print("Corre primeiro o script orbitar_piplups.py no UE5.")
    exit(0)

random.seed(SEED)
random.shuffle(imagens)

n_val   = max(1, int(len(imagens) * RATIO_VAL))
val_set = set(imagens[:n_val])

copiados_train = 0
copiados_val   = 0
sem_label      = 0

for img_path in imagens:
    fname     = os.path.splitext(os.path.basename(img_path))[0]
    lbl_path  = os.path.join(SRC_LABELS, fname + ".txt")

    if img_path in val_set:
        dst_img = os.path.join(VAL_IMAGES, os.path.basename(img_path))
        dst_lbl = os.path.join(VAL_LABELS, fname + ".txt")
        copiados_val += 1
    else:
        dst_img = os.path.join(TRAIN_IMAGES, os.path.basename(img_path))
        dst_lbl = os.path.join(TRAIN_LABELS, fname + ".txt")
        copiados_train += 1

    shutil.copy2(img_path, dst_img)

    if os.path.exists(lbl_path):
        shutil.copy2(lbl_path, dst_lbl)
    else:
        sem_label += 1
        # Cria label vazio (imagem sem objeto visível)
        open(dst_lbl, "w").close()


# ── 4. Resumo ─────────────────────────────────────────────────
print(f"""
─── Resumo ───────────────────────────────
  Total imagens  : {len(imagens)}
  Train          : {copiados_train}  ({100-int(RATIO_VAL*100)}%)
  Val            : {copiados_val}   ({int(RATIO_VAL*100)}%)
  Sem label      : {sem_label}  (labels vazios criados)

  Estrutura final:
    {BASE_DIR}
    ├── train/
    │   ├── images/   ({copiados_train} ficheiros)
    │   └── labels/   ({copiados_train} ficheiros)
    ├── val/
    │   ├── images/   ({copiados_val} ficheiros)
    │   └── labels/   ({copiados_val} ficheiros)
    ├── classes.txt
    └── dataset.yaml
──────────────────────────────────────────
Pronto para treinar com YOLOv8:
  yolo detect train data=dataset.yaml model=yolov8n.pt epochs=50
""")
