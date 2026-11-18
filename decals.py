"""Decalcomanies procedurales : un atlas d'images dessine par le code (aucune image externe) et son materiau.

Atlas 2048 x 2048 (RGBA, empaquete dans le .blend) :
  - 8 tags (graffitis calligraphies, coulures, contour)        : cellules 1024 x 256
  - 3 murs d'affiches collees (dechirees, passees) + autocollants : 512 x 512
  - 1 ancienne publicite peinte sur brique (ghost sign)         : 1024 x 512
  - 2 coulures de salete, 2 coulures de rouille                  : 128 x 512 (verticales)
  - 2 reseaux de fissures                                        : 256 x 512
Les textes sont des barres et des blocs abstraits : rien n'est recopie d'une marque ou d'une oeuvre."""
import math
import random

import bpy

ATLAS = "BG_decals"
SIZE = 2048
VERSION = 1

# type -> liste de cellules (x, y, largeur, hauteur) en pixels, origine en bas a gauche (convention Blender)
CELLS = {
    'tag': [(x, 1024 + 256 * r, 1024, 256) for r in range(4) for x in (0, 1024)],
    'poster': [(0, 512, 512, 512), (512, 512, 512, 512), (1024, 512, 512, 512)],
    'sticker': [(1536, 512, 512, 512)],
    'ghost': [(0, 0, 1024, 512)],
    'streak': [(1024, 0, 128, 512), (1152, 0, 128, 512)],
    'rust': [(1280, 0, 128, 512), (1408, 0, 128, 512)],
    'crack': [(1536, 0, 256, 512), (1792, 0, 256, 512)],
}

SPRAY = [(0.02, 0.02, 0.02), (0.75, 0.75, 0.78), (0.9, 0.9, 0.88), (0.65, 0.04, 0.04), (0.05, 0.18, 0.6), (0.85, 0.25, 0.55),
         (0.1, 0.5, 0.15), (0.95, 0.6, 0.05), (0.45, 0.1, 0.6)]
PAPER = [(0.92, 0.88, 0.2), (0.85, 0.12, 0.1), (0.92, 0.9, 0.84), (0.1, 0.55, 0.75), (0.85, 0.3, 0.6), (0.08, 0.08, 0.08),
         (0.95, 0.5, 0.1), (0.2, 0.6, 0.3)]


def uv_rect(kind, index):
    """Rectangle UV (u0, v0, u1, v1) d'une cellule."""
    cells = CELLS[kind]
    x, y, w, h = cells[index % len(cells)]
    return (x / SIZE, y / SIZE, (x + w) / SIZE, (y + h) / SIZE)


def count(kind):
    return len(CELLS[kind])


# ------------------------------------------------------------------ dessin (numpy)


def _np():
    import numpy as np
    return np


def _vnoise(h, w, cell, rng, octaves=3):
    """Bruit de valeur lisse (h, w) dans [0, 1]."""
    np = _np()
    out = np.zeros((h, w), dtype=np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        c = max(2.0, cell / (2 ** o))
        gh, gw = int(h / c) + 3, int(w / c) + 3
        g = np.array([rng.random() for _ in range(gh * gw)], dtype=np.float32).reshape(gh, gw)
        ys = np.arange(h, dtype=np.float32) / c
        xs = np.arange(w, dtype=np.float32) / c
        y0 = ys.astype(int); x0 = xs.astype(int)
        fy = ys - y0; fx = xs - x0
        fy = fy * fy * (3 - 2 * fy); fx = fx * fx * (3 - 2 * fx)
        a = g[y0][:, x0]; b = g[y0][:, x0 + 1]; c_ = g[y0 + 1][:, x0]; d = g[y0 + 1][:, x0 + 1]
        top = a + (b - a) * fx[None, :]
        bot = c_ + (d - c_) * fx[None, :]
        out += amp * (top + (bot - top) * fy[:, None])
        tot += amp
        amp *= 0.5
    return out / tot


def _over(dst, rgb, a):
    """Compose (rgb, alpha a (h, w)) par-dessus dst (h, w, 4), en place."""
    np = _np()
    a = np.clip(a, 0.0, 1.0)
    da = dst[..., 3]
    oa = a + da * (1 - a)
    safe = np.where(oa > 1e-6, oa, 1.0)
    for k in range(3):
        c = rgb[k] if not hasattr(rgb, 'shape') else rgb[..., k]
        dst[..., k] = (c * a + dst[..., k] * da * (1 - a)) / safe
    dst[..., 3] = oa


def _stroke(cov, pts, r, soft=1.0):
    """Trait epais (polyligne pts en pixels) accumule dans la couverture cov (max)."""
    np = _np()
    h, w = cov.shape
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        bx0, bx1 = int(max(0, min(x0, x1) - r - 2)), int(min(w, max(x0, x1) + r + 3))
        by0, by1 = int(max(0, min(y0, y1) - r - 2)), int(min(h, max(y0, y1) + r + 3))
        if bx1 <= bx0 or by1 <= by0:
            continue
        ys, xs = np.mgrid[by0:by1, bx0:bx1].astype(np.float32)
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy
        t = np.clip(((xs - x0) * dx + (ys - y0) * dy) / L2, 0, 1) if L2 > 1e-9 else 0.0
        d = np.hypot(xs - (x0 + t * dx), ys - (y0 + t * dy))
        a = np.clip((r - d) / soft + 0.5, 0, 1)
        cov[by0:by1, bx0:bx1] = np.maximum(cov[by0:by1, bx0:bx1], a)


def _bezier(p0, p1, p2, p3, n=24):
    out = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        out.append((u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
                    u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1]))
    return out


def _tag(rng, w, h):
    """Graffiti calligraphie : glyphes en courbes penchees, liaisons, soulignement, coulures, contour eventuel."""
    np = _np()
    lay = np.zeros((h, w, 4), dtype=np.float32)
    n = rng.randint(3, 6)
    gw = (w * 0.82) / n
    gh = h * rng.uniform(0.38, 0.52)
    base = h * rng.uniform(0.3, 0.4)            # ligne de base (y vers le haut)
    slant = rng.uniform(0.15, 0.5)
    r = h * rng.uniform(0.022, 0.04)
    paths = []
    x = w * 0.08
    prev = None
    for g in range(n):
        for s in range(rng.randint(2, 3)):
            def P(fx, fy):
                yy = base + fy * gh
                return (x + fx * gw + (yy - base) * slant, yy)
            p0 = P(rng.uniform(0, 0.5), rng.uniform(-0.1, 1.0))
            p3 = P(rng.uniform(0.4, 1.0), rng.uniform(-0.1, 1.0))
            p1 = P(rng.uniform(-0.2, 1.2), rng.uniform(-0.3, 1.3))
            p2 = P(rng.uniform(-0.2, 1.2), rng.uniform(-0.3, 1.3))
            pts = _bezier(p0, p1, p2, p3)
            paths.append(pts)
            if prev is not None and rng.random() < 0.5:
                paths.append(_bezier(prev, (prev[0] + gw * 0.2, prev[1] - gh * 0.3), (p0[0] - gw * 0.2, p0[1] - gh * 0.3), p0, 10))
            prev = pts[-1]
        x += gw * rng.uniform(0.85, 1.1)
    if rng.random() < 0.7:            # soulignement / paraphe
        a = (w * 0.06, base - gh * 0.25)
        b = (min(w * 0.95, x + gw * 0.3), base - gh * rng.uniform(0.15, 0.4))
        paths.append(_bezier(a, (w * 0.4, base - gh * 0.9), (w * 0.7, base + gh * 0.2), b, 40))
    col = SPRAY[rng.randrange(len(SPRAY))]
    outline = rng.random() < 0.45
    oc = SPRAY[0] if col != SPRAY[0] else SPRAY[2]
    drips = []
    for pts in paths:
        if rng.random() < 0.35:
            px, py = pts[rng.randrange(len(pts))]
            ln = h * rng.uniform(0.05, 0.28)
            drips.append([(px, py), (px + rng.uniform(-1, 1), max(2.0, py - ln))])
    # brume de bombe
    mist = np.zeros((h, w), dtype=np.float32)
    for pts in paths:
        _stroke(mist, pts, r * 2.6, soft=r * 2.0)
    nz = _vnoise(h, w, 6, rng, 2)
    _over(lay, col, mist * 0.12 * nz)
    if outline:
        cov = np.zeros((h, w), dtype=np.float32)
        for pts in paths + drips:
            _stroke(cov, pts, r * 1.75, soft=1.2)
        _over(lay, oc, cov)
    cov = np.zeros((h, w), dtype=np.float32)
    for pts in paths:
        _stroke(cov, pts, r, soft=1.2)
    for d in drips:
        _stroke(cov, d, r * 0.45, soft=1.0)
        _stroke(cov, [d[1], (d[1][0], d[1][1] - 0.5)], r * 0.7, soft=1.0)
    # peinture un peu irreguliere et usee
    wear = 0.75 + 0.25 * _vnoise(h, w, 18, rng, 2)
    _over(lay, col, cov * wear)
    return lay


def _poster_wall(rng, w, h, stickers=False):
    """Affiches collees qui se chevauchent : fonds vifs, titres en barres, lignes de texte, dechirures, decoloration."""
    np = _np()
    lay = np.zeros((h, w, 4), dtype=np.float32)
    n = rng.randint(2, 4) if not stickers else rng.randint(14, 26)
    for k in range(n):
        if stickers:
            pw, ph = rng.uniform(0.07, 0.17) * w, rng.uniform(0.05, 0.13) * h
        else:
            pw, ph = rng.uniform(0.45, 0.8) * w, rng.uniform(0.55, 0.9) * h
        x0 = rng.uniform(0.02 * w, w - pw - 0.02 * w)
        y0 = rng.uniform(0.02 * h, h - ph - 0.02 * h)
        X0, X1, Y0, Y1 = int(x0), int(x0 + pw), int(y0), int(y0 + ph)
        bw_, bh_ = X1 - X0, Y1 - Y0
        if bw_ < 6 or bh_ < 6:
            continue
        sub = np.zeros((bh_, bw_, 4), dtype=np.float32)
        bg = PAPER[rng.randrange(len(PAPER))]
        sub[..., 0], sub[..., 1], sub[..., 2] = bg
        sub[..., 3] = 1.0
        fg = PAPER[rng.randrange(len(PAPER))]
        if fg == bg:
            fg = (0.05, 0.05, 0.05) if sum(bg) > 1.5 else (0.95, 0.93, 0.9)
        if stickers:
            if rng.random() < 0.5:
                yy, xx = np.mgrid[0:bh_, 0:bw_].astype(np.float32)
                m = (((xx - bw_ / 2) / (bw_ / 2)) ** 2 + ((yy - bh_ / 2) / (bh_ / 2)) ** 2) <= 1.0
                sub[..., 3] = m.astype(np.float32)
            th = max(2, int(bh_ * 0.25))
            sub[bh_ // 2 - th // 2: bh_ // 2 + th // 2, int(bw_ * 0.15): int(bw_ * 0.85), :3] = fg
        else:
            # titre (barres epaisses) + lignes de texte + bloc image
            y = bh_ - int(bh_ * 0.08)
            for t in range(rng.randint(1, 2)):
                th = int(bh_ * rng.uniform(0.08, 0.14))
                tw = int(bw_ * rng.uniform(0.5, 0.9))
                xo = (bw_ - tw) // 2
                sub[max(0, y - th):y, xo:xo + tw, :3] = fg
                y -= th + int(bh_ * 0.04)
            if rng.random() < 0.6:
                ih = int(bh_ * rng.uniform(0.22, 0.35))
                img = _vnoise(ih, bw_ - int(bw_ * 0.2), 8, rng, 3)
                tint = PAPER[rng.randrange(len(PAPER))]
                for c in range(3):
                    sub[max(0, y - ih):y, int(bw_ * 0.1):int(bw_ * 0.1) + img.shape[1], c] = img[-min(ih, y):, :] * tint[c] * 0.9 + 0.05
                y -= ih + int(bh_ * 0.04)
            lh = max(2, int(bh_ * 0.025))
            while y > bh_ * 0.08:
                lw = int(bw_ * rng.uniform(0.3, 0.8))
                xo = int(bw_ * 0.1)
                sub[max(0, y - lh):y, xo:xo + lw, :3] = fg
                y -= lh * 2 + 1
        # dechirures sur les bords + manques + decoloration + plis
        nz = _vnoise(bh_, bw_, max(4, min(bw_, bh_) / 8), rng, 3)
        yy, xx = np.mgrid[0:bh_, 0:bw_].astype(np.float32)
        edge = np.minimum(np.minimum(xx, bw_ - 1 - xx), np.minimum(yy, bh_ - 1 - yy)) / max(1.0, min(bw_, bh_) * 0.12)
        tear = np.clip((edge + nz * 1.2 - 0.55) * 4.0, 0, 1)
        holes = np.clip((_vnoise(bh_, bw_, max(6, bw_ / 5), rng, 3) - (0.72 if not stickers else 0.9)) * -8.0, 0, 1)
        sub[..., 3] *= tear * holes
        fade = rng.uniform(0.15, 0.5)
        for c in range(3):
            sub[..., c] = sub[..., c] * (1 - fade) + 0.55 * fade
        sub[..., :3] *= (0.8 + 0.2 * _vnoise(bh_, bw_, 5, rng, 2))[..., None]
        reg = lay[Y0:Y1, X0:X1]
        _over(reg, sub[..., :3], sub[..., 3])
    return lay


def _ghost(rng, w, h):
    """Ancienne publicite peinte sur un mur de brique, delavee : cadre, grands blocs de lettres, ecaillage par rangs."""
    np = _np()
    lay = np.zeros((h, w, 4), dtype=np.float32)
    m = np.zeros((h, w), dtype=np.float32)
    bx = int(w * 0.03)
    m[bx:h - bx, bx:bx * 2] = 1; m[bx:h - bx, w - 2 * bx:w - bx] = 1
    m[bx:bx * 2, bx:w - bx] = 1; m[h - 2 * bx:h - bx, bx:w - bx] = 1
    rows = rng.randint(2, 3)
    for r in range(rows):
        y1 = int(h - h * 0.12 - r * h * 0.27)
        lh = int(h * (0.18 if r == 0 else 0.12))
        x = int(w * 0.08)
        while x < w * 0.9:
            lw = int(h * rng.uniform(0.07, 0.14) * (1.3 if r == 0 else 1.0))
            st = max(3, lw // 4)
            kind = rng.random()
            m[y1 - lh:y1, x:x + st] = 1
            if kind < 0.4:
                m[y1 - lh:y1, x + lw - st:x + lw] = 1; m[y1 - st:y1, x:x + lw] = 1
            elif kind < 0.7:
                m[y1 - st:y1, x:x + lw] = 1; m[y1 - lh // 2 - st // 2:y1 - lh // 2 + st // 2, x:x + lw] = 1; m[y1 - lh:y1 - lh + st, x:x + lw] = 1
            else:
                m[y1 - lh:y1 - lh + st, x:x + lw] = 1; m[y1 - lh:y1, x + lw - st:x + lw] = 1
            x += lw + int(lw * 0.45)
            if rng.random() < 0.15:
                x += lw
    m[int(h * 0.12):int(h * 0.15), int(w * 0.1):int(w * 0.9)] = 1
    yy = np.arange(h)[:, None]
    course = ((yy % 9) > 0).astype(np.float32)               # joints de mortier : la peinture y manque
    flake = np.clip((_vnoise(h, w, 30, rng, 4) - 0.35) * 3, 0, 1)
    col = [(0.85, 0.82, 0.72), (0.9, 0.86, 0.6), (0.82, 0.83, 0.85)][rng.randrange(3)]
    bgc = [(0.35, 0.08, 0.05), (0.08, 0.12, 0.22), (0.15, 0.15, 0.13)][rng.randrange(3)]
    bga = np.full((h, w), 0.35, dtype=np.float32) * flake * course
    _over(lay, bgc, bga)
    _over(lay, col, m * 0.75 * flake * course)
    return lay


def _streak(rng, w, h, rust=False):
    """Coulures verticales (eau sale ou rouille) : fortes en haut, s'estompent vers le bas."""
    np = _np()
    lay = np.zeros((h, w, 4), dtype=np.float32)
    yy = np.arange(h, dtype=np.float32)[:, None] / h            # 0 en bas, 1 en haut
    a = np.zeros((h, w), dtype=np.float32)
    for k in range(rng.randint(10, 22)):
        cx = rng.uniform(0.05, 0.95) * w
        sw = rng.uniform(0.01, 0.06) * w
        ln = rng.uniform(0.3, 1.0)
        xs = np.arange(w, dtype=np.float32)[None, :]
        prof = np.exp(-((xs - cx) / sw) ** 2)
        fall = np.clip((yy - (1 - ln)) / ln, 0, 1) ** 1.6
        a = np.maximum(a, prof * fall * rng.uniform(0.4, 1.0))
    a *= 0.6 + 0.4 * _vnoise(h, w, 10, rng, 3)
    top = np.clip((yy - 0.9) * 10, 0, 1)                           # bande sous l'appui / le palier
    a = np.maximum(a, top * 0.7)
    col = (0.26, 0.1, 0.035) if rust else (0.05, 0.045, 0.038)
    _over(lay, col, a * (0.75 if rust else 0.6))
    return lay


def _cracks(rng, w, h):
    """Fissures ramifiees (en escalier dans la brique)."""
    np = _np()
    lay = np.zeros((h, w, 4), dtype=np.float32)
    cov = np.zeros((h, w), dtype=np.float32)

    def branch(x, y, ang, ln, r, depth):
        pts = [(x, y)]
        for i in range(int(ln / 6)):
            ang += rng.uniform(-0.5, 0.5)
            x += math.cos(ang) * 6; y += math.sin(ang) * 6
            pts.append((x, y))
            if depth < 3 and rng.random() < 0.05:
                branch(x, y, ang + rng.choice((-1, 1)) * rng.uniform(0.5, 1.1), ln * 0.45, r * 0.7, depth + 1)
        _stroke(cov, pts, r, soft=0.8)
    for k in range(rng.randint(1, 3)):
        branch(rng.uniform(0.2, 0.8) * w, h * rng.uniform(0.85, 0.98), -math.pi / 2 + rng.uniform(-0.6, 0.6), h * rng.uniform(0.5, 0.95),
               rng.uniform(1.3, 2.2), 0)
    halo = np.zeros((h, w), dtype=np.float32)
    _over(lay, (0.4, 0.38, 0.35), halo)
    _over(lay, (0.03, 0.025, 0.02), cov * 0.9)
    return lay


def build_atlas(seed=7):
    """Dessine l'atlas (une fois par fichier) ; renvoie l'image Blender (empaquetee)."""
    np = _np()
    im = bpy.data.images.get(ATLAS)
    if im is not None and im.get("bg_decals_ver") == VERSION:
        return im
    rng = random.Random(seed)
    buf = np.zeros((SIZE, SIZE, 4), dtype=np.float32)
    for i, (x, y, w, h) in enumerate(CELLS['tag']):
        buf[y:y + h, x:x + w] = _tag(rng, w, h)
    for (x, y, w, h) in CELLS['poster']:
        buf[y:y + h, x:x + w] = _poster_wall(rng, w, h)
    for (x, y, w, h) in CELLS['sticker']:
        buf[y:y + h, x:x + w] = _poster_wall(rng, w, h, stickers=True)
    for (x, y, w, h) in CELLS['ghost']:
        buf[y:y + h, x:x + w] = _ghost(rng, w, h)
    for (x, y, w, h) in CELLS['streak']:
        buf[y:y + h, x:x + w] = _streak(rng, w, h)
    for (x, y, w, h) in CELLS['rust']:
        buf[y:y + h, x:x + w] = _streak(rng, w, h, rust=True)
    for (x, y, w, h) in CELLS['crack']:
        buf[y:y + h, x:x + w] = _cracks(rng, w, h)
    # couleurs en sRGB dans le fichier : on stocke tel quel (image non float, espace sRGB)
    if im is None:
        im = bpy.data.images.new(ATLAS, SIZE, SIZE, alpha=True, float_buffer=False)
    elif tuple(im.size) != (SIZE, SIZE):
        im.scale(SIZE, SIZE)
    im.pixels.foreach_set(buf.ravel())
    im.update()
    im.pack()
    im["bg_decals_ver"] = VERSION
    im.use_fake_user = False
    return im


def material(name="BG_decal"):
    """Materiau des decalcomanies : couleur + alpha de l'atlas, chaque decalque un peu passe (attribut bg_rand)."""
    m = bpy.data.materials.get(name)
    if m is not None and m.get("bg_decals_ver") == VERSION:
        return m
    im = build_atlas()
    if m is None:
        m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); out.location = (700, 0)
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled'); bsdf.location = (400, 0)
    nt.links.new(bsdf.outputs[0], out.inputs['Surface'])
    tx = nt.nodes.new('ShaderNodeTexImage'); tx.location = (-500, 100)
    tx.image = im
    tx.interpolation = 'Linear'
    tx.extension = 'CLIP'
    at = nt.nodes.new('ShaderNodeAttribute'); at.location = (-500, -250)
    at.attribute_name = 'bg_rand'; at.attribute_type = 'GEOMETRY'
    # decoloration : melange vers un gris selon bg_rand
    mix = nt.nodes.new('ShaderNodeMix'); mix.location = (-150, 150)
    mix.data_type = 'RGBA'
    fac = [s for s in mix.inputs if s.identifier == 'Factor_Float'][0]
    A = [s for s in mix.inputs if s.identifier == 'A_Color'][0]
    B = [s for s in mix.inputs if s.identifier == 'B_Color'][0]
    R = [s for s in mix.outputs if s.identifier == 'Result_Color'][0]
    B.default_value = (0.32, 0.31, 0.29, 1)
    mr = nt.nodes.new('ShaderNodeMapRange'); mr.location = (-300, -250)
    mr.inputs['To Min'].default_value = 0.0; mr.inputs['To Max'].default_value = 0.35
    nt.links.new(at.outputs['Fac'], mr.inputs['Value'])
    nt.links.new(mr.outputs[0], fac)
    nt.links.new(tx.outputs['Color'], A)
    nt.links.new(R, bsdf.inputs['Base Color'])
    ma = nt.nodes.new('ShaderNodeMath'); ma.location = (-150, -100); ma.operation = 'MULTIPLY'
    mb_ = nt.nodes.new('ShaderNodeMapRange'); mb_.location = (-300, -400)
    mb_.inputs['To Min'].default_value = 1.0; mb_.inputs['To Max'].default_value = 0.65
    nt.links.new(at.outputs['Fac'], mb_.inputs['Value'])
    nt.links.new(tx.outputs['Alpha'], ma.inputs[0]); nt.links.new(mb_.outputs[0], ma.inputs[1])
    nt.links.new(ma.outputs[0], bsdf.inputs['Alpha'])
    bsdf.inputs['Roughness'].default_value = 0.72
    try:
        m.surface_render_method = 'DITHERED'
    except Exception:
        pass
    m["bg_material"] = True
    m["bg_decals_ver"] = VERSION
    m.diffuse_color = (0.5, 0.5, 0.5, 0.5)
    return m
