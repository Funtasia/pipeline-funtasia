#!/usr/bin/env python3

# Blender Specific modules
import bpy
import bmesh
from mathutils import Vector

# Python modules
import os
import math
import time
from pathlib import Path
import logging
import json


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
import logging

SUCCESS = 25
logging.addLevelName(SUCCESS, "SUCCESS")


class BlenderLogger(logging.LoggerAdapter):
    """
    Thin adapter matching the log/error/success interface used by EncoderPipeline.
    All output goes to stdout (Blender -b mode forwards stdout to the parent process).
    """
    _LOG_FORMAT = "[BLENDER] %(levelname)-8s %(message)s"

    def __init__(self, name: str = "blender_pipeline") -> None:
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)

        if not logger.handlers:
            handler = logging.StreamHandler()          # → stdout
            handler.setFormatter(logging.Formatter(BlenderLogger._LOG_FORMAT))
            logger.addHandler(handler)

        super().__init__(logger, extra={})

    # Convenience wrappers ------------------------------------------------
    # Note: do NOT define log() here — LoggerAdapter.log(level, msg, ...) is called
    # internally by the stdlib (e.g. from self.info()), so overriding it with a
    # single-argument signature causes a TypeError on stacklevel kwarg.

    def info(self, msg: str, *args, **kwargs) -> None:
        self.logger.info(msg, *args, stacklevel=2, **kwargs)

    def error(self, msg: str, *args, **kwargs) -> None:
        self.logger.error(msg, *args, stacklevel=2, **kwargs)

    def success(self, msg: str) -> None:
        self.logger.log(SUCCESS, msg, stacklevel=2)

# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class BlenderPipeline:
    """
    Converts a SketchUp-imported .blend scene into an export-ready .glb.

    Typical usage
    -------------
    pipeline = BlenderPipeline(config)
    pipeline.run()          # first() → second() → exp()

    Or step by step:
    pipeline.first()        # init, clean, separate, set origins
    pipeline.second()       # extrude, tag properties, split materials, rename
    pipeline.exp()          # save .blend and export .glb to all destinations
    """

    ZONES: list[str] = ["NONE", "GREEN", "PURPLE", "RED", "YELLOW", "BLUE", "BROWN", "ORANGE"]

    # Collections that receive per-face material splitting in split_mat()
    SPLIT_MAT_INCLUDE: set[str] = {"ATOILET", "FTOILET", "MTOILET", "LIFT"}

    # Collections that use a fixed 20-unit extrusion thickness in ext()
    THICK_FIXED_COLS: list[str] = ["TOILET", "LIFT", "MTOILET", "FTOILET", "ATOILET"]

    # Collections whose objects receive a named custom property in tag()
    TAG_MAP: dict[str, str] = {
        "STAIRCASE":  "STAIRCASEDIRECTION",
        "MARKER":     "MARKERID",
        "FOOTNODE":   "FOOTNODEID",
        "MISCTAG":    "MISCTAG",
    }

    # ---------------------------------------------------------------------------
    # Construction
    # ---------------------------------------------------------------------------

    def __init__(self, config: dict) -> None:
        self.files_path, self.assets_path, self.export = self._gen_path(config)
        self.version: str = config["general"]["version"]
        self._log = BlenderLogger()

    # ---------------------------------------------------------------------------
    # Logging helpers (mirrors EncoderPipeline interface)
    # ---------------------------------------------------------------------------

    def log(self, msg: str) -> None:
        self._log.info(msg)

    def error(self, msg: str) -> None:
        self._log.error(msg)

    def success(self, msg: str) -> None:
        self._log.success(msg)

    # ---------------------------------------------------------------------------
    # Context / data shortcuts (evaluated fresh each call — never stale)
    # ---------------------------------------------------------------------------

    @property
    def C(self):
        return bpy.context

    @property
    def D(self):
        return bpy.data

    @property
    def S(self):
        return bpy.context.scene

    # ---------------------------------------------------------------------------
    # Path resolution
    # ---------------------------------------------------------------------------

    @staticmethod
    def _gen_path(config: dict) -> tuple[Path, Path]:
        """Resolve all export and config paths from the pipeline config."""
        ver    = config["general"]["version"]
        parent = Path(config["repos"]["root"])
        assets_export = parent / config["repos"]["assets"]   / "model"
        export_config = parent / config["repos"]["pipeline"] / ".blender"  / "export.json"
        return assets_export, export_config

    # ---------------------------------------------------------------------------
    # Stage 1 — Import clean-up
    # ---------------------------------------------------------------------------

    def init(self) -> None:
        """
        Prepare the raw SketchUp import:
          1. Move objects from [SKP Mesh Objects] into [Collection].
          2. Unlink [SKP Imported Data].
          3. Apply all transforms on every mesh.
          4. Separate the loose entity mesh by material.
          5. Replace Sub-Object material with Object.
          6. Purge unused materials.
        """
        C, D, S = self.C, self.D, self.S

        # > Move all groups from [SKP Mesh Objects] to [Collection]
        src_col = D.collections.get("SKP Mesh Objects")
        dst_col = D.collections.get("Collection")

        if src_col and dst_col:
            for obj in src_col.objects:
                src_col.objects.unlink(obj)
                dst_col.objects.link(obj)

        # > Unlink SKP Imported Data collection
        skp_col = D.collections.get("SKP Imported Data")
        if skp_col and skp_col.name in S.collection.children:
            S.collection.children.unlink(skp_col)

        # > Apply all transformations to every mesh
        bpy.ops.object.select_all(action='DESELECT')

        for obj in S.objects:
            if obj.type == "MESH":
                obj.select_set(True)

        C.view_layer.objects.active = C.selected_objects[0]
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        # > Separate meshes by material
        bpy.ops.object.select_all(action='DESELECT')
        D.objects["_(Loose Entity)"].select_set(True)
        C.view_layer.objects.active = obj

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.separate(type='MATERIAL')
        bpy.ops.object.mode_set(mode='OBJECT')

        # > Replace "Subobject" material with "Object"
        for obj in S.objects:
            if obj.type != "MESH":
                continue

            for slot in obj.material_slots:
                if slot.material and "Sub-Object" in slot.material.name:
                    new_mat = D.materials.get("Object")
                    if new_mat:
                        slot.material = new_mat

        # > Purge all unused materials
        used_materials = set()

        for obj in S.objects:
            if obj.type == 'MESH':
                for slot in obj.material_slots:
                    if slot.material:
                        used_materials.add(slot.material)

        for mat in list(bpy.data.materials):
            if mat not in used_materials:
                bpy.data.materials.remove(mat)

    def cln(self) -> None:
        """
        Organise objects into per-material collections.
        Strip 'G-' prefixes from named objects; rename unnamed ones to their material.
        """
        D, S = self.D, self.S

        import_col = D.collections["Collection"]
        col_dict = {i.name.upper(): D.collections.new(i.name.upper()) for i in D.materials}
        for coll in list(col_dict.values()):
            S.collection.children.link(coll)

        for obj in import_col.objects:
            if obj.type == "MESH":
                import_col.objects.unlink(obj)
                if obj.data.materials:
                    mat = obj.data.materials[0].name.upper()
                    col_dict[mat].objects.link(obj)
                    if obj.name.startswith("G-"):
                        obj.name = obj.name[2::]
                    else:
                        obj.name = mat.title()

        D.collections.remove(import_col)

    def sep(self) -> None:
        """Separate loose geometry for objects that live outside the base collections."""
        C, D, S = self.C, self.D, self.S

        target_cols_name = ["BASE", "GREY", "FOOT", "DRIVE", "GRASS", "NONE"]
        target_cols = {c for c in (D.collections.get(name) for name in target_cols_name) if c}

        objects_active = [
            obj
            for col in S.collection.children
            for obj in col.objects
            if target_cols.isdisjoint(obj.users_collection)
        ]
        for obj in objects_active:
            C.view_layer.objects.active = obj
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.separate(type='LOOSE')
            bpy.ops.object.mode_set(mode='OBJECT')

    def join(self, coll_name: str | None = None) -> None:
        """Join all objects in *coll_name* into a single mesh and rename it."""
        D = self.D

        if coll_name is None or (coll := D.collections.get(str(coll_name))) is None:
            return
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        for obj in coll.objects:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = coll.objects[0]
        bpy.ops.object.join()
        bpy.ops.object.select_all(action='DESELECT')
        coll.objects[0].name = coll.name.title()

    def ori(self) -> None:
        """Set each mesh object's origin to its bounding-box centre."""
        C, S = self.C, self.S

        # Ensure Object Mode
        if C.object and C.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        for obj in S.objects:
            if obj.type == "MESH":
                C.view_layer.objects.active = obj
                obj.select_set(True)

                bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')

                obj.select_set(False)

    # ---------------------------------------------------------------------------
    # Stage 2 — Geometry & property processing
    # ---------------------------------------------------------------------------

    def ext(self) -> None:
        """Add Solidify modifiers to mesh objects using per-collection thickness rules."""
        S = self.S

        thickness_map = {
            "GREY":  0.05,
            "FOOT":  0.5,
            "DRIVE": 0.8,
            "GRASS": 0.3,
            "BASE":  0.15,
        }
        thickness_lst = self.THICK_FIXED_COLS + self.ZONES
        scale = 1
        for obj in S.objects:
            # Only process objects in your target collections
            if coll := obj.users_collection:
                if "|" in obj.name:
                    safe_name, thickness = obj.name.split("|")
                    thickness = int(thickness.strip()) / 10
                    obj.name = safe_name.strip().title()
                elif coll[0].name in thickness_lst:
                    thickness = 20
                else:
                    thickness = thickness_map.get(coll[0].name)
                if thickness is None:
                    continue

            if any(m.type == "SOLIDIFY" for m in obj.modifiers):
                continue

            # Add Solidify modifier
            mod = obj.modifiers.new("Solidify", "SOLIDIFY")
            mod.thickness = thickness * -0.01 * scale
            mod.offset = -1.0
            mod.use_even_offset = True
            mod.use_quality_normals = True

    def prop(self) -> None:
        """Assign ROLE and ZONE custom properties to every scene object."""
        S = self.S
        zones_lst = self.ZONES

        for obj in S.objects:
            obj_col = obj.users_collection[0].name
            obj["ROLE"] = ("OBJECT" if obj_col in zones_lst else obj_col)
            obj["ZONE"] = (obj_col.upper() if obj_col in zones_lst else "NONE")

    def tag(self) -> None:
        """
        Assign named custom properties to objects in taggable collections.

        Covers: STAIRCASE, MARKER, FOOTNODE, MISCTAG.
        For STAIRCASE, objects are also renamed to 'Staircase' after tagging.
        """
        D = self.D

        for col_name, prop_key in self.TAG_MAP.items():
            col = D.collections.get(col_name)
            if col is None:
                continue
            for obj in col.objects:
                obj[prop_key] = obj.name

            # STAIRCASE direction is encoded in the name prefix; rename after tagging
            if col_name == "STAIRCASE":
                for obj in col.objects:
                    obj[prop_key] = obj.name.split(".")[0]
                for obj in col.objects:
                    obj.name = "Staircase"

    def make_material_emission(self, name: str):
        """Return (or create) a grey emission material with the given name."""
        mat = bpy.data.materials.get(name) or bpy.data.materials.new(name=name)
        mat.use_nodes = True
        mat.diffuse_color = (0.5, 0.5, 0.5, 1.0)
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        nodes.clear()

        emission = nodes.new("ShaderNodeEmission")
        output   = nodes.new("ShaderNodeOutputMaterial")

        emission.inputs["Color"].default_value = (0.5, 0.5, 0.5, 1.0)
        emission.inputs["Strength"].default_value = 1.0

        links.new(emission.outputs["Emission"], output.inputs["Surface"])

        return mat

    def apply_all_modifiers(self, obj) -> None:
        """Apply modifiers by index 0 repeatedly — avoids broken modifier name encoding."""
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)

        while obj.modifiers:
            mod = obj.modifiers[0]
            try:
                # Sanitise the name before passing it to the operator
                safe_name = mod.name.encode('utf-8', errors='replace').decode('utf-8')
                bpy.ops.object.modifier_apply(modifier=mod.name)
                self.success(f"applied modifier: {safe_name}")
            except (RuntimeError, UnicodeDecodeError) as e:
                self.error(f"skipping modifier (error: {e}), removing instead")
                obj.modifiers.remove(mod)  # Remove it so the while loop doesn't get stuck

        obj.select_set(False)

    def split_mat(self) -> None:
        """Split top vs wall faces into separate emission materials per collection."""
        UP_THRESHOLD = 0.9  # Strict: only faces exactly parallel to XY plane

        UP = Vector((0, 0, 1))
        include = self.SPLIT_MAT_INCLUDE | set(self.ZONES)

        objects = [
            obj
            for coll in bpy.data.collections if coll.name in include
            for obj in coll.objects
        ]
        for obj in objects:
            if obj.type != 'MESH':
                continue

            coll = obj.users_collection[0].name
            self.log(f"processing: {obj.name}")

            # ── Step 2: Apply modifiers so Solidify geometry becomes real ────────────
            self.apply_all_modifiers(obj)

            # ── Step 3: Fix broken normals ───────────────────────────────────────────
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.normals_make_consistent(inside=False)
            bpy.ops.object.mode_set(mode='OBJECT')
            obj.select_set(False)

            # ── Step 4: Rebuild material slots ───────────────────────────────────────
            wall_mat = self.make_material_emission(f"{coll}_Wall")
            top_mat  = self.make_material_emission(f"{coll}_Top")

            obj.data.materials.clear()
            obj.data.materials.append(wall_mat)  # index 0
            obj.data.materials.append(top_mat)   # index 1

            # ── Step 5: Assign per face ───────────────────────────────────────────────
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            bm.faces.ensure_lookup_table()

            for face in bm.faces:
                world_normal = (obj.matrix_world.to_3x3() @ face.normal).normalized()
                dot = world_normal.dot(UP)
                face.material_index = 1 if dot >= UP_THRESHOLD else 0

            bm.to_mesh(obj.data)
            bm.free()
            obj.data.update()

            self.success(f"split materials: {obj.name}")

    def rename_mesh(self) -> None:
        """Sync every mesh data-block name to its parent object name."""
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                obj.data.name = obj.name

    # ---------------------------------------------------------------------------
    # Debug
    # ---------------------------------------------------------------------------

    def display(self) -> None:
        """Print all objects and their custom properties to the console."""
        for obj in self.S.objects:
            self.log(f"object: {obj.name}")
            obj_keys = list(obj.keys())
            for key in obj_keys:
                self.log(f"  {key:<20} | {obj[key]}")
            self.log("")

    # ---------------------------------------------------------------------------
    # Export
    # ---------------------------------------------------------------------------

    def exp(self) -> None:
        """Save the .blend file then export .glb to all configured destinations."""
        D = self.D

        bpy.ops.wm.save_mainfile()

        if not D.filepath:
            raise RuntimeError("Blend file must be saved before exporting.")

        with open(self.export) as f:
            EXPORT_CONFIG = json.load(f)

        blend_path  = Path(bpy.path.abspath(D.filepath))
        export_path = self.assets_path / f"{blend_path.stem}.glb"

        export_path.parent.mkdir(parents=True, exist_ok=True)
        self.log(f"exporting to: {export_path}")
        bpy.ops.export_scene.gltf(filepath=str(export_path), **EXPORT_CONFIG)
        self.success(f"saved: {export_path.name}")

    # ---------------------------------------------------------------------------
    # Orchestration
    # ---------------------------------------------------------------------------

    def first(self) -> None:
        """Stage 1: import clean-up — init, organise, separate, set origins."""
        self.init()
        self.cln()
        self.sep()
        self.ori()

    def second(self) -> None:
        """Stage 2: geometry & property processing — extrude, tag, split, rename."""
        self.ext()
        self.prop()
        self.tag()           # replaces individual staircase/marker/footnode/misctag calls
        self.split_mat()
        self.rename_mesh()

    def run(self) -> None:
        """Run the full pipeline: first → second → export."""
        self.first()
        self.second()
        self.exp()


# ---------------------------------------------------------------------------
# Entrypoint — invoked by: blender -b file.blend -P blender_pipeline.py -- --config config.json
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import sys
    import json

    # Blender passes everything after '--' to the script's argv
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(prog="blender_pipeline")
    parser.add_argument("--config", required=True, type=json.loads)
    args = parser.parse_args(argv)

    config = args.config
    
    pipeline = BlenderPipeline(config)
    pipeline.run()