bl_info = {
    "name": "Stylized Rock Generator",
    "author": "mertnizamoglu",
    "version": (0, 3),
    "blender": (3, 0, 0),
    "location": "View3D > Tool Shelf > Stylized Rock",
    "description": "Applies stylized rock modifiers with procedural displacements and presets.",
    "category": "Object",
}

import bpy
from bpy.props import FloatProperty, EnumProperty, PointerProperty, BoolProperty

# Preset definitions
PRESETS = {
    "Cliff": {
        "displace_strength_1": 1.0,
        "displace_strength_2": 0.5,
        "decimate_ratio": 0.1,
        "subdivision_level": 6,
    },
    "Boulder": {
        "displace_strength_1": 0.7,
        "displace_strength_2": 0.3,
        "decimate_ratio": 0.25,
        "subdivision_level": 4,
    },
    "Pebble": {
        "displace_strength_1": 0.4,
        "displace_strength_2": 0.2,
        "decimate_ratio": 0.6,
        "subdivision_level": 2,
    },
}

class StylizedRockProperties(bpy.types.PropertyGroup):
    displace_strength_1: FloatProperty(
        name="Displace Strength 1",
        default=0.7,
        min=0.0,
        max=5.0
    )
    displace_strength_2: FloatProperty(
        name="Displace Strength 2",
        default=0.5,
        min=0.0,
        max=5.0
    )
    decimate_ratio: FloatProperty(
        name="Decimate Ratio",
        default=0.1,
        min=0.0,
        max=1.0
    )
    subdivision_level: FloatProperty(
        name="Subdivision Level",
        default=6,
        min=0,
        max=7
    )
    preset: EnumProperty(
        name="Preset",
        items=[(key, key, "") for key in PRESETS.keys()],
        update=lambda self, context: apply_preset(self)
    )
    show_stylized: BoolProperty(
        name="Stylized",
        default=True,
        description="Toggle between base mesh and stylized view"
    )

    def apply(self, obj):
        apply_stylized_rock_modifiers(obj, self)

    def bake(self, obj, context):
        baked = obj.copy()
        baked.data = obj.data.copy()
        baked.name = obj.name + "_dynamic"
        context.collection.objects.link(baked)
        baked.hide_viewport = True

        for mod in obj.modifiers:
            bpy.ops.object.modifier_apply(modifier=mod.name)

        return baked

def apply_preset(props):
    data = PRESETS.get(props.preset)
    if data:
        props.displace_strength_1 = data["displace_strength_1"]
        props.displace_strength_2 = data["displace_strength_2"]
        props.decimate_ratio = data["decimate_ratio"]
        props.subdivision_level = data["subdivision_level"]

def create_procedural_texture(name, size):
    tex = bpy.data.textures.get(name)
    if not tex:
        tex = bpy.data.textures.new(name=name, type='MUSGRAVE')

    tex.musgrave_type = 'MULTIFRACTAL'
    tex.noise_basis = 'VORONOI_F2_F1'
    tex.noise_scale = size
    tex.nabla = 0.03
    tex.dimension_max = 1.0
    tex.lacunarity = 2.0
    tex.octaves = 2.0
    tex.intensity = 1.0

    tex.use_clamp = True
    tex.use_color_ramp = True
    tex.color_ramp.interpolation = 'EASE'
    tex.color_ramp.color_mode = 'RGB'

    ramp = tex.color_ramp
    while len(ramp.elements) > 1:
        ramp.elements.remove(ramp.elements[0])

    if len(ramp.elements) == 1:
        ramp.elements[0].position = 0.0
        ramp.elements[0].color = (0.0, 0.0, 0.0, 0.0)
    else:
        ramp.elements.new(0.0).color = (0.0, 0.0, 0.0, 0.0)

    def add_color_stop(pos, hex_color):
        r, g, b, a = [int(hex_color[i:i+2], 16) / 255 for i in (1, 3, 5, 7)]
        e = ramp.elements.new(pos)
        e.color = (r, g, b, a)

    add_color_stop(0.245, "#EFEFEF80")
    add_color_stop(1.000, "#FFFFFFFF")

    return tex

def apply_stylized_rock_modifiers(obj, props):
    for mod in obj.modifiers:
        if mod.name.startswith("Stylized_"):
            obj.modifiers.remove(mod)

    tex1 = create_procedural_texture("baseno1", size=4.0)
    tex2 = create_procedural_texture("seconddispno2", size=3.0)

    mod = obj.modifiers.new("Stylized_Subdivision", type='SUBSURF')
    mod.levels = int(props.subdivision_level)
    mod.render_levels = int(props.subdivision_level)

    mod = obj.modifiers.new("Stylized_Displace1", type='DISPLACE')
    mod.strength = props.displace_strength_1
    mod.texture = tex1
    mod.texture_coords = 'LOCAL'

    mod = obj.modifiers.new("Stylized_Displace2", type='DISPLACE')
    mod.strength = props.displace_strength_2
    mod.texture = tex2
    mod.texture_coords = 'LOCAL'

    mod = obj.modifiers.new("Stylized_Decimate1", type='DECIMATE')
    mod.decimate_type = 'COLLAPSE'
    mod.ratio = props.decimate_ratio
    mod.use_collapse_triangulate = True

    mod = obj.modifiers.new("Stylized_Decimate2", type='DECIMATE')
    mod.decimate_type = 'DISSOLVE'
    mod.angle_limit = 15 * (3.14159265 / 180.0)
    mod.use_dissolve_boundaries = True

    mod = obj.modifiers.new("Stylized_Smooth", type='SMOOTH')
    mod.factor = 0.5
    mod.iterations = 4

    mod = obj.modifiers.new("Stylized_Bevel", type='BEVEL')
    mod.limit_method = 'ANGLE'
    mod.angle_limit = 20 * (3.14159265 / 180.0)
    mod.offset_type = 'PERCENT'
    mod.width = 0.10
    mod.segments = 1
    mod.profile = 0.5
    mod.miter_outer = mod.miter_inner = 'MITER_SHARP'
    mod.loop_slide = True

    mod = obj.modifiers.new("Stylized_WeightedNormal", type='WEIGHTED_NORMAL')
    mod.weight = 50
    mod.mode = 'FACE_AREA'

    mod = obj.modifiers.new("Stylized_Triangulate", type='TRIANGULATE')
    mod.quad_method = 'SHORTEST_DIAGONAL'
    mod.ngon_method = 'BEAUTY'

    mod = obj.modifiers.new("Stylized_FinalDecimate", type='DECIMATE')
    mod.decimate_type = 'COLLAPSE'
    mod.ratio = 0.7

def toggle_modifier_states(obj, enable):
    for mod in obj.modifiers:
        if mod.name.startswith("Stylized_"):
            mod.show_viewport = enable

class OBJECT_OT_add_rock_modifiers(bpy.types.Operator):
    bl_idname = "object.stylized_rock_modifiers"
    bl_label = "Apply Stylized Rock Modifiers"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Active object must be a mesh")
            return {'CANCELLED'}

        props = context.scene.stylized_rock_props
        apply_stylized_rock_modifiers(obj, props)
        return {'FINISHED'}

class OBJECT_OT_toggle_stylized_mode(bpy.types.Operator):
    bl_idname = "object.toggle_stylized_mode"
    bl_label = "Toggle Stylized/Base Mesh"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj:
            return {'CANCELLED'}
        props = context.scene.stylized_rock_props
        toggle_modifier_states(obj, props.show_stylized)
        props.show_stylized = not props.show_stylized
        return {'FINISHED'}

class OBJECT_OT_bake_stylized_mesh(bpy.types.Operator):
    bl_idname = "object.bake_stylized_mesh"
    bl_label = "Bake Mesh"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Active object must be a mesh")
            return {'CANCELLED'}

        baked = obj.copy()
        baked.data = obj.data.copy()
        baked.name = obj.name + "_dynamic"
        context.collection.objects.link(baked)
        baked.hide_viewport = True

        for mod in obj.modifiers:
            bpy.ops.object.modifier_apply(modifier=mod.name)

        return {'FINISHED'}

class OBJECT_PT_stylized_rock_panel(bpy.types.Panel):
    bl_label = "Stylized Rock Generator"
    bl_idname = "OBJECT_PT_stylized_rock_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Stylized Rock"

    def draw(self, context):
        layout = self.layout
        props = context.scene.stylized_rock_props

        layout.prop(props, "preset")
        layout.prop(props, "displace_strength_1")
        layout.prop(props, "displace_strength_2")
        layout.prop(props, "decimate_ratio")
        layout.prop(props, "subdivision_level")

        layout.operator("object.stylized_rock_modifiers", text="Apply Modifiers")
        layout.operator("object.bake_stylized_mesh", text="Bake Mesh")
        layout.operator("object.toggle_stylized_mode", text="Toggle Stylized/Base")

def register():
    bpy.utils.register_class(StylizedRockProperties)
    bpy.types.Scene.stylized_rock_props = PointerProperty(type=StylizedRockProperties)
    bpy.utils.register_class(OBJECT_OT_add_rock_modifiers)
    bpy.utils.register_class(OBJECT_OT_bake_stylized_mesh)
    bpy.utils.register_class(OBJECT_OT_toggle_stylized_mode)
    bpy.utils.register_class(OBJECT_PT_stylized_rock_panel)

def unregister():
    bpy.utils.unregister_class(OBJECT_PT_stylized_rock_panel)
    bpy.utils.unregister_class(OBJECT_OT_toggle_stylized_mode)
    bpy.utils.unregister_class(OBJECT_OT_bake_stylized_mesh)
    bpy.utils.unregister_class(OBJECT_OT_add_rock_modifiers)
    del bpy.types.Scene.stylized_rock_props
    bpy.utils.unregister_class(StylizedRockProperties)

if __name__ == "__main__":
    register()
