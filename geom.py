"""Construction de maillage rapide (listes Python -> bpy.types.Mesh en une passe).

Repere de facade : (u, v, w) = (le long du mur, vers le haut, vers l'exterieur). Un point de facade devient
O + T*u + Z*v + N*w avec N = T x Z, donc un polygone trace dans le sens trigonometrique en (u, v) a sa normale
vers l'exterieur. Les UV sont en metres (les materiaux mettent a l'echelle) : projection sur le plan dominant,
avec le decalage u0 de la facade pour que la brique continue d'une facade a l'autre."""
import math
import bpy
import bmesh
from mathutils import Vector

Z = Vector((0.0, 0.0, 1.0))


class MeshBuilder:
    def __init__(self):
        self.verts = []
        self.faces = []
        self.uvs = []          # une liste de (u, v) par face
        self.mats = []         # index de materiau par face
        self.rand = []         # valeur aleatoire par face (variation des vitres...)
        self.keys = []         # cles de materiau, dans l'ordre des emplacements
        self.mass = []         # volumes simplifies (version de fond) : etages, toits, edicules, chateaux d'eau
        self.tag = 'wall'      # partie en cours de construction (controle des chevauchements, vieillissement)
        self.tags = []         # partie de chaque face

    def mat(self, key):
        try:
            return self.keys.index(key)
        except ValueError:
            self.keys.append(key)
            return len(self.keys) - 1

    def face(self, pts, key, uv=None, rnd=0.0):
        if len(pts) < 3:
            return
        i0 = len(self.verts)
        self.verts.extend(tuple(p) for p in pts)
        self.faces.append(tuple(range(i0, i0 + len(pts))))
        if uv is None:
            uv = box_uv(pts)
        self.uvs.append(uv)
        self.mats.append(self.mat(key))
        self.rand.append(rnd)
        self.tags.append(self.tag)

    def box(self, lo, hi, key, skip=(), rnd=0.0):
        """Boite alignee sur les axes du monde. skip : faces omises parmi '-x','+x','-y','+y','-z','+z'."""
        x0, y0, z0 = lo
        x1, y1, z1 = hi
        if x1 - x0 < 1e-6 or y1 - y0 < 1e-6 or z1 - z0 < 1e-6:
            return
        V = Vector
        f = {
            '-z': [V((x0, y0, z0)), V((x0, y1, z0)), V((x1, y1, z0)), V((x1, y0, z0))],
            '+z': [V((x0, y0, z1)), V((x1, y0, z1)), V((x1, y1, z1)), V((x0, y1, z1))],
            '-y': [V((x0, y0, z0)), V((x1, y0, z0)), V((x1, y0, z1)), V((x0, y0, z1))],
            '+y': [V((x1, y1, z0)), V((x0, y1, z0)), V((x0, y1, z1)), V((x1, y1, z1))],
            '-x': [V((x0, y1, z0)), V((x0, y0, z0)), V((x0, y0, z1)), V((x0, y1, z1))],
            '+x': [V((x1, y0, z0)), V((x1, y1, z0)), V((x1, y1, z1)), V((x1, y0, z1))],
        }
        for k, pts in f.items():
            if k not in skip:
                self.face(pts, key, rnd=rnd)

    def cylinder(self, c, r, z0, z1, key, n=12, cap_top=True, cap_bot=False, r_top=None):
        r_top = r if r_top is None else r_top
        ring0 = [Vector((c[0] + r * math.cos(2 * math.pi * i / n), c[1] + r * math.sin(2 * math.pi * i / n), z0)) for i in range(n)]
        ring1 = [Vector((c[0] + r_top * math.cos(2 * math.pi * i / n), c[1] + r_top * math.sin(2 * math.pi * i / n), z1)) for i in range(n)]
        circ = 2 * math.pi * r
        for i in range(n):
            j = (i + 1) % n
            a, b = circ * i / n, circ * (i + 1) / n
            self.face([ring0[i], ring0[j], ring1[j], ring1[i]], key, uv=[(a, z0), (b, z0), (b, z1), (a, z1)])
        if cap_top and r_top > 1e-6:
            self.face(ring1, key)
        if cap_bot:
            self.face(list(reversed(ring0)), key)

    def cone(self, c, r, z0, z1, key, n=12):
        ring = [Vector((c[0] + r * math.cos(2 * math.pi * i / n), c[1] + r * math.sin(2 * math.pi * i / n), z0)) for i in range(n)]
        tip = Vector((c[0], c[1], z1))
        for i in range(n):
            self.face([ring[i], ring[(i + 1) % n], tip], key)

    def beam(self, a, b, t, key, up=None):
        """Barre de section carree t entre deux points quelconques (garde-corps, montants d'echelle...)."""
        a, b = Vector(a), Vector(b)
        d = b - a
        if d.length < 1e-6:
            return
        d.normalize()
        ref = up if up is not None else (Z if abs(d.dot(Z)) < 0.95 else Vector((1, 0, 0)))
        s1 = d.cross(ref).normalized() * (t / 2)
        s2 = d.cross(s1).normalized() * (t / 2)
        c = [s1 + s2, -s1 + s2, -s1 - s2, s1 - s2]
        A = [a + x for x in c]
        B = [b + x for x in c]
        for i in range(4):
            j = (i + 1) % 4
            self.face([A[i], A[j], B[j], B[i]], key)
        self.face(list(reversed(A)), key)
        self.face(B, key)

    def drop(self, tags):
        """Retire les faces de certaines parties (ex. 'decal' avant une cuisson), sommets compactes."""
        keep = [i for i, t in enumerate(self.tags) if t not in tags]
        if len(keep) == len(self.faces):
            return self
        verts, remap = [], {}
        faces = []
        for i in keep:
            f = []
            for vi in self.faces[i]:
                if vi not in remap:
                    remap[vi] = len(verts)
                    verts.append(self.verts[vi])
                f.append(remap[vi])
            faces.append(tuple(f))
        self.verts = verts
        self.faces = faces
        self.uvs = [self.uvs[i] for i in keep]
        self.mats = [self.mats[i] for i in keep]
        self.rand = [self.rand[i] for i in keep]
        self.tags = [self.tags[i] for i in keep]
        return self

    def append(self, other, offset=(0, 0, 0)):
        o = Vector(offset)
        base = len(self.verts)
        self.verts.extend(tuple(Vector(v) + o) for v in other.verts)
        remap = [self.mat(k) for k in other.keys]
        for f, uv, m, r, t in zip(other.faces, other.uvs, other.mats, other.rand, other.tags):
            self.faces.append(tuple(i + base for i in f))
            self.uvs.append(uv)
            self.mats.append(remap[m])
            self.rand.append(r)
            self.tags.append(t)

    def to_mesh(self, name, materials, merge=True, mesh=None):
        me = mesh or bpy.data.meshes.new(name)
        if mesh is not None:
            me.clear_geometry()
        me.materials.clear()
        for k in self.keys:
            me.materials.append(materials(k))
        me.from_pydata(self.verts, [], self.faces)
        uvl = me.uv_layers.new(name="UVMap") if not me.uv_layers else me.uv_layers[0]
        flat_uv = [c for uv in self.uvs for p in uv for c in p]
        uvl.data.foreach_set("uv", flat_uv)
        me.polygons.foreach_set("material_index", self.mats)
        att = me.attributes.get("bg_rand") or me.attributes.new("bg_rand", 'FLOAT', 'FACE')
        att.data.foreach_set("value", self.rand)
        if merge:
            bm = bmesh.new()
            bm.from_mesh(me)
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
            bm.to_mesh(me)
            bm.free()
        me.polygons.foreach_set("use_smooth", [False] * len(me.polygons))
        me.update()
        return me


def box_uv(pts):
    p0, p1, p2 = Vector(pts[0]), Vector(pts[1]), Vector(pts[2])
    n = (p1 - p0).cross(p2 - p0)
    if n.length < 1e-12 and len(pts) > 3:
        n = (Vector(pts[2]) - p0).cross(Vector(pts[3]) - p0)
    ax, ay, az = abs(n.x), abs(n.y), abs(n.z)
    if az >= ax and az >= ay:
        return [(p[0], p[1]) for p in pts]
    if ax >= ay:
        return [(p[1], p[2]) for p in pts]
    return [(p[0], p[2]) for p in pts]


class Frame:
    """Repere de facade. Les fonctions prennent des points (u, v, w)."""

    def __init__(self, mb, origin, tangent, u0=0.0):
        self.mb = mb
        self.O = Vector(origin)
        self.T = Vector(tangent).normalized()
        self.N = self.T.cross(Z).normalized()
        self.u0 = u0

    def P(self, u, v, w=0.0):
        return self.O + self.T * u + Z * v + self.N * w

    def face(self, pts, key, rnd=0.0):
        if len(pts) < 3:
            return
        a, b, c = (Vector(p) for p in pts[:3])
        n = (b - a).cross(c - a)
        if n.length < 1e-12 and len(pts) > 3:
            n = (Vector(pts[2]) - a).cross(Vector(pts[3]) - a)
        au, av, aw = abs(n.x), abs(n.y), abs(n.z)
        if aw >= au and aw >= av:
            uv = [(p[0] + self.u0, p[1]) for p in pts]
        elif au >= av:
            uv = [(p[2], p[1]) for p in pts]
        else:
            uv = [(p[0] + self.u0, p[2]) for p in pts]
        self.mb.face([self.P(*p) for p in pts], key, uv=uv, rnd=rnd)

    def quad(self, u0, v0, u1, v1, key, w=0.0, rnd=0.0):
        if u1 - u0 > 1e-6 and v1 - v0 > 1e-6:
            self.face([(u0, v0, w), (u1, v0, w), (u1, v1, w), (u0, v1, w)], key, rnd)

    def box(self, u0, u1, v0, v1, w0, w1, key, skip=('back',), rnd=0.0):
        """Boite en repere de facade ; 'back' (w0) omise par defaut (collee au mur)."""
        if u1 - u0 < 1e-6 or v1 - v0 < 1e-6 or w1 - w0 < 1e-6:
            return
        F = {
            'front': [(u0, v0, w1), (u1, v0, w1), (u1, v1, w1), (u0, v1, w1)],
            'back': [(u1, v0, w0), (u0, v0, w0), (u0, v1, w0), (u1, v1, w0)],
            'top': [(u0, v1, w1), (u1, v1, w1), (u1, v1, w0), (u0, v1, w0)],
            'bottom': [(u0, v0, w0), (u1, v0, w0), (u1, v0, w1), (u0, v0, w1)],
            'left': [(u0, v0, w0), (u0, v0, w1), (u0, v1, w1), (u0, v1, w0)],
            'right': [(u1, v0, w1), (u1, v0, w0), (u1, v1, w0), (u1, v1, w1)],
        }
        for k, pts in F.items():
            if k not in skip:
                self.face(pts, key, rnd)

    def prism(self, loop, w0, w1, key, cap_front=True, rnd=0.0):
        """Extrude un contour (u, v) convexe, sens trigonometrique, de w0 a w1 (faces laterales + face avant)."""
        n = len(loop)
        for i in range(n):
            a, b = loop[i], loop[(i + 1) % n]
            self.face([(a[0], a[1], w0), (b[0], b[1], w0), (b[0], b[1], w1), (a[0], a[1], w1)], key, rnd)
        if cap_front:
            self.face([(p[0], p[1], w1) for p in loop], key, rnd)


def offset_loop(loop, d):
    """Decale un contour ferme (x, y) sens trigonometrique de d vers l'exterieur (coins en onglet)."""
    n = len(loop)
    out = []
    for i in range(n):
        p0, p1, p2 = Vector(loop[i - 1]), Vector(loop[i]), Vector(loop[(i + 1) % n])
        e1 = (p1 - p0).normalized()
        e2 = (p2 - p1).normalized()
        n1 = Vector((e1.y, -e1.x))
        n2 = Vector((e2.y, -e2.x))
        k = 1.0 + n1.dot(n2)
        off = (n1 + n2) * (d / k) if k > 1e-6 else n1 * d
        out.append((p1.x + off.x, p1.y + off.y))
    return out


def sweep(mb, path, profile, key, closed=True, cap=True, u0=0.0):
    """Balaye un profil (sortie, hauteur) le long d'un chemin horizontal (x, y, z), sens trigonometrique.
    Profil ordonne du bas vers le haut ; il est ferme contre le mur (sortie 0) aux extremites."""
    pts = [Vector(p) for p in path]
    n = len(pts)
    rings = []
    for off, h in profile:
        if closed:
            lo = offset_loop([(p.x, p.y) for p in pts], off)
        else:
            lo = []
            for i in range(n):
                p = pts[i]
                if i == 0:
                    e = (pts[1] - pts[0]).normalized(); nn = Vector((e.y, -e.x, 0))
                    q = p + nn * off
                elif i == n - 1:
                    e = (pts[-1] - pts[-2]).normalized(); nn = Vector((e.y, -e.x, 0))
                    q = p + nn * off
                else:
                    e1 = (pts[i] - pts[i - 1]).normalized(); e2 = (pts[i + 1] - pts[i]).normalized()
                    n1 = Vector((e1.y, -e1.x, 0)); n2 = Vector((e2.y, -e2.x, 0))
                    k = 1.0 + n1.dot(n2)
                    q = p + (n1 + n2) * (off / k)
                lo.append((q.x, q.y))
        rings.append([Vector((x, y, pts[i].z + h)) for i, (x, y) in enumerate(lo)])
    m = len(profile)
    seg = n if closed else n - 1
    # abscisse curviligne pour les UV
    s = [0.0]
    for i in range(1, n + 1 if closed else n):
        s.append(s[-1] + (pts[i % n] - pts[i - 1]).length)
    for j in range(m - 1):
        for i in range(seg):
            i2 = (i + 1) % n
            a, b, c, d = rings[j][i], rings[j][i2], rings[j + 1][i2], rings[j + 1][i]
            if (a - d).length < 1e-6 and (b - c).length < 1e-6:
                continue
            ua, ub = s[i] + u0, s[i + 1] + u0
            va, vb = profile[j][1] + profile[j][0] * 0.5, profile[j + 1][1] + profile[j + 1][0] * 0.5
            mb.face([a, b, c, d], key, uv=[(ua, va), (ub, va), (ub, vb), (ua, vb)])
    if not closed and cap:
        # bouchons : polygone du profil ferme contre le mur
        for idx, rev in ((0, True), (n - 1, False)):
            poly = [rings[j][idx] for j in range(m)]
            base = [Vector((pts[idx].x, pts[idx].y, pts[idx].z + profile[-1][1])), Vector((pts[idx].x, pts[idx].y, pts[idx].z + profile[0][1]))]
            ring = poly + base
            mb.face(list(reversed(ring)) if rev else ring, key)
