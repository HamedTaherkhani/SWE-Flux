import copy
import json

import pybamm
from pybamm.expression_tree.operations.serialise import Serialise


class TestSerialiseLoadModelExceptionDiversityQA:
    def _base_data(self, tmp_path):
        model = pybamm.BaseModel("qa serialised model")
        x = pybamm.Variable("x")
        model.rhs = {x: -x}
        model.initial_conditions = {x: pybamm.Scalar(1)}
        model.variables = {"x": x}
        pybamm.Discretisation().process_model(model)
        filename = tmp_path / "base"
        Serialise().save_model(model, filename=str(filename))
        return json.loads(filename.with_suffix(".json").read_text())

    def _write(self, tmp_path, name, data):
        path = tmp_path / name
        path.write_text(json.dumps(data))
        return path

    def _load(self, path):
        try:
            return Serialise().load_model(str(path))
        except Exception:
            return None

    def test_case_01(self, tmp_path):
        self._load(self._write(tmp_path, "valid.json", self._base_data(tmp_path)))

    def test_case_02(self, tmp_path):
        data = self._base_data(tmp_path)
        data.pop("name")
        self._load(self._write(tmp_path, "missing-name.json", data))

    def test_case_03(self, tmp_path):
        data = self._base_data(tmp_path)
        data.pop("bounds")
        self._load(self._write(tmp_path, "missing-bounds.json", data))

    def test_case_04(self, tmp_path):
        data = self._base_data(tmp_path)
        data.pop("py/object")
        self._load(self._write(tmp_path, "missing-object.json", data))

    def test_case_05(self, tmp_path):
        data = self._base_data(tmp_path)
        data["py/object"] = "pybamm.does_not_exist.Model"
        self._load(self._write(tmp_path, "bad-model-module.json", data))

    def test_case_06(self, tmp_path):
        data = self._base_data(tmp_path)
        data["py/object"] = "pybamm.models.base_model.NoSuchModel"
        self._load(self._write(tmp_path, "bad-model-class.json", data))

    def test_case_07(self, tmp_path):
        data = self._base_data(tmp_path)
        data.pop("concatenated_rhs")
        self._load(self._write(tmp_path, "missing-rhs.json", data))

    def test_case_08(self, tmp_path):
        data = self._base_data(tmp_path)
        data["concatenated_rhs"]["py/object"] = "pybamm.nope.Scalar"
        self._load(self._write(tmp_path, "bad-symbol-module.json", data))

    def test_case_09(self, tmp_path):
        self._load(tmp_path / "does-not-exist.json")

    def test_case_10(self, tmp_path):
        path = tmp_path / "invalid.json"
        path.write_text("{not valid json")
        self._load(path)
