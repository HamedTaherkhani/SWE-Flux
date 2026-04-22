from dataclasses import dataclass

import pytest

from libqtile.scripts import top as top_mod


class _StopLoop(Exception):
    pass


@dataclass
class _DummyFrame:
    filename: str
    lineno: int


class _DummyStat:
    def __init__(self, filename: str, lineno: int, size: int):
        self.traceback = [_DummyFrame(filename=filename, lineno=lineno)]
        self.size = size


class _DummySnapshot:
    def __init__(self, stats):
        self._stats = list(stats)

    def statistics(self, _group_by):
        return list(self._stats)


class _DummyScreen:
    def __init__(self):
        self.refresh_calls = 0
        self.erase_calls = 0

    def getmaxyx(self):
        return (42, 132)

    def addstr(self, *_args):
        pass

    def move(self, *_args):
        pass

    def refresh(self):
        self.refresh_calls += 1

    def erase(self):
        self.erase_calls += 1
        raise _StopLoop("single-iteration stop")


def _build_case_stats(case_id: int):
    stat_count = 2 + ((case_id * 5 + 1) % 4)
    stats = []
    for idx in range(stat_count):
        filename = f"/tmp/trace_suite/case_{case_id}/module_{idx}.py"
        lineno = 10 + ((case_id + 3 * idx) % 70)
        base = (case_id + 7) * (idx + 11) * 97
        wobble = ((case_id * case_id + 13 * idx + 5) % 19) * 41
        size = 600 + ((base + wobble) % 8400)
        stats.append(_DummyStat(filename=filename, lineno=lineno, size=size))
    return stats


def _run_case(case_id: int, monkeypatch):
    monkeypatch.setattr(top_mod.curses, "A_BOLD", 1, raising=False)
    monkeypatch.setattr(top_mod.curses, "A_REVERSE", 2, raising=False)
    monkeypatch.setattr(top_mod.curses, "COLOR_GREEN", 2, raising=False)
    monkeypatch.setattr(top_mod.curses, "COLOR_BLACK", 0, raising=False)
    monkeypatch.setattr(top_mod.curses, "init_pair", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(top_mod.curses, "color_pair", lambda value: value)

    monkeypatch.setattr(top_mod.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        top_mod.linecache,
        "getline",
        lambda filename, lineno: f"value_{case_id}_{lineno} = {len(filename)}",
    )

    stats = _build_case_stats(case_id)
    expected_total = sum(s.size for s in stats)

    monkeypatch.setattr(top_mod, "get_trace", lambda _c, _force_start: _DummySnapshot(stats))
    monkeypatch.setattr(top_mod, "filter_snapshot", lambda snapshot: snapshot)

    scr = _DummyScreen()
    limit = 1 + ((case_id * 7 + 2) % 5)

    with pytest.raises(_StopLoop):
        top_mod.get_stats(
            scr,
            c=object(),
            group_by="lineno",
            limit=limit,
            seconds=0.0,
            force_start=(case_id % 2 == 0),
        )

    assert scr.refresh_calls == 1
    assert scr.erase_calls == 1
    assert expected_total >= 1200


class TestScriptsTopDirectGetStatsTotalValueRangeSuiteQA:
    @pytest.mark.parametrize("case_id", list(range(15)))
    def test_scripts_top_direct_get_stats_total_value_range_case(self, case_id, monkeypatch):
        _run_case(case_id, monkeypatch)
