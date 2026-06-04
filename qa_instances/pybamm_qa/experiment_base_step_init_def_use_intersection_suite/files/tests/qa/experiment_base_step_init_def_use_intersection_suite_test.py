from __future__ import annotations

from datetime import datetime
import math

import numpy as np
import pybamm


class TestBaseStepInitDefUseIntersectionQA:
    def test_case_01(self):
        step = pybamm.step.current(1.0, duration="10 seconds", tags="baseline")
        assert math.isclose(step.value, 1.0)
        assert math.isclose(step.duration, 10.0)
        assert step.tags == ["baseline"]

    def test_case_02(self):
        step = pybamm.step.c_rate(0.5, duration="2 minutes", period="5 seconds")
        assert math.isclose(step.value, 0.5)
        assert math.isclose(step.duration, 120.0)
        assert math.isclose(step.period, 5.0)

    def test_case_03(self):
        step = pybamm.step.voltage(4.1, duration="30 seconds", termination="50 mA")
        assert math.isclose(step.value, 4.1)
        assert len(step.termination) == 1

    def test_case_04(self):
        step = pybamm.step.power(2.5, duration="45 seconds", temperature="25 oC")
        assert math.isclose(step.value, 2.5)
        assert math.isclose(step.temperature, 298.15)

    def test_case_05(self):
        step = pybamm.step.resistance(0.8, duration="1 minute", direction="discharge")
        assert math.isclose(step.value, 0.8)
        assert step.direction == "discharge"

    def test_case_06(self):
        step = pybamm.step.rest(duration="15 seconds", start_time=datetime(2026, 1, 1))
        assert step.value == 0
        assert step.start_time == datetime(2026, 1, 1)

    def test_case_07(self):
        values = np.array([[0.0, 1.0], [2.0, -0.5], [4.0, 0.25]])
        step = pybamm.step.current(values, duration="8 seconds")
        assert step.value.name == "Drive Cycle"
        assert math.isclose(step.period, 2.0)

    def test_case_08(self):
        step = pybamm.step.current(lambda t: 2.0, duration="20 seconds")
        assert step.value == 2.0

    def test_case_09(self):
        step = pybamm.step.current(
            -1.0, duration="40 seconds", tags=["charge", "qa"], skip_ok=False
        )
        assert step.tags == ["charge", "qa"]
        assert step.skip_ok is False

    def test_case_10(self):
        step = pybamm.step.c_rate(
            -0.25,
            duration="3 minutes",
            termination=["4.2 V", "20 mA"],
            description="qa charge step",
        )
        assert str(step) == "qa charge step"
        assert len(step.termination) == 2
