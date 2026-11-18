"""Assemblage d'un batiment a partir d'un plan (styles.make_plan).

Repere local : x le long de la rue, y vers l'arriere (la facade sur rue est en y=0, tournee vers -y), z vers le haut,
en metres. party=(gauche, droite) : murs mitoyens aveugles (rangee de batiments)."""
import math
from mathutils import Vector
from .geom import MeshBuilder, Frame, sweep, offset_loop
from .facade import build_facade, wall_cell, window, decor, pier_spans
from . import props as PR
from . import services as SV

T_WALL = 0.32          # epaisseur de l'acrotere

CORNICES = {
    'big': [(0, 0), (0.06, 0), (0.06, 0.1), (0.15, 0.18), (0.15, 0.27), (0.5, 0.42), (0.64, 0.5), (0.64, 0.68), (0, 0.68)],
    'brick': [(0, 0), (0.06, 0), (0.06, 0.16), (0.13, 0.16), (0.13, 0.32), (0.2, 0.32), (0.2, 0.56), (0, 0.56)],
    'simple': [(0, 0), (0.16, 0), (0.16, 0.36), (0, 0.36)],
    'eave': [(0, 0), (0.1, 0), (0.45, 0.2), (0.45, 0.32), (0, 0.32)],
}

SIDES = ('front', 'right', 'back', 'left')


def _side_frames(mb, rect):
    x0, y0, x1, y1 = rect
    W, D = x1 - x0, y1 - y0
    return [
        ('front', Frame(mb, (x0, y0, 0), (1, 0, 0), 0.0), W),
        ('right', Frame(mb, (x1, y0, 0), (0, 1, 0), W), D),
        ('back', Frame(mb, (x1, y1, 0), (-1, 0, 0), W + D), W),
        ('left', Frame(mb, (x0, y1, 0), (0, -1, 0), 2 * W + D), D),
    ]


def _corner_path(rect, sides_run, z):
    x0, y0, x1, y1 = rect
    C = {'front': ((x0, y0), (x1, y0)), 'right': ((x1, y0), (x1, y1)), 'back': ((x1, y1), (x0, y1)), 'left': ((x0, y1), (x0, y0))}
    pts = [C[sides_run[0]][0]] + [C[s][1] for s in sides_run]
    return [(p[0], p[1], z) for p in pts]


def _runs(active):
    """Groupe les cotes actifs en suites contigues (ordre trigonometrique). Renvoie (suites, ferme)."""
    if all(active[s] for s in SIDES):
        return [list(SIDES)], True
    runs = []
    start = next(i for i, s in enumerate(SIDES) if not active[s])
    cur = []
    for k in range(1, 5):
        s = SIDES[(start + k) % 4]
        if active[s]:
            cur.append(s)
        elif cur:
            runs.append(cur); cur = []
    if cur:
        runs.append(cur)
    return runs, False


def _ring_xy(mb, outer, inner, z, key):
    """Anneau horizontal (normale +z) entre deux rectangles alignes, inner dans outer."""
    ox0, oy0, ox1, oy1 = outer
    ix0, iy0, ix1, iy1 = inner
    O = [Vector((ox0, oy0, z)), Vector((ox1, oy0, z)), Vector((ox1, oy1, z)), Vector((ox0, oy1, z))]
    I = [Vector((ix0, iy0, z)), Vector((ix1, iy0, z)), Vector((ix1, iy1, z)), Vector((ix0, iy1, z))]
    for i in range(4):
        j = (i + 1) % 4
        mb.face([O[i], O[j], I[j], I[i]], key)


def build(plan, rng, detail=1, party=(False, False), sidewalk=False, yard=0.0, rng2=None):
    """rng2 : generateur des equipements et decalcomanies (v1.5) ; None : batiment sans eux (comme en v1.4)."""
    mb = MeshBuilder()
    plan['_rng2'] = rng2
    faces = []
    M = plan['mat']
    W, D = plan['W'], plan['D']
    n = plan['floors']
    roof = plan.get('roof', 'flat')
    n_vert = n - 1 if roof == 'mansard' and n > 2 else n
    zs = [0.0, plan['ground_h']]
    fho = plan.get('floor_h_over') or {}          # hauteur d'un etage particulier (indice negatif : depuis le haut)
    for i in range(1, n + 1):
        zs.append(zs[-1] + fho.get(i, fho.get(i - n_vert, plan['floor_h'])))
    tiers = plan.get('tiers') or [dict(inset=0.0, f0=0, f1=n_vert)]
    tiers[-1]['f1'] = n_vert
    info = dict(windows=0, floors=n, height=0.0)
    plan['_n_vert'] = n_vert
    plan.pop('_awn', None)
    fe_sides = plan.get('fire_side', 'front')
    fe_sides = [fe_sides] if isinstance(fe_sides, str) else list(fe_sides)
    fe_done = set()
    disks_by_tier = []
    z_prev = 0.0
    for ti, tier in enumerate(tiers):
        ins = tier['inset']
        x0, y0 = ins, ins
        x1, y1 = W - ins, D - ins
        if party[0] and ti == 0:
            x0 = 0.0
        if party[1] and ti == 0:
            x1 = W
        rect = (x0, y0, x1, y1)
        f0, f1 = tier['f0'], tier['f1']
        top_tier = ti == len(tiers) - 1
        z_top_floor = zs[f1]
        has_parapet = not (top_tier and roof in ('mansard', 'hip'))
        par = plan['parapet'] if has_parapet else 0.0
        z_crown = z_top_floor + par
        z_box = z_crown if has_parapet else z_top_floor + 0.3
        mb.mass.append(('tier', rect, z_prev, z_box))
        z_prev = z_box
        active = {}
        blank_of = {sd: ti == 0 and ((sd == 'left' and party[0]) or (sd == 'right' and party[1])) for sd in SIDES}
        ends = {'front': ('left', 'right'), 'right': ('front', 'back'), 'back': ('right', 'left'), 'left': ('back', 'front')}
        decors = {}
        for side, fr, Wf in _side_frames(mb, rect):
            blank = blank_of[side]
            active[side] = not blank
            spec = _facade_spec(plan, M, side, Wf, zs, f0, f1, z_crown, blank, rng, top_tier and roof == 'mansard', ti)
            placed = build_facade(fr, spec, rng, detail)
            decors[side] = (fr, spec)
            info['windows'] += len(placed)
            fe_rng = None
            if not blank:
                mb.tag = 'shopfront'
                _ground_extras(plan, M, side, fr, Wf, spec, zs, rng, detail, ti)
                if side not in fe_done and ti == 0 and plan.get('fire_escape', 0) > 0 and side in fe_sides and n_vert >= 3:
                    if rng.random() < plan['fire_escape']:
                        mb.tag = 'fire_escape'
                        fe_rng = _fire_escape(fr, mb, spec, zs, f1, rng, detail, plan, side)
                    fe_done.add(side)
                avoid = pier_spans(spec)
                og = _oriel_span(spec, plan) if (side == 'front' and ti == 0) else None
                if og:
                    avoid = avoid + [(og[0] - 0.1, og[1] + 0.1)]
                brk = []
                if plan.get('brackets') and plan.get('cornice') in ('big', 'brick') and (has_parapet or roof != 'flat'):
                    mb.tag = 'bracket'
                    gap = _oriel_span(spec, plan) if (side == 'front' and ti == 0) else None
                    brk = _brackets(fr, Wf, z_crown - CORNICES[plan['cornice']][-1][1] + (0.0 if has_parapet else 0.3), plan['cornice'], M, detail, gap, avoid)
                if plan.get('cornice') == 'big' and detail >= 2 and (has_parapet or roof != 'flat'):
                    mb.tag = 'dentil'
                    _dentils(fr, Wf, z_crown - CORNICES['big'][-1][1] + (0.0 if has_parapet else 0.3), M['cornice'], avoid + brk)
                if plan.get('quoins'):
                    mb.tag = 'quoin'
                    e0, e1 = ends[side]
                    _quoins(fr, Wf, zs[1] if plan['ground'] in ('store', 'glass') else 0.0, zs[f1], M['trim'], not blank_of[e0], not blank_of[e1])
                if side == 'front' and ti == 0 and plan.get('_oriel') is not None:
                    mb.tag = 'oriel'
                    prof_o = CORNICES.get(plan.get('cornice', 'simple'))
                    zt_o = (z_crown - prof_o[-1][1] + (0.0 if has_parapet else 0.3) - 0.05) if prof_o else None
                    _oriel(mb, fr, spec, plan, M, zs, f1, rng, detail, zt_o)
                    sp_o = _oriel_span(spec, plan)
                    if sp_o:
                        plan['_oriel_span'] = (sp_o[0], sp_o[1])
            mb.tag = 'wall'
            if ti == 0 and rng2 is not None:
                prof_t = CORNICES.get(plan.get('cornice', 'simple'))
                if prof_t is None and not top_tier:
                    prof_t = CORNICES['simple']
                if prof_t is not None:
                    zc_t = z_crown - prof_t[-1][1] + (0.0 if has_parapet else 0.3)
                    drop = 0.44 if (plan.get('brackets') and plan.get('cornice') == 'big') else (0.27 if (plan.get('brackets') and plan.get('cornice') == 'brick') else (0.14 if plan.get('cornice') == 'big' else 0.0))
                    top_v = zc_t - drop - 0.05
                    proj = max(p_[0] for p_ in prof_t)
                else:
                    top_v = z_crown - 0.15
                    proj = 0.05
                f_ = SV.Face(side, fr, Wf, spec, placed, not spec.get('bays'), blank, top_v)
                f_.crown_top = z_crown + 0.12
                f_.crown_proj = proj
                if fe_rng:
                    f_.fe = fe_rng
                faces.append(f_)
        nxt = {'front': 'right', 'right': 'back', 'back': 'left', 'left': 'front'}
        for sd, (fr_, sp_) in decors.items():
            o = decors.get(nxt[sd])
            ob = bool(o and o[1].get('bands'))
            op_ = bool(o and (o[1].get('piers') or {}).get('corners'))
            decor(fr_, sp_, ob, op_)
        # corniche + couronnement de l'acrotere
        runs, closed = _runs(active)
        prof = CORNICES.get(plan.get('cornice', 'simple'))
        if not top_tier and prof is None:
            prof = CORNICES['simple']
        if prof is not None:
            ch = prof[-1][1]
            ckey = M['cornice'] if plan.get('cornice') != 'brick' else M['wall']
            mb.tag = 'cornice'
            for run in runs:
                sweep(mb, _corner_path(rect, run, z_crown - ch + (0.0 if has_parapet else 0.3)), prof, ckey, closed=closed)
        if has_parapet:
            mb.tag = 'coping'
            cop = [(0.05, 0), (0.05, 0.12), (-T_WALL - 0.03, 0.12), (-T_WALL - 0.03, 0)]
            loop = _corner_path(rect, list(SIDES), z_crown)[:-1]
            sweep(mb, loop, cop, 'coping', closed=True)
            mb.tag = 'parapet'
            sweep(mb, [(p[0], p[1], z_top_floor) for p in loop], [(-T_WALL, par), (-T_WALL, 0.0)], M['side'], closed=True)
            mb.tag = 'roof'
            inner = (x0 + T_WALL, y0 + T_WALL, x1 - T_WALL, y1 - T_WALL)
            if top_tier:
                mb.face([Vector((inner[0], inner[1], z_top_floor)), Vector((inner[2], inner[1], z_top_floor)),
                         Vector((inner[2], inner[3], z_top_floor)), Vector((inner[0], inner[3], z_top_floor))], M['roof'])
                roof_rect = inner
            else:
                nx = tiers[ti + 1]['inset']
                up = (nx, nx, W - nx, D - nx)
                _ring_xy(mb, inner, up, z_top_floor, M['roof'])
                roof_rect = None
                # terrasse du retrait : quelques clims / ventilations
                if plan.get('roof_props', 1.0) and detail >= 1:
                    mb.tag = 'roofprop'
                    _terrace_props(mb, inner, up, z_top_floor, rng, detail)
        mb.tag = 'roof'
        if top_tier:
            info['height'] = z_crown
            if roof == 'mansard':
                mb.tag = 'mansard'
                roof_rect, ztop = _mansard(mb, plan, M, rect, zs, n_vert, n, rng, detail, active)
                mb.mass.append(('mansard', rect, zs[n_vert] + 0.3, plan['floor_h'] + 0.2))
                info['height'] = ztop
                mb.tag = 'roofprop'
                _roof_props(mb, plan, M, roof_rect, ztop, rng, detail, small=not plan.get('mansard_props'))
            elif roof == 'hip':
                ztop = _hip(mb, M, rect, z_top_floor + 0.3, rng, plan.get('hip_pitch'))
                mb.mass.append(('hip', rect, z_top_floor + 0.3, ztop))
                info['height'] = ztop
            else:
                mb.tag = 'roofprop'
                _roof_props(mb, plan, M, roof_rect, z_top_floor, rng, detail)
        mb.tag = 'wall'
    if plan['ground'] == 'stoop':
        mb.tag = 'stoop'
        _stoop(mb, plan, M, zs, rng, detail)
    if rng2 is not None:
        amount = plan.get('decals', 0.6)
        for f_ in faces:
            mb.tag = 'service'
            SV.collect(f_, plan, zs, M)
            SV.facade_services(mb, f_, plan, zs, M, rng2, detail, amount)
            SV.garage_tags(mb, f_, rng2, amount)
        mb.tag = 'wall'
    plan.pop('_rng2', None)
    mb.tag = 'ground'
    if sidewalk:
        _sidewalk(mb, 0.0, W, rng, depth=4.5 + yard, y1=-yard if yard > 0.1 else 0.0)
    if yard > 0.1:
        mb.tag = 'yard'
        _yard(mb, plan, W, yard, detail)
    mb.tag = 'wall'
    return mb, info


# ---------------------------------------------------------------- facades


def _facade_spec(plan, M, side, Wf, zs, f0, f1, z_crown, blank, rng, mansard_above, tier):
    spec = _facade_spec0(plan, M, side, Wf, zs, f0, f1, z_crown, blank, rng, mansard_above, tier)
    spec['defer'] = True
    if not spec['bays']:
        return spec
    n_t = len(plan.get('tiers') or [0])
    top = tier == n_t - 1
    has_par = not (top and plan.get('roof', 'flat') in ('mansard', 'hip'))
    prof = CORNICES.get(plan.get('cornice', 'simple'))
    if prof is None and not top:
        prof = CORNICES['simple']
    clear = [(b[0], b[0] + b[1]) for b in spec['bands']]
    if prof is not None:
        zc = z_crown - prof[-1][1] + (0.0 if has_par else 0.3)
        drop = 0.0
        if plan.get('brackets') and plan.get('cornice') in ('big', 'brick'):
            drop = 0.44 if plan['cornice'] == 'big' else 0.27
        elif plan.get('cornice') == 'big':
            drop = 0.14
        clear.append((zc - drop, 1e9))
        pp = spec.get('piers')
        if pp and not pp.get('base_only') and pp['v1'] > zc:
            pp['v1'] = zc                     # le pilastre porte la corniche au lieu de la traverser
    spec['clear'] = clear
    gaps = []
    if side == 'front' and tier == 0 and plan['ground'] == 'stoop':
        u0, u1 = _stoop_span(plan)
        gaps.append((u0 - 0.3, u1 + 0.3, zs[1] + 1.6))
    if side == 'front' and tier == 0 and plan.get('_oriel') is not None:
        so = _oriel_span(spec, plan)
        if so:
            gaps.append((so[0] - 0.02, so[1] + 0.02, 1e9))      # le bandeau s'arrete contre le bow-window
    if gaps:
        spec['band_gaps'] = gaps
    return spec


def _stoop_span(plan):
    W = plan['W']
    m = min(plan['margin'], W * 0.2)
    nb = max(1, int(round((W - 2 * m) / plan['bay_w'])))
    bw = (W - 2 * m) / nb
    b = plan.get('_door_bay', 0)
    return m + b * bw + 0.05 - 0.22, m + (b + 1) * bw - 0.05 + 0.22


def _facade_spec0(plan, M, side, Wf, zs, f0, f1, z_crown, blank, rng, mansard_above, tier):
    margin = min(plan['margin'], Wf * 0.2)
    bay = plan['bay_w']
    side_win = side in ('front', 'back') or rng.random() < plan.get('side_windows', 0.5) or tier > 0
    if blank or not side_win:
        floors = [dict(v0=0.0 if f0 == 0 else zs[f0], h=z_crown - (0.0 if f0 == 0 else zs[f0]), wall=M['side'] if (blank or plan.get('blank_side')) else M['wall'], blank=True, bays=[])]
        return dict(W=Wf, margin=margin, bays=0, floors=floors, bands=[], piers=None)
    nb = max(1, int(round((Wf - 2 * margin) / bay)))
    n_vert = len(zs) - 2 if not mansard_above else f1
    base_n = plan.get('base_floors', 1)
    top_n = plan.get('top_floors', 1)
    floors = []
    for i in range(f0, f1):
        v0, h = zs[i], zs[i + 1] - zs[i]
        if i < base_n:
            wall, w = M['base'], plan['win_base']
        elif i >= f1 - top_n and tier == (len(plan.get('tiers') or [0]) - 1 if plan.get('tiers') else 0):
            wall, w = M['top'], plan['win_top']
        else:
            wall, w = M['wall'], plan['win_typ']
        cols = None
        ov = _floor_over(plan, i, side)
        if i == 0:
            bays = _ground_bays(plan, M, side, nb, Wf, margin, h, rng)
        elif ov is not None and (ov.get('bays') is not None or ov.get('win')):
            if ov.get('bays') is not None:
                cols = ov.get('cols')
                bays = [None if t is None else dict(t, frame_key=M['frame'], trim=M['trim']) for t in ov['bays']]
            else:
                bays = [dict(ov['win'], frame_key=M['frame'], trim=M['trim']) for _ in range(nb)]
            if ov.get('wall'):
                wall = M.get(ov['wall'], ov['wall'])
        else:
            bays = []
            for b in range(nb):
                o = dict(w)
                o['frame_key'] = M['frame']; o['trim'] = M['trim']
                bays.append(o)
            if i == 1 and side == 'front' and plan['ground'] == 'stoop':
                # porte principale en haut du perron (etage noble)
                bays[plan.setdefault('_door_bay', 0)] = dict(w=1.2, h=min(2.75, h - 0.45), sill_h=0.0, shape=w.get('shape', 'rect'), rise=0.15,
                    frame='door', door_key=M['door'], depth=0.35, lintel='key', sill=False, trim=M['trim'], frame_key=M['frame'], pier_min=0.1, band=True)
        floors.append(dict(v0=v0, h=h, wall=wall, bays=bays, cols=cols, rustic=bool(plan.get('rustic')) and i < base_n))
    # acrotere / mur au-dessus du dernier etage
    if z_crown - zs[f1] > 1e-3:
        floors.append(dict(v0=zs[f1], h=z_crown - zs[f1], wall=M['top'] if plan.get('top_floors') else M['wall'], blank=True, bays=[]))
    bands = []
    for b in plan.get('bands', []):
        if b == 'base':
            fi = base_n
        elif b == 'top':
            fi = f1 - top_n
        else:
            fi = int(b)
        if f0 < fi < f1:
            bands.append((zs[fi] - plan['band_h'] * 0.5, plan['band_h'], plan['band_d'], M['trim']))
    piers = None
    if plan.get('piers'):
        pp = dict(plan['piers'])
        if pp.get('base_only'):
            pp['v0'], pp['v1'] = 0.0, zs[1]
        else:
            pp['v0'] = (0.0 if pp.get('from_ground') else zs[1]) if f0 == 0 else zs[f0]
            pp['v1'] = z_crown
        pp['key'] = M[pp['mat']] if pp.get('mat') else (M['wall'] if not pp.get('base_only') else M['base'])
        piers = pp
    return dict(W=Wf, margin=margin, bays=nb, floors=floors, bands=bands, piers=piers)


def _ground_bays(plan, M, side, nb, Wf, margin, gh, rng):
    g = plan['ground'] if side == 'front' else (plan['ground'] if plan['ground'] in ('glass', 'arcade') else 'base')
    bw = (Wf - 2 * margin) / nb
    base = dict(plan['win_base'], frame_key=M['frame'], trim=M['trim'])
    door = dict(w=min(1.15, bw - 0.4), h=min(2.6, gh - 0.5), sill_h=0.0, shape='rect', frame='door', door_key=M['door'],
                depth=0.3, lintel='flat', sill=False, trim=M['trim'], frame_key=M['frame'], pier_min=0.1)
    out = []
    if g == 'store':
        di = 0 if rng.random() < 0.5 else nb - 1
        for b in range(nb):
            if b == di and nb > 1:
                out.append(dict(door))
            else:
                out.append(dict(w=bw - 0.36, h=gh - 0.95, sill_h=0.06, shape='rect', frame='storefront', door_key=M['door'], depth=0.22,
                                lintel='none', sill=False, frame_key=M['frame'], trim=M['trim'], pier_min=0.08, head_min=0.7))
    elif g == 'glass':
        for b in range(nb):
            out.append(dict(w=bw - 0.1, h=gh - 0.6, sill_h=0.0, shape='rect', frame='storefront', door_key=M['frame'], depth=0.5,
                            lintel='none', sill=False, frame_key=M['frame'], trim=M['trim'], pier_min=0.02, head_min=0.5))
        out[nb // 2] = dict(door, w=min(2.0, bw - 0.2), frame='door', door_key='glass_door')
    elif g == 'lobby':
        c = nb // 2
        for b in range(nb):
            o = dict(base, sill_h=1.0, h=min(base['h'], gh - 1.6))
            out.append(o)
        out[c] = dict(door, w=min(2.4, bw - 0.3), h=gh - 0.9, shape='arch' if bw > 1.8 else 'rect', lintel='key', band=True)
    elif g == 'arcade':
        # grandes baies cintrees a petits bois, porte cintree au centre de la facade
        pw = (plan.get('piers') or {}).get('w', 0.0)
        for b in range(nb):
            out.append(dict(w=bw - max(0.7, pw + 0.4), h=gh - 0.55, sill_h=0.35, shape='arch', frame='grid', grid=(3, 4), depth=0.3,
                            lintel='key', band=True, sill=False, frame_key=M['frame'], trim=M['trim'], pier_min=0.3, head_min=0.3))
        if side == 'front':
            out[nb // 2] = dict(door, w=min(2.4, bw - 0.6), h=gh - 0.6, shape='arch', lintel='key', band=True)
    elif g == 'warehouse':
        di = rng.randrange(nb)
        for b in range(nb):
            if b == di:
                out.append(dict(door))
            elif rng.random() < 0.5:
                out.append(dict(w=bw - 1.0, h=min(3.6, gh - 0.8), sill_h=0.0, shape='rect', frame='garage', door_key='metal_grey',
                                depth=0.35, lintel='none', sill=False, trim=M['trim'], frame_key=M['frame'], pier_min=0.3))
            else:
                out.append(dict(plan['win_typ'], frame_key=M['frame'], trim=M['trim'], sill_h=1.0, h=min(plan['win_typ']['h'] + 0.4, gh - 1.4)))
    elif g == 'stoop':
        for b in range(nb):
            out.append(dict(base, sill_h=0.9, h=min(base['h'], gh - 1.2)))
        if nb >= 3:
            out[1 if side != 'front' else plan.setdefault('_door_bay', 0)] = dict(door, h=min(2.0, gh - 0.3), w=0.95)
    else:  # base
        di = nb // 2
        for b in range(nb):
            out.append(dict(base, sill_h=max(0.9, base['sill_h']), h=min(base['h'], gh - 1.3)))
        out[di] = dict(door)
    return out


def _ground_extras(plan, M, side, fr, Wf, spec, zs, rng, detail, tier):
    if tier != 0 or side != 'front':
        return
    g = plan['ground']
    gh = zs[1]
    m = spec['margin']
    if g == 'store':
        # bandeau d'enseigne et pilastres de devanture (profondeurs distinctes de celles des bandeaux)
        bds = [b[2] for b in spec.get('bands', []) if b[0] < gh + 0.05 and b[0] + b[1] > gh - 0.75]
        sd = 0.14 if all(abs(x - 0.14) > 0.015 for x in bds) else 0.1
        td = 0.2 if all(abs(x - 0.2) > 0.015 for x in bds) else 0.23
        fr.box(m * 0.5, Wf - m * 0.5, gh - 0.72, gh - 0.12, 0.0, sd, M['sign'], skip=('back',))
        fr.box(m * 0.5 - 0.04, Wf - m * 0.5 + 0.04, gh - 0.12, gh + 0.02, 0.0, td, M['trim'], skip=('back',))
        nb = spec['bays']
        bw = (Wf - 2 * m) / nb
        for b in range(nb + 1):
            u = m + b * bw
            fr.box(u - 0.14, u + 0.14, 0.0, gh - 0.72, 0.0, 0.1, M['trim'], skip=('back',))
        if rng.random() < plan.get('awnings', 0.0):
            for b, op in enumerate(spec['floors'][0]['bays']):
                if op is None or op.get('frame') != 'storefront':
                    continue
                u0 = m + b * bw + 0.15; u1 = u0 + bw - 0.3
                _awning(fr, u0, u1, gh - 0.8, M['awning'])
                plan['_awn'] = True
    elif g == 'lobby' and detail >= 1:
        # marquise au-dessus de l'entree
        nb = spec['bays']; bw = (Wf - 2 * m) / nb; c = nb // 2
        u0, u1 = m + c * bw - 0.2, m + (c + 1) * bw + 0.2
        fr.box(u0, u1, gh - 0.53, gh - 0.38, 0.0, 1.6, 'metal_dark', skip=('back',))
    elif g == 'warehouse':
        # quai de chargement sous les rideaux
        nb = spec['bays']; bw = (Wf - 2 * m) / nb
        for b, op in enumerate(spec['floors'][0]['bays']):
            if op and op.get('frame') == 'garage' and detail >= 1:
                u0 = m + b * bw + 0.3; u1 = m + (b + 1) * bw - 0.3
                fr.box(u0, u1, 0.0, 0.25, 0.0, 0.6, 'concrete', skip=('back',))
                vt = op['sill_h'] + op['h']
                fr.box(u0 - 0.1, u1 + 0.1, vt + 0.05, vt + 0.12, 0.0, 0.9, 'metal_dark', skip=('back',))


def _awning(fr, u0, u1, v, key):
    dep, drop = 1.2, 0.7
    fr.face([(u0, v, 0.0), (u1, v, 0.0), (u1, v - drop, dep), (u0, v - drop, dep)], key)       # pente (dessus)
    fr.face([(u0, v - drop, dep), (u1, v - drop, dep), (u1, v - drop - 0.25, dep), (u0, v - drop - 0.25, dep)], key)  # lambrequin
    fr.face([(u0, v, 0.0), (u0, v - drop, dep), (u0, v - drop - 0.25, dep), (u0, v - drop, 0.0)], key)
    fr.face([(u1, v - drop, 0.0), (u1, v - drop - 0.25, dep), (u1, v - drop, dep), (u1, v, 0.0)], key)


def _brackets(fr, Wf, zc, kind, M, detail, gap=None, avoid=()):
    out = []
    if detail < 1:
        return out
    step = 0.85 if kind == 'big' else 0.5
    n = max(2, int(Wf / step))
    key = M['cornice'] if kind == 'big' else M['wall']
    for k in range(n + 1):
        u = 0.12 + (Wf - 0.24) * k / n
        if gap and gap[0] - 0.1 < u < gap[1] + 0.1:
            continue
        if any(u + 0.09 > a and u - 0.09 < b for a, b in avoid):
            continue
        out.append((u - 0.07, u + 0.07))
        if kind == 'big':
            fr.box(u - 0.07, u + 0.07, zc - 0.42, zc + 0.02, 0.0, 0.16, key)
            fr.box(u - 0.07, u + 0.07, zc - 0.14, zc + 0.02, 0.16, 0.42, key)
            fr.box(u - 0.06, u + 0.06, zc - 0.42, zc - 0.32, 0.16, 0.22, key)
        else:
            fr.box(u - 0.1, u + 0.1, zc - 0.25, zc, 0.0, 0.06, key)
    return out


def _fire_escape(fr, mb, spec, zs, f1, rng, detail, plan=None, side='front'):
    nb = spec['bays']
    if nb < 1:
        return
    m, Wf = spec['margin'], spec['W']
    bw = (Wf - 2 * m) / nb
    span = 2 if bw < 3.2 and nb >= 3 else 1
    b0 = rng.randrange(0, max(1, nb - span + 1))
    u0 = m + b0 * bw + 0.1
    u1 = m + (b0 + span) * bw - 0.1
    if u1 - u0 < 2.6:
        u1 = min(Wf - 0.1, u0 + 2.8)
    levels = [zs[i] - 0.02 for i in range(1, f1)]
    # ecart au mur : devant pilastres, bandeaux, linteaux et clefs, enseigne de la devanture
    w0 = 0.09
    pp = spec.get('piers')
    if pp and pp['v1'] > zs[1] + 0.1:
        w0 = max(w0, pp['d'] + 0.04)
    for b in spec.get('bands', []):
        bd = b[2] if not (pp and abs(b[2] - pp['d']) < 0.02) else pp['d'] + 0.04
        w0 = max(w0, bd + 0.03)
    plan = plan or {}
    store = side == 'front' and plan.get('ground') == 'store'
    if store:
        w0 = max(w0, 0.26)
    ladder_min = zs[1] - 0.72 if (store and plan.get('_awn')) else None
    vb = PR.fire_escape(fr, mb, u0, u1, levels, 0.0, detail, 'fire_escape', w0=w0, hang_first=store, ladder_min=ladder_min)
    return (u0, u1, vb if vb is not None else 0.0)


# ---------------------------------------------------------------- toits


def _roof_props(mb, plan, M, rect, z, rng, detail, small=False):
    if rect is None or not plan.get('roof_props', 1.0):
        return
    x0, y0, x1, y1 = rect
    W, D = x1 - x0, y1 - y0
    if W < 2 or D < 2:
        return
    items = []
    disks = []
    if rng.random() < plan.get('bulkhead', 0.0) and W > 4 and D > 4 and not small:
        bw, bd = min(W * 0.4, rng.uniform(3.0, 5.5)), min(D * 0.4, rng.uniform(2.6, 4.5))
        bx = rng.uniform(x0 + 0.6, x1 - bw - 0.6)
        by = rng.uniform(y0 + D * 0.3, y1 - bd - 0.6)
        h = rng.uniform(2.6, 3.4) * (1.4 if plan['floors'] > 12 else 1.0)
        mb.tag = 'bulkhead'
        PR.bulkhead(mb, bx, by, bx + bw, by + bd, z, h, M['wall'], rng, detail)
        mb.tag = 'roofprop'
        disks.append((bx + bw / 2, by + bd / 2, max(bw, bd) * 0.6))
        if rng.random() < plan.get('water_tower', 0.0) and bw > 2.5:
            PR.water_tower(mb, bx + bw / 2, by + bd / 2, z + h + 0.3, rng, detail)
            mb.box((bx - 0.12, by - 0.12, z + h + 0.15), (bx + bw + 0.12, by + bd + 0.12, z + h + 0.3), 'metal_dark')
        if rng.random() < plan.get('antenna', 0.0):
            PR.antenna(mb, bx + 0.4, by + bd - 0.4, z + h + 0.15, rng, h=rng.uniform(5, 12) if plan['floors'] > 15 else None)
    elif rng.random() < plan.get('water_tower', 0.0) * 0.6 and W > 5 and D > 5 and (not small or plan.get('mansard_props')):
        items.append(lambda mb_, x, y, zz, r: PR.water_tower(mb_, x, y, zz, r, detail))
    for _ in range(plan.get('ac', 0)):
        items.append(lambda mb_, x, y, zz, r: PR.ac_unit(mb_, x, y, zz, r, detail))
    for _ in range(plan.get('vents', 0)):
        items.append(lambda mb_, x, y, zz, r: PR.vent(mb_, x, y, zz, r, detail))
    for _ in range(plan.get('skylights', 0)):
        items.append(lambda mb_, x, y, zz, r: PR.skylight(mb_, x, y, zz, r))
    for _ in range(plan.get('chimneys', 0)):
        items.append(lambda mb_, x, y, zz, r: PR.chimney(mb_, x, y, zz, r, M['wall']))
    disks = PR.scatter_roof(mb, (x0 + 0.5, y0 + 0.5, x1 - 0.5, y1 - 0.5), z, rng, items, disks, detail)
    rng2 = plan.get('_rng2')
    if rng2 is not None:
        more = SV.roof_items(plan, rng2, detail)
        if more:
            PR.scatter_roof(mb, (x0 + 0.5, y0 + 0.5, x1 - 0.5, y1 - 0.5), z, rng2, more, disks, detail)


def _terrace_props(mb, outer, inner, z, rng, detail):
    x0, y0, x1, y1 = outer
    ix0, iy0, ix1, iy1 = inner
    zones = [(x0 + 0.4, y0 + 0.4, x1 - 0.4, iy0 - 0.4), (x0 + 0.4, iy1 + 0.4, x1 - 0.4, y1 - 0.4)]
    for zr in zones:
        if zr[3] - zr[1] > 1.6 and zr[2] - zr[0] > 3:
            items = [lambda mb_, x, y, zz, r: PR.ac_unit(mb_, x, y, zz, r, detail) for _ in range(rng.randint(0, 2))]
            items += [lambda mb_, x, y, zz, r: PR.vent(mb_, x, y, zz, r, detail) for _ in range(rng.randint(0, 2))]
            PR.scatter_roof(mb, zr, z, rng, items, (), detail)


def _mansard(mb, plan, M, rect, zs, n_vert, n, rng, detail, active):
    x0, y0, x1, y1 = rect
    z0 = zs[n_vert] + 0.3
    h = plan['floor_h'] + 0.2
    s = min(1.1, (x1 - x0) * 0.2, (y1 - y0) * 0.2)
    key = M['roof_slope']
    lo = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    hi = [(x0 + s, y0 + s), (x1 - s, y0 + s), (x1 - s, y1 - s), (x0 + s, y1 - s)]
    for i in range(4):
        j = (i + 1) % 4
        mb.face([Vector((*lo[i], z0)), Vector((*lo[j], z0)), Vector((*hi[j], z0 + h)), Vector((*hi[i], z0 + h))], key)
    zt = z0 + h
    mb.face([Vector((*p, zt)) for p in hi], M['roof'])
    sweep(mb, [(p[0], p[1], zt) for p in hi], [(0.08, 0), (0.08, 0.15), (0, 0.15)], 'metal_dark', closed=True)
    # lucarnes
    frames = [('front', (x0, y0), (1, 0), x1 - x0), ('right', (x1, y0), (0, 1), y1 - y0), ('back', (x1, y1), (-1, 0), x1 - x0), ('left', (x0, y1), (0, -1), y1 - y0)]
    from .geom import Frame as F
    bay = plan['bay_w']
    for side, o, t, L in frames:
        if not active.get(side, True):
            continue
        fr = F(mb, (o[0], o[1], 0), (t[0], t[1], 0))
        nb = max(1, int(round((L - 2 * s - 0.6) / max(bay, 2.0))))
        span = (L - 2 * s - 0.6) / nb
        for b in range(nb):
            cu = s + 0.3 + span * (b + 0.5)
            dw = min(1.25, span - 0.5)
            vb, vt = z0 + 0.35, z0 + 0.35 + 1.75
            wf = -0.08
            inset = lambda v: -s * (v - z0) / h
            # facade de la lucarne, percee d'une fenetre
            fr2 = F(mb, fr.P(0, 0, wf), (t[0], t[1], 0), 0.0)
            op = dict(u0=cu - dw / 2 + 0.17, u1=cu + dw / 2 - 0.17, v0=vb + 0.12, v1=vt - 0.12, shape=pick_shape(rng), rise=0.12,
                      depth=0.12, frame='sash', frame_key=M['frame'], trim=M['trim'], glass='glass', wall=M['trim'], sill=False, lintel='none', band=False, top_room=0.1)
            r = wall_cell(fr2, cu - dw / 2, vb, cu + dw / 2, vt, M['trim'], op)
            if r:
                window(fr2, op, r[0], r[1], rng, detail)
            # joues et toit de la lucarne
            for uu, sgn in ((cu - dw / 2, -1), (cu + dw / 2, 1)):
                pts = [(uu, vb, wf), (uu, vt, wf), (uu, vt, inset(vt)), (uu, vb, inset(vb))]
                fr.face(pts if sgn < 0 else list(reversed(pts)), M['trim'])
            fr.face([(cu - dw / 2 - 0.08, vt, wf + 0.08), (cu + dw / 2 + 0.08, vt, wf + 0.08), (cu + dw / 2 + 0.08, vt + 0.35, inset(vt + 0.35)), (cu - dw / 2 - 0.08, vt + 0.35, inset(vt + 0.35))], key)
            fr.face([(cu - dw / 2 - 0.08, vt, inset(vt)), (cu - dw / 2 - 0.08, vt, wf + 0.08), (cu - dw / 2 - 0.08, vt + 0.35, inset(vt + 0.35))], key)
            fr.face([(cu + dw / 2 + 0.08, vt, wf + 0.08), (cu + dw / 2 + 0.08, vt, inset(vt)), (cu + dw / 2 + 0.08, vt + 0.35, inset(vt + 0.35))], key)
    return (hi[0][0] + 0.3, hi[0][1] + 0.3, hi[2][0] - 0.3, hi[2][1] - 0.3), zt + 0.15


def pick_shape(rng):
    return 'segment' if rng.random() < 0.5 else 'rect'


def _hip(mb, M, rect, z0, rng, pitch_deg=None):
    x0, y0, x1, y1 = rect
    e = 0.45
    x0 -= e; y0 -= e; x1 += e; y1 += e
    W, D = x1 - x0, y1 - y0
    pitch = math.radians(rng.uniform(25, 38) if pitch_deg is None else pitch_deg)
    key = M['roof_slope']
    if W >= D:
        hr = D / 2 * math.tan(pitch)
        r0 = Vector((x0 + D / 2, (y0 + y1) / 2, z0 + hr)); r1 = Vector((x1 - D / 2, (y0 + y1) / 2, z0 + hr))
        A, B, C, Dd = Vector((x0, y0, z0)), Vector((x1, y0, z0)), Vector((x1, y1, z0)), Vector((x0, y1, z0))
        mb.face([A, B, r1, r0], key); mb.face([C, Dd, r0, r1], key)
        mb.face([B, C, r1], key); mb.face([Dd, A, r0], key)
    else:
        hr = W / 2 * math.tan(pitch)
        r0 = Vector(((x0 + x1) / 2, y0 + W / 2, z0 + hr)); r1 = Vector(((x0 + x1) / 2, y1 - W / 2, z0 + hr))
        A, B, C, Dd = Vector((x0, y0, z0)), Vector((x1, y0, z0)), Vector((x1, y1, z0)), Vector((x0, y1, z0))
        mb.face([B, C, r1, r0], key); mb.face([Dd, A, r0, r1], key)
        mb.face([A, B, r0], key); mb.face([C, Dd, r1], key)
    mb.face([Vector((x0, y1, z0)), Vector((x1, y1, z0)), Vector((x1, y0, z0)), Vector((x0, y0, z0))], 'trim_stone')   # sous-face
    return z0 + hr


# ---------------------------------------------------------------- perron, trottoir


def _stoop(mb, plan, M, zs, rng, detail):
    W = plan['W']
    nb = max(1, int(round((W - 2 * min(plan['margin'], W * 0.2)) / plan['bay_w'])))
    m = min(plan['margin'], W * 0.2)
    bw = (W - 2 * m) / nb
    b = plan.get('_door_bay', 0)
    u0, u1 = m + b * bw + 0.05, m + (b + 1) * bw - 0.05
    H = zs[1]
    fr = Frame(mb, (0, 0, 0), (1, 0, 0))
    rise, run, land = 0.2, 0.26, 1.1
    ns = int(math.ceil(H / rise))
    rise = H / ns
    stone = M['base'] if M['base'].startswith('stone') else ('stone_brown' if M['wall'] == 'stone_brown' else M['trim'])
    fr.box(u0, u1, 0.0, H, 0.0, land, stone, skip=('back', 'left', 'right', 'bottom'))
    for k in range(1, ns):
        fr.box(u0, u1, 0.0, H - k * rise, land + (k - 1) * run, land + k * run, stone, skip=('back', 'left', 'right', 'bottom'))
    L = land + (ns - 1) * run
    # joues et rampe en fonte
    for uu in (u0 - 0.22, u1):
        fr.face([(uu, 0, 0), (uu, 0, L), (uu, 0.55, L), (uu, H + 0.55, land), (uu, H + 0.55, 0)][::-1], stone)
        fr.face([(uu + 0.22, 0, 0), (uu + 0.22, 0, L), (uu + 0.22, 0.55, L), (uu + 0.22, H + 0.55, land), (uu + 0.22, H + 0.55, 0)], stone)
        fr.face([(uu, 0.55, L), (uu + 0.22, 0.55, L), (uu + 0.22, H + 0.55, land), (uu, H + 0.55, land)], 'coping')
        fr.face([(uu, H + 0.55, land), (uu + 0.22, H + 0.55, land), (uu + 0.22, H + 0.55, 0), (uu, H + 0.55, 0)], 'coping')
        fr.face([(uu, 0, L), (uu + 0.22, 0, L), (uu + 0.22, 0.55, L), (uu, 0.55, L)], stone)
        if detail >= 1:
            c = uu + 0.11
            mb.beam(fr.P(c, H + 1.45, land), fr.P(c, 1.45, L - 0.1), 0.05, 'metal_dark')
            mb.beam(fr.P(c, H + 0.55, land), fr.P(c, H + 1.45, land), 0.05, 'metal_dark')
            mb.beam(fr.P(c, 0.55, L - 0.1), fr.P(c, 1.5, L - 0.1), 0.07, 'metal_dark')
            for k in range(1, int(L / 0.35)):
                w = land + (L - 0.1 - land) * k / int(L / 0.35)
                if w > L - 0.15:
                    break
                vb = H + 0.55 - (H) * (w - land) / (L - land)
                mb.beam(fr.P(c, vb, w), fr.P(c, vb + 0.9, w), 0.025, 'metal_dark')


def _sidewalk(mb, x0, x1, rng, depth=4.5, y1=0.0):
    mb.box((x0, -depth, -0.18), (x1, y1, 0.0), 'sidewalk', skip=('+y',))
    mb.box((x0, -depth - 0.25, -0.2), (x1, -depth, 0.0), 'curb', skip=('+y',))


def _quoins(fr, Wf, v0, v1, key, left=True, right=True):
    """Chainages d'angle : pierres alternativement longues et courtes."""
    bh = 0.42
    k = 0
    v = v0 + 0.02
    while v + bh <= v1 + 1e-3:
        w = 0.62 if k % 2 == 0 else 0.36
        if left:
            fr.box(0.0, w, v, v + bh - 0.04, 0.0, 0.035, key, skip=('back',))
        if right:
            fr.box(Wf - w, Wf, v, v + bh - 0.04, 0.0, 0.035, key, skip=('back',))
        v += bh
        k += 1


def _dentils(fr, Wf, zc, key, avoid=()):
    u = 0.1
    while u < Wf - 0.1:
        if not any(u + 0.09 > a and u - 0.02 < b for a, b in avoid):
            fr.box(u, u + 0.07, zc - 0.13, zc, 0.0, 0.1, key)
        u += 0.15


def _oriel_span(spec, plan):
    """Travee du bow-window : (u debut, u fin, u centre, largeur) ou None."""
    if plan.get('_oriel') is None:
        return None
    nb = spec['bays']
    if nb < 2:
        return None
    m, Wf = spec['margin'], spec['W']
    bw = (Wf - 2 * m) / nb
    b = plan['_oriel'] % nb
    if plan['ground'] == 'stoop' and b == plan.get('_door_bay', 0):
        b = (b + 1) % nb
    uc = m + (b + 0.5) * bw
    wb = min(bw + 0.4, 3.4)
    if plan['ground'] == 'stoop' and abs(b - plan.get('_door_bay', 0)) == 1:
        wb = min(wb, max(1.4, bw - 0.6))          # laisse passer la joue du perron voisin
    return (uc - wb / 2, uc + wb / 2, uc, wb)


def _oriel(mb, fr, spec, plan, M, zs, f1, rng, detail, ztop=None):
    """Bow-window a pans coupes sur une travee, du premier etage au dernier (arrete sous la corniche : ztop)."""
    ztop = zs[f1] if ztop is None else min(zs[f1], ztop)
    from .geom import Frame as F, sweep as SW
    sp = _oriel_span(spec, plan)
    if sp is None:
        return
    uc, wb = sp[2], sp[3]
    d = min(0.9, wb * 0.3)
    wf = wb - 2 * d
    v0 = zs[1] + 0.05
    if ztop - v0 < 2.5:
        return
    pts = [(uc - wb / 2, 0.0), (uc - wf / 2, d), (uc + wf / 2, d), (uc + wb / 2, 0.0)]
    win = dict(plan['win_typ'])
    for i in range(3):
        (ua, wa), (ub, wb_) = pts[i], pts[i + 1]
        P0 = fr.P(ua, 0.0, wa)
        Pt = fr.P(ub, 0.0, wb_) - P0
        L = Pt.length
        f2 = F(mb, P0, Pt, 0.0)
        floors = []
        for k in range(1, f1):
            if zs[k] > ztop - 0.3:
                break
            o = dict(win, w=min(win['w'], L - 0.36), frame_key=M['frame'], trim=M['trim'], pier_min=0.1, ac=0.0)
            floors.append(dict(v0=zs[k], h=min(zs[k + 1], ztop) - zs[k], wall=M['wall'], bays=[o]))
        build_facade(f2, dict(W=L, margin=0.12, bays=1, floors=floors, bands=[], piers=None), rng, detail)
    # encorbellement (sous-face) et toit
    base = [fr.P(u, v0 - 0.48, w * 0.3) for u, w in pts]
    top = [fr.P(u, v0, w) for u, w in pts]
    for i in range(3):
        mb.face([base[i], base[i + 1], top[i + 1], top[i]], M['trim'])
    mb.face([base[3], base[2], base[1], base[0]], M['trim'])
    mb.face([fr.P(u, ztop, w) for u, w in reversed(pts)][::-1], M['roof'])
    sw = [fr.P(u, ztop - 0.3, w) for u, w in pts]
    SW(mb, [(p.x, p.y, p.z) for p in sw], [(0, 0), (0.12, 0), (0.18, 0.18), (0.18, 0.3), (0, 0.3)], M['cornice'], closed=False)


def _yard(mb, plan, W, yard, detail):
    """Courette devant une maison reculee : sol pave et grille basse, ouverte au droit du perron."""
    mb.box((0.0, -yard, -0.18), (W, 0.0, 0.0), 'sidewalk', skip=('+y', '-y'))
    if detail < 1:
        return
    m = min(plan['margin'], W * 0.2)
    nb = max(1, int(round((W - 2 * m) / plan['bay_w'])))
    bw = (W - 2 * m) / nb
    b = plan.get('_door_bay', 0)
    gap = (m + b * bw - 0.3, m + (b + 1) * bw + 0.3) if plan['ground'] == 'stoop' else (W / 2 - 0.6, W / 2 + 0.6)
    y = -yard + 0.15
    for a, c in ((0.05, gap[0]), (gap[1], W - 0.05)):
        if c - a < 0.3:
            continue
        mb.box((a, y - 0.12, 0.0), (c, y + 0.12, 0.35), 'trim_stone')
        mb.box((a, y - 0.02, 1.0), (c, y + 0.02, 1.04), 'metal_dark')
        n = int((c - a) / 0.14)
        for k in range(n + 1):
            x = a + (c - a) * k / max(1, n)
            mb.box((x - 0.012, y - 0.012, 0.35), (x + 0.012, y + 0.012, 1.0), 'metal_dark')
        for x in (a + 0.05, c - 0.05):
            mb.box((x - 0.05, y - 0.05, 0.35), (x + 0.05, y + 0.05, 1.12), 'metal_dark')


def _floor_over(plan, i, side):
    """Reglage particulier d'un etage (plan['floor_over'] : {indice: dict ou liste de dicts}). Un indice negatif
    compte depuis le haut (-1 : dernier etage). Chaque dict peut viser des cotes ('sides')."""
    fo = plan.get('floor_over')
    if not fo:
        return None
    nv = plan.get('_n_vert', plan['floors'])
    v = fo.get(i, fo.get(i - nv))
    if v is None:
        return None
    for d in (v if isinstance(v, (list, tuple)) else [v]):
        if side in d.get('sides', SIDES):
            return d
    return None
