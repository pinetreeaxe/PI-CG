"""
Cria uma pasta "roboflow_upload" com tudo junto:
imagens .png + anotacoes .txt + classes.txt
"""
import os, shutil, glob

BASE     = r"C:\Users\Filipa Rebelo\OneDrive - Cachapuz - Bilanciai Group\Ambiente de Trabalho\PI-CG\Dataset\Synthetic"
IMAGES   = os.path.join(BASE, "Cenario_01", "images")
LABELS   = os.path.join(BASE, "Cenario_01", "labels")
CLASSES  = os.path.join(BASE, "classes.txt")
DESTINO  = os.path.join(BASE, "roboflow_upload")

os.makedirs(DESTINO, exist_ok=True)

copiados = 0
for f in glob.glob(os.path.join(IMAGES, "*.png")):
    shutil.copy2(f, DESTINO)
    copiados += 1

for f in glob.glob(os.path.join(LABELS, "*.txt")):
    shutil.copy2(f, DESTINO)

shutil.copy2(CLASSES, DESTINO)

print(f"Pronto! {copiados} imagens + {copiados} labels + classes.txt")
print(f"Pasta: {DESTINO}")
