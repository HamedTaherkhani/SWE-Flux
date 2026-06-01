import numpy as np
import pytest

from control.frdata import FRD, FrequencyResponseData, _convert_to_frd
from control.statesp import ss
from control.xferfcn import tf


def _omega():
    return np.array([0.4, 1.2, 2.5, 5.0])


def _mimo_response():
    omega = _omega()
    data = np.empty((2, 2, len(omega)), dtype=complex)
    data[0, 0, :] = 1.0 / (1.0 + 1j * omega)
    data[0, 1, :] = 0.2 + 0.1j * omega
    data[1, 0, :] = -0.3j / (1.0 + omega)
    data[1, 1, :] = 2.0 / (2.0 + 1j * omega)
    return data


class TestConvertExistingMatchingFRDQA:
    def test_existing_frd_is_returned_after_frequency_sort(self):
        omega = _omega()
        sys = FRD([1.0 + 0.1j, 0.7 + 0.2j, 0.4 + 0.3j, 0.2 + 0.4j], omega)
        out = _convert_to_frd(sys, omega.copy())
        assert out is sys


class TestConvertExistingMismatchedFRDQA:
    def test_existing_frd_with_different_grid_rejected(self):
        sys = FRD([1.0, 0.5, 0.25], [0.5, 1.0, 2.0])
        with pytest.raises(NotImplementedError):
            _convert_to_frd(sys, np.array([0.5, 1.5, 2.0]))


class TestConvertContinuousTransferFunctionQA:
    def test_continuous_transfer_function_samples_to_smooth_frd(self):
        plant = tf([2.0, 1.0], [1.0, 3.0, 2.0])
        out = _convert_to_frd(plant, _omega())
        assert isinstance(out, FrequencyResponseData)
        assert out.frdata.shape == (1, 1, 4)
        assert out._ifunc is not None


class TestConvertDiscreteStateSpaceQA:
    def test_discrete_state_space_uses_dt_frequency_map(self):
        plant = ss([[0.6, 0.1], [0.0, 0.2]], [[1.0], [0.5]], [[1.0, 0.0]], [[0.0]], dt=0.2)
        out = _convert_to_frd(plant, _omega())
        assert isinstance(out, FRD)
        assert out.frdata.shape == (1, 1, 4)


class TestConvertScalarSISOQA:
    def test_scalar_to_siso_frd(self):
        out = _convert_to_frd(2.5, _omega())
        assert out.frdata.shape == (1, 1, 4)
        assert np.allclose(out.frdata, 2.5)


class TestConvertScalarMIMOQA:
    def test_scalar_to_requested_mimo_dimensions(self):
        out = _convert_to_frd(-1.25, _omega(), inputs=3, outputs=2)
        assert out.frdata.shape == (2, 3, 4)
        assert np.allclose(out.frdata[:, :, 0], -1.25)


class TestConvertComplexScalarQA:
    def test_complex_scalar_keeps_complex_values(self):
        out = _convert_to_frd(1.0 - 0.5j, _omega(), inputs=2, outputs=1)
        assert out.frdata.shape == (1, 2, 4)
        assert np.allclose(out.frdata[0, 1, -1], 1.0 - 0.5j)


class TestConvertConstantMatrixQA:
    def test_constant_matrix_to_mimo_frd(self):
        gain = np.array([[1.0, -2.0], [0.5, 3.0]])
        out = _convert_to_frd(gain, _omega())
        assert out.frdata.shape == (2, 2, 4)
        assert np.allclose(out.frdata[:, :, 2], gain)


class TestConvertListMatrixQA:
    def test_nested_list_matrix_conversion(self):
        out = _convert_to_frd([[1.0, 0.0, -1.0]], _omega())
        assert out.frdata.shape == (1, 3, 4)
        assert np.allclose(out.frdata[0, :, 1], [1.0, 0.0, -1.0])


class TestConvertUnsupportedTypeQA:
    def test_unconvertible_object_rejected(self):
        class NotASystem:
            pass

        with pytest.raises(TypeError):
            _convert_to_frd(NotASystem(), _omega())
