import numpy as np
import pytest

from control.exception import ControlArgument, ControlDimension
from control.mateqn import care


def _stable_pair():
    A = np.array([[0.0, 1.0], [-2.0, -3.0]])
    B = np.array([[0.0], [1.0]])
    Q = np.diag([3.0, 1.0])
    R = np.array([[2.0]])
    return A, B, Q, R


class TestCareStandardScipyQA:
    def test_standard_continuous_riccati(self):
        A, B, Q, R = _stable_pair()
        X, L, G = care(A, B, Q, R, method="scipy")
        assert X.shape == (2, 2)
        assert L.shape == (2,)
        assert G.shape == (1, 2)


class TestCareDefaultRQA:
    def test_default_identity_r_path(self):
        A, B, Q, _ = _stable_pair()
        X, L, G = care(A, B, Q, method="scipy")
        assert np.allclose(X, X.T)
        assert len(L) == 2
        assert G.shape == (1, 2)


class TestCareGeneralizedWithSAndEQA:
    def test_generalized_descriptor_path(self):
        A, B, Q, R = _stable_pair()
        S = np.array([[0.05], [0.10]])
        E = np.array([[1.0, 0.05], [0.0, 1.2]])
        X, L, G = care(A, B, Q, R, S=S, E=E, method="scipy")
        assert X.shape == (2, 2)
        assert np.all(np.isfinite(np.real(L)))
        assert G.shape == (1, 2)


class TestCareGeneralizedOnlyEQA:
    def test_generalized_e_initializes_s(self):
        A, B, Q, R = _stable_pair()
        E = np.array([[1.1, 0.0], [0.0, 0.9]])
        X, L, G = care(A, B, Q, R, E=E, method="scipy")
        assert X.shape == (2, 2)
        assert L.shape == (2,)
        assert G.shape == (1, 2)


class TestCareGeneralizedOnlySQA:
    def test_generalized_s_initializes_e(self):
        A, B, Q, R = _stable_pair()
        S = np.array([[0.0], [0.2]])
        X, L, G = care(A, B, Q, R, S=S, method="scipy")
        assert X.shape == (2, 2)
        assert np.all(np.isfinite(G))


class TestCareMatrixLikeInputQA:
    def test_lists_are_reshaped_and_checked(self):
        X, L, G = care(
            [[0.0, 1.0], [-4.0, -2.5]],
            [[0.0], [2.0]],
            [[5.0, 0.25], [0.25, 2.0]],
            [[3.0]],
            method="scipy",
        )
        assert X.shape == (2, 2)
        assert L.shape == (2,)
        assert G.shape == (1, 2)


class TestCareNonstabilizingScipyQA:
    def test_nonstabilizing_rejected_for_scipy(self):
        A, B, Q, R = _stable_pair()
        with pytest.raises(ControlArgument):
            care(A, B, Q, R, stabilizing=False, method="scipy")


class TestCareNonsymmetricQQA:
    def test_nonsymmetric_q_rejected(self):
        A, B, _, R = _stable_pair()
        Q = np.array([[1.0, 2.0], [0.0, 1.0]])
        with pytest.raises(ControlArgument):
            care(A, B, Q, R, method="scipy")


class TestCareBadBDimensionQA:
    def test_incompatible_b_dimension_rejected(self):
        A, _, Q, R = _stable_pair()
        B = np.array([[1.0, 0.0, 0.5]])
        with pytest.raises(ControlDimension):
            care(A, B, Q, R, method="scipy")


class TestCareUnknownMethodQA:
    def test_unknown_method_rejected_before_shapes_finish(self):
        A, B, Q, R = _stable_pair()
        with pytest.raises(ControlArgument):
            care(A, B, Q, R, method="definitely-not-a-solver")
