import bpy
import bmesh
from mathutils import Vector

from pathlib import Path


C = bpy.context

D = bpy.data

S = bpy.context.scene


ZONES = ["NONE","GREEN","PURPLE","RED","YELLOW","BLUE","BROWN","ORANGE"]

EXPORT = {
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

THICKNESS_MAP = {
        "GREY": 0.05,
        "FOOT": 0.5,
        "DRIVE": 0.8,
        "GRASS": 0.3,
        "BASE": 0.15,
    }

SCALE = 1

FILEPATH = Path(bpy.data.filepath)    

FUNTASIA_ROOT = FILEPATH.parents[2]
SAVEPATH = (FUNTASIA_ROOT / ".glb" / FILEPATH.stem).with_suffix(".glb")


def relocate_objects_to_Collection():
    """
    Relocates objects from 'SKP Mesh Objects' to 'Collection' and subsequently 
    unlinks the other redudant files that were introduced as a result of the 
    conversion (by the service)
    """

    src_col = D.collections.get("SKP Mesh Objects")
    dst_col = D.collections.get("Collection")
    
    if src_col and dst_col:
        for obj in src_col.objects:
            src_col.objects.unlink(obj)
            dst_col.objects.link(obj)
    
    skp_col = D.collections.get("SKP Imported Data")
    if skp_col and skp_col.name in S.collection.children:
        S.collection.children.unlink(skp_col)

def apply_all_transformations():
    """
    Applies all transformations that may have been left by the service to ensure 
    that subsequent reopening of the files may not result in unintended translation,
    rotation or transformation
    """

    bpy.ops.object.select_all(action='DESELECT')

    for obj in S.objects:
        if obj.type == "MESH":
            obj.select_set(True)
    
    C.view_layer.objects.active = C.selected_objects[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

def separate_looseEntity():
    """
    Separate '_(Loose Entity)' based on its children's materials
    """

    bpy.ops.object.select_all(action='DESELECT')
    obj = D.objects["_(Loose Entity)"]
    obj.select_set(True)
    C.view_layer.objects.active = obj

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.separate(type='MATERIAL')
    bpy.ops.object.mode_set(mode='OBJECT')
       
def replace_subobject_w_object():
    """
    Finds any object with the material 'Subobject' and replaces it with 'Object'

    !Note: Might be redudant
    """

    for obj in S.objects:
        if obj.type != "MESH":
            continue
    
        for slot in obj.material_slots:
            if slot.material and "Sub-Object" in slot.material.name:
                new_mat = D.materials.get("Object")
                if new_mat:
                    slot.material = new_mat

def purge_all_unused_materials():
    """
    Removes any materials that are not in use by any object from the model file
    """

    used_materials = set()
    
    for obj in S.objects:
        if obj.type == 'MESH':
            for slot in obj.material_slots:
                if slot.material:
                    used_materials.add(slot.material)
    
    for mat in list(bpy.data.materials):
        if mat not in used_materials:
            bpy.data.materials.remove(mat)

def group_objects_n_parse_names():
    """
    Group objects into their respective collections defined by the materials (i.e.\
    the type of object) [capitalized material names]

    Renames all meshes/objects: strips the 'G-' prefix left by the service else 
    renames it to the material title
    """


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

def separate_loose_objects():
    """
    Separates objects based on 'loose' (i.e. disconnected in the spatial sense)
    """

    ignored_cols_names = ["BASE","GREY","FOOT","DRIVE","GRASS","NONE"]
    target_cols = {c for c in (D.collections.get(name) for name in ignored_cols_names) if c}

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

def reset_origin_to_geometric_centre():
    """
    Reset origins of all meshes to the geometric origin of the object
    """
    # Ensure Object Mode
    if C.object and C.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    for obj in S.objects:
        if obj.type == "MESH":
            C.view_layer.objects.active = obj
            obj.select_set(True)

            bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')

            obj.select_set(False)

def extrude_objects(): 
    """
    Extrudes objects by applying a solidify modifier.

    Thickness is decided based on material or predefined measurements indicated in 
    the name of the mesh using a '|' as a separator.
    """
  
    for obj in S.objects:

        if coll := obj.users_collection:

            if "|" in obj.name:
                safe_name,thickness = obj.name.split("|")
                thickness = int(thickness.strip())/10
                obj.name = safe_name.strip().title()

            elif coll[0].name not in THICKNESS_MAP.keys():

                thickness = 20
            else:
                thickness = THICKNESS_MAP.get(coll[0].name)

            if thickness is None:
                continue
            
        if any(m.type == "SOLIDIFY" for m in obj.modifiers):
            continue

        mod = obj.modifiers.new("Solidify", "SOLIDIFY")
        mod.thickness = thickness * -0.01 * SCALE
        mod.offset = -1.0
        mod.use_even_offset = True
        mod.use_quality_normals = True
        
def assign_role_n_zone_properties():
    """
    Assigns role and zones property based on objects' collection
    """

    for obj in S.objects:
        obj_col = obj.users_collection[0].name
        obj["ROLE"] = ("OBJECT" if obj_col in ZONES else obj_col)
        obj["ZONE"] = (obj_col.upper() if obj_col in ZONES else "NONE")

def assign_staircase_direction():
    """
    Assign its direction(object's name) to a property 'STAIRCASEDIRECTION' for 
    objects in 'STAIRCASE' collection

    Subsequently renames all objects in 'STAIRCASE' collection to 'Staircase'
    """

    if D.collections.get("STAIRCASE") is None:
        return
    
    for obj in D.collections["STAIRCASE"].objects:
        obj["STAIRCASEDIRECTION"] = obj.name.split(".")[0]

    for obj in D.collections["STAIRCASE"].objects:
        obj.name = "Staircase"

def assign_marker_markerID():
    """
    Assign its markerID(object's name) the property 'MARKERID' for objects in 
    'MARKER' collection
    """

    if D.collections.get("MARKER") is None:
        return
    for obj in D.collections["MARKER"].objects:
        obj["MARKERID"] = obj.name

def assign_misctag():
    """
    Assign misctag their respective properties defined in the object's name
    """

    if D.collections.get("MISCTAG") is None:
        return
    for obj in D.collections["MISCTAG"].objects:
        obj["MISCTAG"] = obj.name

def assign_footnode_footnodeID():
    """
    Assign its footnodeID(object's name)
    """

    if D.collections.get("FOOTNODE") is None:
        return
    for obj in D.collections["FOOTNODE"].objects:
        obj["FOOTNODEID"] = obj.name

def make_material_emission(name):
    """
    Makes an emission material for objects
    """

    mat = D.materials.get(name) or D.materials.new(name=name)
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
    """
    Apply modifiers by index 0 repeatedly — avoids broken modifier name encoding.
    """

    C.view_layer.objects.active = obj
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
    """
    Split materials to separate upwards and sidewards facing planes
    """

    UP_THRESHOLD = 0.9  # Strict: only faces exactly parallel to XY plane

    UP = Vector((0, 0, 1))
    include = ["ATOILET","FTOILET","MTOILET","LIFT"] + ZONES

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
    """
    Rename meshes
    """
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            obj.data.name = obj.name

def export_glb():
    bpy.ops.wm.save_mainfile()

    if not D.filepath:
        raise RuntimeError("Blend file must be saved before exporting.")

    
    print(f"Exporting to: {SAVEPATH}")
    bpy.ops.export_scene.gltf(filepath=str(SAVEPATH), **EXPORT)

def run():
    relocate_objects_to_Collection()
    apply_all_transformations()
    separate_looseEntity()
    replace_subobject_w_object()
    purge_all_unused_materials()
    group_objects_n_parse_names()

    separate_loose_objects()
    reset_origin_to_geometric_centre()

    extrude_objects()

    assign_role_n_zone_properties()
    assign_staircase_direction()
    assign_marker_markerID()
    assign_footnode_footnodeID()
    assign_misctag()

    split_mat()
    rename_mesh()

    export_glb()

run()