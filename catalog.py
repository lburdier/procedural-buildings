"""Catalogue de batiments prets a glisser-deposer (bibliotheque d'assets Blender).

Un Blender en arriere-plan (catalog_build.py) construit chaque preset et chaque style, rend une vignette, marque
les objets comme assets ranges en catalogues (Brooklyn, Manhattan, Styles) et enregistre le tout dans un dossier
de l'utilisateur ; ce dossier est declare comme bibliotheque d'assets dans les preferences (import : Ajouter).
Les batiments deposes gardent leurs parametres : graine, style, regeneration depuis le panneau."""
import json
import os
import subprocess
import sys

import bpy

LIB_NAME = "Bâtiments procéduraux"
BLEND = "batiments_proceduraux.blend"

BROOKLYN = ['tenement', 'old_law', 'bodega_corner', 'corner_mansard', 'brownstone', 'brick_rowhouse', 'arched_bank',
            'arch_warehouse', 'concrete_loft', 'nycha']
MANHATTAN = ['cast_iron_loft', 'garment_loft', 'hotel_setback', 'tan_prewar', 'stone_lunette', 'white_brick', 'terrace_coop',
             'limestone_office', 'pilaster_tower', 'deco_tower', 'gothic_tower', 'setback_spire', 'modern_slab', 'glass_curtain']

state = {"status": "idle", "done": 0, "total": 0, "msg": "", "proc": None}


def entries(seeds=2):
    """(chemin de catalogue, nom, parametres) pour chaque asset."""
    from . import presets as PS
    from . import styles as ST
    out = []
    for k, n, d, st, fn in PS.PRESETS:
        cat = "Bâtiments procéduraux/Brooklyn" if k in BROOKLYN else ("Bâtiments procéduraux/Manhattan" if k in MANHATTAN else "Bâtiments procéduraux/Autres")
        for s in range(1, seeds + 1):
            out.append((cat, "%s %d" % (n, s), dict(style=st, preset=k, seed=s, opts={})))
    for k, n, d in ST.STYLES:
        for s in range(1, seeds + 2):
            out.append(("Bâtiments procéduraux/Styles", "%s %d" % (n, s), dict(style=k, seed=s, opts={})))
    return out


def catalog_dir():
    pkg = __package__
    try:
        d = bpy.utils.extension_path_user(pkg, path="catalogue", create=True)
    except Exception:
        d = os.path.join(bpy.utils.user_resource('DATAFILES', path="batiments_proceduraux", create=True), "catalogue")
        os.makedirs(d, exist_ok=True)
    return d


def library():
    """Bibliotheque d'assets declaree pour le catalogue, ou None."""
    d = os.path.normcase(os.path.normpath(catalog_dir()))
    for lib in bpy.context.preferences.filepaths.asset_libraries:
        if os.path.normcase(os.path.normpath(bpy.path.abspath(lib.path))) == d:
            return lib
    return None


def built():
    return os.path.isfile(os.path.join(catalog_dir(), BLEND))


def register_library():
    lib = library()
    d = catalog_dir()
    if lib is None:
        libs = bpy.context.preferences.filepaths.asset_libraries
        try:
            lib = libs.new(name=LIB_NAME, directory=d)
        except Exception:
            bpy.ops.preferences.asset_library_add(directory=d)
            lib = libs[-1]
            lib.name = LIB_NAME
    try:
        lib.import_method = 'APPEND'
    except Exception:
        pass
    try:
        bpy.ops.wm.save_userpref()
    except Exception:
        pass
    _refresh()
    return lib


def _refresh():
    try:
        for w in bpy.context.window_manager.windows:
            for a in w.screen.areas:
                if a.type == 'FILE_BROWSER':
                    with bpy.context.temp_override(window=w, area=a):
                        try:
                            bpy.ops.asset.library_refresh()
                        except Exception:
                            pass
                    a.tag_redraw()
    except Exception:
        pass


def start(cfg):
    """Lance la construction en arriere-plan. Renvoie un message d'erreur ou ''."""
    if state["status"] == "running":
        return "Construction déjà en cours"
    here = os.path.dirname(os.path.abspath(__file__))
    script = os.path.join(here, "catalog_build.py")
    parent, pkg_dir = os.path.dirname(here), os.path.basename(here)
    out = catalog_dir()
    args = [bpy.app.binary_path, "-b", "--factory-startup", "-P", script, "--", parent, pkg_dir, out, json.dumps(cfg)]
    flags = 0
    if sys.platform == "win32":
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    env = dict(os.environ, BG_NO_UPDATE_CHECK="1")
    state.update(status="running", done=0, total=len(entries(cfg.get('seeds', 2))), msg="Démarrage...")
    state["proc"] = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                                     errors="replace", creationflags=flags, env=env, bufsize=1)
    import threading
    threading.Thread(target=_reader, args=(state["proc"],), daemon=True).start()
    if not bpy.app.timers.is_registered(_poll):
        bpy.app.timers.register(_poll, first_interval=1.0, persistent=True)
    return ""


def _reader(proc):
    tail = []
    for line in proc.stdout:
        line = line.strip()
        if line.startswith("PROGRESS"):
            parts = line.split(" ", 3)
            state["done"], state["total"] = int(parts[1]), int(parts[2])
            state["msg"] = parts[3] if len(parts) > 3 else ""
        elif line.startswith("DONE"):
            state["msg"] = "Terminé"
        else:
            tail.append(line)
            tail[:] = tail[-12:]
    proc.wait()
    state["tail"] = tail


def _poll():
    p = state.get("proc")
    _redraw()
    if p is None:
        return None
    if p.poll() is None:
        return 1.0
    if p.returncode == 0 and built():
        state.update(status="done", msg="Catalogue prêt : %d bâtiments" % state["total"])
        try:
            register_library()
        except Exception as exc:  # noqa: BLE001
            state["msg"] += " (bibliothèque à déclarer à la main : %s)" % exc
    else:
        err = [t for t in state.get("tail", []) if t][-3:]
        state.update(status="error", msg="Échec de la construction : " + " | ".join(err)[:300])
    state["proc"] = None
    _redraw()
    return None


def _redraw():
    try:
        for w in bpy.context.window_manager.windows:
            for a in w.screen.areas:
                if a.type == 'VIEW_3D':
                    a.tag_redraw()
    except Exception:
        pass


def cancel():
    p = state.get("proc")
    if p is not None and p.poll() is None:
        p.terminate()
    state.update(status="idle", msg="Annulé", proc=None)


def unregister():
    if bpy.app.timers.is_registered(_poll):
        bpy.app.timers.unregister(_poll)
    cancel()
