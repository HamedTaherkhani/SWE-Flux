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
    def __init__(self, stop_after=2):
        self.stop_after = stop_after
        self.erase_calls = 0
        self.refresh_calls = 0
        self.move_calls = []
        self.addstr_calls = []

    def getmaxyx(self):
        return (36, 132)

    def addstr(self, *args):
        self.addstr_calls.append(args)

    def move(self, y, x):
        self.move_calls.append((y, x))

    def refresh(self):
        self.refresh_calls += 1

    def erase(self):
        self.erase_calls += 1
        if self.erase_calls >= self.stop_after:
            raise _StopLoop("stop after enough loop iterations")


class TestScriptsTopDirectGetStatsDefUsePairsQA:
    def test_scripts_top_direct_get_stats_def_use_pairs_case(self, monkeypatch):
        monkeypatch.setattr(top_mod.curses, "A_BOLD", 1, raising=False)
        monkeypatch.setattr(top_mod.curses, "A_REVERSE", 2, raising=False)
        monkeypatch.setattr(top_mod.curses, "COLOR_GREEN", 2, raising=False)
        monkeypatch.setattr(top_mod.curses, "COLOR_BLACK", 0, raising=False)
        monkeypatch.setattr(top_mod.curses, "init_pair", lambda *_args, **_kwargs: None)
        monkeypatch.setattr(top_mod.curses, "color_pair", lambda value: value * 10)

        monkeypatch.setattr(top_mod.time, "sleep", lambda _seconds: None)

        line_map = {
            ("/tmp/project/module_a.py", 11): "alpha = 1",
            ("/tmp/project/module_b.py", 22): "beta = alpha + 2",
            ("/tmp/project/module_c.py", 33): "gamma = beta * 2",
            ("/tmp/project/module_d.py", 44): "delta = gamma - 3",
        }
        monkeypatch.setattr(
            top_mod.linecache,
            "getline",
            lambda filename, lineno: line_map.get((filename, lineno), ""),
        )

        snapshots = [
            _DummySnapshot(
                [
                    _DummyStat("/tmp/project/module_a.py", 11, 4096),
                    _DummyStat("/tmp/project/module_b.py", 22, 3072),
                    _DummyStat("/tmp/project/module_c.py", 33, 2048),
                ]
            ),
            _DummySnapshot([_DummyStat("/tmp/project/module_d.py", 44, 5120)]),
        ]

        state = {"i": 0}

        def _fake_get_trace(_c, _force_start):
            idx = state["i"]
            state["i"] += 1
            if idx >= len(snapshots):
                return snapshots[-1]
            return snapshots[idx]

        monkeypatch.setattr(top_mod, "get_trace", _fake_get_trace)
        monkeypatch.setattr(top_mod, "filter_snapshot", lambda snapshot: snapshot)

        scr = _DummyScreen(stop_after=2)

        with pytest.raises(_StopLoop):
            top_mod.get_stats(
                scr,
                c=object(),
                group_by="lineno",
                limit=2,
                seconds=0.0,
                force_start=True,
            )

        assert scr.refresh_calls == 2
        assert len(scr.addstr_calls) >= 10
        assert scr.move_calls[-1] == (34, 34)
        assert scr.erase_calls == 2
