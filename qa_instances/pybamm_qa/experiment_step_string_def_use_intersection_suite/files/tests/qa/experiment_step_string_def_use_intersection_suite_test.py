from __future__ import annotations

import math

import pybamm

from pybamm.experiment.step.steps import string


class TestExperimentStepStringDefUseIntersectionQA:
    def _assert_step(self, step, cls, value, duration=None, n_termination=0):
        assert isinstance(step, cls)
        assert math.isclose(float(step.value), value)
        if duration is not None:
            assert math.isclose(float(step.duration), duration)
        assert len(step.termination) == n_termination
        assert step.description == str(step)

    def test_case_01(self):
        step = string("Discharge at 1 A for 10 seconds")
        self._assert_step(step, pybamm.step.Current, 1.0, duration=10.0)

    def test_case_02(self):
        step = string("Charge at 500 mA for 2 minutes")
        self._assert_step(step, pybamm.step.Current, -0.5, duration=120.0)

    def test_case_03(self):
        step = string("Discharge at C/2 for 1 hour")
        self._assert_step(step, pybamm.step.CRate, 0.5, duration=3600.0)

    def test_case_04(self):
        step = string("Charge at 0.25 C for 30 minutes")
        self._assert_step(step, pybamm.step.CRate, -0.25, duration=1800.0)

    def test_case_05(self):
        step = string("Discharge at 2 W for 45 seconds")
        self._assert_step(step, pybamm.step.Power, 2.0, duration=45.0)

    def test_case_06(self):
        step = string("Charge at 250 mW for 3 minutes")
        self._assert_step(step, pybamm.step.Power, -0.25, duration=180.0)

    def test_case_07(self):
        step = string("Hold at 4.1 V until 50 mA")
        self._assert_step(step, pybamm.step.Voltage, 4.1, n_termination=1)

    def test_case_08(self):
        step = string("Discharge at 0.8 Ohm for 4 minutes")
        self._assert_step(step, pybamm.step.Resistance, 0.8, duration=240.0)

    def test_case_09(self):
        step = string("Charge at 3 A for 20 seconds or until 4.2 V")
        self._assert_step(
            step, pybamm.step.Current, -3.0, duration=20.0, n_termination=1
        )

    def test_case_10(self):
        step = string("Discharge at 750 mA for 90 seconds (15 seconds period)")
        self._assert_step(step, pybamm.step.Current, 0.75, duration=90.0)
        assert math.isclose(float(step.period), 15.0)
