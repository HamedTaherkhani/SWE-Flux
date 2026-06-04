from __future__ import annotations

import numpy as np
import pybamm


class TestBaseModelSetInitialConditionsFromDefUseDiverseQA:
    def _single_model(self, seed, rank, discretised, return_type, inplace):
        model = pybamm.BaseModel(f"qa ic single {seed}")
        var = pybamm.Variable(
            f"qa ic var {seed}",
            scale=seed + 2,
            reference=seed / 4,
        )
        model.initial_conditions = {var: pybamm.Scalar(0)}
        if discretised:
            model.is_discretised = True
            model.y_slices = {var: [slice(0, self._final_size(rank))]}
        solution = {var.name: self._array(seed, rank)}
        return model.set_initial_conditions_from(
            solution, inplace=inplace, return_type=return_type
        )

    def _concat_model(self, seed, rank_a, rank_b, discretised, return_type, inplace):
        model = pybamm.BaseModel(f"qa ic concat {seed}")
        a = pybamm.Variable(
            f"qa ic neg {seed}",
            domain="negative electrode",
            scale=seed + 3,
            reference=seed / 5,
        )
        b = pybamm.Variable(
            f"qa ic sep {seed}",
            domain="separator",
            scale=seed + 3,
            reference=seed / 5,
        )
        joined = pybamm.concatenation(a, b)
        model.initial_conditions = {joined: pybamm.Scalar(0)}
        if discretised:
            size_a = self._final_size(rank_a)
            size_b = self._final_size(rank_b)
            model.is_discretised = True
            model.y_slices = {
                a: [slice(0, size_a)],
                b: [slice(size_a, size_a + size_b)],
                joined: [slice(0, size_a + size_b)],
            }
        solution = {a.name: self._array(seed, rank_a), b.name: self._array(seed + 20, rank_b)}
        return model.set_initial_conditions_from(
            solution, inplace=inplace, return_type=return_type
        )

    def _array(self, seed, rank):
        if rank == 0:
            return np.array(seed + 0.5)
        if rank == 1:
            return np.array([seed, seed + 1, seed + 2])
        if rank == 2:
            return np.array([[seed, seed + 1, seed + 2], [seed + 3, seed + 4, seed + 5]])
        if rank == 3:
            return np.arange(seed, seed + 12).reshape(2, 2, 3)
        return np.arange(seed, seed + 24).reshape(2, 2, 2, 3)

    def _final_size(self, rank):
        return {0: 1, 1: 1, 2: 2, 3: 4, 4: 8}[rank]

    def test_case_01(self):
        model = self._single_model(1, 0, False, "model", False)
        assert len(model.initial_conditions) == 1

    def test_case_02(self):
        ics, concat = self._single_model(2, 1, False, "ics", True)
        assert len(ics) == 1 and concat is None

    def test_case_03(self):
        ics, concat = self._single_model(3, 2, True, "ics", True)
        assert len(ics) == 1 and concat is not None

    def test_case_04(self):
        model = self._single_model(4, 3, True, "model", False)
        assert model.concatenated_initial_conditions is not None

    def test_case_05(self):
        ics, concat = self._concat_model(5, 1, 2, False, "ics", True)
        assert len(ics) == 1 and concat is None

    def test_case_06(self):
        model = self._concat_model(6, 2, 3, True, "model", False)
        assert model.concatenated_initial_conditions is not None

    def test_case_07(self):
        ics, concat = self._concat_model(7, 3, 4, True, "ics", True)
        assert len(ics) == 1 and concat is not None

    def test_case_08(self):
        model = self._single_model(8, 4, False, "model", True)
        assert len(model.initial_conditions) == 1

    def test_case_09(self):
        ics, concat = self._concat_model(9, 0, 1, False, "ics", False)
        assert len(ics) == 1 and concat is None

    def test_case_10(self):
        model = self._single_model(10, 2, True, "model", True)
        assert model.concatenated_initial_conditions is not None
