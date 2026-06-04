from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pybamm


class TestExperimentInitCallCoverageQA:
    def _make(self, case):
        start = datetime(2025, 1, 1, 8, 0)
        cases = {
            1: (
                ["Discharge at 1 C for 10 minutes", "Rest for 5 minutes"],
                {"termination": ["80% capacity", "2.5 V"]},
            ),
            2: (
                [("Charge at 0.5 C until 4.1 V", "Hold at 4.1 V until C/20")],
                {"period": "30 seconds", "temperature": "25 oC"},
            ),
            3: (
                [
                    pybamm.step.current(1.2, duration="2 minutes", termination="3 V", tags=["pulse"]),
                    pybamm.step.voltage(4.0, duration="1 minute", tags=["hold"]),
                ],
                {"termination": "1 hour"},
            ),
            4: (
                [
                    pybamm.step.power(3, duration="2 minutes"),
                    pybamm.step.resistance(4, duration="1 minute"),
                    pybamm.step.rest("20 seconds"),
                ],
                {"termination": "4 A.h capacity"},
            ),
            5: (
                [
                    pybamm.step.current(1, duration="1 minute", start_time=start),
                    pybamm.step.rest("30 seconds", start_time=start + timedelta(minutes=2)),
                ],
                {},
            ),
            6: (
                [("Discharge at C/3 for 20 minutes", "Rest for 2 minutes")] * 2,
                {"period": "10 seconds", "termination": "75% capacity"},
            ),
            7: (
                [
                    pybamm.step.c_rate(-0.4, duration="3 minutes", temperature="30 oC"),
                    "Rest for 1 minute",
                    "Discharge at 2 A until 3.2 V",
                ],
                {"temperature": 299.15},
            ),
            8: (
                [
                    pybamm.step.current(
                        np.array([[0, 0], [60, 1], [120, 0], [240, -1]])
                    ),
                    pybamm.step.voltage(3.8, duration="2 minutes", termination="C/50"),
                ],
                {"termination": ["3.0 V", "2 hours"]},
            ),
            9: (
                [
                    "Charge at 1 A for 30 seconds",
                    "Charge at 1 A for 30 seconds",
                    pybamm.step.rest("15 seconds", tags=["duplicate"]),
                ],
                {"period": "5 seconds"},
            ),
            10: (
                [
                    (
                        pybamm.step.power(-2.5, duration="90 seconds", tags=["cycle"]),
                        pybamm.step.resistance(5.5, duration="45 seconds"),
                    ),
                    "Rest for 30 seconds",
                ],
                {"temperature": "20 oC", "termination": ["2.8 V", "3 Ah capacity"]},
            ),
        }
        operations, kwargs = cases[case]
        experiment = pybamm.Experiment(operations, **kwargs)
        assert len(experiment.steps) >= 2
        assert len(experiment.unique_steps) >= 1
        return experiment

    def test_case_01(self): assert self._make(1).termination
    def test_case_02(self): assert len(self._make(2).cycles) == 1
    def test_case_03(self): assert self._make(3).termination["time"] == 3600
    def test_case_04(self): assert self._make(4).termination["capacity"][1] == "Ah"
    def test_case_05(self): assert self._make(5).initial_start_time is not None
    def test_case_06(self): assert len(self._make(6).cycles) == 2
    def test_case_07(self): assert self._make(7).temperature == 299.15
    def test_case_08(self): assert len(self._make(8).termination) == 2
    def test_case_09(self): assert len(self._make(9).steps) == 3
    def test_case_10(self): assert len(self._make(10).termination) == 2
