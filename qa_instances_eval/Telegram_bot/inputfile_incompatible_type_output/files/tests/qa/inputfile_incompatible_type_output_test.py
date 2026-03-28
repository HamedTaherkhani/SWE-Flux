import pytest

from telegram import InputFile


class TestInputFileIncompatibleTypeOutputQA:
    def test_inputfile_incompatible_type_output_case(self):
        parts = ["alpha", "beta", "gamma", "delta", "epsilon"]
        incompatible_obj = sum((idx + 1) * len(chunk) for idx, chunk in enumerate(parts)) + 11
        attach_flag = ((incompatible_obj // 3) % 2) == 0

        input_file = InputFile(obj=incompatible_obj, attach=attach_flag)
        field_tuple = input_file.field_tuple

        assert isinstance(field_tuple, tuple)
        assert len(field_tuple) == 3
        assert field_tuple[0]

