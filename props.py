"""Accessoires : chateau d'eau, clims, edicule d'escalier, ventilations, antenne, lanterneau, escalier de secours."""
import math
from mathutils import Vector


def water_tower(mb, x, y, z, rng, detail=1):
    r = rng.uniform(1.5, 2.1)
    leg_h = rng.uniform(2.2, 3.6)
    tank_h = rng.uniform(3.2, 4.4)
    mb.mass.append(('tower', x, y, z, r, leg_h, tank_h))
    n = 16 if detail >= 1 else 10
    # pieds + entretoises
    for a in range(4):
        ang = math.pi / 4 + a * math.pi / 2
        px, py = x + math.cos(ang) * r * 0.75, y + math.sin(ang) * r * 0.75
        mb.box((px - 0.11, py - 0.11, z), (px + 0.11, py + 0.11, z + leg_h), 'metal_dark')
    if detail >= 1:
        for a in range(4):
            a0 = math.pi / 4 + a * math.pi / 2
            a1 = a0 + math.pi / 2
            p0 = Vector((x + math.cos(a0) * r * 0.75, y + math.sin(a0) * r * 0.75, z + 0.3))
            p1 = Vector((x + math.cos(a1) * r * 0.75, y + math.sin(a1) * r * 0.75, z + leg_h - 0.2))
            mb.beam(p0, p1, 0.05, 'metal_dark')
            mb.beam(Vector((p1.x, p1.y, z + 0.3)), Vector((p0.x, p0.y, z + leg_h - 0.2)), 0.05, 'metal_dark')
    # plateforme
    mb.cylinder((x, y), r + 0.25, z + leg_h, z + leg_h + 0.15, 'metal_dark', n=n, cap_bot=True)
    # cuve en douelles + cerclages
    zt = z + leg_h + 0.15
    mb.cylinder((x, y), r, zt, zt + tank_h, 'wood_tank', n=n, cap_top=False)
    if detail >= 1:
        for k in range(int(tank_h / 0.55)):
            zz = zt + 0.3 + k * 0.55
            mb.cylinder((x, y), r + 0.025, zz, zz + 0.05, 'metal_dark', n=n, cap_top=False)
    # toit conique + chapeau
    mb.cone((x, y), r + 0.12, zt + tank_h, zt + tank_h + r * 0.6, 'metal_dark', n=n)
    mb.cylinder((x, y), 0.12, zt + tank_h + r * 0.55, zt + tank_h + r * 0.75, 'metal_dark', n=6)
    # echelle
    if detail >= 1:
        ax, ay = x + r + 0.05, y
        for side in (-0.2, 0.2):
            mb.box((ax, ay + side - 0.02, z), (ax + 0.04, ay + side + 0.02, zt + tank_h), 'metal_dark')
        for k in range(int((zt + tank_h - z) / 0.35)):
            zz = z + 0.2 + k * 0.35
            mb.box((ax, ay - 0.2, zz), (ax + 0.04, ay + 0.2, zz + 0.03), 'metal_dark')
    return r + 0.4


def ac_unit(mb, x, y, z, rng, detail=1):
    w, d, h = rng.uniform(1.0, 2.2), rng.uniform(0.9, 1.6), rng.uniform(0.7, 1.3)
    mb.box((x - w / 2, y - d / 2, z), (x + w / 2, y + d / 2, z + 0.12), 'metal_dark')
    mb.box((x - w / 2 + 0.03, y - d / 2 + 0.03, z + 0.12), (x + w / 2 - 0.03, y + d / 2 - 0.03, z + h), 'metal_grey')
    if detail >= 1:
        nf = 1 if w < 1.4 else 2
        for k in range(nf):
            fx = x - w / 2 + w * (k + 0.5) / nf
            rr = min(w / nf, d) * 0.36
            mb.cylinder((fx, y), rr, z + h, z + h + 0.05, 'metal_dark', n=12)
            mb.cylinder((fx, y), rr * 0.25, z + h + 0.05, z + h + 0.09, 'metal_galv', n=8)
        # grille laterale
        for k in range(6):
            zz = z + 0.2 + k * (h - 0.3) / 6
            mb.box((x - w / 2, y - d / 2 - 0.02, zz), (x + w / 2, y - d / 2 + 0.02, zz + 0.03), 'metal_galv')
    return max(w, d) / 2 + 0.3


def vent(mb, x, y, z, rng, detail=1):
    kind = rng.random()
    if kind < 0.45:
        r = rng.uniform(0.12, 0.25)
        h = rng.uniform(0.6, 1.6)
        mb.cylinder((x, y), r, z, z + h, 'metal_galv', n=8 if detail else 6)
        mb.cylinder((x, y), r * 1.5, z + h, z + h + 0.08, 'metal_galv', n=8)
        mb.cone((x, y), r * 1.6, z + h + 0.08, z + h + 0.3, 'metal_galv', n=8)
        return r + 0.2
    if kind < 0.8:
        s = rng.uniform(0.5, 0.9)
        mb.box((x - s / 2, y - s / 2, z), (x + s / 2, y + s / 2, z + 0.25), 'metal_galv')
        mb.cylinder((x, y), s * 0.42, z + 0.25, z + 0.5, 'metal_galv', n=12)
        mb.cylinder((x, y), s * 0.5, z + 0.5, z + 0.62, 'metal_galv', n=12)
        return s / 2 + 0.2
    # gaine coudee
    w = rng.uniform(0.4, 0.7)
    l = rng.uniform(1.0, 2.5)
    mb.box((x - w / 2, y - w / 2, z), (x + w / 2, y + w / 2, z + 1.0), 'metal_galv')
    mb.box((x - w / 2, y - w / 2, z + 1.0 - w), (x + w / 2 + l, y + w / 2, z + 1.0), 'metal_galv')
    return l / 2 + 0.6


def bulkhead(mb, x0, y0, x1, y1, z, h, wall, rng, detail=1):
    """Edicule (sortie d'escalier / machinerie d'ascenseur) avec porte et couronnement."""
    mb.mass.append(('box', (x0, y0, x1, y1), z, z + h + 0.15))
    mb.box((x0, y0, z), (x1, y1, z + h), wall, skip=('-z',))
    mb.box((x0 - 0.08, y0 - 0.08, z + h), (x1 + 0.08, y1 + 0.08, z + h + 0.15), 'trim_stone')
    # porte sur la face -y
    cx = (x0 + x1) / 2
    mb.box((cx - 0.45, y0 - 0.04, z), (cx + 0.45, y0 + 0.01, z + 2.1), 'metal_door', skip=('-z', '+y'))
    if detail >= 1:
        mb.box((cx - 0.55, y0 - 0.06, z + 2.1), (cx + 0.55, y0, z + 2.25), 'trim_stone', skip=('+y',))
    return h


def antenna(mb, x, y, z, rng, h=None):
    h = h or rng.uniform(5, 14)
    mb.mass.append(('mast', x, y, z, z + h))
    mb.box((x - 0.06, y - 0.06, z), (x + 0.06, y + 0.06, z + h), 'metal_grey')
    for k in range(3):
        zz = z + h * (0.4 + 0.2 * k)
        mb.box((x - 0.6, y - 0.03, zz), (x + 0.6, y + 0.03, zz + 0.05), 'metal_grey')


def skylight(mb, x, y, z, rng):
    w, d = rng.uniform(1.0, 2.5), rng.uniform(0.8, 1.6)
    mb.box((x - w / 2, y - d / 2, z), (x + w / 2, y + d / 2, z + 0.35), 'metal_grey', skip=('+z', '-z'))
    mb.face([Vector((x - w / 2, y - d / 2, z + 0.35)), Vector((x + w / 2, y - d / 2, z + 0.35)), Vector((x + w / 2, y + d / 2, z + 0.6)), Vector((x - w / 2, y + d / 2, z + 0.6))], 'glass')
    mb.face([Vector((x - w / 2, y + d / 2, z + 0.35)), Vector((x - w / 2, y - d / 2, z + 0.35)), Vector((x - w / 2, y + d / 2, z + 0.6))], 'metal_grey')
    mb.face([Vector((x + w / 2, y - d / 2, z + 0.35)), Vector((x + w / 2, y + d / 2, z + 0.35)), Vector((x + w / 2, y + d / 2, z + 0.6))], 'metal_grey')
    mb.face([Vector((x + w / 2, y + d / 2, z + 0.35)), Vector((x - w / 2, y + d / 2, z + 0.35)), Vector((x - w / 2, y + d / 2, z + 0.6)), Vector((x + w / 2, y + d / 2, z + 0.6))], 'metal_grey')
    return max(w, d) / 2 + 0.2


def chimney(mb, x, y, z, rng, wall):
    w = rng.uniform(0.5, 0.9)
    h = rng.uniform(1.0, 2.2)
    mb.box((x - w / 2, y - w / 2, z), (x + w / 2, y + w / 2, z + h), wall, skip=('-z',))
    mb.box((x - w / 2 - 0.06, y - w / 2 - 0.06, z + h), (x + w / 2 + 0.06, y + w / 2 + 0.06, z + h + 0.12), 'trim_stone')
    for k in range(2 if w > 0.7 else 1):
        mb.cylinder((x - w / 4 + k * w / 2 if w > 0.7 else x, y), 0.09, z + h + 0.12, z + h + 0.4, 'terracotta', n=8)
    return w / 2 + 0.2


def scatter_roof(mb, rect, z, rng, items, blocked=(), detail=1):
    """Place des accessoires sans chevauchement dans rect=(x0, y0, x1, y1). items : liste de fonctions
    f(mb, x, y, z, rng) -> rayon. blocked : disques (x, y, r) deja occupes."""
    x0, y0, x1, y1 = rect
    disks = list(blocked)
    for f in items:
        for _ in range(25):
            x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
            # rayon d'essai prudent avant construction
            if all((x - a) ** 2 + (y - b) ** 2 > (r + 1.3) ** 2 for a, b, r in disks):
                tmp_len, tmp_v, tmp_m = len(mb.faces), len(mb.verts), len(mb.mass)
                r = f(mb, x, y, z, rng)
                ok_x = x0 - 0.01 <= x - r * 0.6 and x + r * 0.6 <= x1 + 0.01 and y0 - 0.01 <= y - r * 0.6 and y + r * 0.6 <= y1 + 0.01
                if not ok_x:
                    # on retire ce qui vient d'etre ajoute
                    del mb.faces[tmp_len:]; del mb.uvs[tmp_len:]; del mb.mats[tmp_len:]; del mb.rand[tmp_len:]; del mb.tags[tmp_len:]
                    del mb.verts[tmp_v:]; del mb.mass[tmp_m:]
                    continue
                disks.append((x, y, r))
                break
    return disks


def fire_escape(fr, mb, u0, u1, levels, ground_v, detail=1, key='fire_escape', w0=0.0, hang_first=False, ladder_min=None):
    """Escalier de secours accroche a une facade (repere fr), de u0 a u1, paliers aux hauteurs levels.
    w0 : ecart au mur (devant pilastres, bandeaux, linteaux) ; hang_first : le premier palier est suspendu par des
    tirants montant au mur (au-dessus d'une devanture) ; ladder_min : bas de l'echelle (au-dessus des auvents)."""
    from .geom import Frame
    wall = fr
    fr = Frame(mb, wall.P(0.0, 0.0, w0), wall.T, wall.u0)
    dpt = 1.15
    t = 0.05
    rail_h = 1.0
    W = u1 - u0
    for i, v in enumerate(levels):
        # plancher en caillebotis (plaque + longerons)
        fr.box(u0, u1, v - 0.06, v, 0.0, dpt, key, skip=('back',))
        if detail >= 1:
            fr.box(u0, u1, v - 0.14, v - 0.06, dpt - 0.06, dpt, key, skip=('back',))
            for uu in (u0 + 0.05, u1 - 0.1):
                if i == 0 and hang_first:
                    mb.beam(fr.P(uu, v - 0.03, dpt - 0.05), wall.P(uu, v + 1.3, 0.02), 0.035, key)   # tirant
                else:
                    mb.beam(fr.P(uu, v - 0.1, dpt - 0.05), wall.P(uu, v - 0.9, 0.02), 0.05, key)     # console
                if w0 > 0.02 and not (i == 0 and hang_first):
                    mb.beam(wall.P(uu, v - 0.097, -0.02), fr.P(uu, v - 0.097, 0.05), 0.055, key)    # patte de fixation
        # garde-corps
        fr.box(u0, u1, v + rail_h - t, v + rail_h, dpt - t, dpt, key, skip=())
        fr.box(u0, u1, v + rail_h * 0.5 - t / 2, v + rail_h * 0.5 + t / 2, dpt - t * 0.6, dpt, key, skip=())
        for uu in (u0, u1 - t):
            fr.box(uu, uu + t, v + rail_h * 0.5, v + rail_h, 0.0, t, key, skip=())
            fr.box(uu, uu + t, v + rail_h - t, v + rail_h, 0.0, dpt, key, skip=())
        step = 0.13 if detail >= 2 else (0.3 if detail == 1 else 0.0)
        if step > 0:
            nb = int(W / step)
            for k in range(nb + 1):
                uu = u0 + k * W / max(1, nb)
                fr.box(uu - 0.012, uu + 0.012, v, v + rail_h, dpt - 0.03, dpt - 0.006, key, skip=())
        else:
            fr.box(u0, u1, v + 0.05, v + rail_h - 0.05, dpt - 0.02, dpt - 0.015, key, skip=())
        # escalier vers le palier inferieur (en sens alterne)
        if i > 0:
            vb = levels[i - 1]
            a, b = (u0 + 0.15, u0 + 0.15 + 2.2) if i % 2 else (u1 - 0.15 - 2.2, u1 - 0.15)
            a = max(a, u0 + 0.05); b = min(b, u1 - 0.05)
            top_u, bot_u = (a, b) if i % 2 else (b, a)
            for ww in (dpt * 0.35, dpt * 0.92):
                mb.beam(fr.P(top_u, v, ww), fr.P(bot_u, vb + 0.02, ww), 0.06, key)
            if detail >= 1:
                ns = int((v - vb) / 0.22)
                for k in range(1, ns):
                    s = k / ns
                    uu = top_u + (bot_u - top_u) * s
                    vv = v + (vb - v) * s
                    fr.box(uu - 0.12, uu + 0.12, vv - 0.03, vv, dpt * 0.35, dpt * 0.92, key, skip=())
                mb.beam(fr.P(top_u, v + rail_h * 0.9, dpt * 0.92), fr.P(bot_u, vb + rail_h * 0.9, dpt * 0.92), 0.04, key)
    # echelle escamotable sous le premier palier
    vb = None
    if levels:
        v = levels[0]
        lu = u1 - 0.7
        vb = max(ground_v + 2.4, v - 3.2, ladder_min if ladder_min is not None else -1e9)
        vb = min(vb, v - 0.6)
        for uu in (lu - 0.22, lu + 0.22):
            fr.box(uu - 0.02, uu + 0.02, vb, v, dpt - 0.25, dpt - 0.2, key, skip=())
        for k in range(int((v - vb) / 0.3)):
            vv = vb + 0.15 + k * 0.3
            fr.box(lu - 0.22, lu + 0.22, vv, vv + 0.025, dpt - 0.25, dpt - 0.2, key, skip=())
    return vb


def stack(mb, x, y, z, rng, detail=1):
    """Colonne de ventilation de plomberie (tube et solin)."""
    r = rng.uniform(0.04, 0.07)
    h = rng.uniform(0.45, 1.0)
    mb.cylinder((x, y), r * 2.4, z, z + 0.05, 'roof_flat', n=8)
    mb.cylinder((x, y), r, z + 0.05, z + h, 'metal_dark' if rng.random() < 0.6 else 'metal_galv', n=8 if detail >= 1 else 6, cap_top=True)
    return r * 2.4 + 0.15


def duct_run(mb, x, y, z, rng, detail=1):
    """Gaine rectangulaire posee sur des traverses, coudee dans la toiture aux deux bouts."""
    L = rng.uniform(2.0, 4.5)
    s = rng.uniform(0.3, 0.45)
    along_x = rng.random() < 0.5
    h0 = 0.28
    def B(a0, a1, b0, b1, z0, z1, key):
        if along_x:
            mb.box((x + a0, y + b0, z0), (x + a1, y + b1, z1), key)
        else:
            mb.box((x + b0, y + a0, z0), (x + b1, y + a1, z1), key)
    B(-L / 2, L / 2, -s / 2, s / 2, z + h0, z + h0 + s, 'metal_galv')
    for e in (-L / 2, L / 2 - s):
        B(e, e + s, -s / 2, s / 2, z, z + h0, 'metal_galv')                  # coudes vers le toit
    k = max(1, int(L / 1.4))
    for i in range(1, k):
        a = -L / 2 + L * i / k
        B(a - 0.05, a + 0.05, -s / 2 - 0.12, s / 2 + 0.12, z, z + h0, 'metal_dark')   # traverses
    return (L / 2 + 0.35) / 0.6                      # scatter_roof verifie l'emprise avec 0,6 x rayon
