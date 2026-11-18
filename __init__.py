"""Batiments proceduraux : generateur de batiments new-yorkais (Brooklyn, debut XXe) pour Blender.

Vue 3D > barre laterale (N) > onglet Batiments."""
import json
import random
import bpy
from bpy.props import (BoolProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty, StringProperty)

from . import styles as ST
from . import presets as PS
from . import layout as LY
from . import materials as MT
from . import fond as FD
from . import updater as UP
from . import wear as WR
from . import catalog as CT

WALLS = [('AUTO', "Auto", "")] + [(k, n, "") for k, n in (
    ('brick_red', "Brique rouge"), ('brick_deep', "Brique rouge sombre"), ('brick_dark', "Brique sombre"), ('brick_tan', "Brique beige"), ('brick_brown', "Brique brune"),
    ('brick_painted', "Brique peinte"), ('brick_grey', "Brique grise"), ('stone_brown', "Brownstone"), ('stone_block', "Pierre appareillée"),
    ('stone_smooth', "Pierre claire"), ('stone_warm', "Pierre gris chaud"), ('concrete', "Béton"), ('panel_white', "Panneaux blancs"))]
GROUNDS = [('AUTO', "Auto", ""), ('store', "Commerces", ""), ('lobby', "Hall d'entrée", ""), ('base', "Socle à fenêtres", ""),
           ('stoop', "Perron", ""), ('warehouse', "Quais d'entrepôt", ""), ('glass', "Vitré", "")]
ROOFS = [('AUTO', "Auto", ""), ('flat', "Plat (acrotère)", ""), ('mansard', "Mansarde", ""), ('hip', "Croupe", "")]
MIXES = [('brooklyn', "Brooklyn (mixte)", "Immeubles de rapport, maisons de ville, entrepôts"), ('residentiel', "Résidentiel", "Surtout des maisons de ville"),
         ('industriel', "Industriel", "Surtout des entrepôts"), ('centre', "Centre", "Immeubles d'avant-guerre, tours, moderne"),
         ('catalogue', "Catalogue de presets", "Rangées composées des presets (immeubles d'angle, brownstones, banque, hôtel...)"),
         ('lower_east_side', "Lower East Side / SoHo", "Immeubles de rapport à escalier en façade, bodegas, lofts en fonte"),
         ('midtown', "Midtown", "Lofts de confection, tours Art déco et néo-gothiques, tours de verre, résidentiels à terrasses")]
DISTRICTS = [('mixte', "New York mixte", "Tours, avant-guerre, immeubles de rapport, maisons de ville, entrepôts"),
             ('manhattan', "Manhattan (centre)", "Gratte-ciel à retraits, tours modernes, bureaux, hôtels"),
             ('brooklyn', "Brooklyn", "Immeubles de rapport, brownstones, entrepôts, angles à mansarde")]
PRESET_ITEMS = [('NONE', "Aucun (style libre)", "Le style et la graine tirent tout le bâtiment")] + [(k, n, d) for k, n, d, _s, _f in PS.PRESETS]


def _prefs(context):
    a = context.preferences.addons.get(__package__)
    return a.preferences if a else None


def _mat_args(context):
    s = context.scene.bg_settings
    p = _prefs(context)
    kb = (p.kb_dir if p else "") or s.kb_dir
    kb = bpy.path.abspath(kb) if kb else ""
    mode = 'kb3d' if s.mat_mode == 'KB3D' and MT.kb_available(kb) else 'procedural'
    return mode, kb


def _opts(s):
    o = {}
    if s.floors:
        o['floors'] = s.floors
    if s.width > 0:
        o['W'] = s.width
    if s.depth > 0:
        o['D'] = s.depth
    if s.ground != 'AUTO':
        o['ground'] = s.ground
    if s.roof != 'AUTO':
        o['roof'] = s.roof
    if s.wall != 'AUTO':
        o['wall'] = s.wall
    o['fire_escape'] = s.fire_escape
    o['water_tower'] = s.water_tower
    o['roof_props'] = s.roof_props
    o['storefront'] = s.storefront
    o['awnings'] = s.awnings
    o['win_ac'] = s.win_ac
    o['services'] = s.services
    o['decals'] = s.decals
    return o


def _upd_lit(self, context):
    MT.set_lit_windows(self.lit_strength, 1.0 - self.lit_ratio)


def _upd_wear(self, context):
    WR.set_amount(self.wear)


def draw_update_box(layout, compact=False):
    st = UP.state
    s = st["status"]
    if s == "available":
        box = layout.box()
        row = box.row(align=True)
        row.label(text="Mise à jour %s disponible" % st["latest"], icon='IMPORT')
        row.operator("bg.update_page", text="", icon='URL')
        box.operator("bg.update_install", icon='IMPORT')
    elif s in ("downloading", "installing", "checking"):
        layout.label(text={"downloading": "Téléchargement de la mise à jour...", "installing": "Installation de la mise à jour...",
                           "checking": "Recherche de mise à jour..."}[s], icon='SORTTIME')
    elif s == "installed":
        layout.label(text="Mise à jour installée", icon='CHECKMARK')
    elif not compact:
        if s == "uptodate":
            layout.label(text="Bâtiments procéduraux %s est à jour" % UP.current_version_str(), icon='CHECKMARK')
        elif s == "error":
            layout.label(text="Mise à jour : %s" % st["error"], icon='ERROR')
        elif s == "offline":
            layout.label(text="Accès en ligne désactivé (Préférences › Système › Réseau)", icon='ERROR')


class BG_Preferences(bpy.types.AddonPreferences):
    bl_idname = __package__
    kb_dir: StringProperty(name="Textures Kitbash3D", subtype='DIR_PATH',
                           description="Dossier KB3DTextures du kit Brooklyn (licence personnelle) ; les textures ne sont jamais copiées dans l'add-on")
    check_updates: BoolProperty(name="Chercher les mises à jour", default=True,
                                description="Cherche une nouvelle release sur GitHub au démarrage de Blender (une fois par jour au plus)")
    auto_update: BoolProperty(name="Installer automatiquement", default=True,
                              description="Installe seule une nouvelle release. Désactivé : un bouton apparaît dans le panneau")
    update_repo: StringProperty(name="Dépôt GitHub", default=UP.DEFAULT_REPO,
                                description="propriétaire/nom du dépôt GitHub dont les releases sont installées")

    def draw(self, context):
        col = self.layout.column()
        col.prop(self, "kb_dir")
        ok = MT.kb_available(bpy.path.abspath(self.kb_dir)) if self.kb_dir else False
        col.label(text="Textures trouvées" if ok else "Dossier vide ou introuvable : matériaux procéduraux", icon='CHECKMARK' if ok else 'INFO')
        box = self.layout.box()
        row = box.row(align=True)
        row.label(text="Bâtiments procéduraux %s" % UP.current_version_str())
        row.operator("bg.update_check", icon='FILE_REFRESH')
        draw_update_box(box)
        box.prop(self, "check_updates")
        sub = box.column()
        sub.active = self.check_updates
        sub.prop(self, "auto_update")
        sub.prop(self, "update_repo")


class BG_OT_update_check(bpy.types.Operator):
    """Cherche une nouvelle version de l'extension sur GitHub (releases)"""
    bl_idname = "bg.update_check"
    bl_label = "Chercher une mise à jour"

    def execute(self, context):
        msg = UP.check(manual=True)
        if msg:
            self.report({'WARNING'}, msg)
            return {'CANCELLED'}
        return {'FINISHED'}


class BG_OT_update_install(bpy.types.Operator):
    """Télécharge la nouvelle version depuis GitHub et l'installe (Blender recharge l'extension)"""
    bl_idname = "bg.update_install"
    bl_label = "Installer la mise à jour"

    @classmethod
    def poll(cls, context):
        return UP.state["status"] in ("available", "error") and UP.state.get("asset") is not None

    def execute(self, context):
        msg = UP.install()
        if msg:
            self.report({'WARNING'}, msg)
            return {'CANCELLED'}
        return {'FINISHED'}


class BG_OT_update_page(bpy.types.Operator):
    """Ouvre la page de la release sur GitHub (nouveautés de la version)"""
    bl_idname = "bg.update_page"
    bl_label = "Notes de version"

    def execute(self, context):
        import webbrowser
        webbrowser.open(UP.state.get("page") or UP.repo_url())
        return {'FINISHED'}


class BG_Settings(bpy.types.PropertyGroup):
    style: EnumProperty(name="Style", items=[(k, n, d) for k, n, d in ST.STYLES], default='walkup')
    preset: EnumProperty(name="Preset", items=PRESET_ITEMS, default='NONE',
                         description="Bâtiment-type à silhouette fixe ; la graine ne fait varier que les détails")
    seed: IntProperty(name="Graine", default=1, min=0)
    floors: IntProperty(name="Étages", default=0, min=0, max=80, description="0 : tiré au hasard dans la plage du style")
    width: FloatProperty(name="Largeur", default=0.0, min=0.0, max=200.0, unit='LENGTH', description="0 : auto")
    depth: FloatProperty(name="Profondeur", default=0.0, min=0.0, max=200.0, unit='LENGTH', description="0 : auto")
    detail: EnumProperty(name="Détail", items=[('0', "Bas", "Sans menuiseries ni consoles (lointain)"), ('1', "Moyen", ""), ('2', "Haut", "Petits bois, barreaux, denticules (premier plan)")], default='1')
    ground: EnumProperty(name="Rez-de-chaussée", items=GROUNDS, default='AUTO')
    roof: EnumProperty(name="Toit", items=ROOFS, default='AUTO')
    wall: EnumProperty(name="Mur", items=WALLS, default='AUTO')
    fire_escape: BoolProperty(name="Escalier de secours", default=True)
    water_tower: BoolProperty(name="Château d'eau", default=True)
    roof_props: BoolProperty(name="Équipements de toit", default=True)
    storefront: BoolProperty(name="Commerces", default=True)
    awnings: BoolProperty(name="Auvents", default=True)
    win_ac: FloatProperty(name="Clims de fenêtre", default=0.15, min=0.0, max=1.0, subtype='FACTOR')
    sidewalk: BoolProperty(name="Trottoir", default=True)
    count: IntProperty(name="Nombre", default=9, min=1, max=100)
    spacing: FloatProperty(name="Écart", default=8.0, min=0.0, unit='LENGTH')
    # rue
    street_len: FloatProperty(name="Longueur", default=120.0, min=10.0, max=2000.0, unit='LENGTH')
    street_mix: EnumProperty(name="Quartier", items=MIXES, default='brooklyn')
    street_both: BoolProperty(name="Deux côtés", default=True)
    road_w: FloatProperty(name="Chaussée", default=11.0, min=3.0, max=40.0, unit='LENGTH')
    walk_w: FloatProperty(name="Trottoir", default=4.5, min=1.0, max=15.0, unit='LENGTH')
    # materiaux
    mat_mode: EnumProperty(name="Matériaux", items=[('PROC', "Procéduraux", "Autonomes, aucune texture"), ('KB3D', "Textures Kitbash3D", "Textures du kit Brooklyn (dossier à indiquer)")], default='PROC')
    kb_dir: StringProperty(name="Dossier KB3D", subtype='DIR_PATH', description="Utilisé si les préférences de l'add-on n'en donnent pas")
    scale: FloatProperty(name="Échelle (u/m)", default=1.0, min=0.01, max=100.0, description="Unités de la scène par mètre")
    lit_strength: FloatProperty(name="Fenêtres allumées", default=0.0, min=0.0, max=50.0, update=_upd_lit)
    lit_ratio: FloatProperty(name="Part allumée", default=0.2, min=0.0, max=1.0, subtype='FACTOR', update=_upd_lit)
    # usure et details (v1.5)
    wear: FloatProperty(name="Usure", default=WR.DEFAULT, min=0.0, max=1.0, subtype='FACTOR', update=_upd_wear,
                        description="Salissure, coulures, crasse des recoins, salpêtre, rouille, taches au sol, rugosité variable (tous les bâtiments)")
    decals: FloatProperty(name="Tags et affiches", default=0.6, min=0.0, max=1.0, subtype='FACTOR',
                          description="Densité des décalcomanies : tags, affiches, coulures sous les appuis, fissures, vieilles publicités peintes")
    services: BoolProperty(name="Tuyaux et ventilations", default=True,
                           description="Descentes d'eau pluviale, grilles et gaines de ventilation, compteurs, gaines d'extraction, colonnes de toit")
    cat_seeds: IntProperty(name="Variantes par preset", default=2, min=1, max=4)
    # fond de decor (versions cuites)
    fond_district: EnumProperty(name="Quartier", items=DISTRICTS, default='mixte')
    fond_count: IntProperty(name="Bâtiments uniques", default=32, min=1, max=200, description="Taille de la bibliothèque (chacun est cuit une fois)")
    fond_seed: IntProperty(name="Graine", default=1, min=0)
    fond_density: FloatProperty(name="Densité (px/m)", default=12.0, min=2.0, max=64.0, description="Pixels de texture par mètre de façade")
    fond_max_res: EnumProperty(name="Résolution max", items=[(str(r), str(r), "") for r in (512, 1024, 2048, 4096)], default='2048')
    fond_dir: StringProperty(name="Textures", subtype='DIR_PATH', default="//textures_fond/",
                             description="Dossier des images cuites (relatif au .blend). Fichier non enregistré : images empaquetées")
    fond_hide_src: BoolProperty(name="Masquer les détaillés", default=True, description="Masque les bâtiments détaillés remplacés")
    city_bx: IntProperty(name="Blocs en x", default=4, min=1, max=40)
    city_by: IntProperty(name="Blocs en y", default=3, min=1, max=40)
    city_seed: IntProperty(name="Graine", default=1, min=0)
    city_block_l: FloatProperty(name="Long. de bloc", default=160.0, min=30.0, max=600.0, unit='LENGTH')
    city_block_d: FloatProperty(name="Prof. de bloc", default=64.0, min=20.0, max=200.0, unit='LENGTH')
    city_street: FloatProperty(name="Rues", default=18.0, min=4.0, max=60.0, unit='LENGTH')
    city_avenue: FloatProperty(name="Avenues", default=30.0, min=4.0, max=80.0, unit='LENGTH')
    city_skyline: FloatProperty(name="Skyline", default=0.6, min=0.0, max=1.0, subtype='FACTOR', description="Regroupe les tours au centre")
    city_ground: BoolProperty(name="Sol (rues, trottoirs)", default=True)


def _params(s, seed=None, party=(False, False)):
    p = dict(style=s.style, seed=s.seed if seed is None else seed, opts=_opts(s), detail=int(s.detail), party=list(party), sidewalk=s.sidewalk)
    if s.preset != 'NONE':
        p['preset'] = s.preset
        p['style'] = PS.BY_KEY[s.preset][3]
    return p


def _select(context, obs):
    for o in context.selected_objects:
        o.select_set(False)
    for o in obs:
        o.select_set(True)
    if obs:
        context.view_layer.objects.active = obs[0]


class BG_OT_generate(bpy.types.Operator):
    bl_idname = "bg.generate"
    bl_label = "Générer"
    bl_description = "Crée un bâtiment au curseur 3D avec les réglages du panneau"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        s = context.scene.bg_settings
        mode, kb = _mat_args(context)
        ob, info = LY.create_building(context, _params(s), location=context.scene.cursor.location.copy(), scale=s.scale, mat_mode=mode, kb_dir=kb)
        _select(context, [ob])
        _upd_lit(s, context)
        self.report({'INFO'}, "%s : %d étages, %.0f m, %d fenêtres, %d triangles (%.2f s)" % (ob.name, info['floors'], info['height'], info['windows'], info['tris'], info['time']))
        return {'FINISHED'}


class BG_OT_variants(bpy.types.Operator):
    bl_idname = "bg.variants"
    bl_label = "Variantes"
    bl_description = "Grille de bâtiments du même style, graines successives"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        s = context.scene.bg_settings
        mode, kb = _mat_args(context)
        obs = LY.variants(context, s.style, s.seed, s.count, _opts(s), int(s.detail), s.spacing, context.scene.cursor.location.copy(), s.scale, mode, kb, s.sidewalk,
                          preset=None if s.preset == 'NONE' else s.preset)
        _select(context, obs)
        _upd_lit(s, context)
        self.report({'INFO'}, "%d variantes (graines %d à %d)" % (len(obs), s.seed, s.seed + len(obs) - 1))
        return {'FINISHED'}


class BG_OT_street(bpy.types.Operator):
    bl_idname = "bg.street"
    bl_label = "Générer la rue"
    bl_description = "Rangées de bâtiments mitoyens de part et d'autre d'une chaussée, avec trottoirs"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        s = context.scene.bg_settings
        mode, kb = _mat_args(context)
        o = _opts(s)
        for k in ('floors', 'W', 'D', 'ground', 'roof', 'wall'):
            o.pop(k, None)
        obs = LY.street(context, s.seed, s.street_len, s.street_mix, s.street_both, s.road_w, s.walk_w, int(s.detail), o,
                        context.scene.cursor.location.copy(), s.scale, mode, kb)
        _select(context, obs)
        _upd_lit(s, context)
        self.report({'INFO'}, "Rue : %d objets" % len(obs))
        return {'FINISHED'}


def _bg_objects(context):
    return [o for o in context.selected_objects if o.type == 'MESH' and "bg_params" in o]


class BG_OT_reseed(bpy.types.Operator):
    bl_idname = "bg.reseed"
    bl_label = "Nouvelle variante"
    bl_description = "Régénère les bâtiments sélectionnés avec une autre graine (même style, même place)"
    bl_options = {'REGISTER', 'UNDO'}
    step: IntProperty(name="Pas", default=1)

    def execute(self, context):
        mode, kb = _mat_args(context)
        n = 0
        for ob in _bg_objects(context):
            p = json.loads(ob["bg_params"])
            p['seed'] = p['seed'] + self.step
            LY.regenerate(ob, p, mode, kb)
            n += 1
        self.report({'INFO'}, "%d bâtiment(s) régénéré(s)" % n)
        return {'FINISHED'}


class BG_OT_apply(bpy.types.Operator):
    bl_idname = "bg.apply"
    bl_label = "Appliquer les réglages"
    bl_description = "Régénère les bâtiments sélectionnés avec les réglages du panneau (graine et mitoyenneté conservées)"
    bl_options = {'REGISTER', 'UNDO'}
    keep_style: BoolProperty(name="Garder le style", default=False)

    def execute(self, context):
        s = context.scene.bg_settings
        mode, kb = _mat_args(context)
        n = 0
        for ob in _bg_objects(context):
            old = json.loads(ob["bg_params"])
            p = _params(s, seed=old['seed'], party=old.get('party', (False, False)))
            if self.keep_style:
                p['style'] = old['style']
                p.pop('preset', None)
                if old.get('preset'):
                    p['preset'] = old['preset']
            if any(old.get('party', (False, False))):
                p['sidewalk'] = False
                for k in ('W', 'D'):
                    if k in old.get('opts', {}):
                        p['opts'][k] = old['opts'][k]
            LY.regenerate(ob, p, mode, kb)
            n += 1
        _upd_lit(s, context)
        self.report({'INFO'}, "%d bâtiment(s) régénéré(s)" % n)
        return {'FINISHED'}


class BG_OT_load(bpy.types.Operator):
    bl_idname = "bg.load"
    bl_label = "Lire la sélection"
    bl_description = "Recopie dans le panneau le style et la graine du bâtiment actif"

    def execute(self, context):
        ob = context.active_object
        if not ob or "bg_params" not in ob:
            self.report({'WARNING'}, "L'objet actif n'est pas un bâtiment généré")
            return {'CANCELLED'}
        p = json.loads(ob["bg_params"])
        s = context.scene.bg_settings
        s.style = p['style']; s.seed = p['seed']; s.detail = str(p.get('detail', 1))
        s.preset = p.get('preset') or 'NONE'
        o = p.get('opts', {})
        s.floors = int(o.get('floors', 0)); s.width = float(o.get('W', 0)); s.depth = float(o.get('D', 0))
        return {'FINISHED'}


def _fond_dir():
    d = bpy.context.scene.bg_settings.fond_dir
    if not d or (d.startswith("//") and not bpy.data.filepath):
        return None                       # fichier non enregistre : images empaquetees dans le .blend
    return bpy.path.abspath(d)


def _fond_args(context):
    s = context.scene.bg_settings
    mode, kb = _mat_args(context)
    return dict(mat_mode=mode, kb_dir=kb, density=s.fond_density, max_res=int(s.fond_max_res), out_dir=_fond_dir())


def _progress(context):
    wm = context.window_manager

    def f(i, n):
        try:
            if i == 1:
                wm.progress_begin(0, n)
            wm.progress_update(i)
            if i >= n:
                wm.progress_end()
        except Exception:
            pass
    return f


class BG_OT_fond_selection(bpy.types.Operator):
    bl_idname = "bg.fond_selection"
    bl_label = "Version de fond de la sélection"
    bl_description = ("Pour chaque bâtiment sélectionné : volume simplifié à la même place, textures cuites depuis le détaillé "
                      "(couleur, normales, occlusion + rugosité). Cycles ; GPU s'il est activé dans les préférences")
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        s = context.scene.bg_settings
        src = _bg_objects(context)
        if not src:
            self.report({'WARNING'}, "Sélectionner des bâtiments générés")
            return {'CANCELLED'}
        a = _fond_args(context)
        out, tot = [], 0.0
        prog = _progress(context)
        for i, ob in enumerate(src):
            p = json.loads(ob["bg_params"])
            f, fi = FD.bake(context, p, a['mat_mode'], a['kb_dir'], a['density'], a['max_res'], out_dir=a['out_dir'],
                            name="Fond_" + ob.name, collection=ob.users_collection[0] if ob.users_collection else None)
            f.matrix_world = ob.matrix_world.copy()
            if s.fond_hide_src:
                ob.hide_set(True)
                ob.hide_render = True
            out.append(f)
            tot += fi['time']
            prog(i + 1, len(src))
        _select(context, out)
        self.report({'INFO'}, "%d version(s) de fond cuite(s) en %.0f s" % (len(out), tot))
        return {'FINISHED'}


class BG_OT_fond_library(bpy.types.Operator):
    bl_idname = "bg.fond_library"
    bl_label = "Créer la bibliothèque"
    bl_description = ("Tire et cuit des bâtiments de fond uniques (styles et presets du quartier). "
                      "Ils servent de modèles à la ville de fond. Compter quelques secondes par bâtiment")
    bl_options = {'REGISTER', 'UNDO'}
    replace: BoolProperty(name="Remplacer l'existante", default=True)

    def execute(self, context):
        s = context.scene.bg_settings
        if self.replace:
            for o in FD.library_objects(context):
                me = o.data
                bpy.data.objects.remove(o)
                if me.users == 0:
                    bpy.data.meshes.remove(me)
        a = _fond_args(context)
        obs = FD.library(context, s.fond_district, s.fond_count, s.fond_seed, progress=_progress(context), **a)
        self.report({'INFO'}, "Bibliothèque : %d bâtiments de fond" % len(obs))
        return {'FINISHED'}


class BG_OT_fond_city(bpy.types.Operator):
    bl_idname = "bg.fond_city"
    bl_label = "Créer la ville de fond"
    bl_description = ("Quadrillage de blocs new-yorkais bordés de copies liées des bâtiments de la bibliothèque "
                      "(maillages et images partagés). Crée la bibliothèque si elle est vide")
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        s = context.scene.bg_settings
        lib = FD.library_objects(context)
        if not lib:
            a = _fond_args(context)
            lib = FD.library(context, s.fond_district, s.fond_count, s.fond_seed, progress=_progress(context), **a)
        mode, kb = _mat_args(context)
        obs = FD.city(context, lib, s.city_bx, s.city_by, s.city_seed, s.city_block_l, s.city_block_d, s.city_street, s.city_avenue,
                      skyline=s.city_skyline, origin=context.scene.cursor.location.copy(), ground=s.city_ground, mat_mode=mode, kb_dir=kb)
        lc = context.view_layer.layer_collection.children.get(FD.COLL_LIB)
        if lc:
            lc.exclude = True
        bl = [o for o in obs if o.get("bg_fond_src")]
        tris = sum(len(p.vertices) - 2 for o in bl for p in o.data.polygons)
        self.report({'INFO'}, "Ville de fond : %d bâtiments (%d modèles), %d triangles" % (len(bl), len(lib), tris))
        return {'FINISHED'}


class BG_OT_swap_materials(bpy.types.Operator):
    bl_idname = "bg.swap_materials"
    bl_label = "Basculer les matériaux"
    bl_description = "Passe tous les bâtiments générés en matériaux procéduraux ou en textures Kitbash3D, selon le réglage"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        mode, kb = _mat_args(context)
        n = 0
        for ob in context.scene.objects:
            if ob.type != 'MESH' or not ob.data.materials:
                continue
            for i, m in enumerate(ob.data.materials):
                if m is None or not m.name.startswith(MT.PREFIX):
                    continue
                key = m.name[len(MT.PREFIX):]
                if key.startswith("KB_"):
                    key = key[3:]
                ob.data.materials[i] = MT.get(key, mode, kb)
                n += 1
        _upd_lit(context.scene.bg_settings, context)
        self.report({'INFO'}, "%d emplacements de matériau -> %s" % (n, "Kitbash3D" if mode == 'kb3d' else "procéduraux"))
        return {'FINISHED'}


class BG_PT_main(bpy.types.Panel):
    bl_label = "Bâtiments procéduraux"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Bâtiments"

    def draw(self, context):
        s = context.scene.bg_settings
        L = self.layout
        draw_update_box(L, compact=True)
        col = L.column(align=True)
        col.prop(s, "preset")
        if s.preset == 'NONE':
            col.prop(s, "style")
            desc = next(d for k, n, d in ST.STYLES if k == s.style)
        else:
            desc = PS.BY_KEY[s.preset][2]
        box = col.box(); box.scale_y = 0.7
        for line in _wrap(desc, 42):
            box.label(text=line)
        row = col.row(align=True)
        row.prop(s, "seed")
        row.operator("bg.random_seed", text="", icon='FILE_REFRESH')
        col.prop(s, "detail", expand=True)
        col = L.column(align=True)
        col.operator("bg.generate", icon='HOME')
        row = col.row(align=True)
        row.operator("bg.variants", icon='GRID')
        row.prop(s, "count", text="")
        sel = _bg_objects(context)
        if sel:
            col = L.column(align=True)
            col.label(text="Sélection : %d bâtiment(s)" % len(sel))
            row = col.row(align=True)
            row.operator("bg.reseed", text="Variante précédente", icon='TRIA_LEFT').step = -1
            row.operator("bg.reseed", text="Suivante", icon='TRIA_RIGHT').step = 1
            row = col.row(align=True)
            row.operator("bg.apply", icon='FILE_REFRESH')
            row.operator("bg.load", text="", icon='IMPORT')
            ob = context.active_object
            if ob and "bg_info" in ob:
                i = json.loads(ob["bg_info"])
                nm = PS.BY_KEY[i['preset']][1] if i.get('preset') in PS.BY_KEY else i.get('style')
                col.label(text="%s, graine %d : %d étages, %.0f m, %d tris" % (nm, json.loads(ob['bg_params'])['seed'], i.get('floors', 0), i.get('height', 0), i.get('tris', 0)))


class BG_PT_shape(bpy.types.Panel):
    bl_label = "Gabarit et options"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Bâtiments"
    bl_parent_id = "BG_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        s = context.scene.bg_settings
        col = self.layout.column(align=True)
        col.prop(s, "floors"); col.prop(s, "width"); col.prop(s, "depth")
        col.separator()
        col.prop(s, "ground"); col.prop(s, "roof"); col.prop(s, "wall")
        col.separator()
        g = col.grid_flow(columns=2, align=True)
        for k in ("fire_escape", "water_tower", "roof_props", "storefront", "awnings", "sidewalk"):
            g.prop(s, k, toggle=True)
        col.prop(s, "win_ac")
        col.prop(s, "spacing")


class BG_PT_street(bpy.types.Panel):
    bl_label = "Rue"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Bâtiments"
    bl_parent_id = "BG_PT_main"

    def draw(self, context):
        s = context.scene.bg_settings
        col = self.layout.column(align=True)
        col.prop(s, "street_mix"); col.prop(s, "street_len")
        row = col.row(align=True); row.prop(s, "road_w"); row.prop(s, "walk_w")
        col.prop(s, "street_both")
        col.operator("bg.street", icon='MOD_ARRAY')


class BG_PT_materials(bpy.types.Panel):
    bl_label = "Matériaux et rendu"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Bâtiments"
    bl_parent_id = "BG_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        s = context.scene.bg_settings
        col = self.layout.column(align=True)
        col.prop(s, "mat_mode", expand=True)
        if s.mat_mode == 'KB3D':
            p = _prefs(context)
            if not (p and p.kb_dir):
                col.prop(s, "kb_dir")
            mode, kb = _mat_args(context)
            col.label(text="Textures trouvées" if mode == 'kb3d' else "Textures introuvables : matériaux procéduraux", icon='CHECKMARK' if mode == 'kb3d' else 'ERROR')
        col.operator("bg.swap_materials", icon='MATERIAL')
        col.separator()
        col.prop(s, "wear", slider=True)
        col.prop(s, "decals", slider=True)
        col.prop(s, "services", toggle=True)
        col.separator()
        col.prop(s, "lit_strength"); col.prop(s, "lit_ratio")
        col.prop(s, "scale")


class BG_PT_fond(bpy.types.Panel):
    bl_label = "Fond de décor (versions cuites)"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Bâtiments"
    bl_parent_id = "BG_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        s = context.scene.bg_settings
        L = self.layout
        col = L.column(align=True)
        col.label(text="Textures cuites", icon='TEXTURE')
        col.prop(s, "fond_density"); col.prop(s, "fond_max_res")
        col.prop(s, "fond_dir")
        if _fond_dir() is None:
            col.label(text="Fichier non enregistré : images empaquetées", icon='INFO')
        col = L.column(align=True)
        col.label(text="Bâtiments sélectionnés", icon='RESTRICT_SELECT_OFF')
        col.prop(s, "fond_hide_src")
        col.operator("bg.fond_selection", icon='RENDER_STILL')
        col = L.column(align=True)
        col.label(text="Bibliothèque", icon='ASSET_MANAGER')
        col.prop(s, "fond_district")
        row = col.row(align=True); row.prop(s, "fond_count"); row.prop(s, "fond_seed")
        n = len(FD.library_objects(context))
        col.operator("bg.fond_library", icon='FILE_REFRESH' if n else 'ADD')
        col.label(text="%d modèle(s) en bibliothèque" % n if n else "Bibliothèque vide")
        col = L.column(align=True)
        col.label(text="Ville de fond", icon='MESH_GRID')
        row = col.row(align=True); row.prop(s, "city_bx"); row.prop(s, "city_by")
        row = col.row(align=True); row.prop(s, "city_block_l"); row.prop(s, "city_block_d")
        row = col.row(align=True); row.prop(s, "city_street"); row.prop(s, "city_avenue")
        col.prop(s, "city_skyline")
        row = col.row(align=True); row.prop(s, "city_seed"); row.prop(s, "city_ground", toggle=True)
        col.operator("bg.fond_city", icon='WORLD')
        ob = context.active_object
        if ob and ob.get("bg_fond_info"):
            i = json.loads(ob["bg_fond_info"])
            L.label(text="Fond : %d tris (détaillé %d), %d px, %.0f px/m" % (i['tris'], i['tris_detail'], i['res'], i['px_m']))


def _kb_cfg(context):
    s = context.scene.bg_settings
    mode, kb = _mat_args(context)
    return dict(detail=int(s.detail), mat_mode=mode, kb_dir=kb, seeds=s.cat_seeds, wear=s.wear, decals=s.decals)


class BG_OT_catalog_build(bpy.types.Operator):
    """Construit en arrière-plan le catalogue des bâtiments prêts à glisser-déposer (tous les presets et styles, avec vignettes) et le déclare comme bibliothèque d'assets"""
    bl_idname = "bg.catalog_build"
    bl_label = "Construire le catalogue"

    def execute(self, context):
        msg = CT.start(_kb_cfg(context))
        if msg:
            self.report({'WARNING'}, msg)
            return {'CANCELLED'}
        self.report({'INFO'}, "Construction du catalogue lancée en arrière-plan (environ 2 à 4 minutes)")
        return {'FINISHED'}


class BG_OT_catalog_cancel(bpy.types.Operator):
    """Arrête la construction du catalogue"""
    bl_idname = "bg.catalog_cancel"
    bl_label = "Annuler"

    def execute(self, context):
        CT.cancel()
        return {'FINISHED'}


class BG_OT_catalog_register(bpy.types.Operator):
    """Déclare le dossier du catalogue comme bibliothèque d'assets (Préférences › Fichiers › Bibliothèques d'assets)"""
    bl_idname = "bg.catalog_register"
    bl_label = "Déclarer la bibliothèque"

    def execute(self, context):
        if not CT.built():
            self.report({'WARNING'}, "Catalogue pas encore construit")
            return {'CANCELLED'}
        CT.register_library()
        return {'FINISHED'}


class BG_OT_catalog_open(bpy.types.Operator):
    """Ouvre l'explorateur d'assets sous la vue 3D, sur la bibliothèque des bâtiments : glisser un bâtiment dans la scène pour le poser"""
    bl_idname = "bg.catalog_open"
    bl_label = "Ouvrir l'explorateur d'assets"

    def execute(self, context):
        lib = CT.library()
        if lib is None:
            self.report({'WARNING'}, "Bibliothèque non déclarée")
            return {'CANCELLED'}
        area = context.area
        if area is None or area.type != 'VIEW_3D':
            area = next((a for a in context.screen.areas if a.type == 'VIEW_3D'), None)
        if area is None:
            return {'CANCELLED'}
        before = set(context.screen.areas)
        with context.temp_override(area=area):
            bpy.ops.screen.area_split(direction='HORIZONTAL', factor=0.32)
        new = [a for a in context.screen.areas if a not in before]
        if not new:
            return {'CANCELLED'}
        na = min(new, key=lambda a: a.y)
        na.ui_type = 'ASSETS'
        try:
            sp = na.spaces.active
            sp.params.asset_library_reference = lib.name
        except Exception:
            pass
        return {'FINISHED'}


class BG_PT_catalog(bpy.types.Panel):
    bl_label = "Catalogue (glisser-déposer)"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Bâtiments"
    bl_parent_id = "BG_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        s = context.scene.bg_settings
        L = self.layout
        st = CT.state
        col = L.column(align=True)
        if st["status"] == "running":
            col.label(text="Construction : %d / %d" % (st["done"], st["total"]), icon='SORTTIME')
            if st["msg"]:
                col.label(text=st["msg"])
            col.operator("bg.catalog_cancel", icon='CANCEL')
            return
        built = CT.built()
        lib = CT.library()
        col.prop(s, "cat_seeds")
        col.label(text="Détail et matériaux : réglages du panneau", icon='INFO')
        col.operator("bg.catalog_build", text="Mettre à jour le catalogue" if built else "Construire le catalogue", icon='ASSET_MANAGER')
        if st["status"] in ("done", "error") and st["msg"]:
            for line in _wrap(st["msg"], 44):
                col.label(text=line, icon='ERROR' if st["status"] == "error" else 'NONE')
        if built:
            col = L.column(align=True)
            if lib is None:
                col.operator("bg.catalog_register", icon='ADD')
            else:
                col.label(text="Bibliothèque « %s » prête" % lib.name, icon='CHECKMARK')
                col.operator("bg.catalog_open", icon='FILEBROWSER')
                box = col.box(); box.scale_y = 0.7
                for line in _wrap("Glisser un bâtiment de l'explorateur d'assets dans la vue 3D. Il reste réglable ici (graine, variantes, matériaux).", 44):
                    box.label(text=line)


class BG_OT_random_seed(bpy.types.Operator):
    bl_idname = "bg.random_seed"
    bl_label = "Graine au hasard"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        context.scene.bg_settings.seed = random.randint(1, 99999)
        return {'FINISHED'}


def _wrap(t, n):
    out, cur = [], ""
    for w in t.split():
        if len(cur) + len(w) + 1 > n:
            out.append(cur); cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        out.append(cur)
    return out


classes = (BG_Preferences, BG_OT_update_check, BG_OT_update_install, BG_OT_update_page, BG_Settings, BG_OT_generate, BG_OT_variants, BG_OT_street, BG_OT_reseed, BG_OT_apply, BG_OT_load,
           BG_OT_swap_materials, BG_OT_random_seed, BG_OT_fond_selection, BG_OT_fond_library, BG_OT_fond_city,
           BG_OT_catalog_build, BG_OT_catalog_cancel, BG_OT_catalog_register, BG_OT_catalog_open,
           BG_PT_main, BG_PT_shape, BG_PT_street, BG_PT_fond, BG_PT_materials, BG_PT_catalog)


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.bg_settings = PointerProperty(type=BG_Settings)
    UP.register()


def unregister():
    CT.unregister()
    UP.unregister()
    del bpy.types.Scene.bg_settings
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
