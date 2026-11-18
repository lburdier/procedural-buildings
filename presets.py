"""Presets : batiments-types fixes, inspires des grands archetypes new-yorkais (immeuble d'angle a mansarde,
hotel a gradins, tour a pilastres, gratte-ciel a pyramide...).

Un preset fige la silhouette, les materiaux, la trame et les ouvertures ; la graine ne fait varier que les details
(accessoires de toit, emplacement des portes et escaliers de secours, clims, teinte). Les reglages Etages, Largeur et
Profondeur du panneau restent pris en compte. Toute la geometrie est generee par le code : aucun modele n'est repris."""
from . import styles as ST

win = ST.win


def _n(o, d):
    return int(o['floors']) if o.get('floors') else d


def _f(o, k, d):
    return float(o[k]) if o.get(k) else d


def _ac(o, v):
    """Densite de clims du preset, modulee par le reglage du panneau (0,15 par defaut = valeur du preset)."""
    return min(1.0, v * o.get('win_ac', 0.15) / 0.15)


def _base(style, rng, n, W, D):
    p = getattr(ST, '_' + style)(rng, dict(floors=n, W=W, D=D))
    p.update(W=W, D=D, floors=n, tiers=None, piers=None, floor_over=None, quoins=False, rustic=False, _oriel=None)
    return p


def _mats(p, **kw):
    p['mat'].update(kw)


# ---------------------------------------------------------------- petits immeubles

def _corner_mansard(rng, o):
    n = _n(o, 4)
    p = _base('walkup', rng, n, _f(o, 'W', 20.1), _f(o, 'D', 18.0))
    _mats(p, wall='brick_red', base='brick_red', top='brick_red', side='brick_red', trim='trim_stone', cornice='trim_grey',
          roof_slope='roof_seam_green', frame='frame_dark', awning='awning_black', sign='sign_dark')
    typ = win(0.95, 1.75, 0.8, 'segment', 'sash', rise=0.18, depth=0.18, lintel='none', sill=True, surround=True, grid=(1, 1), ac=_ac(o, 0.25))
    p.update(floor_h=3.35, ground_h=4.3, bay_w=2.45, margin=1.0, win_typ=typ, win_top=dict(typ), win_base=dict(typ),
             ground='store', base_floors=1, top_floors=0, bands=[1], band_h=0.3, band_d=0.08,
             cornice='simple', brackets=False, parapet=0.6, roof='mansard', mansard_props=True, quoins=True,
             fire_escape=1.0, fire_side=['front', 'right'], water_tower=1.7, bulkhead=0.0,
             ac=rng.randint(5, 8), vents=3, chimneys=1, skylights=0, antenna=0.1, awnings=1.0, side_windows=1.0)
    return p


def _tenement(rng, o):
    n = _n(o, 8)
    p = _base('walkup', rng, n, _f(o, 'W', 12.6), _f(o, 'D', 22.0))
    _mats(p, wall='brick_red', base='brick_red', top='brick_red', side='brick_red', trim='trim_grey', cornice='trim_grey',
          frame='frame_dark', awning='awning_black')
    typ = win(1.0, 1.75, 0.8, 'rect', 'sash', depth=0.18, lintel='flat', sill=True, grid=(1, 1), ac=_ac(o, 0.3))
    p.update(floor_h=3.2, ground_h=4.4, bay_w=2.5, margin=0.8, win_typ=typ, win_top=dict(typ), win_base=dict(typ),
             ground='store', base_floors=1, top_floors=1, bands=[1, n - 1], band_h=0.3, band_d=0.08,
             cornice='simple', brackets=False, parapet=1.1,
             fire_escape=1.0, fire_side=['right'], water_tower=0.0, bulkhead=1.0,
             ac=3, vents=3, chimneys=1, skylights=0, antenna=0.2, awnings=0.0, side_windows=1.0)
    return p


def _brownstone(rng, o):
    n = _n(o, 4)
    p = _base('rowhouse', rng, n, _f(o, 'W', 6.1), _f(o, 'D', 14.0))
    _mats(p, wall='stone_brown', base='stone_brown', top='stone_brown', side='brick_brown', trim='trim_brown', cornice='metal_cornice',
          frame='frame_dark', door='wood_dark')
    typ = win(1.0, 1.95, 0.7, 'segment', 'sash', rise=0.15, depth=0.22, lintel='key', sill=True, surround=True, ac=_ac(o, 0.1))
    p.update(floor_h=3.3, win_typ=typ, win_top=dict(typ, h=1.75), rustic=True, cornice='big', brackets=True, parapet=0.35,
             bands=[1], setback=3.2, ground='stoop')
    return p


def _brick_rowhouse(rng, o):
    n = _n(o, 4)
    p = _base('rowhouse', rng, n, _f(o, 'W', 7.0), _f(o, 'D', 15.0))
    _mats(p, wall='brick_red', base='stone_brown', top='brick_red', side='brick_red', trim='trim_stone', cornice='trim_stone',
          frame='frame_dark', door='wood_green')
    typ = win(1.05, 1.8, 0.75, 'rect', 'sash', depth=0.2, lintel='flat', sill=True, surround=False, ac=_ac(o, 0.15))
    p.update(floor_h=3.25, win_typ=typ, win_top=dict(typ, h=1.6), rustic=True, cornice='big', brackets=True, parapet=0.4,
             bands=[1, 2], band_h=0.2, setback=3.2, ground='stoop')
    return p


def _arched_bank(rng, o):
    n = _n(o, 2)
    p = _base('walkup', rng, n, _f(o, 'W', 14.4), _f(o, 'D', 22.0))
    _mats(p, wall='brick_deep', base='brick_deep', top='brick_deep', side='brick_deep', trim='stone_warm', cornice='stone_warm', frame='frame_dark')
    big = win(2.9, 7.6, 0.45, 'arch', 'grid', grid=(3, 6), depth=0.3, band=True, lintel='none', sill=True, head_min=0.4, pier_min=0.3)
    p.update(floor_h=8.6 if n <= 2 else 4.2, ground_h=4.6, bay_w=4.2, margin=0.9, win_typ=dict(big), win_top=big, win_base=dict(big),
             ground='glass', base_floors=1, top_floors=1, bands=[1], band_h=0.7, band_d=0.32,
             piers=dict(w=0.8, d=0.32, corners=True, edges=True, mat='trim', from_ground=True),
             cornice='big', brackets=False, parapet=1.3, roof='flat',
             fire_escape=0.0, water_tower=0.0, bulkhead=0.5, ac=rng.randint(4, 6), vents=2, chimneys=0, skylights=1,
             antenna=0.0, awnings=0.0, side_windows=1.0)
    return p


# ---------------------------------------------------------------- immeubles moyens

def _hotel_setback(rng, o):
    n = _n(o, 12)
    p = _base('prewar', rng, n, _f(o, 'W', 30.0), _f(o, 'D', 26.0))
    _mats(p, wall='brick_red', base='brick_red', top='brick_red', side='brick_red', trim='trim_stone', cornice='trim_stone',
          frame='frame_dark', awning='awning_black', sign='sign_dark')
    typ = win(0.85, 1.6, 0.85, 'rect', 'sash', depth=0.18, lintel='flat', sill=True, per_bay=2, grid=(1, 1), ac=_ac(o, 0.35))
    a, b = max(3, n - 2), max(4, n - 1)
    p.update(floor_h=3.2, ground_h=4.4, bay_w=2.6, margin=1.2, win_typ=typ, win_top=dict(typ), win_base=dict(typ),
             ground='store', base_floors=1, top_floors=1, bands=[1, 2, a - 1], band_h=0.4, band_d=0.1,
             tiers=[dict(inset=0.0, f0=0, f1=a), dict(inset=6.0, f0=a, f1=b), dict(inset=10.5, f0=b, f1=n)] if n >= 6 else None,
             cornice='simple', brackets=False, parapet=0.9, roof='flat',
             fire_escape=1.0, fire_side=['front', 'right'], water_tower=0.0, bulkhead=1.0,
             ac=rng.randint(5, 8), vents=4, chimneys=1, skylights=0, antenna=0.2, awnings=1.0, side_windows=1.0)
    return p


def _pilaster_tower(rng, o):
    n = _n(o, 13)
    p = _base('prewar', rng, n, _f(o, 'W', 18.6), _f(o, 'D', 18.6))
    _mats(p, wall='brick_deep', base='brick_deep', top='brick_deep', side='brick_deep', trim='trim_white', cornice='stone_warm',
          frame='frame_dark', roof_slope='roof_seam_green')
    typ = win(0.75, 1.6, 0.85, 'rect', 'sash', depth=0.15, lintel='none', sill=True, per_bay=2, ac=_ac(o, 0.3), pier_min=0.3)
    top = win(2.1, 2.75, 0.35, 'arch', 'grid', grid=(2, 3), depth=0.2, lintel='none', band=True, sill=False, head_min=0.25)
    glaz = win(2.3, 3.0, 0.25, 'rect', 'grid', grid=(2, 3), depth=0.12, lintel='none', sill=False, head_min=0.2, pier_min=0.25)
    g0, g1 = int(n * 0.45), int(n * 0.7)
    p.update(floor_h=3.5, ground_h=5.0, bay_w=3.3, margin=1.1, win_typ=typ, win_top=top, win_base=dict(typ),
             ground='arcade', base_floors=1, top_floors=1, bands=[1, 4, g0, g1, n - 1], band_h=0.55, band_d=0.25,
             piers=dict(w=0.85, d=0.2, corners=True, edges=True, mat='trim', from_ground=True),
             floor_over={k: dict(win=glaz) for k in range(g0, g1)},
             cornice='big', brackets=False, parapet=0.9, roof='hip', hip_pitch=17,
             fire_escape=0.0, water_tower=0.0, bulkhead=0.0, ac=0, vents=0, chimneys=0, skylights=0, antenna=0.0,
             awnings=0.0, side_windows=1.0)
    return p


def _stone_lunette(rng, o):
    n = _n(o, 11)
    p = _base('prewar', rng, n, _f(o, 'W', 28.0), _f(o, 'D', 28.0))
    _mats(p, wall='stone_warm', base='stone_warm', top='stone_warm', side='stone_warm', trim='trim_grey', cornice='trim_grey',
          frame='frame_dark', roof_slope='metal_grey', sign='sign_dark')
    typ = win(0.95, 1.85, 0.75, 'rect', 'grid', grid=(2, 3), depth=0.16, lintel='none', sill=True, per_bay=2, ac=_ac(o, 0.3))
    top = win(2.0, 1.9, 0.6, 'rect', 'grid', grid=(3, 2), depth=0.18, lintel='none', sill=True)
    small = win(0.9, 3.6, 0.9, 'arch', 'grid', grid=(1, 4), depth=0.18, lintel='none', sill=True, band=True)
    lunette = win(9.0, 5.4, 0.3, 'arch', 'grid', grid=(6, 2), depth=0.25, lintel='none', sill=False, band=True, head_min=0.12, pier_min=0.2)
    p.update(floor_h=3.3, floor_h_over={-2: 6.2}, ground_h=4.4, bay_w=2.9, margin=1.2, win_typ=typ, win_top=top, win_base=dict(typ),
             ground='store', base_floors=1, top_floors=1, bands=[1, n - 2, n - 1], band_h=0.45, band_d=0.2,
             floor_over={-2: [dict(sides=('front',), cols=[2, 1.2, 4, 1.2, 2], bays=[None, small, lunette, small, None]),
                              dict(win=dict(small, per_bay=2))]},
             cornice='simple', brackets=False, parapet=0.9, roof='hip', hip_pitch=24,
             fire_escape=0.0, water_tower=0.0, bulkhead=0.0, ac=0, vents=0, chimneys=0, skylights=0, antenna=0.0,
             awnings=0.0, side_windows=1.0)
    return p


def _tan_prewar(rng, o):
    n = _n(o, 11)
    p = _base('prewar', rng, n, _f(o, 'W', 24.0), _f(o, 'D', 21.0))
    _mats(p, wall='brick_tan', base='stone_warm', top='brick_tan', side='brick_tan', trim='trim_grey', cornice='trim_grey', frame='frame_dark')
    typ = win(0.95, 1.8, 0.8, 'rect', 'sash', depth=0.18, lintel='flat', sill=True, grid=(1, 1), ac=_ac(o, 0.35))
    p.update(floor_h=3.3, ground_h=4.6, bay_w=2.3, margin=1.3, win_typ=typ,
             win_top=win(0.95, 2.1, 0.7, 'arch', 'sash', depth=0.2, lintel='none', sill=True, ac=0.0), win_base=dict(typ, h=2.0, surround=True),
             ground='lobby', base_floors=2, top_floors=1, bands=['base', 'top'], band_h=0.35, band_d=0.14, rustic=True,
             cornice='big', brackets=True, parapet=2.4, roof='flat',
             fire_escape=1.0, fire_side=['front', 'right'], water_tower=0.0, bulkhead=1.0,
             ac=4, vents=3, chimneys=0, skylights=0, antenna=1.0, awnings=0.0, side_windows=1.0)
    return p


def _arch_warehouse(rng, o):
    n = _n(o, 7)
    p = _base('warehouse', rng, n, _f(o, 'W', 45.0), _f(o, 'D', 22.0))
    _mats(p, wall='brick_deep', base='brick_deep', top='brick_deep', side='brick_deep', trim='metal_grey', cornice='metal_grey', frame='frame_dark')
    typ = win(1.0, 2.2, 0.8, 'segment', 'grid', grid=(1, 3), rise=0.15, depth=0.22, lintel='none', sill=True, per_bay=2, pier_min=0.25)
    top = win(2.8, 3.0, 0.4, 'arch', 'grid', grid=(3, 3), depth=0.25, band=True, lintel='none', sill=True, head_min=0.2)
    p.update(floor_h=3.8, ground_h=4.6, bay_w=4.2, margin=1.5, win_typ=typ, win_top=top, win_base=dict(typ),
             ground='arcade', base_floors=1, top_floors=1, bands=[1, 2, n - 1], band_h=0.3, band_d=0.1,
             piers=dict(w=0.6, d=0.16, corners=True, edges=False, mat='wall'),
             cornice='simple', brackets=False, parapet=0.8, roof='flat',
             fire_escape=0.0, water_tower=0.0, bulkhead=1.0, ac=rng.randint(8, 12), vents=5, chimneys=0, skylights=0,
             antenna=0.1, awnings=0.0, side_windows=1.0)
    return p


def _limestone_office(rng, o):
    n = _n(o, 14)
    p = _base('prewar', rng, n, _f(o, 'W', 28.0), _f(o, 'D', 26.0))
    _mats(p, wall='stone_smooth', base='stone_warm', top='stone_smooth', side='stone_smooth', trim='stone_warm', cornice='trim_grey', frame='frame_dark')
    typ = win(0.8, 1.9, 0.75, 'rect', 'grid', grid=(1, 2), depth=0.18, lintel='none', sill=True, per_bay=2, ac=_ac(o, 0.12))
    a = max(3, n - 2)
    p.update(floor_h=3.4, ground_h=6.2, bay_w=2.5, margin=1.4, win_typ=typ, win_top=dict(typ), win_base=dict(typ),
             ground='arcade', base_floors=1, top_floors=1, bands=[1, 2, a - 1], band_h=0.4, band_d=0.15,
             piers=dict(w=0.42, d=0.14, corners=True, edges=False, mat='trim'),
             tiers=[dict(inset=0.0, f0=0, f1=a), dict(inset=2.2, f0=a, f1=n)] if n >= 6 else None,
             cornice='simple', brackets=False, parapet=1.1, roof='flat',
             fire_escape=0.0, water_tower=0.0, bulkhead=1.0, ac=4, vents=3, chimneys=0, skylights=0, antenna=0.3,
             awnings=0.0, side_windows=1.0)
    return p


# ---------------------------------------------------------------- grands immeubles

def _setback_spire(rng, o):
    n = _n(o, 27)
    p = _base('tower', rng, n, _f(o, 'W', 24.0), _f(o, 'D', 24.0))
    _mats(p, wall='brick_deep', base='stone_smooth', top='brick_deep', side='brick_deep', trim='trim_white', cornice='trim_white',
          frame='frame_dark', roof_slope='roof_seam_green')
    typ = win(0.75, 1.6, 0.85, 'rect', 'sash', depth=0.15, lintel='none', sill=True, per_bay=2, grid=(1, 1), ac=_ac(o, 0.3))
    t1, t2, t3 = int(n * 0.62), int(n * 0.77), int(n * 0.89)
    tiers = [dict(inset=0.0, f0=0, f1=t1), dict(inset=1.8, f0=t1, f1=t2), dict(inset=3.6, f0=t2, f1=t3), dict(inset=6.2, f0=t3, f1=n)]
    p.update(floor_h=3.5, ground_h=6.5, bay_w=2.6, margin=1.2, win_typ=typ, win_top=dict(typ), win_base=dict(typ),
             ground='glass', base_floors=1, top_floors=1, bands=[1, 3, 4], band_h=0.3, band_d=0.1,
             piers=dict(w=0.8, d=0.3, corners=True, edges=True, base_only=True),
             tiers=tiers if n >= 10 else None, cornice='simple', brackets=False, parapet=1.0, roof='hip', hip_pitch=55,
             fire_escape=0.0, water_tower=0.0, bulkhead=0.0, ac=0, vents=0, chimneys=0, skylights=0, antenna=0.0,
             awnings=0.0, side_windows=1.0)
    return p


def _modern_slab(rng, o):
    n = _n(o, 28)
    p = _base('modern', rng, n, _f(o, 'W', 30.0), _f(o, 'D', 54.0))
    _mats(p, wall='panel_white', base='stone_grey', top='panel_white', side='panel_white', trim='panel_white', cornice='panel_white', frame='frame_alu')
    typ = win(1.6, 1.6, 0.95, 'rect', 'grid', grid=(1, 1), depth=0.1, lintel='none', sill=False, pier_min=0.05, head_min=0.2)
    p.update(floor_h=3.5, ground_h=5.5, bay_w=1.7, margin=0.6, win_typ=typ, win_top=dict(typ), win_base=dict(typ),
             ground='glass', base_floors=1, top_floors=1, bands=[1], band_h=0.5, band_d=0.3,
             piers=dict(w=0.5, d=0.3, corners=False, edges=True, base_only=True),
             cornice='none', brackets=False, parapet=1.2, roof='flat',
             fire_escape=0.0, water_tower=0.0, bulkhead=1.0, ac=rng.randint(4, 7), vents=3, chimneys=0, skylights=0, antenna=1.0,
             awnings=0.0, side_windows=1.0)
    return p


# ---------------------------------------------------------------- v1.3 : autres archetypes new-yorkais

def _old_law(rng, o):
    """Immeuble de rapport etroit du Lower East Side : 3 travees, escalier de secours en facade, corniche en tole."""
    n = _n(o, 5)
    p = _base('walkup', rng, n, _f(o, 'W', 7.8), _f(o, 'D', 24.0))
    wall = ST.pick(rng, ['brick_orange', 'brick_red', 'brick_painted'], [3, 2, 1])
    _mats(p, wall=wall, base=wall, top=wall, side=wall, trim='trim_stone', cornice='metal_cornice',
          frame='frame_dark', awning=ST.pick(rng, ['awning_red', 'awning_green', 'awning_blue']), sign=ST.pick(rng, ST.SIGNS))
    typ = win(0.95, 1.75, 0.8, 'segment', 'sash', rise=0.14, depth=0.18, lintel='key', sill=True, surround=False, ac=_ac(o, 0.35))
    p.update(floor_h=3.1, ground_h=4.0, bay_w=2.3, margin=0.45, win_typ=typ, win_top=dict(typ), win_base=dict(typ),
             ground='store', base_floors=1, top_floors=0, bands=[1], band_h=0.25, band_d=0.06,
             cornice='big', brackets=True, parapet=0.55, roof='flat',
             fire_escape=1.0, fire_side=['front'], water_tower=0.0, bulkhead=0.7,
             ac=0, vents=2, chimneys=2, skylights=1, antenna=0.3, awnings=1.0, side_windows=0.0)
    return p


def _bodega_corner(rng, o):
    """Immeuble d'angle a commerces : brique peinte, enseignes et auvents, escaliers de secours sur les deux rues."""
    n = _n(o, 4)
    p = _base('walkup', rng, n, _f(o, 'W', 15.0), _f(o, 'D', 16.5))
    wall = ST.pick(rng, ['brick_painted', 'brick_tan', 'brick_orange'], [2, 1, 1])
    _mats(p, wall=wall, base=wall, top=wall, side=wall, trim='trim_white', cornice=wall,
          frame='frame_dark', awning=ST.pick(rng, ['awning_red', 'awning_green', 'awning_blue']),
          sign=ST.pick(rng, ['sign_red', 'sign_green', 'sign_dark']))
    typ = win(1.0, 1.7, 0.85, 'rect', 'sash', depth=0.16, lintel='flat', sill=True, ac=_ac(o, 0.4))
    p.update(floor_h=3.1, ground_h=4.2, bay_w=2.4, margin=0.7, win_typ=typ, win_top=dict(typ), win_base=dict(typ),
             ground='store', base_floors=1, top_floors=0, bands=[], cornice='brick', brackets=False, parapet=0.8, roof='flat',
             fire_escape=1.0, fire_side=['front', 'right'], water_tower=0.0, bulkhead=1.0,
             ac=rng.randint(2, 4), vents=2, chimneys=1, skylights=0, antenna=0.4, awnings=1.0, side_windows=1.0)
    return p


def _cast_iron_loft(rng, o):
    """Loft a facade de fonte (SoHo) : colonnes peintes, entablement a chaque etage, hautes baies, escalier de secours."""
    n = _n(o, 6)
    p = _base('warehouse', rng, n, _f(o, 'W', 15.3), _f(o, 'D', 30.0))
    paint, trim = ST.pick(rng, [('trim_white', 'trim_stone'), ('stone_smooth', 'trim_white'), ('metal_grey', 'trim_grey')], [3, 2, 1])
    _mats(p, wall=paint, base=paint, top=paint, side='brick_red', trim=trim, cornice=trim,
          frame='frame_dark', awning='awning_black', sign='sign_dark')
    typ = win(1.35, 2.75, 0.55, 'segment', 'sash', rise=0.18, depth=0.2, lintel='none', sill=True, grid=(1, 1), pier_min=0.4,
              ac=_ac(o, 0.12))
    p.update(floor_h=4.2, ground_h=4.8, bay_w=3.05, margin=0.6, win_typ=typ, win_top=dict(typ), win_base=dict(typ),
             ground='store', base_floors=1, top_floors=0, bands=list(range(1, n)), band_h=0.42, band_d=0.14,
             piers=dict(w=0.5, d=0.2, corners=True, edges=True, mat='trim'),
             cornice='big', brackets=True, parapet=0.9, roof='flat',
             fire_escape=1.0, fire_side=['front'], water_tower=1.0, bulkhead=1.0, blank_side=True,
             ac=rng.randint(1, 3), vents=3, chimneys=0, skylights=2, antenna=0.1, awnings=0.0, side_windows=0.0)
    return p


def _garment_loft(rng, o):
    """Loft de confection (Garment District) : brique beige, baies industrielles, retraits du zonage de 1916, chateau d'eau."""
    n = _n(o, 18)
    p = _base('prewar', rng, n, _f(o, 'W', 30.0), _f(o, 'D', 30.0))
    _mats(p, wall='brick_tan', base='stone_smooth', top='brick_tan', side='brick_tan', trim='trim_stone', cornice='trim_stone',
          frame=ST.pick(rng, ['frame_dark', 'frame_green']), sign='sign_dark', awning='awning_black')
    typ = win(2.5, 2.3, 0.8, 'rect', 'grid', grid=(3, 2), depth=0.18, lintel='none', sill=True, pier_min=0.3)
    t1, t2 = max(3, n - 5), max(4, n - 2)
    p.update(floor_h=3.75, ground_h=5.0, bay_w=3.4, margin=1.1, win_typ=typ, win_top=dict(typ), win_base=dict(typ, h=2.6),
             ground='store', base_floors=2, top_floors=0, bands=[2, t1], band_h=0.4, band_d=0.12,
             piers=dict(w=0.5, d=0.12, corners=True, edges=False, mat='trim'),
             tiers=[dict(inset=0.0, f0=0, f1=t1), dict(inset=3.0, f0=t1, f1=t2), dict(inset=6.0, f0=t2, f1=n)] if n >= 8 else None,
             cornice='simple', brackets=False, parapet=1.0, roof='flat',
             fire_escape=0.7, fire_side=['right', 'back'], water_tower=1.0, bulkhead=1.0,
             ac=rng.randint(3, 6), vents=4, chimneys=0, skylights=0, antenna=0.3, awnings=0.0, side_windows=1.0)
    return p


def _deco_tower(rng, o):
    """Tour Art deco a gradins : brique chamois, rayures verticales de piliers, cinq gradins, mat au sommet."""
    n = _n(o, 36)
    p = _base('tower', rng, n, _f(o, 'W', 36.0), _f(o, 'D', 36.0))
    _mats(p, wall='brick_tan', base='stone_smooth', top='stone_smooth', side='brick_tan', trim='stone_smooth', cornice='stone_smooth',
          frame='frame_dark')
    typ = win(0.9, 1.75, 0.8, 'rect', 'sash', depth=0.16, lintel='none', sill=False, grid=(1, 1), ac=_ac(o, 0.1), pier_min=0.2)
    t = [int(n * f) for f in (0.55, 0.7, 0.82, 0.92)]
    tiers = [dict(inset=0.0, f0=0, f1=t[0]), dict(inset=3.0, f0=t[0], f1=t[1]), dict(inset=6.5, f0=t[1], f1=t[2]),
             dict(inset=10.0, f0=t[2], f1=t[3]), dict(inset=12.5, f0=t[3], f1=n)]
    p.update(floor_h=3.6, ground_h=6.8, bay_w=1.6, margin=1.0, win_typ=typ, win_top=dict(typ, h=2.2, shape='arch', band=True),
             win_base=win(1.3, 2.6, 0.8, 'rect', 'grid', grid=(2, 3), depth=0.22, lintel='none', sill=True),
             ground='lobby', base_floors=3, top_floors=1, bands=['base'], band_h=0.5, band_d=0.18,
             piers=dict(w=0.36, d=0.22, corners=True, edges=True),
             tiers=tiers if n >= 14 else None, cornice='none', brackets=False, parapet=1.6, roof='flat',
             fire_escape=0.0, water_tower=0.0, bulkhead=1.0, ac=0, vents=2, chimneys=0, skylights=0, antenna=1.0,
             awnings=0.0, side_windows=1.0)
    return p


def _white_brick(rng, o):
    """Immeuble d'appartements en brique blanche (annees 60) : longues fenetres a cadre alu, clims, chateau d'eau."""
    n = _n(o, 20)
    p = _base('modern', rng, n, _f(o, 'W', 40.0), _f(o, 'D', 22.0))
    _mats(p, wall='brick_white', base='stone_grey', top='brick_white', side='brick_white', trim='trim_grey', cornice='brick_white',
          frame='frame_alu', door='metal_door')
    typ = win(2.1, 1.5, 0.9, 'rect', 'sash', depth=0.1, lintel='none', sill=True, grid=(2, 1), ac=_ac(o, 0.35), pier_min=0.3)
    p.update(floor_h=2.85, ground_h=4.2, bay_w=3.2, margin=1.0, win_typ=typ, win_top=dict(typ), win_base=dict(typ),
             ground='glass', base_floors=1, top_floors=0, bands=[], cornice='none', brackets=False, parapet=1.0, roof='flat',
             piers=dict(w=0.5, d=0.3, corners=False, edges=True, base_only=True),
             fire_escape=0.0, water_tower=1.0, bulkhead=1.0, ac=0, vents=3, chimneys=0, skylights=0, antenna=0.6,
             awnings=0.0, side_windows=1.0)
    return p


def _nycha(rng, o):
    """Barre de logements sociaux en brique rouge-orange : trame simple et repetitive, sans corniche."""
    n = _n(o, 14)
    p = _base('modern', rng, n, _f(o, 'W', 58.0), _f(o, 'D', 14.0))
    _mats(p, wall='brick_orange', base='brick_orange', top='brick_orange', side='brick_orange', trim='trim_grey', cornice='brick_orange',
          frame='frame_alu', door='metal_door')
    typ = win(1.25, 1.45, 0.85, 'rect', 'sash', depth=0.1, lintel='none', sill=True, per_bay=2, ac=_ac(o, 0.3))
    p.update(floor_h=2.75, ground_h=3.0, bay_w=3.4, margin=1.2, win_typ=typ, win_top=dict(typ), win_base=dict(typ),
             ground='base', base_floors=1, top_floors=0, bands=[], cornice='none', brackets=False, parapet=0.9, roof='flat',
             fire_escape=0.0, water_tower=0.0, bulkhead=1.0, ac=0, vents=4, chimneys=0, skylights=0, antenna=0.5,
             awnings=0.0, side_windows=0.0)
    return p


def _glass_curtain(rng, o):
    """Tour de bureaux a mur-rideau (style international) : verre sombre, meneaux, pilotis, ecran technique."""
    n = _n(o, 38)
    p = _base('modern', rng, n, _f(o, 'W', 32.0), _f(o, 'D', 46.0))
    _mats(p, wall='spandrel_dark', base='stone_grey', top='spandrel_dark', side='spandrel_dark', trim='spandrel_dark',
          cornice='spandrel_dark', frame=ST.pick(rng, ['frame_dark', 'frame_bronze']))
    typ = win(1.48, 2.7, 0.75, 'rect', 'grid', grid=(1, 1), depth=0.06, lintel='none', sill=False, pier_min=0.04, head_min=0.15)
    p.update(floor_h=3.9, ground_h=7.5, bay_w=1.55, margin=0.4, win_typ=typ, win_top=dict(typ), win_base=dict(typ),
             ground='glass', base_floors=1, top_floors=0, bands=[], cornice='none', brackets=False, parapet=2.4, roof='flat',
             piers=dict(w=0.5, d=0.5, corners=False, edges=True, base_only=True),
             fire_escape=0.0, water_tower=0.0, bulkhead=1.0, ac=rng.randint(3, 6), vents=2, chimneys=0, skylights=0, antenna=0.3,
             awnings=0.0, side_windows=1.0)
    return p


def _terrace_coop(rng, o):
    """Grand immeuble residentiel d'avant-guerre (Upper West Side) : socle a bossages, marquise, terrasses en gradins."""
    n = _n(o, 17)
    p = _base('prewar', rng, n, _f(o, 'W', 30.0), _f(o, 'D', 30.0))
    wall = ST.pick(rng, ['brick_brown', 'brick_tan', 'brick_red'], [2, 2, 1])
    _mats(p, wall=wall, base='stone_block', top='stone_smooth', side=wall, trim='trim_stone', cornice='trim_stone',
          frame='frame_dark', roof_slope='roof_seam_green')
    typ = win(1.0, 1.85, 0.8, 'rect', 'grid', grid=(2, 3), depth=0.18, lintel='flat', sill=True, per_bay=2, ac=_ac(o, 0.25))
    t1, t2 = max(3, n - 3), max(4, n - 1)
    p.update(floor_h=3.25, ground_h=4.8, bay_w=2.7, margin=1.4, win_typ=typ,
             win_top=dict(typ, shape='arch', h=2.2, lintel='key', band=True, ac=0.0), win_base=dict(typ, h=2.0, surround=True),
             ground='lobby', base_floors=2, top_floors=1, bands=['base', t1, 'top'], band_h=0.4, band_d=0.15, rustic=True,
             tiers=[dict(inset=0.0, f0=0, f1=t1), dict(inset=2.8, f0=t1, f1=t2), dict(inset=6.5, f0=t2, f1=n)] if n >= 8 else None,
             cornice='big', brackets=True, parapet=1.1, roof='flat',
             fire_escape=0.0, water_tower=1.0, bulkhead=1.0, ac=2, vents=3, chimneys=1, skylights=0, antenna=0.2,
             awnings=0.0, side_windows=1.0)
    return p


def _gothic_tower(rng, o):
    """Gratte-ciel neo-gothique : pierre claire, piliers continus du sol au sommet, baies cintrees, fleche de cuivre."""
    n = _n(o, 30)
    p = _base('tower', rng, n, _f(o, 'W', 26.0), _f(o, 'D', 26.0))
    _mats(p, wall='stone_smooth', base='stone_smooth', top='stone_smooth', side='stone_smooth', trim='trim_white', cornice='trim_white',
          frame='frame_dark', roof_slope='roof_seam_green')
    typ = win(0.85, 2.0, 0.7, 'rect', 'grid', grid=(1, 2), depth=0.2, lintel='none', sill=False, per_bay=2, pier_min=0.2, ac=_ac(o, 0.05))
    top = win(1.8, 3.2, 0.5, 'arch', 'grid', grid=(2, 4), depth=0.28, lintel='none', sill=False, band=True, head_min=0.25)
    t1, t2 = int(n * 0.72), int(n * 0.87)
    p.update(floor_h=3.6, ground_h=7.0, bay_w=2.6, margin=1.2, win_typ=typ, win_top=top,
             win_base=win(1.9, 4.0, 1.0, 'arch', 'grid', grid=(2, 4), depth=0.3, lintel='key', band=True, sill=True, head_min=0.3),
             floor_h_over={-1: 5.0}, ground='arcade', base_floors=2, top_floors=1, bands=[2], band_h=0.5, band_d=0.2,
             piers=dict(w=0.55, d=0.38, corners=True, edges=True, mat='wall', from_ground=True),
             tiers=[dict(inset=0.0, f0=0, f1=t1), dict(inset=3.2, f0=t1, f1=t2), dict(inset=6.6, f0=t2, f1=n)] if n >= 10 else None,
             cornice='simple', brackets=False, parapet=1.4, roof='hip', hip_pitch=64,
             fire_escape=0.0, water_tower=0.0, bulkhead=0.0, ac=0, vents=0, chimneys=0, skylights=0, antenna=0.0,
             awnings=0.0, side_windows=1.0)
    return p


def _concrete_loft(rng, o):
    """Entrepot a ossature beton du bord de l'eau (Brooklyn) : grille de poteaux et dalles, baies d'acier, chateau d'eau."""
    n = _n(o, 9)
    p = _base('warehouse', rng, n, _f(o, 'W', 48.0), _f(o, 'D', 30.0))
    _mats(p, wall=ST.pick(rng, ['concrete', 'brick_painted'], [3, 1]), base='concrete', top='concrete', side='concrete',
          trim='concrete', cornice='concrete', frame=ST.pick(rng, ['frame_dark', 'frame_green']))
    typ = win(4.2, 2.6, 0.9, 'rect', 'grid', grid=(6, 3), depth=0.25, lintel='none', sill=True, pier_min=0.15, head_min=0.25)
    p.update(floor_h=3.9, ground_h=4.8, bay_w=5.0, margin=0.5, win_typ=typ, win_top=dict(typ), win_base=dict(typ),
             ground='warehouse', base_floors=1, top_floors=0, bands=list(range(1, n)), band_h=0.55, band_d=0.12,
             piers=dict(w=0.6, d=0.12, corners=True, edges=True, mat='trim'),
             cornice='simple', brackets=False, parapet=1.1, roof='flat',
             fire_escape=0.0, water_tower=1.0, bulkhead=1.0, ac=rng.randint(2, 4), vents=5, chimneys=1, skylights=2, antenna=0.2,
             awnings=0.0, side_windows=1.0)
    return p


# (cle, nom, description, style de base, fonction)
PRESETS = [
    ('corner_mansard', "Angle à mansarde verte", "Brique rouge, chaînages de pierre, mansarde de zinc vert à lucarnes, commerces, deux escaliers de secours, château d'eau", 'walkup', _corner_mansard),
    ('tenement', "Immeuble de rapport étroit", "8 étages de brique rouge, bandeaux gris, escalier de secours latéral, commerce", 'walkup', _tenement),
    ('brownstone', "Brownstone", "Maison de ville en grès brun à bossages, perron, linteaux à clé, corniche en tôle", 'rowhouse', _brownstone),
    ('brick_rowhouse', "Maison de ville en brique", "Brique rouge sur soubassement de grès, perron, bandeaux de pierre", 'rowhouse', _brick_rowhouse),
    ('arched_bank', "Banque à grandes arcades", "Deux niveaux : grandes baies cintrées entre pilastres de pierre, rez-de-chaussée vitré", 'walkup', _arched_bank),
    ('hotel_setback', "Hôtel en brique à gradins", "12 étages de brique rouge, bandeaux crème, deux retraits en couronnement, escaliers de secours", 'prewar', _hotel_setback),
    ('pilaster_tower', "Tour à pilastres et toit vert", "Brique et pilastres de pierre sur toute la hauteur, étages vitrés, attique cintré, croupe en zinc vert", 'prewar', _pilaster_tower),
    ('stone_lunette', "Immeuble de pierre à lunette", "Pierre appareillée, fenêtres à petits bois, grande lunette en attique, toit en croupe", 'prewar', _stone_lunette),
    ('tan_prewar', "Avant-guerre en brique beige", "Brique beige sur socle de pierre à bossages, attique cintré, haute frise, deux escaliers de secours", 'prewar', _tan_prewar),
    ('arch_warehouse', "Entrepôt à arcades", "Long bâtiment de brique, baies à petits carreaux, dernier étage cintré, arcades au rez-de-chaussée", 'warehouse', _arch_warehouse),
    ('limestone_office', "Bureaux en pierre claire", "14 étages de pierre claire, pilastres, arcades sur double hauteur, attique en retrait", 'prewar', _limestone_office),
    ('setback_spire', "Gratte-ciel à pyramide verte", "Brique rouge, trois retraits, colonnade de pierre au pied, pyramide de zinc vert", 'tower', _setback_spire),
    ('modern_slab', "Tour de bureaux moderne", "Lame de 28 étages en panneaux blancs, fenêtres en bandeau, rez-de-chaussée vitré", 'modern', _modern_slab),
    ('old_law', "Immeuble de rapport à escalier en façade", "5 étages, 3 travées, escalier de secours sur la rue, corniche en tôle, commerce à auvent (Lower East Side)", 'walkup', _old_law),
    ('bodega_corner', "Angle à commerces (bodega)", "4 étages de brique peinte, enseignes et auvents, escaliers de secours sur les deux rues", 'walkup', _bodega_corner),
    ('cast_iron_loft', "Loft à façade de fonte", "6 étages : colonnes peintes, entablement à chaque étage, hautes baies, château d'eau (SoHo)", 'warehouse', _cast_iron_loft),
    ('garment_loft', "Loft de confection à retraits", "18 étages de brique beige, baies industrielles, deux retraits, château d'eau (Garment District)", 'prewar', _garment_loft),
    ('deco_tower', "Tour Art déco à gradins", "36 étages de brique chamois, piliers en rayures verticales, cinq gradins, mât", 'tower', _deco_tower),
    ('white_brick', "Immeuble en brique blanche", "20 étages des années 60, longues fenêtres à cadre alu, clims, château d'eau", 'modern', _white_brick),
    ('nycha', "Barre de logements sociaux", "14 étages de brique orangée, trame répétitive, sans corniche", 'modern', _nycha),
    ('glass_curtain', "Tour de verre (style international)", "38 étages de mur-rideau sombre, pilotis, rez-de-chaussée vitré", 'modern', _glass_curtain),
    ('terrace_coop', "Résidentiel à terrasses (Upper West Side)", "17 étages, socle à bossages, marquise, gradins en terrasses, château d'eau", 'prewar', _terrace_coop),
    ('gothic_tower', "Gratte-ciel néo-gothique", "30 étages de pierre claire, piliers continus, baies cintrées, flèche de cuivre vert", 'tower', _gothic_tower),
    ('concrete_loft', "Entrepôt en béton (bord de l'eau)", "9 étages à ossature béton, grandes baies d'acier, quais, château d'eau", 'warehouse', _concrete_loft),
]
KEYS = [p[0] for p in PRESETS]
BY_KEY = {p[0]: p for p in PRESETS}


def make(key, rng, opts=None):
    opts = opts or {}
    _, label, _, style, fn = BY_KEY[key]
    p = fn(rng, opts)
    p['style'] = style
    p['preset'] = key
    return ST.apply_opts(p, opts)
