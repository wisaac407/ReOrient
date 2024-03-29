from bpy.props import EnumProperty
import bpy
import bmesh
from math import pi
from mathutils import Vector, Matrix


###### Utilities ######
class create_bmesh(object):
    def __init__(self, mesh):
        self.bm = bmesh.new()
        self.mesh = mesh

    def __enter__(self):
        self.bm.from_mesh(self.mesh)
        return self.bm

    def __exit__(self, type, value, traceback):
        self.bm.to_mesh(self.mesh)
        self.bm.free()


class create_edit_bmesh(object):
    def __init__(self, mesh):
        self.bm = None
        self.mesh = mesh

    def __enter__(self):
        self.bm = bmesh.from_edit_mesh(self.mesh)
        return self.bm

    def __exit__(self, type, value, traceback):
        bmesh.update_edit_mesh(self.mesh)


def create_general_bmesh(context, mesh):
    if context.mode == 'EDIT_MESH':
        return create_edit_bmesh(mesh)
    else:
        return create_bmesh(mesh)


# Old version!
def _get_rotation_matrix(obj):
    """
    Return the rotation matrix that correctly aligns the objects.
    
    The objects are aligned by axis in this order:
        longest axis  -> y
        middle axis   -> x
        shortest axis -> z
    """
    rot = Matrix()
    dimx, dimy, dimz = obj.dimensions

    # First find the correct y axis
    if dimx > dimy and dimx > dimz:
        rot @= Matrix.Rotation(pi / 2, 4, 'Z')
        dimx, dimy = dimy, dimx

    elif dimz > dimy and dimz > dimx:
        rot @= Matrix.Rotation(pi / 2, 4, 'X')
        dimy, dimz = dimz, dimy

    if dimx < dimz:
        rot @= Matrix.Rotation(pi / 2, 4, 'Y')

    return rot


def get_rotation_matrix(obj, long_axis='Y', short_axis='Z'):
    """
    Return the rotation matrix that correctly aligns the objects.
    
    The objects are aligned by axis in this order:
        longest axis  -> long_axis(Y by default)
        middle axis   -> not long_axis or short_axis(X by default)
        shortest axis -> short_axis(Z by default)
    """
    rot = Matrix()
    dimx, dimy, dimz = obj.dimensions

    # TODO: This code isn't very DRY, find a way to make it more concise and elegant.
    if long_axis == 'X':
        if dimy > dimx and dimy > dimz:
            rot @= Matrix.Rotation(pi / 2, 4, 'Z')
            dimx, dimy = dimy, dimx

        elif dimz > dimy and dimz > dimx:
            rot @= Matrix.Rotation(pi / 2, 4, 'Y')
            dimx, dimz = dimz, dimx

        # Find the short axis
        if short_axis == 'Y':
            if dimz < dimy:
                rot @= Matrix.Rotation(pi / 2, 4, 'X')

        else:  # Assume Z (the long and short axis can't be the same)
            if dimy < dimz:
                rot @= Matrix.Rotation(pi / 2, 4, 'X')

    elif long_axis == 'Y':
        if dimx > dimy and dimx > dimz:
            rot @= Matrix.Rotation(pi / 2, 4, 'Z')
            dimx, dimy = dimy, dimx

        elif dimz > dimy and dimz > dimx:
            rot @= Matrix.Rotation(pi / 2, 4, 'X')
            dimy, dimz = dimz, dimy

        # Find the short axis
        if short_axis == 'X':
            if dimz < dimx:
                rot @= Matrix.Rotation(pi / 2, 4, 'Y')

        else:  # Assume Z (the long and short axis can't be the same)
            if dimx < dimz:
                rot @= Matrix.Rotation(pi / 2, 4, 'Y')

    else:  # Assume Z
        if dimx > dimy and dimx > dimz:
            rot @= Matrix.Rotation(pi / 2, 4, 'Y')
            dimx, dimz = dimz, dimx

        elif dimy > dimz and dimy > dimx:
            rot @= Matrix.Rotation(pi / 2, 4, 'X')
            dimy, dimz = dimz, dimy

        # Find the short axis
        if short_axis == 'X':
            if dimz < dimx:
                rot @= Matrix.Rotation(pi / 2, 4, 'Z')

        else:  # Assume Y (the long and short axis can't be the same)
            if dimx < dimy:
                rot @= Matrix.Rotation(pi / 2, 4, 'Z')

    return rot


def orient_to_largest_face(ctx, ob):
    with create_general_bmesh(ctx, ob.data) as bm:
        bm.faces.ensure_lookup_table()
        # Find the face that has the largest area
        f = max(bm.faces, key=(lambda x: x.calc_area()))

        n = f.normal

        t = f.calc_tangent_edge_pair()
        t.normalize()

        u = n.cross(t)

        mat = Matrix((
            (t.x, u.x, n.x),
            (t.y, u.y, n.y),
            (t.z, u.z, n.z)
        )).to_4x4()

        ob.matrix_world @= mat

        bm.transform(mat.inverted())
        bm.normal_update()


class ReOrientOperator(bpy.types.Operator):
    """Align the selected objects so that the y is the longest dimension"""
    bl_idname = "object.reorient"
    bl_label = "Re-Orient Objects"
    bl_options = {'REGISTER', 'UNDO'}

    long_axis: EnumProperty(
        items=[
            ('X', 'X', 'X Axis', 0),
            ('Y', 'Y', 'Y Axis', 1),
            ('Z', 'Z', 'Z Axis', 2)
        ],
        default='Y',
        name="Long Axis",
        description="The axis for the longest dimension"
    )

    short_axis: EnumProperty(
        items=[
            ('X', 'X', 'X Axis', 0),
            ('Y', 'Y', 'Y Axis', 1),
            ('Z', 'Z', 'Z Axis', 2)
        ],
        default='Z',
        name="Short Axis",
        description="The axis for the shortest dimension"
    )

    @classmethod
    def poll(cls, context):
        return len(context.selected_objects) > 0

    def execute(self, context):
        for obj in context.selected_objects:
            matrix = get_rotation_matrix(obj, self.long_axis, self.short_axis)

            obj.matrix_world @= matrix

            with create_general_bmesh(context, obj.data) as bm:
                bm.transform(matrix.inverted())
                bm.normal_update()

        return {'FINISHED'}


class OrientToLargestFaceOperator(bpy.types.Operator):
    """Align the selected objects to the normal of their first face (works best on cubes and planes)"""
    bl_idname = "object.orient_to_largest_face"
    bl_label = "Orient Objects To Largest Face"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(context.selected_objects) > 0

    def execute(self, context):
        for obj in context.selected_objects:
            orient_to_largest_face(context, obj)

        return {'FINISHED'}


classes = (
    ReOrientOperator,
    OrientToLargestFaceOperator
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == '__main__':
    register()
