from __future__ import annotations

try:
    from xarray.core.merge import merge_attrs
except ModuleNotFoundError:
    from xarray.structure.merge import merge_attrs


class TestMergeAttrsDirectFunctionOutputHardQA:
    def test_merge_attrs_direct_function_output_hard_case(self) -> None:
        attrs_sequence = [
            {
                "units": "m",
                "source": "sensorA",
                "qc": ("ok", 1),
                "scale": 1,
                "tag": "x",
            },
            {
                "units": "m",
                "source": "sensorB",
                "qc": ("ok", 1),
                "scale": 1,
                "new": 5,
                "tag": "x",
            },
            {
                "units": "cm",
                "qc": ("ok", 2),
                "new": 5,
                "tag": "x",
                "note": "v3",
            },
        ]

        merged = merge_attrs(attrs_sequence, combine_attrs="drop_conflicts")

        assert isinstance(merged, dict)
        assert "source" not in merged
        assert "tag" in merged
