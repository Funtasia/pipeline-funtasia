import bpy
import os
import math
import time
import bmesh
from mathutils import Vector
from pathlib import Path

C = bpy.context
D = bpy.data
S = C.scene

zones_lst = ["NONE","GREEN","PURPLE","RED","YELLOW","BLUE","BROWN","ORANGE"]

def init(): 
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


def cln():     
    import_col = D.collections["Collection"]
    col_dict = {i.name.upper():D.collections.new(i.name.upper()) for i in D.materials}
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


def sep():
    target_cols_name = ["BASE","GREY","FOOT","DRIVE","GRASS","NONE"]
    target_cols = {c for c in (D.collections.get(name) for name in target_cols_name) if c}

    objects_active = [
        obj
        for col in S.collection.children
        for obj in col.objects
        if target_cols.isdisjoint(obj.users_collection)
    ]
    for obj in objects_active:

            # Make this object active
            C.view_layer.objects.active = obj
            
            # Ensure only this object is selected
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)

            # Now enter edit mode safely
            bpy.ops.object.mode_set(mode='EDIT')

            # Select all mesh data
            bpy.ops.mesh.select_all(action='SELECT')

            # Separate by loose parts
            bpy.ops.mesh.separate(type='LOOSE')

            # Exit edit mode
            bpy.ops.object.mode_set(mode='OBJECT')


def join(coll_name=None):
    if coll_name is None or  (coll := D.collections.get(str(coll_name))) is None:
        return
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    for obj in coll.objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = coll.objects[0]
    bpy.ops.object.join()
    bpy.ops.object.select_all(action='DESELECT')
    coll.objects[0].name = coll.name.title()


def ext():
    thickness_map = {
        "GREY": 0.05,
        "FOOT": 0.5,
        "DRIVE": 0.8,
        "GRASS": 0.3,
        "BASE": 0.15,
    }
    thickness_lst = ["TOILET","LIFT","MTOILET","FTOILET","ATOILET"] + zones_lst
    scale = 1
    for obj in S.objects:
        # Only process objects in your target collections
        if coll := obj.users_collection:
            if "|" in obj.name:
                safe_name,thickness = obj.name.split("|")
                thickness = int(thickness.strip())/10
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
        

def prop():
    for obj in S.objects:
        obj_col = obj.users_collection[0].name
        obj["ROLE"] = ("OBJECT" if obj_col in zones_lst else obj_col)
        obj["ZONE"] = (obj_col.upper() if obj_col in zones_lst else "NONE")


def staircase():
    if D.collections.get("STAIRCASE") is None:
        return
    for obj in D.collections["STAIRCASE"].objects:
        obj["STAIRCASEDIRECTION"] = obj.name.split(".")[0]
    for obj in D.collections["STAIRCASE"].objects:
        obj.name = "Staircase"
        
def marker():
    if D.collections.get("MARKER") is None:
        return
    for obj in D.collections["MARKER"].objects:
        obj["MARKERID"] = obj.name
        

def misctag():
    if D.collections.get("MISCTAG") is None:
        return
    for obj in D.collections["MISCTAG"].objects:
        obj["MISCTAG"] = obj.name


def footnode():
    if D.collections.get("FOOTNODE") is None:
        return
    for obj in D.collections["FOOTNODE"].objects:
        obj["FOOTNODEID"] = obj.name
    
def ori():
    # Ensure Object Mode
    if C.object and C.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    for obj in S.objects:
        if obj.type == "MESH":
            C.view_layer.objects.active = obj
            obj.select_set(True)

            bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')

            obj.select_set(False)


def display():
    for obj in S.objects:
        print(f"Object: {obj.name}")
        obj_keys = list(obj.keys())
        for key in obj_keys:
            print(f"Key: {key:<20} |Value: {obj[key]}")
        print()
        


def make_material_emission(name):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name=name)
    mat.use_nodes = True
    mat.diffuse_color = (0.5,0.5,0.5,1.0)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    nodes.clear()

    emission = nodes.new("ShaderNodeEmission")
    output   = nodes.new("ShaderNodeOutputMaterial")

    emission.inputs["Color"].default_value = (0.5,0.5,0.5,1.0)
    emission.inputs["Strength"].default_value = 1.0

    links.new(emission.outputs["Emission"], output.inputs["Surface"])

    return mat

def apply_all_modifiers(obj):
    """Apply modifiers by index 0 repeatedly — avoids broken modifier name encoding."""
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    while obj.modifiers:
        mod = obj.modifiers[0]
        try:
            # Sanitise the name before passing it to the operator
            safe_name = mod.name.encode('utf-8', errors='replace').decode('utf-8')
            bpy.ops.object.modifier_apply(modifier=mod.name)
            print(f"  ✓ Applied modifier: {safe_name}")
        except (RuntimeError, UnicodeDecodeError) as e:
            print(f"  ⚠ Skipping modifier (error: {e}), removing instead")
            obj.modifiers.remove(mod)  # Remove it so the while loop doesn't get stuck

    obj.select_set(False)



def split_mat():
    UP_THRESHOLD = 0.9  # Strict: only faces exactly parallel to XY plane

    UP = Vector((0, 0, 1))
    include = {"ATOILET","FTOILET","MTOILET","LIFT"} | set(zones_lst)

    objects = [
        obj
        for coll in bpy.data.collections if coll.name in include
        for obj in coll.objects
    ]
    for obj in objects:
        if obj.type != 'MESH':
            continue
        
        coll = obj.users_collection[0].name
        print(f"\nProcessing: {obj.name}")

        # ── Step 2: Apply modifiers so Solidify geometry becomes real ────────────
        apply_all_modifiers(obj)

        # ── Step 3: Fix broken normals ───────────────────────────────────────────
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode='OBJECT')
        obj.select_set(False)

        # ── Step 4: Rebuild material slots ───────────────────────────────────────
        wall_mat = make_material_emission(f"{coll}_Wall")
        top_mat  = make_material_emission(f"{coll}_Top")

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

        print(f"✓ Done")

def rename_mesh():
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            obj.data.name = obj.name


def first():
    init()
    cln()
    sep()
    ori()
    
def second():
    ext()
    prop()
    staircase()
    marker()
    footnode()
    misctag()
    split_mat()
    rename_mesh()

EXPORT_CONFIG = {
    "export_format": "GLB",
    "export_image_format": "NONE",
    "export_image_add_webp": False,
    "export_image_webp_fallback": False,
    "export_keep_originals": False,
    "export_texcoords": True,
    "export_normals": True,
    "export_gn_mesh": False,
    "export_draco_mesh_compression_enable": False,
    "export_tangents": False,
    "export_materials": "EXPORT",
    "export_unused_images": False,
    "export_unused_textures": False,
    "export_vertex_color": "MATERIAL",
    "export_vertex_color_name": "Color",
    "export_all_vertex_colors": True,
    "export_active_vertex_color_when_no_material": True,
    "export_attributes": False,
    "use_mesh_edges": False,
    "use_mesh_vertices": False,
    "export_cameras": False,
    "use_selection": False,
    "use_visible": False,
    "use_renderable": False,
    "use_active_collection_with_nested": True,
    "use_active_collection": False,
    "use_active_scene": False,
    "export_extras": True,
    "export_yup": True,
    "export_apply": True,
    "export_shared_accessors": False,
    "export_animations": False,
    "export_skins": False,
    "export_morph": False,
    "export_lights": False,
    "export_import_convert_lighting_mode": "COMPAT",
    "will_save_settings": True,
    "export_loglevel": -1,
}

BASE_DIR = Path(r"C:\Users\goofy\Documents\School\Non Academics\Funtasia\Funtasia App\funtasia-3d-files")
SECONDARY_EXPORT_BASE = Path(r"C:\Users\goofy\Documents\School\Non Academics\Funtasia\Funtasia App\funtasia_app\funtasia_assets\models")

def exp():
    bpy.ops.wm.save_mainfile()

    if not D.filepath:
        raise RuntimeError("Blend file must be saved before exporting.")

    blend_path = Path(bpy.path.abspath(D.filepath))

    # Extract version from the parent folder name (e.g. "v5-30-4")
    version = blend_path.parent.parent.name

    # Build the versioned export filename (e.g. "njc-b3-v5-30-4.glb")
    export_name = f"{blend_path.stem}-{version}.glb"

    # --- Export locations ---
    glb_dir      = BASE_DIR / ".glb" / version 
    app_dir      = SECONDARY_EXPORT_BASE / version

    export_paths = [
        glb_dir  / export_name,
        app_dir  / export_name,
    ]

    for path in export_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        print(f"Exporting to: {path}")
        bpy.ops.export_scene.gltf(filepath=str(path), **EXPORT_CONFIG)
        print(f"  ✓ Saved")

    print(f"\nDone — exported '{export_name}' to {len(export_paths)} locations.",*export_paths,sep="\n\t")
        
    
first()
second()
exp()