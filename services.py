"""Equipements et usure de facade (v1.5) : descentes d'eau pluviale, grilles et gaines de ventilation, compteurs et
conduits, gaine d'extraction de restaurant, fenetres condamnees, et decalcomanies (tags, affiches, coulures,
fissures, vieilles publicites peintes).

Tout est tire avec un generateur separe (rng2) : le reste du batiment est identique a la version precedente.
Chaque element est place sur une zone libre de la facade (ni ouverture et ses appui / linteau, ni pilastre,
bandeau, bossage, chainage, perron, devanture, bow-window, escalier de secours, corniche) : pas de chevauchement."""
import math
from mathutils import Vector

from . import decals as DC

# envie de tags / affiches par style de base
TAG_RATE = {'walkup': 1.0, 'warehouse': 1.4, 'rowhouse': 0.35, 'prewar': 0.55, 'tower': 0.3, 'modern': 0.5}


class Face:
    """Facade vue par les equipements : repere, largeur, obstacles (rectangles u0, u1, v0, v1)."""

    def __init__(self, side, fr, W, spec, ops, blank, party, top_v, ground_v=0.0):
        self.side, self.fr, self.W, self.spec, self.ops = side, fr, W, spec, ops
        self.blank, self.party, self.top_v, self.ground_v = blank, party, top_v, ground_v
        self.obst = []           # rectangles interdits a tout
        self.relief = []         # (u0, u1, v0, v1, saillie) : reliefs devant lesquels un tuyau doit passer
        self.fe = None           # escalier de secours (u0, u1, v_bas)
        self.taken = []          # elements deja poses (tuyaux, grilles, decalques)

    def free(self, u0, u1, v0, v1, pad=0.04, fe=True, relief=True):
        if u0 < 0.02 or u1 > self.W - 0.02 or v0 < self.ground_v or v1 > self.top_v:
            return False
        rects = self.obst + self.taken + ([r[:4] for r in self.relief] if relief else [])
        if fe and self.fe:
            rects = rects + [(self.fe[0] - 0.1, self.fe[1] + 0.1, self.fe[2], 1e9)]
        for a0, a1, b0, b1 in rects:
            if u1 + pad > a0 and u0 - pad < a1 and v1 + pad > b0 and v0 - pad < b1:
                return False
        return True

    def standoff(self, u0, u1, v0, v1):
        """Saillie maximale des reliefs sur une bande (pour decoller un tuyau)."""
        s = 0.0
        for a0, a1, b0, b1, d in self.relief:
            if u1 > a0 and u0 < a1 and v1 > b0 and v0 < b1:
                s = max(s, d)
        return s


def collect(face, plan, zs, M):
    """Obstacles d'une facade a partir de son spec, de ses ouvertures et du plan."""
    sp = face.spec
    W = face.W
    for o in face.ops:
        arch = o.get('shape', 'rect') != 'rect'
        g = 0.3 if arch else 0.14
        face.obst.append((o['u0'] - g, o['u1'] + g, o['v0'] - 0.12, o['v1'] + min(0.4, o.get('top_room', 0.3)) + 0.02))
    pier = sp.get('piers')
    if pier and sp.get('bays'):
        from .facade import pier_spans
        for a, b in pier_spans(sp):
            face.relief.append((a, b, pier['v0'], pier['v1'], pier['d']))
    for v, bh, bd, key in sp.get('bands', []):
        face.relief.append((-1.0, W + 1.0, v, v + bh, max(bd, (pier['d'] + 0.04) if pier and abs(bd - pier['d']) < 0.02 else bd)))
    for fl in sp.get('floors', []):
        if fl.get('rustic'):
            face.relief.append((-1.0, W + 1.0, fl['v0'], fl['v0'] + fl['h'], 0.035))
    if plan.get('quoins') and not face.blank:
        qv0 = zs[1] if plan['ground'] in ('store', 'glass') else 0.0
        face.relief.append((-1.0, 0.65, qv0, face.top_v + 1, 0.035))
        face.relief.append((W - 0.65, W + 1.0, qv0, face.top_v + 1, 0.035))
    m = sp.get('margin', 0.0)
    gh = zs[1]
    if face.side == 'front':
        g = plan['ground']
        if g == 'store':
            face.obst.append((m * 0.5 - 0.12, W - m * 0.5 + 0.12, 0.0, gh + 0.08))
        elif g == 'lobby':
            face.obst.append((W * 0.3, W * 0.7, gh - 0.7, gh - 0.3))
        if g == 'stoop':
            from .building import _stoop_span
            u0, u1 = _stoop_span(plan)
            face.obst.append((u0 - 0.1, u1 + 0.1, 0.0, gh + 1.7))
        if plan.get('_oriel_span'):
            a, b = plan['_oriel_span']
            face.obst.append((a - 0.1, b + 0.1, gh - 0.6, face.top_v + 1.0))


# ------------------------------------------------------------------ equipements


def downspout(mb, face, u, v_top, key, detail):
    fr = face.fr
    r = 0.05
    w = face.standoff(u - 0.15, u + 0.15, 0.0, v_top + 0.5) + r + 0.02
    # descente + colliers
    p0 = fr.P(u, 0.45, w)
    p1 = fr.P(u, v_top, w)
    mb.cylinder((p0.x, p0.y), r, 0.45, v_top, key, n=8 if detail >= 1 else 6, cap_top=False)
    v = 1.6
    while v < v_top - 0.5 and detail >= 1:
        mb.cylinder((p0.x, p0.y), r + 0.012, v, v + 0.035, key, n=8, cap_top=True, cap_bot=True)
        mb.beam(fr.P(u, v + 0.0175, -0.02), fr.P(u, v + 0.0175, w - r), 0.025, key)
        v += 1.8
    # dauphin (coude au pied)
    mb.beam(fr.P(u, 0.5, w), fr.P(u, 0.06, w + 0.24), 0.095, key)
    # boite a eau (cuvette) sous le toit
    fr.box(u - 0.17, u + 0.17, v_top, v_top + 0.38, max(0.0, w - 0.12), w + 0.14, key, skip=('back',) if w - 0.12 <= 0.0 else ())
    if w - 0.12 > 0.01:
        mb.beam(fr.P(u, v_top + 0.3, -0.02), fr.P(u, v_top + 0.3, w - 0.12), 0.08, key)      # dauphine dans l'acrotere
    face.taken.append((u - 0.2, u + 0.2, 0.0, v_top + 0.4))


def louver(mb, face, u0, v0, wv, hv, detail):
    fr = face.fr
    fr.box(u0, u0 + wv, v0, v0 + hv, 0.0, 0.03, 'metal_galv')
    if detail >= 1:
        k = max(2, int(hv / 0.045))
        for i in range(k):
            vv = v0 + 0.025 + i * (hv - 0.05) / k
            fr.box(u0 + 0.025, u0 + wv - 0.025, vv, vv + 0.014, 0.03, 0.045, 'metal_galv')
    face.taken.append((u0, u0 + wv, v0, v0 + hv))


def hood(mb, face, u, v, detail):
    """Sortie de seche-linge / hotte : caisson et capot incline."""
    fr = face.fr
    fr.box(u - 0.09, u + 0.09, v, v + 0.16, 0.0, 0.05, 'metal_galv')
    fr.face([(u - 0.1, v + 0.17, 0.05), (u + 0.1, v + 0.17, 0.05), (u + 0.1, v + 0.06, 0.14), (u - 0.1, v + 0.06, 0.14)], 'metal_galv')
    fr.face([(u - 0.1, v + 0.06, 0.14), (u + 0.1, v + 0.06, 0.14), (u + 0.1, v + 0.17, 0.05), (u - 0.1, v + 0.17, 0.05)][::-1], 'metal_galv')
    face.taken.append((u - 0.11, u + 0.11, v, v + 0.18))


def meters(mb, face, u0, rng, detail):
    """Compteurs (gaz / electricite) et conduits au pied d'une facade."""
    fr = face.fr
    n = rng.randint(2, 4)
    w = 0.38
    for i in range(n):
        a = u0 + i * (w + 0.06)
        fr.box(a, a + w, 0.95, 1.45, 0.0, 0.2, 'metal_grey')
        if detail >= 1:
            fr.box(a + 0.08, a + w - 0.08, 1.2, 1.36, 0.2, 0.215, 'glass')
            mb.cylinder(tuple(fr.P(a + w / 2, 0, 0.1))[:2], 0.022, 0.0, 0.95, 'metal_galv', n=6, cap_top=False)
    span = n * (w + 0.06)
    # conduit vertical qui monte vers le premier etage
    c = fr.P(u0 + span + 0.05, 0, 0.04)
    mb.cylinder((c.x, c.y), 0.025, 0.3, 2.9, 'metal_dark', n=6)
    face.taken.append((u0 - 0.05, u0 + span + 0.12, 0.0, 2.95))


def exhaust(mb, face, u, v_top, detail):
    """Gaine d'extraction de cuisine (restaurant du rez-de-chaussee) montant le long de la facade arriere."""
    fr = face.fr
    s = 0.46
    w0 = max(face.standoff(u - s, u + s, 0.0, v_top), getattr(face, 'crown_proj', 0.0)) + 0.06
    fr.box(u - s / 2, u + s / 2, 2.4, v_top + 1.2, w0, w0 + s, 'metal_galv', skip=())
    fr.box(u - s / 2 - 0.05, u + s / 2 + 0.05, 1.7, 2.4, -0.0, w0 + s + 0.05, 'metal_galv', skip=('back',))   # caisson / coude
    if detail >= 1:
        v = 3.2
        while v < face.top_v - 0.1:
            fr.box(u - s / 2 - 0.02, u + s / 2 + 0.02, v, v + 0.05, w0 - 0.02, w0 + s + 0.02, 'metal_galv', skip=())
            mb.beam(fr.P(u, v + 0.025, -0.02), fr.P(u, v + 0.025, w0), 0.04, 'metal_dark')
            v += 2.5
        # chapeau au-dessus du toit
        fr.box(u - s / 2 - 0.08, u + s / 2 + 0.08, v_top + 1.2, v_top + 1.28, w0 - 0.08, w0 + s + 0.08, 'metal_galv', skip=())
    face.taken.append((u - s / 2 - 0.1, u + s / 2 + 0.1, 1.6, 1e9))


def board(mb, face, o):
    """Fenetre condamnee : panneau de contreplaque epousant le contour de l'ouverture, dans le tableau."""
    from .facade import opening_loop
    from .geom import offset_loop
    fr = face.fr
    d = o.get('depth', 0.18)
    loop, vs = opening_loop(o, 10)
    loop = offset_loop(loop, -0.012)
    fr.face([(p[0], p[1], -d * 0.35) for p in loop], 'wood_ply')


# ------------------------------------------------------------------ decalcomanies


def decal(mb, face, kind, idx, u0, v0, w_, h_, rnd, w=0.006, flip=False):
    a, b, c, d = DC.uv_rect(kind, idx)
    fr = face.fr
    pts = [fr.P(u0, v0, w), fr.P(u0 + w_, v0, w), fr.P(u0 + w_, v0 + h_, w), fr.P(u0, v0 + h_, w)]
    uv = [(a, b), (c, b), (c, d), (a, d)] if not flip else [(c, b), (a, b), (a, d), (c, d)]
    old = mb.tag
    mb.tag = 'decal'
    mb.face(pts, 'decal', uv=uv, rnd=rnd)
    mb.tag = old
    face.taken.append((u0, u0 + w_, v0, v0 + h_))


def _try(face, rng, wv, hv, vlo, vhi, tries=14, **kw):
    for _ in range(tries):
        if face.W - wv < 0.1 or vhi - hv < vlo:
            return None
        u0 = rng.uniform(0.05, face.W - wv - 0.05)
        v0 = rng.uniform(vlo, vhi - hv)
        if face.free(u0, u0 + wv, v0, v0 + hv, **kw):
            return u0, v0
    return None


def facade_services(mb, face, plan, zs, M, rng, detail, amount):
    """Equipements d'une facade (cote rue ou non). amount : taux de decalcomanies (0 a 1)."""
    side = face.side
    W = face.W
    n_fl = len(zs) - 1
    style = plan.get('style', 'walkup')
    rate = TAG_RATE.get(style, 0.7) * amount
    pipe_key = ['metal_galv', 'metal_dark', 'metal_grey'][rng.randrange(3)]
    if not face.blank:
        # 1. descentes d'eau pluviale : facade arriere et cotes ; en facade sur rue pour les immeubles de rapport
        want = {'back': 0.85, 'left': 0.5, 'right': 0.5, 'front': 0.35 if style in ('walkup', 'warehouse') else 0.12}[side]
        if plan.get('services', True) and rng.random() < want:
            for u in ((0.2, W - 0.2) if rng.random() < 0.5 else (W - 0.2, 0.2)):
                if face.top_v > 3.0 and face.free(u - 0.18, u + 0.18, 0.0, face.top_v, relief=False):
                    downspout(mb, face, u, face.top_v - 0.45, pipe_key, detail)
                    break
        if plan.get('services', True) and detail >= 1:
            # 2. gaine d'extraction de restaurant (commerce en pied d'immeuble) sur la facade arriere
            if side == 'back' and plan.get('ground') == 'store' and rng.random() < 0.55:
                us = [0.6 + k * 0.25 for k in range(int((W - 1.2) / 0.25))]
                rng.shuffle(us)
                for u in us:
                    if face.free(u - 0.35, u + 0.35, 1.6, face.top_v, relief=False):
                        exhaust(mb, face, u, getattr(face, 'crown_top', face.top_v), detail)
                        break
            # 3. grilles de ventilation et sorties de seche-linge entre les fenetres
            k_vents = {'back': 6, 'left': 3, 'right': 3, 'front': 1}[side]
            for _ in range(k_vents):
                if rng.random() < 0.6:
                    fl = rng.randrange(1, max(2, n_fl - 1))
                    if fl >= len(zs) - 1:
                        continue
                    v_lo, v_hi = zs[fl] + 0.25, zs[fl + 1] - 0.25
                    if rng.random() < 0.5:
                        p = _try(face, rng, 0.32, 0.24, v_lo, v_hi, 8)
                        if p:
                            louver(mb, face, p[0], p[1], 0.32, 0.24, detail)
                    else:
                        p = _try(face, rng, 0.22, 0.2, v_lo, v_hi, 8)
                        if p:
                            hood(mb, face, p[0] + 0.11, p[1], detail)
            # 4. compteurs au pied de la facade arriere ou d'un cote
            if side in ('back', 'left', 'right') and rng.random() < (0.6 if side == 'back' else 0.25):
                for _ in range(10):
                    u0 = rng.uniform(0.4, max(0.5, W - 2.2))
                    if face.free(u0 - 0.1, u0 + 1.9, 0.0, 3.0):
                        meters(mb, face, u0, rng, detail)
                        break
        # 5. fenetres condamnees (entrepots, arrieres d'immeubles de rapport)
        p_board = {'warehouse': 0.04, 'walkup': 0.012}.get(style, 0.0) * (1.6 if side != 'front' else 1.0) * amount * 2
        for o in face.ops:
            small = (o['u1'] - o['u0']) <= 1.5 and (o['v1'] - o['v0']) <= 2.5
            if small and o.get('frame') in ('sash', 'grid', 'fixed') and not o.get('_ac') and rng.random() < p_board:
                board(mb, face, o)
        # 6. coulures sous les appuis (eau sale) : quelques fenetres, a tous les etages
        for o in face.ops:
            if o.get('frame') in ('sash', 'grid', 'fixed') and rng.random() < 0.18 * (0.4 + amount):
                ww = (o['u1'] - o['u0']) + 0.1
                hh = rng.uniform(0.7, 1.6)
                v1 = o['v0'] - 0.085
                u0 = o['u0'] - 0.05
                if face.free(u0, u0 + ww, v1 - hh, o['v0'] - 0.125, pad=0.0, fe=False):
                    decal(mb, face, 'streak', rng.randrange(DC.count('streak')), u0, v1 - hh, ww, hh, rng.random())
        # 7. fissures
        for _ in range(int(rng.random() * 3 * amount + 0.3)):
            hh = rng.uniform(0.8, 2.2)
            p = _try(face, rng, hh * 0.5, hh, 0.3, face.top_v, 10, fe=False)
            if p:
                decal(mb, face, 'crack', rng.randrange(DC.count('crack')), p[0], p[1], hh * 0.5, hh, rng.random(), flip=rng.random() < 0.5)
    # 8. tags et affiches au niveau de la rue (facades exposees, pas les murs mitoyens)
    if face.party or amount <= 0:
        return
    n_tags = int(rng.random() * 4 * rate + rate * 0.8)
    for _ in range(n_tags):
        wv = rng.uniform(0.9, 2.2)
        p = _try(face, rng, wv, wv / 4, 0.35, min(3.2, face.top_v), 14, fe=False)
        if p:
            decal(mb, face, 'tag', rng.randrange(DC.count('tag')), p[0], p[1], wv, wv / 4, rng.random(), flip=False)
    if rng.random() < 0.6 * rate:
        sz = rng.uniform(1.0, 1.9)
        p = _try(face, rng, sz, sz, 0.4, min(3.0, face.top_v), 12, fe=False)
        if p:
            decal(mb, face, 'poster', rng.randrange(DC.count('poster')), p[0], p[1], sz, sz, rng.random())
    if rng.random() < 0.5 * rate:
        sz = rng.uniform(0.5, 0.9)
        p = _try(face, rng, sz, sz, 0.8, 2.4, 10, fe=False)
        if p:
            decal(mb, face, 'sticker', 0, p[0], p[1], sz, sz, rng.random())
    # 9. mur aveugle expose : vieille publicite peinte en hauteur, tags et affiches en bas
    if face.blank and face.top_v > 9 and W > 10 and style in ('walkup', 'warehouse', 'prewar') and rng.random() < 0.55:
        ww = min(W * 0.75, rng.uniform(7, 14))
        hh = ww * 0.5
        p = _try(face, rng, ww, hh, max(5.0, face.top_v * 0.45), face.top_v - 0.6, 8, fe=False)
        if p:
            decal(mb, face, 'ghost', 0, p[0], p[1], ww, hh, rng.random() * 0.6)


def garage_tags(mb, face, rng, amount):
    """Tags sur les rideaux metalliques des quais (devant les lames)."""
    for o in face.ops:
        if o.get('frame') == 'garage' and rng.random() < 0.7 * amount:
            d = o.get('depth', 0.35)
            w = -d * 0.6 + 0.026
            wv = min(o['u1'] - o['u0'] - 0.2, rng.uniform(1.2, 2.4))
            if wv < 0.6:
                continue
            u0 = rng.uniform(o['u0'] + 0.1, o['u1'] - 0.1 - wv)
            v0 = rng.uniform(o['v0'] + 0.3, max(o['v0'] + 0.31, min(o['v1'] - wv / 4 - 0.1, o['v0'] + 2.0)))
            decal(mb, face, 'tag', rng.randrange(DC.count('tag')), u0, v0, wv, wv / 4, rng.random(), w=w)


# ------------------------------------------------------------------ toit


def roof_items(plan, rng2, detail):
    """Elements de toit supplementaires (tirage rng2) : colonnes de ventilation de plomberie, gaines sur supports."""
    from . import props as PR
    items = []
    if not plan.get('services', True):
        return items
    for _ in range(rng2.randint(1, 4)):
        items.append(lambda mb_, x, y, zz, r: PR.stack(mb_, x, y, zz, r, detail))
    if detail >= 1 and rng2.random() < 0.5:
        items.append(lambda mb_, x, y, zz, r: PR.duct_run(mb_, x, y, zz, r, detail))
    return items
