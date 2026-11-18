"""Versions de fond : pour les arriere-plans, chaque batiment devient un volume simplifie (quelques dizaines a
quelques centaines de triangles) qui garde sa silhouette (retraits, mansarde, croupe, edicules, chateau d'eau),
avec des textures cuites depuis le batiment detaille :
  - couleur (couleur de base des materiaux, sans eclairage) ;
  - normales en espace tangent (fenetres en creux, corniches, bandeaux, escaliers de secours en relief) ;
  - occlusion ambiante (R) + rugosite (G) dans une seule image.
Toutes les copies d'un meme batiment partagent le maillage et les images : une ville de fond entiere tient en
quelques dizaines de maillages et d'images."""
import json
import math
import os
import random
import time

import bpy
import bmesh
from mathutils import Vector

from .geom import MeshBuilder
from . import building as BD
from . import layout as LY
from . import materials as MT
from . import presets as PS
from . import styles as ST

X = Vector((1.0, 0.0, 0.0))
Z = Vector((0.0, 0.0, 1.0))
KEY = 'fond'
COLL_LIB = "Fond - bibliotheque"
COLL_CITY = "Fond - ville"

# quartiers : (style ou @preset, poids)
DISTRICTS = {
    'manhattan': [('@setback_spire', 2), ('@modern_slab', 2), ('@limestone_office', 3), ('@pilaster_tower', 2), ('@stone_lunette', 2),
                  ('@hotel_setback', 2), ('@tan_prewar', 2), ('tower', 4), ('prewar', 4), ('modern', 3), ('@tenement', 1), ('walkup', 1),
                  ('@deco_tower', 3), ('@glass_curtain', 2), ('@gothic_tower', 2), ('@garment_loft', 3), ('@terrace_coop', 2),
                  ('@white_brick', 2), ('@cast_iron_loft', 1), ('@old_law', 1)],
    'brooklyn': [('walkup', 5), ('@tenement', 3), ('@corner_mansard', 2), ('@brownstone', 3), ('@brick_rowhouse', 3), ('rowhouse', 2),
                 ('warehouse', 2), ('@arch_warehouse', 1), ('@arched_bank', 1), ('prewar', 1), ('@tan_prewar', 1),
                 ('@old_law', 3), ('@bodega_corner', 2), ('@concrete_loft', 1.5), ('@nycha', 1), ('@white_brick', 0.5), ('@cast_iron_loft', 0.5)],
    'mixte': [('@setback_spire', 1), ('@modern_slab', 1), ('@limestone_office', 1), ('@pilaster_tower', 1), ('@stone_lunette', 1),
              ('@hotel_setback', 1), ('@tan_prewar', 2), ('tower', 2), ('prewar', 3), ('modern', 2), ('walkup', 4), ('@tenement', 2),
              ('@corner_mansard', 1), ('@brownstone', 2), ('@brick_rowhouse', 1), ('warehouse', 2), ('@arch_warehouse', 1), ('@arched_bank', 1),
              ('@old_law', 2), ('@bodega_corner', 1), ('@cast_iron_loft', 1), ('@garment_loft', 1.5), ('@deco_tower', 1), ('@white_brick', 1),
              ('@nycha', 0.5), ('@glass_curtain', 1), ('@terrace_coop', 1), ('@gothic_tower', 0.7), ('@concrete_loft', 1)],
}


# ------------------------------------------------------------------ volume simplifie


def _quad(mb, pts, key=KEY):
    mb.face([Vector(p) for p in pts], key)


def proxy(mass):
    """Volume simplifie a partir des volumes notes par building.build (mb.mass). Renvoie (principal, mats) :
    le principal recoit les textures cuites ; mats : antennes (trop fines pour une texture, materiau metal)."""
    mb, extra = MeshBuilder(), MeshBuilder()
    tiers = [m for m in mass if m[0] == 'tier']
    roofs = [m for m in mass if m[0] in ('mansard', 'hip')]
    for i, (_, rect, z0, z1) in enumerate(tiers):
        x0, y0, x1, y1 = rect
        if z1 - z0 > 1e-3:
            mb.box((x0, y0, z0), (x1, y1, z1), KEY, skip=('-z', '+z'))
        nxt = tiers[i + 1][1] if i + 1 < len(tiers) else None
        if nxt is not None:
            if max(abs(a - b) for a, b in zip(rect, nxt)) > 0.02:
                BD._ring_xy(mb, rect, nxt, z1, KEY)
        elif not roofs:
            _quad(mb, [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)])
    for r in roofs:
        if r[0] == 'mansard':
            _, (x0, y0, x1, y1), z0, h = r
            s = min(1.1, (x1 - x0) * 0.2, (y1 - y0) * 0.2)
            lo = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
            hi = [(x0 + s, y0 + s), (x1 - s, y0 + s), (x1 - s, y1 - s), (x0 + s, y1 - s)]
            for a in range(4):
                b = (a + 1) % 4
                _quad(mb, [(*lo[a], z0), (*lo[b], z0), (*hi[b], z0 + h), (*hi[a], z0 + h)])
            _quad(mb, [(*p, z0 + h) for p in hi])
        else:
            _, rect, z0, ztop = r
            x0, y0, x1, y1 = rect
            e = 0.45
            X0, Y0, X1, Y1 = x0 - e, y0 - e, x1 + e, y1 + e
            W, D = X1 - X0, Y1 - Y0
            A, B, C, Dd = (X0, Y0, z0), (X1, Y0, z0), (X1, Y1, z0), (X0, Y1, z0)
            if W >= D:
                r0, r1 = (X0 + D / 2, (Y0 + Y1) / 2, ztop), (X1 - D / 2, (Y0 + Y1) / 2, ztop)
                _quad(mb, [A, B, r1, r0]); _quad(mb, [C, Dd, r0, r1]); _quad(mb, [B, C, r1]); _quad(mb, [Dd, A, r0])
            else:
                r0, r1 = ((X0 + X1) / 2, Y0 + W / 2, ztop), ((X0 + X1) / 2, Y1 - W / 2, ztop)
                _quad(mb, [B, C, r1, r0]); _quad(mb, [Dd, A, r0, r1]); _quad(mb, [A, B, r0]); _quad(mb, [C, Dd, r1])
            # sous-face du debord (vers le bas)
            O = [(X0, Y0, z0), (X1, Y0, z0), (X1, Y1, z0), (X0, Y1, z0)]
            I = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)]
            for a in range(4):
                b = (a + 1) % 4
                _quad(mb, [O[a], I[a], I[b], O[b]])
    for m in mass:
        if m[0] == 'box':
            _, (x0, y0, x1, y1), z0, z1 = m
            mb.box((x0, y0, z0), (x1, y1, z1), KEY, skip=('-z',))
        elif m[0] == 'tower':
            _, x, y, z, r, leg, tank = m
            for a in range(4):
                ang = math.pi / 4 + a * math.pi / 2
                px, py = x + math.cos(ang) * r * 0.75, y + math.sin(ang) * r * 0.75
                mb.box((px - 0.13, py - 0.13, z), (px + 0.13, py + 0.13, z + leg), KEY, skip=('-z', '+z'))
            zt = z + leg
            mb.cylinder((x, y), r + 0.1, zt, zt + 0.15 + tank, KEY, n=8, cap_top=False, cap_bot=True)
            mb.cone((x, y), r + 0.12, zt + 0.15 + tank, zt + 0.15 + tank + r * 0.6, KEY, n=8)
        elif m[0] == 'mast':
            _, x, y, z0, z1 = m
            extra.box((x - 0.07, y - 0.07, z0), (x + 0.07, y + 0.07, z1), 'metal_grey', skip=('-z',))
    return mb, extra


# ------------------------------------------------------------------ depliage UV (une ile par face, rangement en etageres)


def _face_frame(pts):
    n = Vector()
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        n += Vector(((a.y - b.y) * (a.z + b.z), (a.z - b.z) * (a.x + b.x), (a.x - b.x) * (a.y + b.y)))
    n.normalize()
    u = X.copy() if abs(n.z) > 0.985 else Z.cross(n).normalized()
    return u, n.cross(u)


def unwrap(mb, res, pad_px=4.0):
    """UV de chaque face projetee dans son plan (sans etirement, en metres), puis rangement « skyline » dans le carre
    unite avec la plus grande echelle commune possible (meme densite de pixels partout). Renvoie les px / m obtenus."""
    isl = []
    for fi, f in enumerate(mb.faces):
        pts = [Vector(mb.verts[i]) for i in f]
        u, v = _face_frame(pts)
        q = [(p.dot(u), p.dot(v)) for p in pts]
        mu, mv = min(a for a, _ in q), min(b for _, b in q)
        q = [(a - mu, b - mv) for a, b in q]
        w, h = max(a for a, _ in q), max(b for _, b in q)
        if h > w:                      # couchee (rotation d'un quart de tour : l'espace tangent la suit)
            q = [(h - b, a) for a, b in q]
            w, h = h, w
        isl.append([fi, q, w, h])
    pad = pad_px / res

    def place(s):
        return _skyline([(w * s, h * s) for _fi, _q, w, h in isl], pad)
    lo, hi = 0.0, 1.0
    while place(hi) is not None:
        hi *= 2.0
    for _ in range(24):
        mid = (lo + hi) / 2
        if place(mid) is None:
            hi = mid
        else:
            lo = mid
    pos = place(lo)
    for k, (fi, q, w, h) in enumerate(isl):
        ox, oy, rot = pos[k]
        if rot:
            q = [(h - b, a) for a, b in q]
        mb.uvs[fi] = [(ox + a * lo, oy + b * lo) for a, b in q]
    return lo * res


def _skyline(sizes, pad):
    """Rangement « skyline » (en bas a gauche d'abord, quart de tour permis) de rectangles (w, h) dans le carre
    unite, chacun entoure d'une marge pad. Renvoie [(x, y, tourne)] ou None si ca ne rentre pas."""
    order = sorted(range(len(sizes)), key=lambda k: -max(sizes[k]))
    sky = [(0.0, 0.0, 1.0)]                    # segments (x, hauteur, largeur), tries par x
    out = [None] * len(sizes)
    eps = 1e-9
    for k in order:
        best = None
        for rot in (False, True):
            w, h = sizes[k][::-1] if rot else sizes[k]
            w += 2 * pad
            h += 2 * pad
            for i in range(len(sky)):
                x = sky[i][0]
                if x + w > 1.0 + eps:
                    break
                y, j, rem = 0.0, i, w
                while rem > eps and j < len(sky):
                    y = max(y, sky[j][1])
                    rem -= sky[j][2]
                    j += 1
                if rem > eps or y + h > 1.0 + eps:
                    continue
                score = (y + h, x)
                if best is None or score < best[0]:
                    best = (score, x, y, w, h, rot)
        if best is None:
            return None
        _sc, x, y, w, h, rot = best
        out[k] = (x + pad, y + pad, rot)
        rest = [(x, y + h, w)]
        for sx, sy, sw in sky:
            if sx + sw <= x + eps or sx >= x + w - eps:
                rest.append((sx, sy, sw))
                continue
            if sx < x:
                rest.append((sx, sy, x - sx))
            if sx + sw > x + w:
                rest.append((x + w, sy, sx + sw - x - w))
        rest.sort()
        sky = []
        for s in rest:
            if sky and abs(sky[-1][1] - s[1]) < eps and abs(sky[-1][0] + sky[-1][2] - s[0]) < 1e-7:
                sky[-1] = (sky[-1][0], sky[-1][1], sky[-1][2] + s[2])
            else:
                sky.append(s)
    return out


def area(mb):
    tot = 0.0
    for f in mb.faces:
        pts = [Vector(mb.verts[i]) for i in f]
        for i in range(1, len(pts) - 1):
            tot += (pts[i] - pts[0]).cross(pts[i + 1] - pts[0]).length / 2
    return tot


def pick_res(a, density, max_res, min_res=256):
    """Resolution (puissance de 2) pour une densite cible en pixels par metre (rangement ~75 % efficace)."""
    want = math.sqrt(a / 0.75) * density
    r = min_res
    while r < want * 0.7 and r < max_res:
        r *= 2
    return int(r)


# ------------------------------------------------------------------ cuisson


def _cycles_device(scene):
    """GPU si l'utilisateur en a active un dans les preferences de Cycles, sinon CPU."""
    try:
        cp = bpy.context.preferences.addons['cycles'].preferences
        if cp.compute_device_type != 'NONE':
            cp.get_devices()
            if any(d.use and d.type != 'CPU' for d in cp.devices):
                scene.cycles.device = 'GPU'
                return 'GPU'
    except Exception:
        pass
    scene.cycles.device = 'CPU'
    return 'CPU'


def _image(name, res, color, data=False):
    im = bpy.data.images.get(name)
    if im is not None and (im.size[0] != res or im.size[1] != res):
        bpy.data.images.remove(im)
        im = None
    if im is None:
        im = bpy.data.images.new(name, res, res, alpha=False, float_buffer=False)
    im.generated_color = color
    im.colorspace_settings.name = 'Non-Color' if data else 'sRGB'
    return im


def _bake_material(name):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    bs = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(bs.outputs[0], out.inputs['Surface'])
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.name = "BGF_cible"
    nt.nodes.active = tex
    return m, tex


def _final_material(name, col, nrm, orm, ao=0.85):
    m = bpy.data.materials.get(name)
    if m is not None:
        bpy.data.materials.remove(m)
    m, nt, bsdf = MT._new(name)
    m["bg_fond"] = True

    def tex(im, x, y):
        n = MT._n(nt, 'ShaderNodeTexImage', x, y)
        n.image = im
        n.interpolation = 'Cubic' if im is nrm else 'Linear'
        return n
    tc = tex(col, -900, 300)
    tn = tex(nrm, -900, -350)
    to = tex(orm, -900, -50)
    sep = MT._n(nt, 'ShaderNodeSeparateColor', -600, -50)
    nt.links.new(to.outputs['Color'], sep.inputs[0])
    mix, A, B, F, R = MT._mix(nt, -350, 300, 'MULTIPLY', ao)
    mix.label = "occlusion ambiante"
    mix.name = "BGF_ao"
    nt.links.new(tc.outputs['Color'], A)
    nt.links.new(sep.outputs['Red'], B)
    col_s = MT._rand_tint(nt, R, x=150, y=300, hue=0.012, val=0.08, sat=0.06)
    nt.links.new(col_s, bsdf.inputs['Base Color'])
    nt.links.new(sep.outputs['Green'], bsdf.inputs['Roughness'])
    nm = MT._n(nt, 'ShaderNodeNormalMap', -350, -350)
    nm.uv_map = "UVMap"
    nt.links.new(tn.outputs['Color'], nm.inputs['Color'])
    nt.links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
    m.diffuse_color = (0.3, 0.25, 0.22, 1)
    return m


def _set_vis(ob, on):
    for a in ('visible_camera', 'visible_diffuse', 'visible_glossy', 'visible_transmission', 'visible_volume_scatter', 'visible_shadow'):
        try:
            setattr(ob, a, on)
        except AttributeError:
            pass


def bake(context, params, mat_mode='procedural', kb_dir="", density=12.0, max_res=2048, detail=2, out_dir=None,
         samples=8, ao_samples=32, name=None, collection=None, keep_high=False, log=print):
    """Construit le batiment detaille, son volume simplifie, cuit les textures et renvoie l'objet de fond."""
    t0 = time.perf_counter()
    scene = context.scene
    p = dict(params)
    p.update(party=(False, False), sidewalk=False, yard=False, detail=detail)
    nm = name or "Fond_%s_%03d" % (LY.label(p), p['seed'])
    # 1. detaille (meme tirage que build_mesh) + volumes notes
    rng = LY._rng(p)
    plan = LY._plan(p, rng)
    mb_hi, info = BD.build(plan, rng, detail=detail, party=(False, False), sidewalk=False, yard=0.0, rng2=LY._rng2(p))
    mb_hi.drop({'decal'})          # decalques transparents : non cuits (la cuisson ne gere pas leur transparence)
    me_hi = mb_hi.to_mesh(nm + "_detail", lambda k: MT.get(k, mat_mode, kb_dir))
    hi = bpy.data.objects.new(nm + "_detail", me_hi)
    tris_hi = sum(len(f.vertices) - 2 for f in me_hi.polygons)
    # 2. volume simplifie + UV
    mb_lo, extra = proxy(mb_hi.mass)
    res = pick_res(area(mb_lo), density, max_res)
    px_m = unwrap(mb_lo, res)
    # resolution ajustee sur la densite obtenue apres rangement
    while px_m < density * 0.8 and res < max_res:
        res *= 2
        px_m = unwrap(mb_lo, res)
    while px_m > density * 1.7 and res > 256:
        res //= 2
        px_m = unwrap(mb_lo, res)
    me_bake = mb_lo.to_mesh(nm + "_cuisson", lambda k: None, merge=False)
    bmat, tex = _bake_material("BGF_cuisson")
    me_bake.materials.clear()
    me_bake.materials.append(bmat)
    lo = bpy.data.objects.new(nm + "_cuisson", me_bake)
    tmp = bpy.data.collections.new("BGF_tmp")
    scene.collection.children.link(tmp)
    tmp.objects.link(hi)
    tmp.objects.link(lo)
    _set_vis(lo, False)            # le volume ne doit pas masquer le detaille (occlusion ambiante)
    # 3. cuisson
    old_engine = scene.render.engine
    old_samples = scene.cycles.samples if hasattr(scene, 'cycles') else None
    scene.render.engine = 'CYCLES'
    dev = _cycles_device(scene)
    vl = context.view_layer
    vl.update()
    sel = [o for o in vl.objects if o is not None and o.select_get()]
    act = vl.objects.active
    for o in sel:
        o.select_set(False)
    hi.select_set(True)
    lo.select_set(True)
    vl.objects.active = lo
    ext, ray = 1.6, 3.4
    im_col = _image(nm + "_couleur", res, (0.3, 0.25, 0.22, 1))
    im_nrm = _image(nm + "_normales", res, (0.5, 0.5, 1.0, 1), data=True)
    im_ao = _image(nm + "_ao_tmp", res, (1, 1, 1, 1), data=True)
    im_rg = _image(nm + "_rugo_tmp", res, (0.8, 0.8, 0.8, 1), data=True)
    world = scene.world
    old_dist = world.light_settings.distance if world else None
    try:
        if world:
            world.light_settings.distance = 4.0
        jobs = [(im_col, 'DIFFUSE', {'COLOR'}, samples), (im_nrm, 'NORMAL', set(), samples),
                (im_rg, 'ROUGHNESS', set(), samples), (im_ao, 'AO', set(), ao_samples)]
        for im, typ, pf, spp in jobs:
            tex.image = im
            bmat.node_tree.nodes.active = tex
            scene.cycles.samples = spp
            kw = dict(type=typ, use_selected_to_active=True, cage_extrusion=ext, max_ray_distance=ray, margin=max(2, res // 256),
                      margin_type='EXTEND', target='IMAGE_TEXTURES', use_clear=True)
            if typ == 'DIFFUSE':
                kw['pass_filter'] = pf
            if typ == 'NORMAL':
                kw.update(normal_space='TANGENT')
            bpy.ops.object.bake(**kw)
    finally:
        if world and old_dist is not None:
            world.light_settings.distance = old_dist
        scene.render.engine = old_engine
        if old_samples is not None:
            scene.cycles.samples = old_samples
    # occlusion (R) + rugosite (G) dans une image
    import numpy as np
    n = res * res * 4
    a = np.empty(n, dtype=np.float32); r = np.empty(n, dtype=np.float32)
    im_ao.pixels.foreach_get(a); im_rg.pixels.foreach_get(r)
    o = np.ones(n, dtype=np.float32)
    o[0::4] = a[0::4]; o[1::4] = r[0::4]; o[2::4] = 0.0
    im_orm = _image(nm + "_ao_rugo", res, (1, 0.8, 0, 1), data=True)
    im_orm.pixels.foreach_set(o)
    im_orm.update()
    bpy.data.images.remove(im_ao); bpy.data.images.remove(im_rg)
    # 4. enregistrement des images (ou empaquetage si le fichier n'est pas enregistre)
    for im in (im_col, im_nrm, im_orm):
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
            path = os.path.join(out_dir, im.name + ".png")
            im.filepath_raw = path
            im.file_format = 'PNG'
            im.save()
            try:
                rel = bpy.path.relpath(path)
                im.filepath = rel
            except ValueError:
                im.filepath = path
        else:
            im.pack()
    # 5. objet final : volume (avec ses UV) + antennes, sommets soudes
    fin = MeshBuilder()
    fin.append(mb_lo)
    fin.append(extra)
    mat = _final_material("BGF_" + nm, im_col, im_nrm, im_orm)
    me = fin.to_mesh(nm, lambda k: mat if k == KEY else MT.get(k, mat_mode, kb_dir), merge=True)
    old = bpy.data.objects.get(nm)
    if old is not None and old.type == 'MESH' and old.get("bg_fond_params"):
        old_me = old.data
        old.data = me
        if old_me.users == 0:
            bpy.data.meshes.remove(old_me)
        ob = old
    else:
        ob = bpy.data.objects.new(nm, me)
        (collection or LY._collection(context, COLL_LIB)).objects.link(ob)
    tris = sum(len(f.vertices) - 2 for f in me.polygons)
    finfo = dict(W=plan['W'], D=plan['D'], height=info['height'], floors=info['floors'], style=p['style'], preset=p.get('preset') or "",
                 tris=tris, tris_detail=tris_hi, res=res, px_m=round(px_m, 1), device=dev)
    ob["bg_fond_params"] = json.dumps(p)
    ob["bg_fond_info"] = json.dumps(finfo)
    # nettoyage
    for o2 in (hi, lo):
        bpy.data.objects.remove(o2)
    if not keep_high:
        bpy.data.meshes.remove(me_hi)
    bpy.data.meshes.remove(me_bake)
    bpy.data.collections.remove(tmp)
    vl.update()
    for o in sel:
        if o.name in vl.objects:
            o.select_set(True)
    if act and act.name in vl.objects:
        vl.objects.active = act
    finfo['time'] = time.perf_counter() - t0
    log("  %-32s %5d -> %4d tris, %4d px (%.1f px/m), %.1f s" % (nm, tris_hi, tris, res, px_m, finfo['time']))
    return ob, finfo


# ------------------------------------------------------------------ bibliotheque et ville


def _spec(rng, entry, opts=None):
    p = dict(style=entry, seed=rng.randrange(1, 10 ** 6), opts=dict(opts or {}), detail=2)
    if entry.startswith('@'):
        p['preset'] = entry[1:]
        p['style'] = PS.BY_KEY[entry[1:]][3]
    return p


def library(context, district='mixte', count=24, seed=1, mat_mode='procedural', kb_dir="", density=12.0, max_res=2048,
            out_dir=None, opts=None, log=print, progress=None):
    """count batiments de fond tires dans un quartier (chaque archetype au moins une fois si possible)."""
    rng = random.Random(seed * 104729 + 17)
    mix = DISTRICTS.get(district, DISTRICTS['mixte'])
    entries = [e for e, _w in mix]
    picks = list(entries[:count]) if count >= len(entries) else []
    while len(picks) < count:
        picks.append(ST.pick(rng, entries, [w for _e, w in mix]))
    rng.shuffle(picks)
    coll = LY._collection(context, COLL_LIB)
    obs = []
    x = 0.0
    for i, e in enumerate(picks):
        p = _spec(rng, e, opts)
        ob, fi = bake(context, p, mat_mode, kb_dir, density, max_res, out_dir=out_dir, collection=coll, log=log)
        ob.location = (x, -60.0, 0.0)
        x += fi['W'] + 6.0
        obs.append(ob)
        if progress:
            progress(i + 1, count)
    return obs


def library_objects(context):
    c = bpy.data.collections.get(COLL_LIB)
    return [o for o in (c.objects if c else []) if o.get("bg_fond_info")]


def city(context, lib, blocks_x=4, blocks_y=3, seed=1, block_l=160.0, block_d=64.0, street_w=18.0, avenue_w=30.0, walk_w=4.0,
         skyline=0.6, origin=(0, 0, 0), ground=True, mat_mode='procedural', kb_dir=""):
    """Quadrillage de blocs bordes de batiments de fond (copies liees : maillage et images partages).
    Blocs le long de x (rues entre les rangees), avenues entre les colonnes. skyline : tours plutot au centre."""
    if not lib:
        return []
    rng = random.Random(seed * 7907 + 3)
    coll = LY._collection(context, COLL_CITY)
    O = Vector(origin)
    info = [(o, json.loads(o["bg_fond_info"])) for o in lib]
    hmax = max(i['height'] for _o, i in info) or 1.0
    pitch_x = block_l + 2 * walk_w + avenue_w
    pitch_y = block_d + 2 * walk_w + street_w
    cx, cy = (blocks_x - 1) / 2.0, (blocks_y - 1) / 2.0
    rmax = math.hypot(cx, cy) or 1.0
    obs = []
    count = {}

    def weight(i, c):
        t = min(1.0, i['height'] / max(60.0, hmax))
        return max(0.03, 1.0 + skyline * (2.0 * c - 1.0) * 2.5 * t)

    def put(src, x, y, rot):
        ob = bpy.data.objects.new("%s.%03d" % (src.name, count.setdefault(src.name, 0)), src.data)
        count[src.name] += 1
        ob.location = O + Vector((x, y, 0.0))
        ob.rotation_euler = (0.0, 0.0, rot)
        ob["bg_fond_src"] = src.name
        coll.objects.link(ob)
        obs.append(ob)
    for bx in range(blocks_x):
        for by in range(blocks_y):
            c = 1.0 - math.hypot(bx - cx, by - cy) / rmax
            X0 = bx * pitch_x + walk_w
            Y0 = by * pitch_y + walk_w
            ws = [weight(i, c) for _o, i in info]
            cur = {'S': 0.0, 'N': 0.0}
            guard = 0
            while guard < 200:
                guard += 1
                side = 'S' if cur['S'] <= cur['N'] else 'N'
                k = ST.pick(rng, list(range(len(info))), ws)
                src, i = info[k]
                W, D = i['W'], i['D']
                deep = D > block_d / 2 - 1.0
                x = max(cur['S'], cur['N']) if deep else cur[side]
                if D > block_d + 1.0 or x + W > block_l + 0.01:
                    # rien ne rentre ici : on essaie un plus petit, sinon le cote est fini
                    fits = [j for j, (_o, ii) in enumerate(info) if ii['W'] <= block_l - x + 0.01 and ii['D'] <= block_d / 2 - 1.0]
                    if not fits:
                        cur[side] = block_l + 1
                        if min(cur.values()) > block_l:
                            break
                        continue
                    k = ST.pick(rng, fits, [ws[j] for j in fits])
                    src, i = info[k]
                    W, D = i['W'], i['D']
                    deep = False
                    x = cur[side]
                if deep:
                    # traverse le bloc : facade au sud ou au nord au hasard
                    if rng.random() < 0.5:
                        put(src, X0 + x, Y0, 0.0)
                    else:
                        put(src, X0 + x + W, Y0 + block_d, math.pi)
                    cur['S'] = cur['N'] = x + W
                elif side == 'S':
                    put(src, X0 + x, Y0, 0.0)
                    cur['S'] = x + W
                else:
                    put(src, X0 + x + W, Y0 + block_d, math.pi)
                    cur['N'] = x + W
                if min(cur.values()) > block_l - 3.0:
                    break
    if ground:
        mb = MeshBuilder()
        tot_x = blocks_x * pitch_x - avenue_w
        tot_y = blocks_y * pitch_y - street_w
        mb.face([Vector((-avenue_w / 2, -street_w / 2, -0.02)), Vector((tot_x + avenue_w / 2, -street_w / 2, -0.02)),
                 Vector((tot_x + avenue_w / 2, tot_y + street_w / 2, -0.02)), Vector((-avenue_w / 2, tot_y + street_w / 2, -0.02))], 'asphalt')
        for bx in range(blocks_x):
            for by in range(blocks_y):
                x0, y0 = bx * pitch_x, by * pitch_y
                mb.box((x0, y0, -0.02), (x0 + block_l + 2 * walk_w, y0 + block_d + 2 * walk_w, 0.15), 'sidewalk', skip=('-z',))
        me = mb.to_mesh("Fond_sol", lambda k: MT.get(k, mat_mode, kb_dir))
        g = bpy.data.objects.new("Fond_sol_%d" % seed, me)
        g.location = O
        coll.objects.link(g)
        obs.append(g)
    return obs
