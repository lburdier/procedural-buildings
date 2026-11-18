"""Facades : trame de travees x etages, ouvertures percees sans booleen, details de fenetres.

Une ouverture est un dict : u0, u1, v0, v1 (rectangle englobant), shape 'rect' | 'arch' | 'segment', rise
(fleche de l'arc segmentaire), depth (profondeur du tableau), frame ('sash', 'grid', 'fixed', 'storefront',
'door', 'garage', 'none'), grid (colonnes, rangees), sill (bool), lintel ('flat', 'key', 'none'), band (bandeau
d'arc), surround (bool), trim / glass / frame_key / door_key (cles de materiau), ac (clim de fenetre), detail (0-2)."""
import math
from mathutils import Vector
from .geom import offset_loop

EPS = 1e-5


def opening_loop(op, n_arc=10):
    """Contour (u, v) de l'ouverture, sens trigonometrique, en partant du coin bas gauche.
    Renvoie (points, indice du premier point de l'arc/haut, indice du dernier, hauteur de naissance)."""
    u0, u1, v0, v1 = op['u0'], op['u1'], op['v0'], op['v1']
    shape = op.get('shape', 'rect')
    if shape == 'arch':
        r = (u1 - u0) / 2
        vs = v1 - r
        cx = (u0 + u1) / 2
        arc = [(cx + r * math.cos(math.pi * k / n_arc), vs + r * math.sin(math.pi * k / n_arc)) for k in range(n_arc + 1)]
        arc[0] = (u1, vs); arc[-1] = (u0, vs)
        return [(u0, v0), (u1, v0)] + arc, vs
    if shape == 'segment':
        c = (u1 - u0) / 2
        h = max(0.02, min(op.get('rise', 0.2), c * 0.9))
        R = (c * c + h * h) / (2 * h)
        cx, cy = (u0 + u1) / 2, v1 - R
        a = math.asin(min(1.0, c / R))
        n = max(4, n_arc // 2)
        arc = [(cx + R * math.cos(math.pi / 2 - a + 2 * a * k / n), cy + R * math.sin(math.pi / 2 - a + 2 * a * k / n)) for k in range(n + 1)]
        arc[0] = (u1, v1 - h); arc[-1] = (u0, v1 - h)
        return [(u0, v0), (u1, v0)] + arc, v1 - h
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], v1


def wall_cell(fr, cu0, cv0, cu1, cv1, key, op=None, n_arc=10):
    """Panneau de mur [cu0, cu1] x [cv0, cv1], perce de l'ouverture op (anneau de quads). Renvoie le contour."""
    if op is None:
        fr.quad(cu0, cv0, cu1, cv1, key)
        return None
    loop, vs = opening_loop(op, n_arc)
    BL, BR = loop[0], loop[1]
    arc = loop[2:]
    pairs = [(BL, (cu0, cv0)), (BR, (cu1, cv0)), (arc[0], (cu1, arc[0][1])), (arc[0], (cu1, cv1))]
    for p in arc[1:-1]:
        pairs.append((p, (p[0], cv1)))
    pairs += [(arc[-1], (cu0, cv1)), (arc[-1], (cu0, arc[-1][1]))]
    n = len(pairs)
    for i in range(n):
        (ia, oa), (ib, ob) = pairs[i], pairs[(i + 1) % n]
        pts = [oa, ob, ib, ia]
        clean = []
        for p in pts:
            if not clean or (abs(p[0] - clean[-1][0]) > EPS or abs(p[1] - clean[-1][1]) > EPS):
                clean.append(p)
        if len(clean) > 1 and abs(clean[0][0] - clean[-1][0]) < EPS and abs(clean[0][1] - clean[-1][1]) < EPS:
            clean.pop()
        if len(clean) < 3:
            continue
        # aire signee : on saute les faces degenerees (porte posee au sol : bas d'anneau nul)
        area = 0.0
        for k in range(len(clean)):
            x0, y0 = clean[k]; x1, y1 = clean[(k + 1) % len(clean)]
            area += x0 * y1 - x1 * y0
        if area * 0.5 < 1e-5:
            continue
        fr.face([(p[0], p[1], 0.0) for p in clean], key)
    return loop, vs


def window(fr, op, loop, vs, rng, detail=1):
    """Tableau, vitrage, menuiserie, appui, linteau / arc, clim. loop : contour renvoye par wall_cell."""
    d = op.get('depth', 0.18)
    wall = op['wall']
    trim = op.get('trim', 'trim_stone')
    fk = op.get('frame_key', 'frame_dark')
    gk = op.get('glass', 'glass')
    kind = op.get('frame', 'sash')
    rnd = rng.random()
    n = len(loop)
    # tableau (retour de mur)
    for i in range(n):
        a, b = loop[i], loop[(i + 1) % n]
        if abs(a[0] - b[0]) < EPS and abs(a[1] - b[1]) < EPS:
            continue
        fr.face([(a[0], a[1], 0.0), (b[0], b[1], 0.0), (b[0], b[1], -d), (a[0], a[1], -d)], wall)
    u0, u1, v0, v1 = op['u0'], op['u1'], op['v0'], op['v1']
    W, H = u1 - u0, v1 - v0
    fw = op.get('frame_w', 0.06 if kind not in ('storefront', 'garage') else 0.08)
    fd = 0.05
    wg = -d                                # plan du vitrage
    wf = -d + fd                           # face avant de la menuiserie
    if kind == 'door':
        _door(fr, op, loop, vs, d, rng)
    elif kind == 'garage':
        _garage(fr, op, d)
    else:
        fr.face([(p[0], p[1], wg) for p in loop], gk, rnd)
        if kind != 'none' and detail >= 1:
            inner = offset_loop(loop, -fw)
            m = len(loop)
            for i in range(m):
                a, b = loop[i], loop[(i + 1) % m]
                ia, ib = inner[i], inner[(i + 1) % m]
                if abs(a[0] - b[0]) < EPS and abs(a[1] - b[1]) < EPS:
                    continue
                fr.face([(a[0], a[1], wf), (b[0], b[1], wf), (ib[0], ib[1], wf), (ia[0], ia[1], wf)], fk)
                fr.face([(ia[0], ia[1], wf), (ib[0], ib[1], wf), (ib[0], ib[1], wg), (ia[0], ia[1], wg)], fk)
            _muntins(fr, op, kind, vs, fw, wg, wf, fk, detail)
    # appui
    if op.get('sill', True) and kind not in ('door', 'garage', 'storefront'):
        fr.box(u0 - 0.07, u1 + 0.07, v0 - 0.08, v0 + 0.005, -0.03, 0.07, trim)
    # linteau / arc
    lt = op.get('lintel', 'flat')
    top_room = op.get('top_room', 0.4)
    if op.get('shape', 'rect') == 'rect':
        if lt in ('flat', 'key') and top_room > 0.12:
            lh = min(0.28, top_room - 0.04)
            fr.box(u0 - 0.1, u1 + 0.1, v1, v1 + lh, 0.0, 0.035, trim)
            if lt == 'key' and detail >= 1:
                cx = (u0 + u1) / 2
                fr.box(cx - 0.11, cx + 0.11, v1 - 0.04, v1 + min(lh + 0.06, top_room - 0.02), 0.035, 0.075, trim)
    elif op.get('band', True) and top_room > 0.1:
        _arch_band(fr, loop, vs, min(0.24, top_room - 0.03), trim, key_stone=(lt == 'key' and detail >= 1))
    if op.get('surround') and kind not in ('door', 'garage'):
        sw = 0.11
        fr.box(u0 - sw, u0, v0, vs, 0.0, 0.03, trim)
        fr.box(u1, u1 + sw, v0, vs, 0.0, 0.03, trim)
    if op.get('ac') and rng.random() < op['ac'] and kind == 'sash' and W > 0.7:
        cx = (u0 + u1) / 2
        aw = min(0.36, W / 2 - 0.05)
        fr.box(cx - aw, cx + aw, v0 + 0.02, v0 + 0.44, -0.3, 0.22, 'ac_unit', skip=())
        if detail >= 2:
            for k in range(5):
                vv = v0 + 0.08 + k * 0.065
                fr.box(cx - aw + 0.04, cx + aw - 0.04, vv, vv + 0.02, 0.22, 0.235, 'metal_dark')


def _muntins(fr, op, kind, vs, fw, wg, wf, fk, detail):
    u0, u1, v0 = op['u0'] + fw, op['u1'] - fw, op['v0'] + fw
    top = vs - (fw if op.get('shape', 'rect') == 'rect' else 0.0)
    bw = 0.045
    w1 = wg + (wf - wg) * 0.8
    if kind == 'sash':
        vm = v0 + (top - v0) * 0.5
        fr.box(u0, u1, vm - 0.035, vm + 0.035, wg, wf + 0.01, fk, skip=('back',))
        cols = op.get('grid', (1, 1))[0]
        if detail >= 2 and cols > 1:
            for c in range(1, cols):
                uc = u0 + (u1 - u0) * c / cols
                fr.box(uc - bw / 2, uc + bw / 2, v0, top, wg, w1, fk)
    elif kind in ('grid', 'storefront'):
        cols, rows = op.get('grid', (2, 2))
        if kind == 'storefront':
            cols = max(1, int(round((u1 - u0) / 1.3)))
            rows = 1
            vt = v0 + (top - v0) * 0.78                     # imposte
            fr.box(u0, u1, vt - 0.05, vt + 0.05, wg, wf, fk)
            fr.box(u0, u1, v0, v0 + 0.45, wg, wf, op.get('door_key', 'frame_dark'))   # soubassement
        for c in range(1, cols):
            uc = u0 + (u1 - u0) * c / cols
            fr.box(uc - bw / 2, uc + bw / 2, v0, top, wg, w1, fk)
        if kind == 'grid':
            for r in range(1, rows):
                vr = v0 + (top - v0) * r / rows
                fr.box(u0, u1, vr - bw / 2, vr + bw / 2, wg, w1, fk)
    if op.get('shape', 'rect') != 'rect':
        fr.box(u0, u1, vs - 0.035, vs + 0.035, wg, wf, fk)        # imposte a la naissance de l'arc
        if detail >= 2 and op['shape'] == 'arch':
            cx, r = (op['u0'] + op['u1']) / 2, (op['u1'] - op['u0']) / 2 - fw
            for ang in (math.pi / 4, math.pi / 2, 3 * math.pi / 4):
                a = Vector((cx, vs)); b = Vector((cx + r * math.cos(ang), vs + r * math.sin(ang)))
                t = (b - a).normalized(); nrm = Vector((-t.y, t.x)) * (bw / 2)
                fr.face([(a.x - nrm.x, a.y - nrm.y, w1), (b.x - nrm.x, b.y - nrm.y, w1), (b.x + nrm.x, b.y + nrm.y, w1), (a.x + nrm.x, a.y + nrm.y, w1)], fk)


def _arch_band(fr, loop, vs, bw, trim, key_stone=False):
    arc = [p for p in loop[2:]]
    cx = (arc[0][0] + arc[-1][0]) / 2
    # centre de l'arc (plein cintre : naissance ; segmentaire : sous la naissance)
    top = max(p[1] for p in arc)
    half = (arc[0][0] - arc[-1][0]) / 2
    rise = top - vs
    R = (half * half + rise * rise) / (2 * rise) if rise > 1e-4 else half
    cy = top - R
    outer = []
    for p in arc:
        dv = Vector((p[0] - cx, p[1] - cy))
        dv = dv.normalized() * (dv.length + bw) if dv.length > 1e-6 else dv
        outer.append((cx + dv.x, cy + dv.y))
    t = 0.035
    for i in range(len(arc) - 1):
        a, b, A, B = arc[i], arc[i + 1], outer[i], outer[i + 1]
        fr.face([(a[0], a[1], t), (A[0], A[1], t), (B[0], B[1], t), (b[0], b[1], t)], trim)
        fr.face([(A[0], A[1], 0), (B[0], B[1], 0), (B[0], B[1], t), (A[0], A[1], t)], trim)
        fr.face([(b[0], b[1], 0), (a[0], a[1], 0), (a[0], a[1], t), (b[0], b[1], t)], trim)
    if key_stone:
        ks = 0.12
        fr.box(cx - ks, cx + ks, top - 0.05, top + bw + 0.05, 0.0, 0.075, trim)


def _door(fr, op, loop, vs, d, rng):
    u0, u1, v0 = op['u0'], op['u1'], op['v0']
    dk = op.get('door_key', 'wood_green')
    gk = op.get('glass', 'glass')
    w = -d + 0.03
    top = vs
    fr.face([(p[0], p[1], -d) for p in loop], gk)
    fw = 0.08
    # dormant
    fr.box(u0, u0 + fw, v0, top, -d, w, 'frame_dark')
    fr.box(u1 - fw, u1, v0, top, -d, w, 'frame_dark')
    fr.box(u0, u1, top - fw, top, -d, w, 'frame_dark')
    # vantail(x) : panneau plein en bas, vitre en haut
    leaves = 2 if (u1 - u0) > 1.5 else 1
    lw = (u1 - u0 - 2 * fw) / leaves
    for k in range(leaves):
        a = u0 + fw + k * lw
        b = a + lw
        hp = (top - fw - v0) * 0.45
        fr.box(a + 0.01, b - 0.01, v0, v0 + hp, -d, w, dk)
        fr.box(a + 0.01, a + 0.09, v0 + hp, top - fw, -d, w, dk)
        fr.box(b - 0.09, b - 0.01, v0 + hp, top - fw, -d, w, dk)
        fr.box(a + 0.09, b - 0.09, top - fw - 0.09, top - fw, -d, w, dk)
        fr.box(a + 0.15, b - 0.15, v0 + 0.15, v0 + hp - 0.12, w, w + 0.015, dk)


def _garage(fr, op, d):
    u0, u1, v0, v1 = op['u0'], op['u1'], op['v0'], op['v1']
    gk = op.get('door_key', 'metal_grey')
    w = -d * 0.6
    fr.quad(u0, v0, u1, v1, gk, w=w)
    # lames du rideau metallique
    h = v1 - v0
    n = max(4, int(h / 0.22))
    for k in range(1, n):
        vv = v0 + h * k / n
        fr.box(u0, u1, vv - 0.012, vv + 0.012, w, w + 0.02, gk)


def build_facade(fr, spec, rng, detail=1):
    """Construit une facade complete. spec : W, margin, bays, floors[{v0, h, wall, bays:[op|None]*n, per_bay}],
    piers, bands. Renvoie la liste des ouvertures posees (pour les escaliers de secours)."""
    W = spec['W']
    m = spec['margin']
    n = spec['bays']
    bw = (W - 2 * m) / n if n > 0 else W
    placed = []
    n_arc = 12 if detail >= 2 else 8
    for fl in spec['floors']:
        v0, h = fl['v0'], fl['h']
        v1 = v0 + h
        wall = fl['wall']
        cells = []
        if n <= 0 or fl.get('blank'):
            cells.append((0.0, W, None))
        else:
            cells.append((0.0, m, None))
            cols = fl.get('cols')
            if cols:
                tot = float(sum(cols))
                widths = [(W - 2 * m) * c / tot for c in cols]
            else:
                widths = [bw] * n
            bu0 = m
            for b, bwb in enumerate(widths):
                if b:
                    bu0 += widths[b - 1]
                op = fl['bays'][b] if b < len(fl['bays']) else None
                if op is None:
                    cells.append((bu0, bu0 + bwb, None))
                    continue
                k = op.get('per_bay', 1)
                sw = bwb / k
                for j in range(k):
                    su0 = bu0 + j * sw
                    cx = su0 + sw / 2
                    ow = min(op['w'], sw - 2 * op.get('pier_min', 0.18))
                    o = dict(op)
                    o['u0'], o['u1'] = cx - ow / 2, cx + ow / 2
                    o['v0'] = v0 + op['sill_h']
                    o['v1'] = min(v1 - op.get('head_min', 0.3), o['v0'] + op['h'])
                    if o['v1'] - o['v0'] < 0.4:
                        cells.append((su0, su0 + sw, None))
                        continue
                    o['top_room'] = v1 - o['v1']
                    o['wall'] = wall
                    o['floor_v0'] = v0
                    cells.append((su0, su0 + sw, o))
            cells.append((W - m, W, None))
        for (cu0, cu1, op) in cells:
            if cu1 - cu0 < 1e-5:
                continue
            if fl.get('rustic') and detail >= 1:
                _rustic(fr, cu0, cu1, v0, v1, op, wall)
            r = wall_cell(fr, cu0, v0, cu1, v1, wall, op, n_arc)
            if op is not None and r is not None:
                loop, vs = r
                window(fr, op, loop, vs, rng, detail)
                placed.append(op)
    # pilastres (entre travees, de v_a a v_b)
    pier = spec.get('piers')
    if pier and n > 0:
        pw, pd = pier['w'], pier['d']
        key = pier.get('key', spec['floors'][-1]['wall'])
        skip = ('back', 'bottom') if pier['v0'] > 0.01 else ('back',)
        bs = range(0 if pier.get('edges') else 1, n + 1 if pier.get('edges') else n)
        for b in bs:
            u = m + b * bw
            fr.box(u - pw / 2, u + pw / 2, pier['v0'], pier['v1'], 0.0, pd, key, skip=skip)
        if pier.get('corners') and m > 0.05:
            fr.box(0.0, m, pier['v0'], pier['v1'], 0.0, pd, key, skip=skip)
            fr.box(W - m, W, pier['v0'], pier['v1'], 0.0, pd, key, skip=skip)
    # bandeaux horizontaux
    for band in spec.get('bands', []):
        v, bh, bd, key = band
        fr.box(-bd, W + bd, v, v + bh, 0.0, bd, key, skip=('back',))
    return placed


def _rustic(fr, cu0, cu1, v0, v1, op, key, course=0.5, gap=0.05, t=0.035):
    """Bossage : assises en saillie separees par des joints creux, autour de l'ouverture eventuelle."""
    v = v0 + gap
    while v + course * 0.5 < v1:
        vt = min(v1 - gap * 0.5, v + course - gap)
        spans = [(cu0, cu1)]
        if op is not None:
            top = op['v1'] + 0.3
            if vt > op['v0'] - 0.1 and v < top:
                spans = [(cu0, op['u0'] - 0.14), (op['u1'] + 0.14, cu1)]
        for a, b in spans:
            if b - a > 0.08:
                fr.box(a, b, v, vt, 0.0, t, key, skip=('back',))
        v += course
