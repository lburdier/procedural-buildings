"""Usure des materiaux (v1.5) : groupes de noeuds partages, inseres entre les textures et le BSDF.

  BG_usure_mur    : salissure au pied des murs, coulures verticales, crasse des recoins (occlusion ambiante),
                    taches et decolorations a grande echelle, salpetre (efflorescence) sur la maconnerie,
                    rugosite variable (plus mate ou sale, plus lisse sous les coulures).
  BG_usure_metal  : rouille (taches, recoins, coulures), peinture qui part, poussiere sur les faces du dessus.
  BG_usure_sol    : chewing-gums, taches d'huile, flaques (rugosite basse), crasse le long des murs.
  BG_usure_vitre  : poussiere et coulures sur les vitres (plus claires, plus rugueuses).

La force globale (noeud « BG_usure » de chaque groupe) se regle dans le panneau ; chaque batiment varie un peu
(Object Info > Random) et chaque materiau a sa propre entree Force (0 : intact)."""
import bpy

GROUPS = ("BG_usure_mur", "BG_usure_metal", "BG_usure_sol", "BG_usure_vitre")
VERSION = 1
DEFAULT = 0.7


class _G:
    """Petit assistant de construction de groupe."""

    def __init__(self, name, inputs, outputs):
        ng = bpy.data.node_groups.get(name)
        if ng is None:
            ng = bpy.data.node_groups.new(name, 'ShaderNodeTree')
        else:
            ng.nodes.clear()
            ng.interface.clear()
        self.ng = ng
        for nm, typ, dv in inputs:
            s = ng.interface.new_socket(name=nm, in_out='INPUT', socket_type=typ)
            if dv is not None:
                s.default_value = dv
            if typ == 'NodeSocketFloat':
                s.min_value, s.max_value = -10.0, 10.0
        for nm, typ in outputs:
            ng.interface.new_socket(name=nm, in_out='OUTPUT', socket_type=typ)
        self.i = self.n('NodeGroupInput', -1400, 0)
        self.o = self.n('NodeGroupOutput', 1200, 0)
        ng["bg_wear_ver"] = VERSION

    def n(self, t, x, y, **kw):
        nd = self.ng.nodes.new(t)
        nd.location = (x, y)
        for k, v in kw.items():
            setattr(nd, k, v)
        return nd

    def l(self, a, b):
        self.ng.links.new(a, b)

    def math(self, op, a, b=None, c=None, x=0, y=0, clamp=False):
        m = self.n('ShaderNodeMath', x, y, operation=op, use_clamp=clamp)
        for k, v in ((0, a), (1, b), (2, c)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                m.inputs[k].default_value = v
            else:
                self.l(v, m.inputs[k])
        return m.outputs[0]

    def mrange(self, v, f0, f1, t0=0.0, t1=1.0, x=0, y=0):
        m = self.n('ShaderNodeMapRange', x, y)
        self.l(v, m.inputs['Value'])
        m.inputs['From Min'].default_value = f0; m.inputs['From Max'].default_value = f1
        m.inputs['To Min'].default_value = t0; m.inputs['To Max'].default_value = t1
        return m.outputs[0]

    def noise(self, vec, scale, detail=4.0, rough=0.55, x=0, y=0, out='Fac'):
        nz = self.n('ShaderNodeTexNoise', x, y)
        nz.inputs['Scale'].default_value = scale
        nz.inputs['Detail'].default_value = detail
        nz.inputs['Roughness'].default_value = rough
        self.l(vec, nz.inputs['Vector'])
        return nz.outputs[out]

    def mix(self, a, b, fac, blend='MIX', x=0, y=0):
        m = self.n('ShaderNodeMix', x, y, data_type='RGBA', blend_type=blend)
        S = {s.identifier: s for s in m.inputs}
        for sock, v in ((S['A_Color'], a), (S['B_Color'], b), (S['Factor_Float'], fac)):
            if isinstance(v, (tuple, list)):
                sock.default_value = (*v, 1.0) if len(v) == 3 else v
            elif isinstance(v, (int, float)):
                sock.default_value = v
            else:
                self.l(v, sock)
        return [s for s in m.outputs if s.identifier == 'Result_Color'][0]

    def common(self):
        """Coordonnees objet, hauteur, verticalite, force (globale x materiau x variation par batiment), recoins."""
        tc = self.n('ShaderNodeTexCoord', -1200, 400)
        sep = self.n('ShaderNodeSeparateXYZ', -1000, 400)
        self.l(tc.outputs['Object'], sep.inputs[0])
        geo = self.n('ShaderNodeNewGeometry', -1200, 150)
        sn = self.n('ShaderNodeSeparateXYZ', -1000, 150)
        self.l(geo.outputs['Normal'], sn.inputs[0])
        nz = self.math('ABSOLUTE', sn.outputs['Z'], x=-850, y=150)
        vert = self.math('SUBTRACT', 1.0, nz, x=-700, y=150)
        up = self.math('MAXIMUM', sn.outputs['Z'], 0.0, x=-850, y=50)
        val = self.n('ShaderNodeValue', -1200, -150)
        val.name = val.label = "BG_usure"
        val.outputs[0].default_value = DEFAULT
        oi = self.n('ShaderNodeObjectInfo', -1200, -300)
        var = self.math('MULTIPLY_ADD', oi.outputs['Random'], 0.9, x=-1000, y=-300)
        var.node.inputs[2].default_value = 0.55
        amt = self.math('MULTIPLY', val.outputs[0], self.i.outputs['Force'], x=-850, y=-150)
        amt = self.math('MULTIPLY', amt, var, x=-700, y=-150)
        ao = self.n('ShaderNodeAmbientOcclusion', -1000, -500, samples=8, only_local=True)
        ao.inputs['Distance'].default_value = 0.7
        crev = self.mrange(ao.outputs['AO'], 0.95, 0.35, 0.0, 1.0, x=-800, y=-500)
        return tc.outputs['Object'], sep.outputs['Z'], vert, up, amt, crev


def _wall():
    g = _G("BG_usure_mur", [('Color', 'NodeSocketColor', (0.5, 0.5, 0.5, 1)), ('Roughness', 'NodeSocketFloat', 0.8),
                            ('Force', 'NodeSocketFloat', 1.0), ('Salpetre', 'NodeSocketFloat', 1.0)],
           [('Color', 'NodeSocketColor'), ('Roughness', 'NodeSocketFloat')])
    obj, z, vert, up, amt, crev = g.common()
    # pied de mur (eclaboussures)
    foot = g.mrange(z, 1.7, 0.0, 0.0, 1.0, x=-600, y=600)
    foot = g.math('POWER', foot, 1.6, x=-450, y=600)
    fnz = g.noise(obj, 2.2, 3.0, x=-600, y=800)
    foot = g.math('MULTIPLY', foot, g.mrange(fnz, 0.3, 0.7, 0.45, 1.0, x=-450, y=800), x=-300, y=650)
    # coulures verticales (bruit etire en z), plus marquees sur les murs que sur les dessus
    mp = g.n('ShaderNodeMapping', -800, 1000)
    mp.inputs['Scale'].default_value = (7.0, 7.0, 0.32)
    g.l(obj, mp.inputs['Vector'])
    st = g.noise(mp.outputs['Vector'], 1.0, 3.0, 0.5, x=-600, y=1000)
    st = g.mrange(st, 0.52, 0.78, 0.0, 1.0, x=-450, y=1000)
    stl = g.noise(obj, 0.18, 2.0, x=-600, y=1200)
    st = g.math('MULTIPLY', st, g.mrange(stl, 0.35, 0.7, 0.15, 1.0, x=-450, y=1200), x=-300, y=1050)
    st = g.math('MULTIPLY', st, vert, x=-150, y=1050)
    # grandes taches / reprises (casse la repetition des textures)
    big = g.noise(obj, 0.22, 3.0, 0.6, x=-600, y=-750)
    bigd = g.mrange(big, 0.5, 0.75, 0.0, 1.0, x=-450, y=-750)
    # salete totale
    d = g.math('MULTIPLY_ADD', foot, 0.85, crev, x=0, y=500)
    d = g.math('ADD', d, g.math('MULTIPLY', st, 1.0, x=0, y=900), x=150, y=600)
    d = g.math('ADD', d, g.math('MULTIPLY', bigd, 0.45, x=0, y=-700), x=300, y=600)
    d = g.math('MULTIPLY', d, amt, x=450, y=600, clamp=True)
    # couleur : assombrir / desaturer vers une crasse brune, salpetre clair en bas, variation de valeur
    vv = g.n('ShaderNodeHueSaturation', 200, 0)
    g.l(g.i.outputs['Color'], vv.inputs['Color'])
    vrange = g.mrange(big, 0.3, 0.7, 0.9, 1.1, x=0, y=-200)
    vv.inputs['Value'].default_value = 1.0
    g.l(vrange, vv.inputs['Value'])
    c = g.mix(vv.outputs['Color'], (0.33, 0.29, 0.25), d, 'MULTIPLY', x=600, y=200)
    c = g.mix(c, (0.09, 0.08, 0.07), g.math('MULTIPLY', d, 0.45, x=600, y=450), 'MIX', x=750, y=250)
    eff = g.mrange(g.noise(obj, 1.3, 4.0, x=200, y=-400), 0.58, 0.78, 0.0, 1.0, x=400, y=-400)
    effh = g.mrange(z, 3.2, 0.2, 0.0, 1.0, x=400, y=-550)
    eff = g.math('MULTIPLY', eff, effh, x=550, y=-450)
    eff = g.math('MULTIPLY', eff, g.math('MULTIPLY', amt, g.i.outputs['Salpetre'], x=550, y=-600), x=700, y=-450)
    eff = g.math('MULTIPLY', eff, 0.45, x=850, y=-450, clamp=True)
    c = g.mix(c, (0.62, 0.6, 0.56), eff, 'MIX', x=950, y=150)
    g.l(c, g.o.inputs['Color'])
    # rugosite
    r = g.math('MULTIPLY_ADD', d, 0.12, g.i.outputs['Roughness'], x=600, y=-150)
    r = g.math('SUBTRACT', r, g.math('MULTIPLY', st, g.math('MULTIPLY', amt, 0.14, x=450, y=-300), x=600, y=-300), x=750, y=-150)
    r = g.math('ADD', r, g.mrange(big, 0.2, 0.8, -0.06, 0.06, x=600, y=-450), x=900, y=-150, clamp=True)
    g.l(r, g.o.inputs['Roughness'])
    return g.ng


def _metal():
    g = _G("BG_usure_metal", [('Color', 'NodeSocketColor', (0.1, 0.1, 0.1, 1)), ('Roughness', 'NodeSocketFloat', 0.5),
                              ('Metallic', 'NodeSocketFloat', 0.5), ('Force', 'NodeSocketFloat', 1.0)],
           [('Color', 'NodeSocketColor'), ('Roughness', 'NodeSocketFloat'), ('Metallic', 'NodeSocketFloat')])
    obj, z, vert, up, amt, crev = g.common()
    sp = g.mrange(g.noise(obj, 3.5, 5.0, 0.6, x=-600, y=600), 0.56, 0.72, 0.0, 1.0, x=-450, y=600)
    mp = g.n('ShaderNodeMapping', -800, 850)
    mp.inputs['Scale'].default_value = (14.0, 14.0, 0.8)
    g.l(obj, mp.inputs['Vector'])
    rs = g.mrange(g.noise(mp.outputs['Vector'], 1.0, 3.0, x=-600, y=850), 0.55, 0.8, 0.0, 0.7, x=-450, y=850)
    rust = g.math('ADD', sp, g.math('MULTIPLY', crev, 0.9, x=-300, y=450), x=-150, y=600)
    rust = g.math('ADD', rust, g.math('MULTIPLY', rs, vert, x=-300, y=850), x=0, y=650)
    rust = g.math('MULTIPLY', rust, amt, x=150, y=650, clamp=True)
    rc = g.mix((0.2, 0.072, 0.028), (0.36, 0.14, 0.05), g.noise(obj, 12.0, 4.0, x=0, y=900), 'MIX', x=200, y=900)
    c = g.mix(g.i.outputs['Color'], rc, rust, 'MIX', x=450, y=300)
    dust = g.math('MULTIPLY', g.math('POWER', up, 4.0, x=300, y=-300), g.math('MULTIPLY', amt, 0.35, x=300, y=-450), x=450, y=-300, clamp=True)
    c = g.mix(c, (0.34, 0.32, 0.29), dust, 'MIX', x=650, y=250)
    g.l(c, g.o.inputs['Color'])
    r = g.math('ADD', g.i.outputs['Roughness'], g.math('MULTIPLY', rust, 0.45, x=450, y=-100), x=650, y=-100, clamp=True)
    r = g.math('ADD', r, g.math('MULTIPLY', dust, 0.3, x=650, y=-250), x=800, y=-100, clamp=True)
    g.l(r, g.o.inputs['Roughness'])
    m = g.math('MULTIPLY', g.i.outputs['Metallic'], g.math('SUBTRACT', 1.0, rust, x=650, y=-450), x=800, y=-400)
    g.l(m, g.o.inputs['Metallic'])
    return g.ng


def _ground():
    g = _G("BG_usure_sol", [('Color', 'NodeSocketColor', (0.4, 0.4, 0.4, 1)), ('Roughness', 'NodeSocketFloat', 0.85),
                            ('Force', 'NodeSocketFloat', 1.0)],
           [('Color', 'NodeSocketColor'), ('Roughness', 'NodeSocketFloat')])
    obj, z, vert, up, amt, crev = g.common()
    vo = g.n('ShaderNodeTexVoronoi', -600, 700)
    vo.inputs['Scale'].default_value = 2.6
    vo.inputs['Randomness'].default_value = 1.0
    g.l(obj, vo.inputs['Vector'])
    gum = g.mrange(vo.outputs['Distance'], 0.06, 0.035, 0.0, 1.0, x=-400, y=700)
    keep = g.mrange(g.noise(obj, 0.9, 2.0, x=-600, y=900), 0.45, 0.6, 0.0, 1.0, x=-400, y=900)
    gum = g.math('MULTIPLY', gum, keep, x=-250, y=750)
    oil = g.mrange(g.noise(obj, 0.45, 4.0, 0.6, x=-600, y=450), 0.6, 0.7, 0.0, 1.0, x=-400, y=450)
    wet = g.mrange(g.noise(obj, 0.3, 3.0, 0.5, x=-600, y=250), 0.64, 0.7, 0.0, 1.0, x=-400, y=250)
    d = g.math('ADD', g.math('MULTIPLY', gum, 0.8, x=-100, y=700), g.math('MULTIPLY', oil, 0.55, x=-100, y=450), x=50, y=600)
    d = g.math('ADD', d, g.math('MULTIPLY', crev, 0.6, x=-100, y=300), x=200, y=600)
    d = g.math('MULTIPLY', d, amt, x=350, y=600, clamp=True)
    c = g.mix(g.i.outputs['Color'], (0.04, 0.038, 0.035), d, 'MIX', x=500, y=300)
    w = g.math('MULTIPLY', wet, amt, x=200, y=200, clamp=True)
    c = g.mix(c, (0.55, 0.55, 0.55), w, 'MULTIPLY', x=700, y=300)
    g.l(c, g.o.inputs['Color'])
    r = g.math('SUBTRACT', g.i.outputs['Roughness'], g.math('MULTIPLY', w, 0.65, x=500, y=0), x=700, y=0, clamp=True)
    r = g.math('SUBTRACT', r, g.math('MULTIPLY', oil, g.math('MULTIPLY', amt, 0.25, x=500, y=-250), x=600, y=-150), x=850, y=0, clamp=True)
    g.l(r, g.o.inputs['Roughness'])
    return g.ng


def _glass():
    g = _G("BG_usure_vitre", [('Color', 'NodeSocketColor', (0.02, 0.02, 0.02, 1)), ('Roughness', 'NodeSocketFloat', 0.05),
                              ('Force', 'NodeSocketFloat', 1.0)],
           [('Color', 'NodeSocketColor'), ('Roughness', 'NodeSocketFloat')])
    obj, z, vert, up, amt, crev = g.common()
    mp = g.n('ShaderNodeMapping', -800, 700)
    mp.inputs['Scale'].default_value = (10.0, 10.0, 0.9)
    g.l(obj, mp.inputs['Vector'])
    st = g.mrange(g.noise(mp.outputs['Vector'], 1.0, 3.0, x=-600, y=700), 0.5, 0.8, 0.0, 1.0, x=-450, y=700)
    dust = g.mrange(g.noise(obj, 1.5, 4.0, x=-600, y=450), 0.35, 0.75, 0.0, 1.0, x=-450, y=450)
    d = g.math('ADD', g.math('MULTIPLY', st, 0.6, x=-300, y=700), g.math('MULTIPLY', dust, 0.5, x=-300, y=450), x=-150, y=600)
    d = g.math('ADD', d, crev, x=0, y=600)
    d = g.math('MULTIPLY', d, amt, x=150, y=600, clamp=True)
    c = g.mix(g.i.outputs['Color'], (0.16, 0.15, 0.13), g.math('MULTIPLY', d, 0.35, x=300, y=400), 'MIX', x=450, y=300)
    g.l(c, g.o.inputs['Color'])
    r = g.math('ADD', g.i.outputs['Roughness'], g.math('MULTIPLY', d, 0.3, x=300, y=0), x=450, y=0, clamp=True)
    g.l(r, g.o.inputs['Roughness'])
    return g.ng


_BUILDERS = {"BG_usure_mur": _wall, "BG_usure_metal": _metal, "BG_usure_sol": _ground, "BG_usure_vitre": _glass}


def group(name):
    ng = bpy.data.node_groups.get(name)
    if ng is None or ng.get("bg_wear_ver") != VERSION:
        ng = _BUILDERS[name]()
        set_amount(current_amount(), [ng])
    return ng


def current_amount():
    try:
        return float(bpy.context.scene.bg_settings.wear)
    except Exception:
        return DEFAULT


def set_amount(v, groups=None):
    """Force globale de l'usure (0 : neuf, 1 : tres use) sur tous les groupes."""
    for ng in groups or [bpy.data.node_groups.get(n) for n in GROUPS]:
        if ng is None:
            continue
        nd = ng.nodes.get("BG_usure")
        if nd:
            nd.outputs[0].default_value = v


def apply(nt, bsdf, col, rough, kind, force=1.0, metal=None, salpetre=1.0, x=420, y=-650):
    """Insere le groupe d'usure entre (couleur, rugosite[, metal]) et le BSDF. col / rough / metal : prises ou valeurs."""
    name = {'wall': "BG_usure_mur", 'metal': "BG_usure_metal", 'ground': "BG_usure_sol", 'glass': "BG_usure_vitre"}[kind]
    gn = nt.nodes.new('ShaderNodeGroup')
    gn.node_tree = group(name)
    gn.location = (x, y)
    gn.name = "BG_usure_grp"

    def put(sock, v):
        if v is None:
            return
        if isinstance(v, (int, float)):
            sock.default_value = v
        elif isinstance(v, (tuple, list)):
            sock.default_value = v
        else:
            nt.links.new(v, sock)
    put(gn.inputs['Color'], col)
    put(gn.inputs['Roughness'], rough)
    gn.inputs['Force'].default_value = force
    if kind == 'wall':
        gn.inputs['Salpetre'].default_value = salpetre
    if kind == 'metal':
        put(gn.inputs['Metallic'], metal if metal is not None else bsdf.inputs['Metallic'].default_value)
        nt.links.new(gn.outputs['Metallic'], bsdf.inputs['Metallic'])
    nt.links.new(gn.outputs['Color'], bsdf.inputs['Base Color'])
    nt.links.new(gn.outputs['Roughness'], bsdf.inputs['Roughness'])
    return gn
