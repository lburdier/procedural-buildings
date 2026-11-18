"""Construit le paquet d'extension procedural_buildings-X.Y.Z.zip (fichiers de l'extension a la racine du zip).

python tools/build_zip.py [dossier_sortie]   (depuis la racine du depot)"""
import os
import sys
import tomllib
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEEP_EXT = (".py", ".toml")
KEEP_FILES = ("LICENSE",)

with open(os.path.join(ROOT, "blender_manifest.toml"), "rb") as f:
    man = tomllib.load(f)
out_dir = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "dist"))
os.makedirs(out_dir, exist_ok=True)
out = os.path.join(out_dir, "%s-%s.zip" % (man["id"], man["version"]))
files = sorted(n for n in os.listdir(ROOT) if os.path.isfile(os.path.join(ROOT, n)) and (n.endswith(KEEP_EXT) or n in KEEP_FILES))
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for n in files:
        z.write(os.path.join(ROOT, n), n)
print(out, len(files), "fichiers")
