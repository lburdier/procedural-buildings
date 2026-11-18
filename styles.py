"""Styles (archetypes de quartier new-yorkais du debut du XXe siecle) : chaque style tire un plan complet d'une graine.

Un plan est un dict lu par building.build(). Les reglages de l'utilisateur (opts) priment sur le tirage :
floors, W, D, ground, roof, fire_escape, water_tower, roof_props, storefront, palette."""

STYLES = [
    ('walkup', "Immeuble de rapport", "3 à 6 étages en brique, fenêtres à guillotine, corniche à consoles, escalier de secours, commerce au rez-de-chaussée"),
    ('rowhouse', "Maison de ville (brownstone)", "Étroite, 3 à 4 étages, perron, grandes fenêtres de l'étage noble"),
    ('warehouse', "Entrepôt / loft", "Large, pilastres entre travées, grandes baies à petits carreaux, quais de chargement, château d'eau"),
    ('prewar', "Immeuble d'avant-guerre", "8 à 16 étages, soubassement en pierre, bandeaux, étages d'attique cintrés, grande corniche"),
    ('tower', "Tour à redans", "18 à 40 étages, retraits successifs, pilastres verticaux, couronnement, antenne"),
    ('modern', "Moderne (années 50-60)", "Fenêtres en bandeau, allèges pleines, rez-de-chaussée vitré, édicule technique"),
]
STYLE_KEYS = [s[0] for s in STYLES]

BRICKS = ['brick_red', 'brick_dark', 'brick_tan', 'brick_brown', 'brick_painted', 'brick_grey']
AWNINGS = ['awning_red', 'awning_green', 'awning_black', 'awning_blue']
SIGNS = ['sign_dark', 'sign_red', 'sign_green', 'sign_cream']


def pick(rng, items, weights=None):
    if weights is None:
        return items[rng.randrange(len(items))]
    t = rng.random() * sum(weights)
    for it, w in zip(items, weights):
        t -= w
        if t <= 0:
            return it
    return items[-1]


def win(w, h, sill_h, shape='rect', frame='sash', **kw):
    d = dict(w=w, h=h, sill_h=sill_h, shape=shape, frame=frame)
    d.update(kw)
    return d


def _opt_int(opts, key, lo, hi, rng):
    v = opts.get(key)
    if v:
        return int(v)
    return rng.randint(lo, hi)


def _opt_f(opts, key, lo, hi, rng):
    v = opts.get(key)
    if v:
        return float(v)
    return rng.uniform(lo, hi)


def _snap(x, step):
    return max(step, round(x / step) * step)


def make_plan(style, rng, opts=None):
    opts = opts or {}
    f = globals()['_' + style]
    p = f(rng, opts)
    p['style'] = style
    return apply_opts(p, opts)


def apply_opts(p, opts):
    """Options de l'utilisateur communes a tous les styles et presets (priment sur le tirage)."""
    # options communes
    for k in ('fire_escape', 'water_tower', 'roof_props', 'storefront', 'awnings'):
        if opts.get(k) is False:
            p[k] = 0.0 if k != 'storefront' else False
    if opts.get('ground'):
        p['ground'] = opts['ground']
    if opts.get('roof'):
        p['roof'] = opts['roof']
    if opts.get('wall'):
        p['mat']['wall'] = opts['wall']
    if opts.get('storefront') is False and p.get('ground') == 'store':
        p['ground'] = 'base'
    return p


def _common_mats(rng, wall, trim):
    return dict(wall=wall, base=wall, top=wall, side=wall, trim=trim,
                frame=pick(rng, ['frame_dark', 'frame_white', 'frame_green', 'frame_bronze'], [5, 3, 1.5, 1.5]),
                door=pick(rng, ['wood_green', 'wood_dark', 'wood_red', 'metal_door']),
                awning=pick(rng, AWNINGS), sign=pick(rng, SIGNS),
                roof='roof_flat', roof_slope=pick(rng, ['roof_seam_green', 'roof_slate']), cornice=trim)


def _walkup(rng, o):
    n = _opt_int(o, 'floors', 3, 6, rng)
    W = _snap(_opt_f(o, 'W', 7.6, 15.2, rng), 0.3)
    D = _snap(_opt_f(o, 'D', 15, 22, rng), 0.3)
    wall = pick(rng, BRICKS, [5, 3, 2, 2, 1, 1])
    trim = pick(rng, ['trim_stone', 'trim_white', 'trim_brown', 'trim_grey'], [4, 3, 1, 2])
    m = _common_mats(rng, wall, trim)
    if trim == 'trim_white' and rng.random() < 0.5:
        m['cornice'] = 'metal_cornice'
    fh = rng.uniform(3.05, 3.35)
    shape = pick(rng, ['rect', 'segment', 'rect'], [5, 3, 1])
    typ = win(rng.uniform(0.9, 1.05), rng.uniform(1.6, 1.85), 0.82, shape, 'sash', rise=0.16, depth=0.17,
              lintel=pick(rng, ['flat', 'key', 'flat']), sill=True, ac=o.get('win_ac', 0.18), grid=(pick(rng, [1, 2]), 1))
    top = dict(typ)
    if rng.random() < 0.25:
        top.update(shape='arch', h=typ['h'] + 0.2)
    store = o.get('storefront', True) and rng.random() < 0.75
    return dict(
        W=W, D=D, floors=n, floor_h=fh, ground_h=rng.uniform(3.9, 4.4) if store else fh + 0.3,
        bay_w=rng.uniform(2.2, 2.6), margin=rng.uniform(0.55, 0.85), mat=m,
        win_typ=typ, win_top=top, win_base=dict(typ),
        ground='store' if store else pick(rng, ['base', 'stoop'], [2, 1]) if W < 9 else 'base',
        base_floors=1, top_floors=1, bands=[1] if rng.random() < 0.6 else [],
        band_h=0.22, band_d=0.06,
        cornice=pick(rng, ['big', 'big', 'brick']), brackets=rng.random() < 0.85, parapet=rng.uniform(0.5, 0.9),
        roof='flat', piers=None, tiers=None,
        fire_escape=0.7, fire_side='front', water_tower=0.3 if W > 9 else 0.0, bulkhead=0.75,
        ac=rng.randint(0, 2), vents=rng.randint(1, 4), chimneys=rng.randint(1, 3), skylights=rng.randint(0, 1), antenna=0.15,
        awnings=0.5, side_windows=0.3,
        quoins=trim in ('trim_stone', 'trim_grey') and wall.startswith('brick') and rng.random() < 0.35,
        _oriel=rng.randrange(8) if (W < 10 and rng.random() < 0.2) else None,
    )


def _rowhouse(rng, o):
    n = _opt_int(o, 'floors', 3, 4, rng)
    W = _snap(_opt_f(o, 'W', 5.5, 7.6, rng), 0.3)
    D = _snap(_opt_f(o, 'D', 12, 16, rng), 0.3)
    brown = rng.random() < 0.5
    wall = 'stone_brown' if brown else pick(rng, ['brick_red', 'brick_dark', 'brick_brown'])
    trim = 'trim_brown' if brown else pick(rng, ['trim_stone', 'trim_brown', 'trim_white'])
    m = _common_mats(rng, wall, trim)
    m['base'] = 'stone_brown' if (brown or rng.random() < 0.6) else wall
    m['cornice'] = pick(rng, ['metal_cornice', trim, 'wood_dark'])
    typ = win(1.0, rng.uniform(1.8, 2.0), 0.7, pick(rng, ['rect', 'segment', 'arch'], [5, 3, 1]), 'sash', rise=0.15, depth=0.2,
              lintel=pick(rng, ['key', 'flat']), sill=True, surround=rng.random() < 0.5, ac=o.get('win_ac', 0.1))
    return dict(
        W=W, D=D, floors=n, floor_h=rng.uniform(3.1, 3.4), ground_h=2.5, setback=3.2,
        bay_w=W / 3 - 0.2, margin=0.3, mat=m,
        win_typ=typ, win_top=dict(typ, h=typ['h'] - 0.2), win_base=win(0.95, 1.1, 0.9, 'rect', 'grid', grid=(2, 2), lintel='flat', depth=0.2),
        ground='stoop', base_floors=1, top_floors=1, bands=[1], band_h=0.18, band_d=0.05,
        cornice='big', brackets=True, parapet=0.35, roof='flat', piers=None, tiers=None,
        fire_escape=0.0, fire_side='back', water_tower=0.0, bulkhead=0.3,
        ac=0, vents=rng.randint(1, 2), chimneys=rng.randint(1, 2), skylights=1, antenna=0.1, awnings=0.0, side_windows=0.0,
        rustic=m['base'] == 'stone_brown', quoins=False, _oriel=rng.randrange(8) if rng.random() < 0.4 else None,
    )


def _warehouse(rng, o):
    n = _opt_int(o, 'floors', 4, 8, rng)
    W = _snap(_opt_f(o, 'W', 18, 36, rng), 0.3)
    D = _snap(_opt_f(o, 'D', 18, 30, rng), 0.3)
    wall = pick(rng, BRICKS, [5, 4, 2, 2, 1.5, 1])
    m = _common_mats(rng, wall, pick(rng, ['trim_stone', 'trim_grey', wall], [2, 1, 3]))
    m['frame'] = pick(rng, ['frame_dark', 'frame_green', 'frame_white'], [5, 2, 2])
    bay = rng.uniform(3.6, 4.6)
    shape = pick(rng, ['segment', 'rect', 'arch'], [5, 3, 1])
    cols = pick(rng, [3, 4, 4, 5])
    typ = win(bay - rng.uniform(1.0, 1.4), rng.uniform(2.1, 2.6), 0.9, shape, 'grid', rise=0.3, depth=0.28, grid=(cols, pick(rng, [2, 3, 3])),
              lintel='none' if shape != 'rect' else 'flat', band=True, sill=True, pier_min=0.3)
    top = dict(typ)
    if rng.random() < 0.5:
        top.update(shape='arch', h=typ['h'] + 0.3)
    fh = rng.uniform(3.66, 4.2)
    return dict(
        W=W, D=D, floors=n, floor_h=fh, ground_h=rng.uniform(4.4, 5.2),
        bay_w=bay, margin=rng.uniform(1.0, 1.6), mat=m,
        win_typ=typ, win_top=top, win_base=dict(typ),
        ground='warehouse', base_floors=1, top_floors=1, bands=[1] if rng.random() < 0.5 else [], band_h=0.3, band_d=0.08,
        cornice=pick(rng, ['brick', 'simple', 'big'], [4, 2, 1]), brackets=rng.random() < 0.3, parapet=rng.uniform(0.9, 1.4),
        roof='flat', piers=dict(w=rng.uniform(0.45, 0.65), d=rng.uniform(0.1, 0.2), corners=True, edges=False) if rng.random() < 0.8 else None,
        tiers=None, fire_escape=0.4, fire_side=pick(rng, ['front', 'left', 'right']), water_tower=0.65, bulkhead=0.8,
        ac=rng.randint(1, 3), vents=rng.randint(2, 5), chimneys=rng.randint(0, 1), skylights=rng.randint(1, 3), antenna=0.1,
        awnings=0.0, side_windows=0.6,
    )


def _prewar(rng, o):
    n = _opt_int(o, 'floors', 8, 16, rng)
    W = _snap(_opt_f(o, 'W', 18, 30, rng), 0.3)
    D = _snap(_opt_f(o, 'D', 18, 28, rng), 0.3)
    shaft = pick(rng, ['brick_red', 'brick_tan', 'brick_dark', 'stone_smooth', 'brick_brown'], [3, 3, 2, 2, 1])
    m = _common_mats(rng, shaft, pick(rng, ['trim_stone', 'trim_grey']))
    m['base'] = pick(rng, ['stone_block', 'stone_smooth', 'stone_grey'])
    m['top'] = pick(rng, [m['base'], shaft, 'stone_smooth'])
    per = pick(rng, [1, 2], [2, 1])
    bay = rng.uniform(2.3, 2.8) * per
    typ = win(rng.uniform(1.0, 1.2), rng.uniform(1.75, 2.0), 0.8, 'rect', pick(rng, ['sash', 'grid']), depth=0.2, grid=(2, 2),
              lintel=pick(rng, ['flat', 'key', 'none']), sill=True, per_bay=per, ac=o.get('win_ac', 0.12))
    top = dict(typ, shape=pick(rng, ['arch', 'rect', 'segment'], [3, 2, 1]), h=typ['h'] + 0.3, rise=0.25, band=True, lintel='key')
    base = dict(typ, h=typ['h'] + 0.4, surround=True)
    return dict(
        W=W, D=D, floors=n, floor_h=rng.uniform(3.2, 3.5), ground_h=rng.uniform(4.6, 5.4),
        bay_w=bay, margin=rng.uniform(1.0, 1.6), mat=m,
        win_typ=typ, win_top=top, win_base=base,
        ground=pick(rng, ['lobby', 'store'], [2, 1]), base_floors=pick(rng, [2, 3]), top_floors=pick(rng, [1, 2]),
        bands=['base', 'top'], band_h=0.35, band_d=0.12,
        cornice='big', brackets=rng.random() < 0.7, parapet=rng.uniform(0.9, 1.3),
        roof=pick(rng, ['flat', 'mansard', 'hip'], [6, 2, 1]), piers=None, tiers=None,
        fire_escape=0.45 if W < 24 else 0.2, fire_side=pick(rng, ['front', 'left', 'right', 'back']), water_tower=0.55, bulkhead=1.0,
        ac=rng.randint(1, 4), vents=rng.randint(2, 5), chimneys=rng.randint(0, 2), skylights=rng.randint(0, 2), antenna=0.25,
        awnings=0.3, side_windows=0.8, rustic=rng.random() < 0.7,
        quoins=shaft.startswith('brick') and rng.random() < 0.4,
    )


def _tower(rng, o):
    n = _opt_int(o, 'floors', 18, 40, rng)
    W = _snap(_opt_f(o, 'W', 26, 40, rng), 0.3)
    D = _snap(_opt_f(o, 'D', 24, 38, rng), 0.3)
    shaft = pick(rng, ['brick_red', 'brick_tan', 'stone_smooth', 'brick_dark', 'concrete'], [3, 2, 3, 2, 1])
    m = _common_mats(rng, shaft, pick(rng, ['trim_stone', 'trim_grey']))
    m['base'] = pick(rng, ['stone_block', 'stone_grey', 'stone_smooth'])
    m['top'] = pick(rng, [shaft, 'stone_smooth'])
    typ = win(rng.uniform(1.0, 1.25), rng.uniform(1.7, 2.0), 0.8, 'rect', pick(rng, ['sash', 'fixed', 'grid']), depth=0.18,
              lintel='none', sill=True, grid=(2, 2), ac=o.get('win_ac', 0.05))
    # retraits : 2 ou 3 niveaux
    k = pick(rng, [2, 3, 3])
    cuts = sorted(rng.sample(range(int(n * 0.45), n - 2), k - 1)) if n > 8 else []
    tiers = []
    f0 = 0
    inset = 0.0
    for i, c in enumerate(cuts + [n]):
        tiers.append(dict(inset=inset, f0=f0, f1=c))
        f0 = c
        inset += rng.uniform(2.4, 4.2)
    return dict(
        W=W, D=D, floors=n, floor_h=rng.uniform(3.5, 3.8), ground_h=rng.uniform(5.2, 6.4),
        bay_w=rng.uniform(1.9, 2.5), margin=rng.uniform(1.2, 2.0), mat=m,
        win_typ=typ, win_top=dict(typ, shape='arch', h=typ['h'] + 0.4, band=True), win_base=dict(typ, h=typ['h'] + 0.6, surround=True, lintel='flat'),
        ground='lobby', base_floors=pick(rng, [2, 3, 4]), top_floors=1, bands=['base'], band_h=0.45, band_d=0.15,
        cornice=pick(rng, ['simple', 'big']), brackets=False, parapet=rng.uniform(1.0, 1.4),
        roof=pick(rng, ['flat', 'hip', 'flat'], [4, 1, 1]),
        piers=dict(w=rng.uniform(0.35, 0.5), d=rng.uniform(0.12, 0.22), corners=True, edges=False, base_only=False) if rng.random() < 0.85 else None,
        tiers=tiers, fire_escape=0.0, fire_side='back', water_tower=0.5, bulkhead=1.0,
        ac=rng.randint(2, 6), vents=rng.randint(3, 6), chimneys=0, skylights=0, antenna=0.6, awnings=0.0, side_windows=1.0,
        rustic=rng.random() < 0.6, quoins=False,
    )


def _modern(rng, o):
    n = _opt_int(o, 'floors', 6, 22, rng)
    W = _snap(_opt_f(o, 'W', 15, 34, rng), 0.3)
    D = _snap(_opt_f(o, 'D', 15, 28, rng), 0.3)
    wall = pick(rng, ['concrete', 'panel_white', 'brick_tan', 'stone_grey', 'brick_grey'], [3, 3, 2, 1, 1])
    m = _common_mats(rng, wall, pick(rng, ['metal_grey', 'trim_grey', 'panel_white']))
    m['frame'] = pick(rng, ['frame_bronze', 'frame_dark', 'frame_alu'])
    m['base'] = pick(rng, ['stone_grey', 'concrete', wall])
    bay = rng.uniform(1.5, 2.2)
    typ = win(bay - 0.12, rng.uniform(1.5, 1.9), 0.9, 'rect', 'grid', depth=0.08, grid=(1, 1), lintel='none', sill=False, pier_min=0.02, head_min=0.2)
    return dict(
        W=W, D=D, floors=n, floor_h=rng.uniform(3.3, 3.6), ground_h=rng.uniform(4.2, 5.0),
        bay_w=bay, margin=rng.uniform(0.4, 1.0), mat=m,
        win_typ=typ, win_top=dict(typ), win_base=dict(typ),
        ground='glass', base_floors=1, top_floors=1, bands=[], band_h=0.2, band_d=0.05,
        cornice='none', brackets=False, parapet=rng.uniform(0.8, 1.1), roof='flat',
        piers=dict(w=0.4, d=0.25, corners=False, edges=True, base_only=True) if rng.random() < 0.6 else None,
        tiers=None, fire_escape=0.0, fire_side='back', water_tower=0.15, bulkhead=1.0,
        ac=rng.randint(2, 5), vents=rng.randint(2, 4), chimneys=0, skylights=0, antenna=0.4, awnings=0.0, side_windows=0.7,
    )
