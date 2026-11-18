"""Materiaux : procéduraux (autonomes, par defaut) ou textures Kitbash3D Brooklyn locales (dossier KB3DTextures
de l'utilisateur, jamais copie dans l'add-on). Les UV des batiments sont en metres.

Variation par batiment : chaque materiau decale legerement teinte et valeur avec le nombre aleatoire de l'objet
(Object Info > Random) ; les vitres varient fenetre par fenetre (attribut de face bg_rand)."""
import os
import bpy

from . import wear as WR

PREFIX = "BG_"
MAT_VER = 2               # v1.5 : usure (les materiaux plus anciens d'une scene sont reconstruits sur place)
KB_TILE = 3.6576          # 12 pieds : tuile des textures Brooklyn (mesuree sur le kit)
KB_TILE_GLASS = 8.0

# cle -> (texture Kitbash3D, teinte (multiplicateur RGB) ou None)
KB_MAP = {
    'brick_red': ('BrickWallStandard', None), 'brick_dark': ('BrickWallDark', None), 'brick_tan': ('BrickWallTan', None),
    'brick_brown': ('BrickWallDark', (1.15, 0.9, 0.8)), 'brick_painted': ('BrickWallTan', (1.5, 1.55, 1.6)), 'brick_grey': ('CinderBlockWall', None),
    'stone_brown': ('ConcreteWarmGrey', (0.42, 0.26, 0.18)), 'stone_block': ('StoneBlock', None), 'stone_smooth': ('StoneVerticalScore', None),
    'stone_grey': ('ConcreteGrey', None), 'concrete': ('ConcreteWarmGrey', None), 'panel_white': ('ModernPanelingWhite', None),
    'trim_stone': ('ConcreteBeige', None), 'trim_white': ('ModernPanelingWhite', None), 'trim_brown': ('ConcreteWarmGrey', (0.38, 0.24, 0.17)),
    'trim_grey': ('ConcreteGrey', None), 'coping': ('ConcreteGrey', None), 'metal_cornice': ('CoolGreyPaintedMetal', None),
    'roof_flat': ('FlatAsphaltRoof', None), 'roof_seam_green': ('StandingSeamRoofGreen', None), 'roof_slate': ('FlatAsphaltRoof', (0.7, 0.72, 0.8)),
    'glass': ('GlassBlack', None), 'fire_escape': ('FireEscapePaintedMetal', None), 'metal_galv': ('GalvanizedMetal', None),
    'metal_dark': ('MetalPaintedBlack', None), 'metal_grey': ('CoolGreyPaintedMetal', None), 'ac_unit': ('WarmGreyPaintedMetal', None),
    'wood_green': ('WoodPaintedGreen', None), 'sidewalk': ('ConcreteWithExpansionJoints', None), 'curb': ('ConcreteCurb', None),
    'wood_tank': ('FauxWoodTilesBrown', None), 'metal_door': ('MetalPaintedGrey', None), 'frame_bronze': ('MetalBronze', None),
    'frame_alu': ('MetalAluminum', None),
    'brick_deep': ('BrickWallDark', None), 'stone_warm': ('ConcreteWarmGrey', None),
    'brick_white': ('BrickWallTan', (1.75, 1.78, 1.8)), 'brick_orange': ('BrickWallStandard', (1.35, 1.12, 0.95)),
    'spandrel_dark': ('MetalPaintedBlack', None),
}

# usure : cle -> (groupe, force, salpetre)
def wear_of(key):
    if key in ('glass', 'glass_door'):
        return ('glass', 1.0, 0.0)
    if key in ('sidewalk', 'curb', 'asphalt'):
        return ('ground', 1.0, 0.0)
    if key in ('roof_flat', 'roof_slate'):
        return ('ground', 0.6, 0.0)
    if key.startswith('metal_') or key in ('fire_escape', 'ac_unit', 'spandrel_dark', 'roof_seam_green', 'frame_bronze', 'frame_alu', 'frame_dark'):
        f = {'frame_alu': 0.25, 'frame_bronze': 0.4, 'frame_dark': 0.35, 'roof_seam_green': 0.6, 'spandrel_dark': 0.4}.get(key, 1.0)
        return ('metal', f, 0.0)
    if key.startswith('brick_') or key.startswith('stone_') or key == 'concrete':
        return ('wall', 1.0, 0.0 if key == 'brick_painted' else 1.0)
    f = {'wood_tank': 0.7, 'wood_ply': 0.9, 'frame_white': 0.45, 'frame_green': 0.45, 'panel_white': 0.8}.get(key, 0.6)
    if key.startswith('awning') or key.startswith('sign'):
        f = 0.5
    return ('wall', f, 0.0)


# cle -> parametres proceduraux
P = {
    'brick_red': dict(kind='brick', c1=(0.30, 0.080, 0.048), c2=(0.22, 0.060, 0.040), mortar=(0.26, 0.25, 0.23)),
    'brick_dark': dict(kind='brick', c1=(0.15, 0.050, 0.034), c2=(0.105, 0.038, 0.028), mortar=(0.28, 0.27, 0.25)),
    'brick_tan': dict(kind='brick', c1=(0.42, 0.29, 0.17), c2=(0.35, 0.24, 0.145), mortar=(0.4, 0.38, 0.34)),
    'brick_brown': dict(kind='brick', c1=(0.21, 0.095, 0.058), c2=(0.16, 0.075, 0.048), mortar=(0.36, 0.34, 0.31)),
    'brick_painted': dict(kind='brick', c1=(0.55, 0.53, 0.48), c2=(0.52, 0.5, 0.46), mortar=(0.47, 0.45, 0.42), bump=0.4, rough=0.75),
    'brick_deep': dict(kind='brick', c1=(0.21, 0.068, 0.045), c2=(0.16, 0.052, 0.036), mortar=(0.27, 0.26, 0.24)),
    'stone_warm': dict(kind='block', c1=(0.34, 0.315, 0.30), c2=(0.30, 0.28, 0.27), mortar=(0.21, 0.2, 0.19), bw=1.2, bh=0.6, joint=0.008),
    'brick_white': dict(kind='brick', c1=(0.66, 0.65, 0.61), c2=(0.62, 0.61, 0.58), mortar=(0.5, 0.49, 0.46), bump=0.3, rough=0.55),
    'brick_orange': dict(kind='brick', c1=(0.40, 0.14, 0.065), c2=(0.33, 0.11, 0.055), mortar=(0.36, 0.35, 0.32)),
    'spandrel_dark': dict(kind='noise', c1=(0.03, 0.033, 0.036), c2=(0.045, 0.047, 0.05), rough=0.3, metal=0.6, scale=4),
    'brick_grey': dict(kind='brick', c1=(0.33, 0.32, 0.30), c2=(0.28, 0.28, 0.27), mortar=(0.45, 0.44, 0.42)),
    'stone_brown': dict(kind='block', c1=(0.105, 0.055, 0.036), c2=(0.085, 0.045, 0.03), mortar=(0.07, 0.04, 0.028), bw=0.9, bh=0.38, joint=0.006),
    'stone_block': dict(kind='block', c1=(0.36, 0.33, 0.28), c2=(0.31, 0.29, 0.25), mortar=(0.2, 0.19, 0.17), bw=1.2, bh=0.6, joint=0.012),
    'stone_smooth': dict(kind='block', c1=(0.42, 0.38, 0.31), c2=(0.39, 0.355, 0.29), mortar=(0.3, 0.28, 0.24), bw=1.5, bh=0.75, joint=0.005),
    'stone_grey': dict(kind='block', c1=(0.37, 0.37, 0.36), c2=(0.33, 0.33, 0.32), mortar=(0.25, 0.25, 0.25), bw=1.5, bh=0.75, joint=0.006),
    'concrete': dict(kind='noise', c1=(0.33, 0.32, 0.3), c2=(0.26, 0.255, 0.24), rough=0.85),
    'panel_white': dict(kind='block', c1=(0.58, 0.58, 0.56), c2=(0.56, 0.56, 0.54), mortar=(0.35, 0.35, 0.34), bw=1.22, bh=1.8, joint=0.008, rough=0.45),
    'trim_stone': dict(kind='noise', c1=(0.45, 0.41, 0.33), c2=(0.38, 0.35, 0.29), rough=0.8),
    'trim_white': dict(kind='noise', c1=(0.62, 0.62, 0.6), c2=(0.55, 0.55, 0.53), rough=0.5, scale=8),
    'trim_brown': dict(kind='noise', c1=(0.12, 0.065, 0.042), c2=(0.095, 0.052, 0.034), rough=0.8),
    'trim_grey': dict(kind='noise', c1=(0.44, 0.44, 0.43), c2=(0.38, 0.38, 0.37), rough=0.8),
    'coping': dict(kind='noise', c1=(0.48, 0.47, 0.45), c2=(0.40, 0.40, 0.38), rough=0.85),
    'metal_cornice': dict(kind='noise', c1=(0.36, 0.36, 0.34), c2=(0.30, 0.30, 0.29), rough=0.45, metal=0.3, scale=6),
    'frame_dark': dict(kind='flat', c1=(0.018, 0.018, 0.018), rough=0.4),
    'frame_white': dict(kind='flat', c1=(0.72, 0.72, 0.69), rough=0.45),
    'frame_green': dict(kind='flat', c1=(0.025, 0.075, 0.045), rough=0.45),
    'frame_bronze': dict(kind='flat', c1=(0.12, 0.07, 0.035), rough=0.35, metal=0.8),
    'frame_alu': dict(kind='flat', c1=(0.6, 0.6, 0.62), rough=0.35, metal=1.0),
    'wood_green': dict(kind='noise', c1=(0.02, 0.075, 0.04), c2=(0.015, 0.06, 0.03), rough=0.5, scale=30),
    'wood_dark': dict(kind='noise', c1=(0.055, 0.032, 0.018), c2=(0.04, 0.024, 0.014), rough=0.5, scale=30),
    'wood_red': dict(kind='noise', c1=(0.20, 0.025, 0.02), c2=(0.16, 0.02, 0.016), rough=0.5, scale=30),
    'metal_door': dict(kind='flat', c1=(0.09, 0.09, 0.09), rough=0.5, metal=0.4),
    'glass_door': dict(kind='glass'),
    'glass': dict(kind='glass'),
    'sign_dark': dict(kind='flat', c1=(0.02, 0.02, 0.025), rough=0.35),
    'sign_red': dict(kind='flat', c1=(0.25, 0.02, 0.02), rough=0.4),
    'sign_green': dict(kind='flat', c1=(0.02, 0.11, 0.06), rough=0.4),
    'sign_cream': dict(kind='flat', c1=(0.66, 0.58, 0.42), rough=0.5),
    'awning_red': dict(kind='stripes', c1=(0.33, 0.03, 0.03), c2=(0.6, 0.58, 0.52), rough=0.85),
    'awning_green': dict(kind='stripes', c1=(0.02, 0.12, 0.05), c2=(0.6, 0.58, 0.52), rough=0.85),
    'awning_black': dict(kind='flat', c1=(0.03, 0.03, 0.03), rough=0.85),
    'awning_blue': dict(kind='flat', c1=(0.02, 0.05, 0.17), rough=0.85),
    'roof_flat': dict(kind='noise', c1=(0.085, 0.085, 0.09), c2=(0.06, 0.06, 0.065), rough=0.92, scale=3),
    'roof_seam_green': dict(kind='seam', c1=(0.14, 0.30, 0.24), c2=(0.10, 0.22, 0.18), rough=0.5, metal=0.4),
    'roof_slate': dict(kind='block', c1=(0.075, 0.08, 0.09), c2=(0.06, 0.065, 0.075), mortar=(0.03, 0.03, 0.035), bw=0.3, bh=0.18, joint=0.008, rough=0.6),
    'metal_dark': dict(kind='noise', c1=(0.025, 0.025, 0.025), c2=(0.04, 0.03, 0.025), rough=0.5, metal=0.5, scale=4),
    'metal_grey': dict(kind='noise', c1=(0.30, 0.31, 0.32), c2=(0.26, 0.27, 0.28), rough=0.5, metal=0.3, scale=4),
    'metal_galv': dict(kind='noise', c1=(0.55, 0.56, 0.57), c2=(0.45, 0.46, 0.47), rough=0.45, metal=1.0, scale=5),
    'fire_escape': dict(kind='noise', c1=(0.03, 0.03, 0.03), c2=(0.09, 0.045, 0.025), rough=0.6, metal=0.3, scale=6),
    'ac_unit': dict(kind='noise', c1=(0.34, 0.33, 0.3), c2=(0.27, 0.26, 0.24), rough=0.5, metal=0.2, scale=5),
    'wood_tank': dict(kind='planks', c1=(0.17, 0.11, 0.065), c2=(0.12, 0.08, 0.05), rough=0.8),
    'terracotta': dict(kind='noise', c1=(0.33, 0.11, 0.055), c2=(0.27, 0.09, 0.045), rough=0.8),
    'sidewalk': dict(kind='block', c1=(0.44, 0.43, 0.41), c2=(0.40, 0.39, 0.37), mortar=(0.2, 0.2, 0.2), bw=1.52, bh=1.52, joint=0.012, rough=0.85),
    'curb': dict(kind='noise', c1=(0.50, 0.49, 0.47), c2=(0.42, 0.41, 0.40), rough=0.8),
    'asphalt': dict(kind='noise', c1=(0.05, 0.05, 0.052), c2=(0.075, 0.075, 0.078), rough=0.9, scale=12),
    'wood_ply': dict(kind='noise', c1=(0.2, 0.16, 0.11), c2=(0.13, 0.11, 0.085), rough=0.85, scale=3),
}


def get(key, mode='procedural', kb_dir=""):
    """Materiau pour une cle (cree a la demande, reutilise ensuite)."""
    if key == 'decal':
        from . import decals
        return decals.material()
    if mode == 'kb3d' and kb_dir and key in KB_MAP:
        name = PREFIX + "KB_" + key
        m = bpy.data.materials.get(name)
        if m is None or m.get("bg_mat_ver") != MAT_VER:
            m2 = _kb_material(name, key, kb_dir)
            m = m2 or m
        if m is not None:
            return m
    name = PREFIX + key
    m = bpy.data.materials.get(name)
    if m is None or m.get("bg_mat_ver") != MAT_VER:
        m = _procedural(name, P.get(key, dict(kind='flat', c1=(0.5, 0.5, 0.5))))
    return m


def kb_available(kb_dir):
    return bool(kb_dir) and os.path.isfile(os.path.join(kb_dir, "KB3D_BRK_BrickWallStandard_basecolor.png"))


# ------------------------------------------------------------------ outils de noeuds


def _new(name):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)     # reconstruit sur place : les objets le gardent
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); out.location = (900, 0)
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled'); bsdf.location = (600, 0)
    nt.links.new(bsdf.outputs[0], out.inputs['Surface'])
    m["bg_material"] = True
    m["bg_mat_ver"] = MAT_VER
    return m, nt, bsdf


def _n(nt, t, x, y, **kw):
    n = nt.nodes.new(t)
    n.location = (x, y)
    for k, v in kw.items():
        setattr(n, k, v)
    return n


def _sock(sockets, ident):
    for x in sockets:
        if x.identifier == ident:
            return x
    raise KeyError(ident)


def _mix(nt, x, y, blend='MIX', fac=None):
    """Noeud Mix en mode couleur ; renvoie (noeud, A, B, facteur, resultat) par identifiant (A/B/Result existent
    en plusieurs types sous le meme nom)."""
    n = _n(nt, 'ShaderNodeMix', x, y, data_type='RGBA', blend_type=blend)
    f = _sock(n.inputs, 'Factor_Float')
    if fac is not None:
        f.default_value = fac
    return n, _sock(n.inputs, 'A_Color'), _sock(n.inputs, 'B_Color'), f, _sock(n.outputs, 'Result_Color')


def _uv(nt, scale=1.0):
    tc = _n(nt, 'ShaderNodeTexCoord', -1400, 0)
    if scale == 1.0:
        return tc.outputs['UV']
    mp = _n(nt, 'ShaderNodeMapping', -1200, 0)
    mp.inputs['Scale'].default_value = (scale, scale, scale)
    nt.links.new(tc.outputs['UV'], mp.inputs['Vector'])
    return mp.outputs['Vector']


def _rand_tint(nt, col_socket, x=200, y=200, hue=0.025, val=0.18, sat=0.15):
    """Decale teinte / valeur avec Object Info > Random (chaque batiment est un peu different)."""
    oi = _n(nt, 'ShaderNodeObjectInfo', x - 600, y + 250)
    hsv = _n(nt, 'ShaderNodeHueSaturation', x, y)
    m1 = _n(nt, 'ShaderNodeMath', x - 350, y + 300, operation='MULTIPLY_ADD')
    m1.inputs[1].default_value = hue * 2; m1.inputs[2].default_value = 0.5 - hue
    nt.links.new(oi.outputs['Random'], m1.inputs[0]); nt.links.new(m1.outputs[0], hsv.inputs['Hue'])
    m2 = _n(nt, 'ShaderNodeMath', x - 350, y + 150, operation='MULTIPLY_ADD')
    m2.inputs[1].default_value = val * 2; m2.inputs[2].default_value = 1.0 - val
    nt.links.new(oi.outputs['Random'], m2.inputs[0]); nt.links.new(m2.outputs[0], hsv.inputs['Value'])
    m3 = _n(nt, 'ShaderNodeMath', x - 350, y + 0, operation='MULTIPLY_ADD')
    m3.inputs[1].default_value = sat * 2; m3.inputs[2].default_value = 1.0 - sat
    nt.links.new(oi.outputs['Random'], m3.inputs[0]); nt.links.new(m3.outputs[0], hsv.inputs['Saturation'])
    nt.links.new(col_socket, hsv.inputs['Color'])
    return hsv.outputs['Color']


def _grime(nt, uv, col_socket, amount=0.35, x=0, y=-300):
    """Salissure : coulures verticales (bruit etire) + pied de mur plus sombre (v = hauteur en metres)."""
    mp = _n(nt, 'ShaderNodeMapping', x - 700, y)
    mp.inputs['Scale'].default_value = (1.2, 0.08, 1.0)
    nt.links.new(uv, mp.inputs['Vector'])
    nz = _n(nt, 'ShaderNodeTexNoise', x - 500, y)
    nz.inputs['Scale'].default_value = 3.0; nz.inputs['Detail'].default_value = 4.0
    nt.links.new(mp.outputs['Vector'], nz.inputs['Vector'])
    ramp = _n(nt, 'ShaderNodeMapRange', x - 300, y)
    ramp.inputs['From Min'].default_value = 0.45; ramp.inputs['From Max'].default_value = 0.75
    ramp.inputs['To Max'].default_value = amount
    nt.links.new(nz.outputs['Fac'], ramp.inputs['Value'])
    sep = _n(nt, 'ShaderNodeSeparateXYZ', x - 500, y - 250)
    nt.links.new(uv, sep.inputs[0])
    foot = _n(nt, 'ShaderNodeMapRange', x - 300, y - 250)
    foot.inputs['From Min'].default_value = 1.2; foot.inputs['From Max'].default_value = 0.0
    foot.inputs['To Max'].default_value = amount * 1.2
    nt.links.new(sep.outputs['Y'], foot.inputs['Value'])
    add = _n(nt, 'ShaderNodeMath', x - 100, y, operation='ADD', use_clamp=True)
    nt.links.new(ramp.outputs[0], add.inputs[0]); nt.links.new(foot.outputs[0], add.inputs[1])
    mix, A, B, F, R = _mix(nt, x + 100, y, 'MULTIPLY')
    B.default_value = (0.45, 0.42, 0.38, 1.0)
    nt.links.new(add.outputs[0], F); nt.links.new(col_socket, A)
    return R


def _bump(nt, height_socket, bsdf, strength=0.5, dist=0.02, x=350, y=-450):
    b = _n(nt, 'ShaderNodeBump', x, y)
    b.inputs['Strength'].default_value = strength
    b.inputs['Distance'].default_value = dist
    nt.links.new(height_socket, b.inputs['Height'])
    nt.links.new(b.outputs['Normal'], bsdf.inputs['Normal'])


def _procedural(name, s):
    m, nt, bsdf = _new(name)
    kind = s['kind']
    c1 = (*s.get('c1', (0.5, 0.5, 0.5)), 1.0)
    c2 = (*s.get('c2', s.get('c1', (0.5, 0.5, 0.5))), 1.0)
    bsdf.inputs['Roughness'].default_value = s.get('rough', 0.85)
    bsdf.inputs['Metallic'].default_value = s.get('metal', 0.0)
    if kind == 'glass':
        _glass(nt, bsdf)
        m.diffuse_color = (0.02, 0.025, 0.03, 1)
        return m
    key = name[len(PREFIX):]
    uv = _uv(nt)
    col = None
    if kind in ('brick', 'block'):
        bt = _n(nt, 'ShaderNodeTexBrick', -700, 100)
        bt.offset = 0.5
        bt.inputs['Color1'].default_value = c1
        bt.inputs['Color2'].default_value = c2
        bt.inputs['Mortar'].default_value = (*s.get('mortar', (0.4, 0.4, 0.4)), 1.0)
        bt.inputs['Scale'].default_value = 1.0
        if kind == 'brick':
            bt.inputs['Mortar Size'].default_value = 0.01
            bt.inputs['Brick Width'].default_value = 0.225
            bt.inputs['Row Height'].default_value = 0.0762
            bt.inputs['Bias'].default_value = 0.0
        else:
            bt.inputs['Mortar Size'].default_value = s.get('joint', 0.008)
            bt.inputs['Brick Width'].default_value = s.get('bw', 1.2)
            bt.inputs['Row Height'].default_value = s.get('bh', 0.6)
        bt.inputs['Mortar Smooth'].default_value = 0.1
        nt.links.new(uv, bt.inputs['Vector'])
        # variation fine a l'interieur des briques / blocs
        nz = _n(nt, 'ShaderNodeTexNoise', -700, -150)
        nz.inputs['Scale'].default_value = 18.0 if kind == 'brick' else 6.0
        nz.inputs['Detail'].default_value = 6.0
        nt.links.new(uv, nz.inputs['Vector'])
        mixn, A, B, F, R = _mix(nt, -400, 100, 'OVERLAY', 0.25)
        nt.links.new(bt.outputs['Color'], A); nt.links.new(nz.outputs['Color'], B)
        col = R
        inv = _n(nt, 'ShaderNodeMath', -400, -400, operation='SUBTRACT')
        inv.inputs[0].default_value = 1.0
        nt.links.new(bt.outputs['Fac'], inv.inputs[1])
        h = _n(nt, 'ShaderNodeMath', -200, -400, operation='MULTIPLY_ADD')
        h.inputs[1].default_value = 1.0
        nt.links.new(inv.outputs[0], h.inputs[0])
        nt.links.new(nz.outputs['Fac'], h.inputs[2])
        hh = _n(nt, 'ShaderNodeMath', 0, -400, operation='MULTIPLY')
        hh.inputs[1].default_value = 0.6
        nt.links.new(h.outputs[0], hh.inputs[0])
        _bump(nt, hh.outputs[0], bsdf, strength=s.get('bump', 1.0) * (0.6 if kind == 'brick' else 0.35), dist=0.01)
        rr = _n(nt, 'ShaderNodeMapRange', 300, -150)
        rr.inputs['To Min'].default_value = s.get('rough', 0.85) - 0.08; rr.inputs['To Max'].default_value = min(1.0, s.get('rough', 0.85) + 0.1)
        nt.links.new(bt.outputs['Fac'], rr.inputs['Value'])
        nt.links.new(rr.outputs[0], bsdf.inputs['Roughness'])
        col = _grime(nt, uv, col, 0.3 if kind == 'brick' else 0.25)
    elif kind in ('noise', 'flat', 'planks', 'seam', 'stripes'):
        if kind == 'flat':
            rgb = _n(nt, 'ShaderNodeRGB', -400, 100)
            rgb.outputs[0].default_value = c1
            col = rgb.outputs[0]
        elif kind == 'noise':
            nz = _n(nt, 'ShaderNodeTexNoise', -700, 100)
            nz.inputs['Scale'].default_value = s.get('scale', 2.0)
            nz.inputs['Detail'].default_value = 8.0
            nz.inputs['Roughness'].default_value = 0.6
            nt.links.new(uv, nz.inputs['Vector'])
            mix, A, B, F, R = _mix(nt, -400, 100)
            A.default_value = c1; B.default_value = c2
            nt.links.new(nz.outputs['Fac'], F)
            col = R
            _bump(nt, nz.outputs['Fac'], bsdf, strength=0.15, dist=0.01)
            if s.get('rough', 0.8) > 0.7:
                col = _grime(nt, uv, col, 0.2)
        else:
            wv = _n(nt, 'ShaderNodeTexWave', -700, 100)
            wv.wave_type = 'BANDS'
            wv.bands_direction = 'X'
            wv.wave_profile = 'SAW' if kind == 'planks' else ('SIN' if kind == 'stripes' else 'TRI')
            wv.inputs['Scale'].default_value = {'planks': 1.0 / 0.14, 'seam': 1.0 / 0.45, 'stripes': 1.0 / 0.3}[kind] / 1.0
            wv.inputs['Distortion'].default_value = 0.0
            nt.links.new(uv, wv.inputs['Vector'])
            ramp = _n(nt, 'ShaderNodeMapRange', -500, 100)
            if kind == 'stripes':
                ramp.inputs['From Min'].default_value = 0.49; ramp.inputs['From Max'].default_value = 0.51
            else:
                ramp.inputs['From Min'].default_value = 0.85; ramp.inputs['From Max'].default_value = 0.98
            nt.links.new(wv.outputs['Fac'], ramp.inputs['Value'])
            mix, A, B, F, R = _mix(nt, -300, 100)
            A.default_value = c1; B.default_value = c2
            nt.links.new(ramp.outputs[0], F)
            col = R
            _bump(nt, wv.outputs['Fac'], bsdf, strength=0.3, dist=0.01)
    if kind != 'flat':
        col = _rand_tint(nt, col, x=350, y=250)
    rin = bsdf.inputs['Roughness']
    rough = rin.links[0].from_socket if rin.is_linked else rin.default_value
    wk, wf, ws = wear_of(key)
    WR.apply(nt, bsdf, col, rough, wk, force=wf, metal=s.get('metal', 0.0), salpetre=ws)
    m.diffuse_color = c1
    return m


def _glass(nt, bsdf):
    """Vitre sombre et reflechissante ; chaque fenetre (attribut bg_rand) a sa nuance, quelques rideaux clairs."""
    at = _n(nt, 'ShaderNodeAttribute', -900, 100, attribute_name='bg_rand', attribute_type='GEOMETRY')
    ramp = _n(nt, 'ShaderNodeValToRGB', -600, 100)
    cr = ramp.color_ramp
    cr.interpolation = 'CONSTANT'
    cr.elements[0].position = 0.0; cr.elements[0].color = (0.012, 0.015, 0.018, 1)
    cr.elements[1].position = 0.55; cr.elements[1].color = (0.02, 0.024, 0.03, 1)
    e = cr.elements.new(0.8); e.color = (0.03, 0.03, 0.028, 1)
    e = cr.elements.new(0.93); e.color = (0.16, 0.13, 0.09, 1)          # rideau / store clair
    nt.links.new(at.outputs['Fac'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
    rr = _n(nt, 'ShaderNodeMapRange', -600, -150)
    rr.inputs['To Min'].default_value = 0.03; rr.inputs['To Max'].default_value = 0.14
    nt.links.new(at.outputs['Fac'], rr.inputs['Value'])
    nt.links.new(rr.outputs[0], bsdf.inputs['Roughness'])
    WR.apply(nt, bsdf, ramp.outputs['Color'], rr.outputs[0], 'glass')
    bsdf.inputs['Metallic'].default_value = 0.0
    try:
        bsdf.inputs['Specular IOR Level'].default_value = 0.8
    except KeyError:
        pass
    # fenetres allumees : force reglee par l'add-on (propriete du materiau)
    em = _n(nt, 'ShaderNodeMapRange', -300, -350)
    em.inputs['From Min'].default_value = 0.0; em.inputs['From Max'].default_value = 1.0
    nt.links.new(at.outputs['Fac'], em.inputs['Value'])
    gt = _n(nt, 'ShaderNodeMath', -100, -350, operation='GREATER_THAN')
    gt.inputs[1].default_value = 0.78
    gt.label = "seuil fenetres allumees"
    gt.name = "BG_seuil"
    nt.links.new(em.outputs[0], gt.inputs[0])
    st = _n(nt, 'ShaderNodeMath', 100, -350, operation='MULTIPLY')
    st.inputs[1].default_value = 0.0
    st.name = "BG_allumage"
    st.label = "force des fenetres allumees"
    nt.links.new(gt.outputs[0], st.inputs[0])
    bsdf.inputs['Emission Color'].default_value = (1.0, 0.72, 0.42, 1)
    nt.links.new(st.outputs[0], bsdf.inputs['Emission Strength'])


def _kb_material(name, key, kb_dir):
    tex, tint = KB_MAP[key]
    base = os.path.join(kb_dir, f"KB3D_BRK_{tex}_")
    if not os.path.isfile(base + "basecolor.png"):
        return None
    m, nt, bsdf = _new(name)
    tile = KB_TILE_GLASS if key == 'glass' else KB_TILE
    uv = _uv(nt, 1.0 / tile)

    def img(suffix, x, y, color=False):
        p = base + suffix + ".png"
        if not os.path.isfile(p):
            return None
        im = bpy.data.images.load(p, check_existing=True)
        if not color:
            im.colorspace_settings.name = 'Non-Color'
        n = _n(nt, 'ShaderNodeTexImage', x, y)
        n.image = im
        nt.links.new(uv, n.inputs['Vector'])
        return n
    bc = img("basecolor", -800, 300, True)
    col = bc.outputs['Color']
    if tint:
        mul, A, B, F, R = _mix(nt, -450, 300, 'MULTIPLY', 1.0)
        B.default_value = (*tint, 1.0)
        nt.links.new(col, A)
        col = R
    if key != 'glass':
        col = _rand_tint(nt, col, x=250, y=300, hue=0.015, val=0.12, sat=0.1)
    r = img("roughness", -800, 0)
    mt = img("metallic", -800, -250)
    if mt:
        nt.links.new(mt.outputs['Color'], bsdf.inputs['Metallic'])
    wk, wf, ws = wear_of(key)
    WR.apply(nt, bsdf, col, r.outputs['Color'] if r else 0.6, wk, force=wf * 0.8, metal=mt.outputs['Color'] if mt else None, salpetre=ws)
    nm = img("normal", -800, -500)
    if nm:
        nmap = _n(nt, 'ShaderNodeNormalMap', -400, -500)
        nt.links.new(nm.outputs['Color'], nmap.inputs['Color'])
        nt.links.new(nmap.outputs['Normal'], bsdf.inputs['Normal'])
    m["bg_kb3d"] = tex
    return m


def set_lit_windows(strength, threshold=0.78):
    """Fenetres allumees (nuit) : force d'emission et proportion, sur tous les vitrages BG_."""
    for m in bpy.data.materials:
        if not m.get("bg_material") or not m.node_tree:
            continue
        s = m.node_tree.nodes.get("BG_allumage")
        g = m.node_tree.nodes.get("BG_seuil")
        if s:
            s.inputs[1].default_value = strength
        if g:
            g.inputs[1].default_value = threshold
