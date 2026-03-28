from sympy import symbols
from sympy.geometry import Plane, Point3D, Ray3D
from sympy.matrices import Matrix
from sympy.physics.optics import deviation


class TestPhysicsOpticsDeviationRefractionCaughtExceptionKindsQA:
    def test_physics_optics_deviation_refraction_caught_exception_kinds_case(self):
        n1, n2 = symbols("n1 n2")
        ray = Ray3D(Point3D(-1, -1, 1), Point3D(0, 0, 0))
        normal = Matrix([0, 0, 1])
        plane = Plane(Point3D(0, 0, 0), normal_vector=[0, 0, 1])

        outputs = [
            deviation(ray, 1, 2, normal=normal),
            deviation(ray, n1, n2, plane=plane),
        ]

        assert len(outputs) == 2
        assert outputs[0] != outputs[1]
