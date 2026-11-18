"""Construit le catalogue d'assets (lance par l'add-on dans un Blender en arriere-plan).

blender -b --factory-startup -P catalog_build.py -- <dossier parent du paquet> <nom du paquet> <dossier de sortie> <json reglages>
Ecrit <sortie>/batiments_proceduraux.blend (objets marques comme assets, vignettes) et blender_assets.cats.txt."""
import importlib
import json
import math
import os
import sys
import time
import uuid

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
PARENT, PKG, OUT = argv[0], argv[1], argv[2]
CFG = json.loads(argv[3]) if len(argv) > 3 else {}
sys.path.insert(0, PARENT)
pkg = importlib.import_module(PKG)
L = importlib.import_module(PKG + ".layout")
PS = importlib.import_module(PKG + ".presets")
ST = importlib.import_module(PKG + ".styles")
MT = importlib.import_module(PKG + ".materials")
WR = importlib.import_module(PKG + ".wear")
CT = importlib.import_module(PKG + ".catalog")

detail = int(CFG.get('detail', 1))
mat_mode = CFG.get('mat_mode', 'procedural')
kb_dir = CFG.get('kb_dir', "")
seeds = int(CFG.get('seeds', 2))
opts = dict(decals=float(CFG.get('decals', 0.6)))
os.makedirs(OUT, exist_ok=True)
tmp = os.path.join(OUT, "_vignettes")
os.makedirs(tmp, exist_ok=True)

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)
sc = bpy.context.scene
WR.set_amount(float(CFG.get('wear', WR.DEFAULT)))

# rendu des vignettes
sc.render.engine = 'BLENDER_EEVEE'
try:
    sc.eevee.taa_render_samples = 24
except Exception:
    pass
sc.render.resolution_x = sc.render.resolution_y = 256
sc.render.film_transparent = True
sc.render.image_settings.file_format = 'PNG'
sc.render.image_settings.color_mode = 'RGBA'
w = bpy.data.worlds.new("BG_catalogue") if not sc.world else sc.world
sc.world = w
w.use_nodes = True
bgn = w.node_tree.nodes.get('Background')
bgn.inputs[0].default_value = (0.62, 0.68, 0.78, 1)
bgn.inputs[1].default_value = 1.0
sun = bpy.data.objects.new("Soleil", bpy.data.lights.new("Soleil", 'SUN'))
sun.data.energy = 3.2
sun.data.angle = math.radians(3)
sun.rotation_euler = (math.radians(52), 0, math.radians(-38))
sc.collection.objects.link(sun)
cam = bpy.data.objects.new("Vignette", bpy.data.cameras.new("Vignette"))
cam.data.lens = 50
sc.collection.objects.link(cam)
sc.camera = cam

entries = CT.entries(seeds)
cats = {}
for path in sorted(set(e[0] for e in entries)):
    cats[path] = str(uuid.uuid5(uuid.NAMESPACE_URL, "procedural_buildings/" + path))
coll = bpy.data.collections.new("Batiments - catalogue")
sc.collection.children.link(coll)
x = 0.0
t0 = time.time()
for i, (path, label, p) in enumerate(entries):
    p = dict(p)
    p.update(opts=dict(p.get('opts', {}), **opts), detail=detail, party=(False, False), sidewalk=False)
    ob, info = L.create_building(bpy.context, p, mat_mode=mat_mode, kb_dir=kb_dir, collection=coll, name=label)
    for o in coll.objects:
        o.hide_render = o is not ob
    # cadrage 3/4 face
    bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    lo = Vector((min(v.x for v in bb), min(v.y for v in bb), min(v.z for v in bb)))
    hi = Vector((max(v.x for v in bb), max(v.y for v in bb), max(v.z for v in bb)))
    c = (lo + hi) / 2
    r = (hi - lo).length / 2
    d = r / math.tan(cam.data.angle / 2) * 1.02
    dirv = Vector((-0.55, -1.0, 0.42)).normalized()
    cam.location = c + dirv * d
    cam.rotation_euler = (-dirv).to_track_quat('-Z', 'Y').to_euler()
    cam.data.clip_end = d * 4
    png = os.path.join(tmp, "v%03d.png" % i)
    sc.render.filepath = png
    bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(png)
    pv = ob.preview_ensure()
    pv.image_size = tuple(im.size)
    px = [0.0] * (im.size[0] * im.size[1] * 4)
    im.pixels.foreach_get(px)
    pv.image_pixels_float.foreach_set(px)
    bpy.data.images.remove(im)
    ob.asset_mark()
    ob.asset_data.catalog_id = cats[path]
    ob.asset_data.description = info.get('preset') and PS.BY_KEY[info['preset']][2] or next(dd for k, n, dd in ST.STYLES if k == p['style'])
    ob.asset_data.author = "Bâtiments procéduraux"
    for t in (p.get('preset') or p['style'], "%d étages" % info['floors'], "New York"):
        ob.asset_data.tags.new(t, skip_if_exists=True)
    ob.location = (x, 0, 0)
    x += info['W'] + 10
    print("PROGRESS %d %d %s" % (i + 1, len(entries), label), flush=True)
for o in coll.objects:
    o.hide_render = False
bpy.data.objects.remove(cam)
bpy.data.objects.remove(sun)
# catalogues
with open(os.path.join(OUT, "blender_assets.cats.txt"), "w", encoding="utf-8") as f:
    f.write("# Catalogues de Bâtiments procéduraux (généré)\nVERSION 1\n\n")
    for path, cid in cats.items():
        f.write("%s:%s:%s\n" % (cid, path, path.replace("/", "-")))
blend = os.path.join(OUT, CT.BLEND)
# atlas des decalques deja empaquete ; les textures Kitbash3D restent liees (licence : jamais copiees)
bpy.ops.wm.save_as_mainfile(filepath=blend, compress=True)
for fn in os.listdir(tmp):
    try:
        os.remove(os.path.join(tmp, fn))
    except OSError:
        pass
try:
    os.rmdir(tmp)
except OSError:
    pass
print("DONE %d %.0f" % (len(entries), time.time() - t0), flush=True)
