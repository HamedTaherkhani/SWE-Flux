from __future__ import annotations

import numpy as np
import pytest

from control.exception import ControlMIMONotImplemented
from control.frdata import FrequencyResponseData
from control.margins import margin, phase_crossover_frequencies, stability_margins
from control.statesp import StateSpace
from control.xferfcn import TransferFunction


S = TransferFunction.s


class TestMarginsContinuousPolynomialQA:
    def test_continuous_polynomial_default(self):
        sys = TransferFunction([1.0], [1.0, 2.0, 3.0, 4.0])
        gm, pm, sm, wpc, wgc, wms = stability_margins(sys)

        assert gm > 0
        assert np.isfinite(sm)
        assert np.isfinite(wpc)
        assert np.isnan(wgc) or wgc >= 0


class TestMarginsContinuousReturnAllQA:
    def test_continuous_returnall_with_eps(self):
        sys = 8.75 * (4 * S**2 + 0.4 * S + 1) / (
            (100 * S + 1) * (S**2 + 0.22 * S + 1)
        ) / (S**2 / 10.0**2 + 2 * 0.04 * S / 10.0 + 1)
        margins = stability_margins(sys, returnall=True, epsw=1e-4)

        assert len(margins) == 6
        assert all(np.asarray(part).ndim <= 1 for part in margins)


class TestMarginsStateSpaceConversionQA:
    def test_state_space_input_is_converted(self):
        sys = StateSpace(
            [[1.0, 4.0], [3.0, 2.0]],
            [[1.0], [-4.0]],
            [[1.0, 0.0]],
            [[0.0]],
        )
        margins = stability_margins(sys, method="poly")

        assert len(margins) == 6
        assert margins[1] > 0


class TestMarginsFrequencyTupleQA:
    def test_mag_phase_omega_tuple_input(self):
        sys = TransferFunction(15.0, [1.0, 6.0, 11.0, 6.0])
        omega = np.logspace(-2, 2, 500)
        mag, phase, omega_out = sys.frequency_response(omega)
        margins = stability_margins((mag, phase * 180.0 / np.pi, omega_out))

        assert len(margins) == 6
        assert margins[0] > 0


class TestMarginsFrequenciesDataQA:
    def test_frequency_response_data_input(self):
        omega = np.linspace(0.9, 2.1, 17)
        magnitude = 0.55 + 0.7 * np.exp(-((omega - 1.5) ** 2) / 0.08)
        phase = -90.0 - 130.0 * (omega - omega.min()) / (omega.max() - omega.min())
        response = magnitude * np.exp(1j * np.pi / 180.0 * phase)
        frd = FrequencyResponseData(response, omega)
        margins = stability_margins(frd, returnall=True)

        assert len(margins) == 6
        assert all(np.asarray(part).ndim <= 1 for part in margins)


class TestMarginsForcedFrdMethodQA:
    def test_transfer_function_forced_frd_method_exception_path(self):
        sys = (S + 0.2) / ((S + 1) * (S + 3) * (S + 5))

        with pytest.raises(ValueError, match="not all frequencies"):
            stability_margins(sys, method="frd")


class TestMarginsDiscretePolynomialQA:
    def test_discrete_transfer_function_poly_method(self):
        sys = TransferFunction([0.3, -0.05], [1.0, -1.2, 0.35], 0.2)
        margins = stability_margins(sys, method="poly", returnall=True)

        assert len(margins) == 6
        assert all(np.asarray(part).ndim <= 1 for part in margins)


class TestMarginsBestDiscreteQA:
    def test_discrete_best_method_runs_accuracy_check(self):
        sys = TransferFunction([1e-6, 2e-6], [1.0, -1.85, 0.86], 0.1)
        with pytest.warns(UserWarning, match="Falling back"):
            margins = stability_margins(sys, method="best")

        assert len(margins) == 6
        assert np.isinf(margins[0]) or margins[0] > 0


class TestMarginsWrapperQA:
    def test_margin_wrapper_calls_stability_margins(self):
        sys = TransferFunction([2.0], [1.0, 3.0, 2.0, 0.0])
        gm, pm, wpc, wgc = margin(sys)

        assert gm > 0 or np.isinf(gm)
        assert np.isfinite(pm) or np.isinf(pm)
        assert np.isnan(wpc) or wpc >= 0
        assert np.isnan(wgc) or wgc >= 0


class TestMarginsExceptionPathsQA:
    def test_exception_paths_are_caught(self):
        mimo = TransferFunction(
            [[[1.0], [2.0]], [[3.0], [4.0]]],
            [[[1.0, 1.0], [1.0, 2.0]], [[1.0, 3.0], [1.0, 4.0]]],
        )

        with pytest.raises(ControlMIMONotImplemented):
            stability_margins(mimo)

        with pytest.raises(ValueError, match="unknown"):
            stability_margins(TransferFunction([1.0], [1.0, 1.0]), method="bogus")

        omega, gains = phase_crossover_frequencies(
            TransferFunction([1.0], [1.0, 2.0, 3.0, 4.0]))
        assert omega.ndim == 1
        assert gains.ndim == 1
