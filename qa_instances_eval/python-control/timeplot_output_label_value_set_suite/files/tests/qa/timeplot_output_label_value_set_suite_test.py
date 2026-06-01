import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from control.timeplot import time_response_plot
from control.timeresp import TimeResponseData


def _data(name, outputs, traces, *, output_labels=None, trace_labels=None):
    time = np.array([0.0, 0.5, 1.0, 1.5])
    base = np.arange(outputs * traces * time.size, dtype=float)
    y = (base.reshape(outputs, traces, time.size) + 1.0) / (outputs + traces)
    return TimeResponseData(
        time, y, multi_trace=True, output_labels=output_labels,
        trace_labels=trace_labels, sysname=name, plot_inputs=False,
        issiso=(outputs == 1 and traces <= 1))


def _plot(data, **kwargs):
    cplt = time_response_plot(data, plot_inputs=False, **kwargs)
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


class TestTimePlotLabelValueSetQA:
    def test_case_01(self):
        data = _data("case_01_resp", 1, 1, output_labels=["alt"])
        assert _plot(data, overlay_signals=True, overlay_traces=True) == [
            "alt, case_01_resp"]

    def test_case_02(self):
        data = _data(
            "case_02_resp", 2, 1, output_labels=["speed", "angle"])
        assert len(_plot(data, overlay_signals=True, overlay_traces=True)) == 2

    def test_case_03(self):
        data = _data(
            "case_03_resp", 1, 3, output_labels=["temp"],
            trace_labels=["low", "mid", "high"])
        assert len(_plot(data, overlay_signals=True, overlay_traces=True)) == 3

    def test_case_04(self):
        data = _data(
            "case_04_resp", 2, 2, output_labels=["roll", "yaw"],
            trace_labels=["left", "right"])
        assert len(_plot(data, overlay_signals=True, overlay_traces=True)) == 4

    def test_case_05(self):
        data = _data(
            "case_05_resp", 3, 1, output_labels=["north", "east", "down"])
        assert len(_plot(data, overlay_signals=True, overlay_traces=False)) == 3

    def test_case_06(self):
        data = _data(
            "case_06_resp", 1, 2, output_labels=["mix"],
            trace_labels=["warm", "cool"])
        assert _plot(data, overlay_signals=False, overlay_traces=True) == [
            "warm, case_06_resp", "cool, case_06_resp"]

    def test_case_07(self):
        data = _data(
            "case_07_resp", 2, 2, output_labels=["height", "rate"])
        assert len(_plot(data, overlay_signals=True, overlay_traces=True)) == 4

    def test_case_08(self):
        data = _data(
            "case_08_resp", 2, 3, output_labels=["alpha", "beta"],
            trace_labels=["red", "green", "blue"])
        assert len(_plot(data, overlay_signals=True, overlay_traces=True)) == 6

    def test_case_09(self):
        data = _data(
            "case_09_resp", 1, 2, output_labels=["bearing"],
            trace_labels=["east", "west"])
        assert len(_plot(data, overlay_signals=True, overlay_traces=True)) == 2

    def test_case_10(self):
        data = _data(
            "case_10_resp", 3, 2, output_labels=["inner", "outer", "total"],
            trace_labels=["first", "second"])
        assert len(_plot(data, overlay_signals=True, overlay_traces=True)) == 6
