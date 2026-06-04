from __future__ import annotations

import pybamm


class TestExperimentReadTerminationDefUseIntersectionQA:
    def _build(self, termination):
        experiment = pybamm.Experiment(
            ["Discharge at 1 A for 1 minute"], termination=termination
        )
        assert experiment.termination["capacity"][1] == "%"
        return experiment

    def test_case_01(self):
        experiment = self._build(["80% capacity", "2.5 V"])
        assert experiment.termination["voltage"] == (2.5, "V")

    def test_case_02(self):
        experiment = self._build(["75% capacity", "10 seconds"])
        assert experiment.termination["time"] == 10.0

    def test_case_03(self):
        experiment = self._build(["70% capacity", "1 minute"])
        assert experiment.termination["time"] == 60.0

    def test_case_04(self):
        experiment = self._build(["65% capacity", "30 sec"])
        assert experiment.termination["time"] == 30.0

    def test_case_05(self):
        experiment = self._build(["60% capacity", "2.8 V"])
        assert experiment.termination["voltage"] == (2.8, "V")

    def test_case_06(self):
        experiment = self._build(["55% capacity", "2 minutes"])
        assert experiment.termination["time"] == 120.0

    def test_case_07(self):
        experiment = self._build(["50% capacity", "45 s"])
        assert experiment.termination["time"] == 45.0

    def test_case_08(self):
        experiment = self._build(["85% capacity", "3.0 V"])
        assert experiment.termination["voltage"] == (3.0, "V")

    def test_case_09(self):
        experiment = self._build(["90% capacity", "1 hour"])
        assert experiment.termination["time"] == 3600.0

    def test_case_10(self):
        experiment = self._build(["95% capacity", "15 min"])
        assert experiment.termination["time"] == 900.0
