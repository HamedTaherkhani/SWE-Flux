import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from control.freqplot import bode_plot
from control.statesp import ss


OMEGA = np.array([0.7, 1.4, 2.8, 5.6])


def _static(name, matrix, inputs=None, outputs=None, dt=None):
    return ss([], [], [], matrix, dt=dt, name=name, inputs=inputs, outputs=outputs)


def _plot(data, **kwargs):
    cplt = bode_plot(
        data, omega=OMEGA, plot_phase=False, dB=False,
        share_frequency=False, **kwargs)
    labels = [
        line.get_label()
        for ax in np.ravel(cplt.axes)
        if ax is not None
        for line in ax.get_lines()
        if not line.get_label().startswith("_")
    ]
    assert labels
    plt.close("all")
    return labels


class TestBodeLabelValueSetQA:
    def test_case_01(self):
        sys = _static("case_01_sys", [[1.0]])
        assert _plot(sys, overlay_outputs=True, overlay_inputs=True) == ["case_01_sys"]

    def test_case_02(self):
        sys = _static(
            "case_02_sys", [[1.0], [2.0]],
            inputs=["cmd"], outputs=["speed", "angle"])
        labels = _plot(sys, overlay_outputs=True, overlay_inputs=True)
        assert len(labels) == 2

    def test_case_03(self):
        sys = _static(
            "case_03_sys", [[1.0, -0.5]],
            inputs=["left", "right"], outputs=["sum"])
        labels = _plot(sys, overlay_outputs=True, overlay_inputs=True)
        assert len(labels) == 2

    def test_case_04(self):
        sys = _static(
            "case_04_sys", [[1.0, 0.2], [-0.4, 1.5]],
            inputs=["aileron", "rudder"], outputs=["roll", "yaw"])
        labels = _plot(sys, overlay_outputs=True, overlay_inputs=True)
        assert len(labels) == 4

    def test_case_05(self):
        sys = _static(
            "case_05_sys", [[0.5, 1.0], [1.5, -0.25]],
            inputs=["drive", "trim"], outputs=["north", "east"])
        labels = _plot(sys, overlay_outputs=False, overlay_inputs=True)
        assert sorted(set(labels)) == ["drive, case_05_sys", "trim, case_05_sys"]

    def test_case_06(self):
        sys = _static(
            "case_06_sys", [[1.0, -1.0], [0.3, 0.7]],
            inputs=["hot", "cold"], outputs=["mix", "waste"])
        labels = _plot(sys, overlay_outputs=True, overlay_inputs=False)
        assert sorted(set(labels)) == ["mix, case_06_sys", "waste, case_06_sys"]

    def test_case_07(self):
        sys_a = _static("case_07_a", [[1.0]])
        sys_b = _static("case_07_b", [[0.25]])
        labels = _plot([sys_a, sys_b], overlay_outputs=True, overlay_inputs=True)
        assert sorted(labels) == ["case_07_a", "case_07_b"]

    def test_case_08(self):
        sys_a = _static(
            "case_08_a", [[1.0], [0.5]],
            inputs=["force"], outputs=["height", "rate"])
        sys_b = _static(
            "case_08_b", [[-0.25], [1.25]],
            inputs=["force"], outputs=["height", "rate"])
        labels = _plot([sys_a, sys_b], overlay_outputs=True, overlay_inputs=True)
        assert len(labels) == 4

    def test_case_09(self):
        sys = _static(
            "case_09_sys", [[0.8, -0.1]],
            inputs=["east", "west"], outputs=["bearing"], dt=0.2)
        labels = _plot(sys, overlay_outputs=True, overlay_inputs=True)
        assert len(labels) == 2

    def test_case_10(self):
        sys = _static(
            "case_10_sys",
            [[1.0, 0.1], [0.2, 1.2], [-0.5, 0.4]],
            inputs=["inner", "outer"],
            outputs=["alpha", "beta", "gamma"],
        )
        labels = _plot(sys, overlay_outputs=True, overlay_inputs=True)
        assert len(labels) == 6
