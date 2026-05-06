from __future__ import annotations

from reflex.components.core.match import Match


class TestComponentsMatchProcessCasesDefUsePairsQA:
    def test_components_match_process_cases_def_use_pairs_case(self):
        cases = [
            ("idle", "Idle"),
            ("busy", "Busy", "Working"),
            ("done", "Done"),
        ]

        match_cases = Match._process_match_cases(cases)

        assert [[str(element) for element in case] for case in match_cases] == [
            ['"idle"', '"Idle"'],
            ['"busy"', '"Busy"', '"Working"'],
            ['"done"', '"Done"'],
        ]
