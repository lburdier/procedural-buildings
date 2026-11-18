"""Mise en scene : un batiment, une grille de variantes, une rue (rangees mitoyennes + trottoirs + chaussee).

Chaque objet garde ses parametres (propriete bg_params, JSON) : on peut le regenerer, changer sa graine ou son
style sans le deplacer."""
import json
import math
import random
import time
import bpy
from mathutils import Vector, Matrix

from . import styles as ST
from . import presets as PS
from . import building as BD
from . import materials as MT
from .geom import MeshBuilder

COLL = "Batiments proceduraux"

# composition d'une rue : (style, poids)
STREET_MIX = {
    'brooklyn': [('walkup', 6), ('rowhouse', 3), ('warehouse', 2), ('prewar', 2), ('modern', 0.5), ('tower', 0.3)],
    'residentiel': [('rowhouse', 6), ('walkup', 4), ('prewar', 1)],
    'industriel': [('warehouse', 6), ('walkup', 2), ('modern', 1)],
    'centre': [('prewar', 4), ('tower', 3), ('modern', 2), ('walkup', 1)],
    # '@cle' : un preset
    'catalogue': [('@tenement', 3), ('@corner_mansard', 2), ('@brownstone', 3), ('@brick_rowhouse', 3), ('@arched_bank', 1),
                  ('@tan_prewar', 1), ('@hotel_setback', 0.6), ('@arch_warehouse', 0.5), ('walkup', 2),
                  ('@old_law', 2), ('@bodega_corner', 1), ('@cast_iron_loft', 1)],
    'lower_east_side': [('@old_law', 5), ('@tenement', 2), ('@bodega_corner', 1.2), ('@cast_iron_loft', 2), ('walkup', 2),
                        ('@corner_mansard', 0.6), ('@white_brick', 0.3)],
    'midtown': [('@garment_loft', 2), ('@deco_tower', 1), ('@glass_curtain', 1), ('@gothic_tower', 0.8), ('@terrace_coop', 1.5),
                ('@limestone_office', 1.5), ('@hotel_setback', 1), ('@tan_prewar', 1), ('@white_brick', 1), ('prewar', 2), ('tower', 1), ('modern', 1)],
}


def _rng(p):
    off = 100 + PS.KEYS.index(p['preset']) if p.get('preset') else ST.STYLE_KEYS.index(p['style'])
    return random.Random(p['seed'] * 7919 + off)


def _plan(p, rng):
    o = dict(p.get('opts', {}))
    return PS.make(p['preset'], rng, o) if p.get('preset') else ST.make_plan(p['style'], rng, o)


def label(p):
    """Nom court pour l'objet : preset ou style."""
    return p.get('preset') or p['style']


def _collection(context, name=COLL):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        context.scene.collection.children.link(c)
    return c


def build_mesh(params, mat_mode='procedural', kb_dir="", mesh=None, name="Batiment"):
    """Construit le maillage d'un batiment. params : style, seed, opts, detail, party, sidewalk."""
    rng = _rng(params)
    plan = _plan(params, rng)
    yard = plan.get('setback', 0.0) if (params.get('yard') or params.get('sidewalk')) else 0.0
    mb, info = BD.build(plan, rng, detail=params.get('detail', 1), party=tuple(params.get('party', (False, False))),
                        sidewalk=params.get('sidewalk', False), yard=yard)
    me = mb.to_mesh(name, lambda k: MT.get(k, mat_mode, kb_dir), mesh=mesh)
    info.update(W=plan['W'], D=plan['D'], style=params['style'], preset=params.get('preset') or "", tris=sum(len(p.vertices) - 2 for p in me.polygons))
    return me, info


def create_building(context, params, location=(0, 0, 0), rot_z=0.0, scale=1.0, mat_mode='procedural', kb_dir="", collection=None, name=None):
    t = time.perf_counter()
    nm = name or "Bat_%s_%03d" % (label(params), params['seed'])
    me, info = build_mesh(params, mat_mode, kb_dir, name=nm)
    ob = bpy.data.objects.new(nm, me)
    ob.location = location
    ob.rotation_euler = (0, 0, rot_z)
    ob.scale = (scale, scale, scale)
    ob["bg_params"] = json.dumps(params)
    ob["bg_info"] = json.dumps(info)
    (collection or _collection(context)).objects.link(ob)
    info['time'] = time.perf_counter() - t
    return ob, info


def regenerate(ob, params, mat_mode='procedural', kb_dir=""):
    old = ob.data
    me, info = build_mesh(params, mat_mode, kb_dir, name=old.name)
    ob.data = me
    if old.users == 0:
        bpy.data.meshes.remove(old)
    ob["bg_params"] = json.dumps(params)
    ob["bg_info"] = json.dumps(info)
    return info


def variants(context, style, seed, count, opts, detail, spacing=8.0, origin=(0, 0, 0), scale=1.0, mat_mode='procedural', kb_dir="", sidewalk=True,
             preset=None):
    coll = _collection(context, COLL + " - variantes")
    cols = max(1, int(math.ceil(math.sqrt(count))))
    x = 0.0
    obs = []
    row_y = 0.0
    row_depth = 0.0
    for i in range(count):
        p = dict(style=style, seed=seed + i, opts=opts, detail=detail, party=(False, False), sidewalk=sidewalk)
        if preset:
            p['preset'] = preset
            p['style'] = PS.BY_KEY[preset][3]
        ob, info = create_building(context, p, scale=scale, mat_mode=mat_mode, kb_dir=kb_dir, collection=coll)
        if i % cols == 0 and i:
            row_y += (row_depth + spacing + (4.8 if sidewalk else 0)) * scale
            x = 0.0
            row_depth = 0.0
        ob.location = (origin[0] + x, origin[1] + row_y, origin[2])
        x += (info['W'] + spacing) * scale
        row_depth = max(row_depth, info['D'])
        obs.append(ob)
    return obs


def street(context, seed, length, mix='brooklyn', both_sides=True, road_w=11.0, walk_w=4.5, detail=1, opts=None, origin=(0, 0, 0),
           scale=1.0, mat_mode='procedural', kb_dir=""):
    """Rue le long de +x : rangees de batiments mitoyens de part et d'autre, trottoirs, bordures, chaussee."""
    rng = random.Random(seed)
    coll = _collection(context, COLL + " - rue %d" % seed)
    weights = STREET_MIX.get(mix, STREET_MIX['brooklyn'])
    O = Vector(origin)
    obs = []
    sides = [(-1, 0.0)] + ([(1, math.pi)] if both_sides else [])
    for sgn, rot in sides:
        x = 0.0
        prev_style = None
        lots = []
        while x < length - 4:
            st = ST.pick(rng, [w[0] for w in weights], [w[1] for w in weights])
            # les maisons de ville vont par series
            if prev_style in ('rowhouse', '@brownstone', '@brick_rowhouse') and rng.random() < 0.6:
                st = prev_style
            o = dict(opts or {})
            p = dict(style=st, seed=rng.randrange(1, 10 ** 6), opts=o, detail=detail, party=(True, True), sidewalk=False)
            if st.startswith('@'):
                p['preset'] = st[1:]
                p['style'] = PS.BY_KEY[st[1:]][3]
            plan = _plan(p, _rng(p))
            if x + plan['W'] > length + 2:
                break
            p['setback'] = plan.get('setback', 0.0)
            p['yard'] = p['setback'] > 0
            lots.append((p, plan['W']))
            x += plan['W']
            prev_style = st
        if not lots:
            continue
        # extremites : pas de mur mitoyen (cote sud tourne de 180 deg : gauche et droite s'inversent)
        first, last = ((False, True), (True, False)) if sgn > 0 else ((True, False), (False, True))
        lots[0][0]['party'] = first
        lots[-1][0]['party'] = last
        if len(lots) == 1:
            lots[0][0]['party'] = (False, False)
        x = 0.0
        for p, Wl in lots:
            ob, info = create_building(context, p, scale=scale, mat_mode=mat_mode, kb_dir=kb_dir, collection=coll)
            sb = p.get('setback', 0.0)                # recul (courette devant les maisons a perron)
            if sgn < 0:
                # cote sud : on tourne la facade vers la rue (+y) : rotation pi, x inverse
                ob.rotation_euler = (0, 0, math.pi)
                ob.location = O + Vector((x + Wl, -(road_w / 2 + walk_w + sb), 0)) * scale
            else:
                ob.rotation_euler = (0, 0, 0)
                ob.location = O + Vector((x, road_w / 2 + walk_w + sb, 0)) * scale
            x += Wl
            obs.append(ob)
        total = x
        # trottoir + bordure
        mb = MeshBuilder()
        y_in = road_w / 2 + walk_w
        if sgn < 0:
            mb.box((0, -y_in, -0.18), (total, -road_w / 2, 0.0), 'sidewalk', skip=('-y',))
            mb.box((0, -road_w / 2, -0.2), (total, -road_w / 2 + 0.25, 0.0), 'curb')
        else:
            mb.box((0, road_w / 2, -0.18), (total, y_in, 0.0), 'sidewalk', skip=('+y',))
            mb.box((0, road_w / 2 - 0.25, -0.2), (total, road_w / 2, 0.0), 'curb')
        me = mb.to_mesh("Trottoir", lambda k: MT.get(k, mat_mode, kb_dir))
        tw = bpy.data.objects.new("Trottoir_%s_%d" % ('sud' if sgn < 0 else 'nord', seed), me)
        tw.location = O
        tw.scale = (scale,) * 3
        coll.objects.link(tw)
        obs.append(tw)
    # chaussee
    mb = MeshBuilder()
    mb.face([Vector((0, -road_w / 2 + 0.25, -0.2)), Vector((length, -road_w / 2 + 0.25, -0.2)), Vector((length, road_w / 2 - 0.25, -0.2)), Vector((0, road_w / 2 - 0.25, -0.2))], 'asphalt')
    me = mb.to_mesh("Chaussee", lambda k: MT.get(k, mat_mode, kb_dir))
    rd = bpy.data.objects.new("Chaussee_%d" % seed, me)
    rd.location = O
    rd.scale = (scale,) * 3
    coll.objects.link(rd)
    obs.append(rd)
    return obs
