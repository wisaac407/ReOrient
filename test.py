import unittest
import bpy
from bpy_extras.object_utils import object_data_add
from mathutils import Matrix, Vector
from math import pi


def add_object(context, transform):
    # Cube geometry
    verts = [
        Vector((-1, 1, -1)),
        Vector((1, 1, -1)),
        Vector((1, -1, -1)),
        Vector((-1, -1, -1)),

        Vector((-1, 1, 1)),
        Vector((1, 1, 1)),
        Vector((1, -1, 1)),
        Vector((-1, -1, 1)),
    ]
    edges = []
    faces = [
        [3, 2, 1, 0],
        [7, 6, 5, 4],
        [4, 5, 1, 0],
        [5, 6, 2, 1],
        [6, 7, 3, 2],
        [4, 7, 3, 0]
    ]

    new_verts = []
    for vert in verts:
        new_vert = transform @ vert.to_4d()

        new_verts.append(new_vert.to_3d() / new_vert[3])

    mesh = bpy.data.meshes.new(name="Test Mesh")
    mesh.from_pydata(new_verts, edges, faces)

    # useful for development when the mesh may be invalid.
    mesh.calc_normals()
    mesh.validate(verbose=True)
    return object_data_add(context, mesh)


def get_world_transform():
    rotate = Matrix.Rotation(pi / 4, 4, 'Z')
    return rotate


def get_transform(world_transform):
    scale_x = Matrix.Scale(2, 4, Vector((1, 0, 0)))
    scale_y = Matrix.Scale(0.5, 4, Vector((0, 1, 0)))
    scale_z = Matrix.Scale(0.5, 4, Vector((0, 0, 1)))

    perspective = Matrix()
    perspective[3][2] = -0.5

    transform = world_transform @ perspective @ scale_x @ scale_y @ scale_z

    return transform


def compare_matrix(m1, m2, error=0.0001):
    for i in range(4):
        for j in range(4):
            if abs(m1[i][j] - m2[i][j]) > error:
                return False
    return True


class Context:
    space_data = bpy.data.screens['Layout'].areas[3].spaces[0]
    scene = bpy.data.scenes['Scene']

    def __getattr__(self, item):
        return getattr(bpy.context, item)


class TestReOrientOperator(unittest.TestCase):
    def test_run(self):
        transform = get_world_transform()
        obj = add_object(Context(), get_transform(transform))

        bpy.ops.object.orient_to_largest_face({'selected_objects': [
            obj
        ]})

        obj.matrix_world @= transform.inverted()

        # allow for the object to be rotated 180 degrees
        passes = compare_matrix(obj.matrix_world, Matrix()) or \
                 compare_matrix(obj.matrix_world, Matrix.Rotation(pi, 4, 'Z'))

        self.assertTrue(passes)


if __name__ == '__main__':
    import os
    import sys
    sys.path.append(os.getcwd())
    reorient = __import__("re-orient")
    reorient.register()

    try:
        argv = sys.argv[sys.argv.index('--') + 1:]
    except ValueError:
        argv = []

    argv.insert(0, 'test.py')

    unittest.main(argv=argv)
