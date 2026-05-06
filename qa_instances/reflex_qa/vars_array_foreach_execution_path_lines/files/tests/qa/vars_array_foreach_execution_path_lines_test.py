from unittest.mock import patch

from reflex.vars.base import Var
from reflex.vars.sequence import ArrayVar


class TestVarsArrayForeachExecutionPathLinesQA:
    def test_vars_array_foreach_execution_path_lines_case(self):
        rows = Var(
            _js_expr="state.rows.filter((row) => row.active)",
            _var_type=list[dict[str, int]],
        ).to(ArrayVar, list[dict[str, int]])

        with patch("reflex.vars.sequence.get_unique_variable_name", return_value="qa_row"):
            result = rows.foreach(
                lambda item: item["score"] + item["bonus"] * 2,
            )

        assert (
            str(result)
            == 'state.rows.filter((row) => row.active).map(((qa_row) => (qa_row["score"] + (qa_row["bonus"] * 2))))'
        )
        assert str(result._var_type) == "list[typing.Any]"
