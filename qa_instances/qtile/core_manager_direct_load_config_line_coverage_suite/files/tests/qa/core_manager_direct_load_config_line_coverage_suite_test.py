from __future__ import annotations

from pathlib import Path

import pytest

from libqtile.core import manager as manager_mod
from libqtile.core.manager import Qtile


class DummyLayout:
    def __init__(self):
        self.show_calls = []

    def show(self, rect):
        self.show_calls.append(rect)


class DummyGroup:
    def __init__(self, name, label=None):
        self.name = name
        self.label = label if label is not None else f"label-{name}"
        self.layout = DummyLayout()
        self.layout_all_calls = 0

    def layout_all(self):
        self.layout_all_calls += 1


class DummyScreen:
    def __init__(self, group):
        self.group = group
        self.set_group_calls = []

    def set_group(self, group):
        self.group = group
        self.set_group_calls.append(group.name)

    def get_rect(self):
        return (10, 20, 300, 200)


class DummyInstalledExtension:
    def __init__(self, name):
        self.name = name
        self.configure_calls = 0

    def _configure(self, qtile):
        self.configure_calls += 1
        qtile.extension_hits.append(self.name)


class FakeScratchPadConfig:
    def __init__(self, name):
        self.name = name
        self.dropdowns = [f"{name}-dropdown"]
        self.label = f"label-{name}"
        self.single = True


class FakeScratchPad:
    def __init__(self, name, dropdowns, label, single):
        self.name = name
        self.dropdowns = list(dropdowns)
        self.label = label
        self.single = single
        self.configure_calls = []

    def _configure(self, layouts, floating_layout, qtile):
        self.configure_calls.append(
            {"layouts_len": len(layouts), "floating_layout": floating_layout, "qtile_id": id(qtile)}
        )


class DummyState:
    def __init__(self, tag):
        self.tag = tag
        self.apply_calls = 0

    def apply(self, qtile):
        self.apply_calls += 1
        qtile.state_apply_tags.append(self.tag)


class DummyConfig:
    def __init__(
        self,
        *,
        groups,
        wmname,
        reconfigure_screens,
        load_raises=False,
        validate_raises=False,
    ):
        self.groups = list(groups)
        self.wmname = wmname
        self.dgroups_key_binder = "binder-token"
        self.widget_defaults = {"font": "mono", "size": 11}
        self.extension_defaults = {"timeout": 3}
        self.floating_layout = "FLOATING-LAYOUT"
        self.keys = ["k1", "k2", "k3"]
        self.mouse = ["m1", "m2"]
        self.reconfigure_screens = reconfigure_screens
        self.load_raises = load_raises
        self.validate_raises = validate_raises
        self.load_calls = 0
        self.validate_calls = 0

    def load(self):
        self.load_calls += 1
        if self.load_raises:
            raise RuntimeError("load failed")

    def validate(self):
        self.validate_calls += 1
        if self.validate_raises:
            raise ValueError("validate failed")


class DummyCore:
    def __init__(self, has_wmname=True):
        if has_wmname:
            self.wmname = "before-load"
        self.on_config_load_calls = []

    def on_config_load(self, initial):
        self.on_config_load_calls.append(initial)


class DummySubscribe:
    def __init__(self):
        self.setgroup_calls = []
        self.screen_change_calls = []

    def setgroup(self, fn):
        self.setgroup_calls.append(fn.__name__)

    def screen_change(self, fn):
        self.screen_change_calls.append(fn.__name__)


class DummyHook:
    def __init__(self):
        self.fire_calls = []
        self.subscribe = DummySubscribe()

    def fire(self, event_name):
        self.fire_calls.append(event_name)


class DummyQtileLoadConfigProbe:
    load_config = Qtile.load_config

    def __init__(self, config, core, groups, screens, *, no_spawn, state):
        self.config = config
        self.core = core
        self.groups = list(groups)
        self.screens = list(screens)
        self.groups_map = {}
        self.no_spawn = no_spawn
        self._state = state
        self.dgroups = None
        self.extension_hits = []
        self.state_apply_tags = []
        self.process_screens_calls = []
        self.grabbed_keys = []
        self.grabbed_buttons = []
        self.update_desktops_calls = 0

    def _process_screens(self, reloading=False):
        self.process_screens_calls.append(reloading)

    def grab_key(self, key):
        self.grabbed_keys.append(key)

    def grab_button(self, button):
        self.grabbed_buttons.append(button)

    def update_desktops(self, *args, **kwargs):
        self.update_desktops_calls += 1

    def reconfigure_screens(self, *args, **kwargs):
        return None


CASES = [
    {
        "name": "baseline_initial_true",
        "initial": True,
        "core_has_wmname": True,
        "load_raises": False,
        "validate_raises": False,
        "include_scratchpad": False,
        "state_mode": "none",
        "no_spawn": False,
        "reconfigure_screens": False,
        "extension_count": 1,
    },
    {
        "name": "baseline_initial_false",
        "initial": False,
        "core_has_wmname": True,
        "load_raises": False,
        "validate_raises": False,
        "include_scratchpad": False,
        "state_mode": "none",
        "no_spawn": False,
        "reconfigure_screens": False,
        "extension_count": 1,
    },
    {
        "name": "config_load_exception",
        "initial": False,
        "core_has_wmname": True,
        "load_raises": True,
        "validate_raises": False,
        "include_scratchpad": False,
        "state_mode": "none",
        "no_spawn": False,
        "reconfigure_screens": False,
        "extension_count": 1,
    },
    {
        "name": "config_validate_exception",
        "initial": False,
        "core_has_wmname": True,
        "load_raises": False,
        "validate_raises": True,
        "include_scratchpad": False,
        "state_mode": "none",
        "no_spawn": False,
        "reconfigure_screens": False,
        "extension_count": 2,
    },
    {
        "name": "core_without_wmname_attr",
        "initial": True,
        "core_has_wmname": False,
        "load_raises": False,
        "validate_raises": False,
        "include_scratchpad": False,
        "state_mode": "none",
        "no_spawn": False,
        "reconfigure_screens": False,
        "extension_count": 1,
    },
    {
        "name": "scratchpad_group_branch",
        "initial": False,
        "core_has_wmname": True,
        "load_raises": False,
        "validate_raises": False,
        "include_scratchpad": True,
        "state_mode": "none",
        "no_spawn": False,
        "reconfigure_screens": False,
        "extension_count": 1,
    },
    {
        "name": "state_object_apply_branch",
        "initial": False,
        "core_has_wmname": True,
        "load_raises": False,
        "validate_raises": False,
        "include_scratchpad": False,
        "state_mode": "object",
        "no_spawn": False,
        "reconfigure_screens": False,
        "extension_count": 1,
    },
    {
        "name": "state_file_apply_success",
        "initial": True,
        "core_has_wmname": True,
        "load_raises": False,
        "validate_raises": False,
        "include_scratchpad": True,
        "state_mode": "path_success",
        "no_spawn": False,
        "reconfigure_screens": True,
        "extension_count": 2,
    },
    {
        "name": "state_file_apply_failure",
        "initial": False,
        "core_has_wmname": True,
        "load_raises": False,
        "validate_raises": False,
        "include_scratchpad": False,
        "state_mode": "path_error",
        "no_spawn": False,
        "reconfigure_screens": True,
        "extension_count": 1,
    },
    {
        "name": "already_no_spawn_reconfigure",
        "initial": False,
        "core_has_wmname": True,
        "load_raises": False,
        "validate_raises": False,
        "include_scratchpad": True,
        "state_mode": "none",
        "no_spawn": True,
        "reconfigure_screens": True,
        "extension_count": 1,
    },
]


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
class TestCoreManagerDirectLoadConfigLineCoverageSuiteQA:
    def test_core_manager_direct_load_config_line_coverage_suite_case(self, case, monkeypatch, tmp_path):
        hook = DummyHook()
        notifications = []
        log_exceptions = []
        inhibitor_calls = []
        removed_paths = []
        dgroups_calls = []

        installed_extensions = [
            DummyInstalledExtension(f"ext-{i}") for i in range(case["extension_count"])
        ]

        def fake_dgroups(qtile, groups, binder):
            dgroups_calls.append({"groups_len": len(groups), "binder": binder, "qtile_id": id(qtile)})
            return {"tag": "dgroups", "count": len(groups)}

        def fake_notify(title, message):
            notifications.append((title, message))

        def fake_log_exception(*args, **kwargs):
            if args:
                log_exceptions.append(str(args[0]))
            else:
                log_exceptions.append("exception")

        def fake_inhibitor_start():
            inhibitor_calls.append("start")

        def fake_remove(path):
            removed_paths.append(path)
            Path(path).unlink(missing_ok=True)

        pickle_state = DummyState("pickle-state")

        def fake_pickle_load(_stream):
            if case["state_mode"] == "path_error":
                raise RuntimeError("corrupt state")
            return pickle_state

        monkeypatch.setattr(manager_mod, "DGroups", fake_dgroups)
        monkeypatch.setattr(manager_mod, "ScratchPadConfig", FakeScratchPadConfig)
        monkeypatch.setattr(manager_mod, "ScratchPad", FakeScratchPad)
        monkeypatch.setattr(manager_mod._Extension, "installed_extensions", installed_extensions)
        monkeypatch.setattr(manager_mod, "hook", hook)
        monkeypatch.setattr(manager_mod, "send_notification", fake_notify)
        monkeypatch.setattr(manager_mod.logger, "exception", fake_log_exception)
        monkeypatch.setattr(manager_mod.inhibitor, "start", fake_inhibitor_start)
        monkeypatch.setattr(manager_mod.os, "remove", fake_remove)
        monkeypatch.setattr(manager_mod.pickle, "load", fake_pickle_load)

        config_groups = [DummyGroup("cfg-main")]
        if case["include_scratchpad"]:
            config_groups.append(FakeScratchPadConfig("scratch-1"))

        config = DummyConfig(
            groups=config_groups,
            wmname=f"wm-{case['name']}",
            reconfigure_screens=case["reconfigure_screens"],
            load_raises=case["load_raises"],
            validate_raises=case["validate_raises"],
        )
        core = DummyCore(has_wmname=case["core_has_wmname"])

        managed_groups = [DummyGroup("g1"), DummyGroup("g2")]
        screen_groups = [DummyGroup("screen-g1"), DummyGroup("screen-g2")]
        screens = [DummyScreen(screen_groups[0]), DummyScreen(screen_groups[1])]

        if case["state_mode"] == "object":
            state = DummyState("object-state")
        elif case["state_mode"] in ("path_success", "path_error"):
            state_path = tmp_path / f"qtile_state_{case['name']}.bin"
            state_path.write_bytes(b"serialized-state")
            state = str(state_path)
        else:
            state = None

        probe = DummyQtileLoadConfigProbe(
            config=config,
            core=core,
            groups=managed_groups,
            screens=screens,
            no_spawn=case["no_spawn"],
            state=state,
        )

        probe.load_config(initial=case["initial"])

        assert config.load_calls == 1
        assert config.validate_calls == (0 if case["load_raises"] else 1)
        assert probe.process_screens_calls == [not case["initial"]]
        assert probe.grabbed_keys == config.keys
        assert probe.grabbed_buttons == config.mouse
        assert len(dgroups_calls) == 1
        assert probe.dgroups["count"] == len(config.groups)
        assert probe.update_desktops_calls == 1
        assert core.on_config_load_calls == [case["initial"]]
        assert inhibitor_calls == ["start"]

        if case["core_has_wmname"]:
            assert core.wmname == config.wmname
        else:
            assert not hasattr(core, "wmname")

        if case["load_raises"] or case["validate_raises"]:
            assert len(notifications) == 1
            assert notifications[0][0] == "Configuration error"
            assert any("Configuration error:" in msg for msg in log_exceptions)
        else:
            assert notifications == []

        for ext in installed_extensions:
            assert ext.configure_calls == 1
        assert sorted(probe.extension_hits) == sorted([e.name for e in installed_extensions])

        assert "startup" in hook.fire_calls
        if case["no_spawn"]:
            assert "startup_once" not in hook.fire_calls
            assert probe.no_spawn is True
        else:
            assert "startup_once" in hook.fire_calls
            assert probe.no_spawn is True

        if case["initial"]:
            assert "startup_complete" in hook.fire_calls
        else:
            assert "startup_complete" not in hook.fire_calls

        assert len(hook.subscribe.setgroup_calls) == 1
        assert hook.subscribe.setgroup_calls[0] == "update_desktops"

        if case["reconfigure_screens"]:
            assert len(hook.subscribe.screen_change_calls) == 1
            assert hook.subscribe.screen_change_calls[0] == "reconfigure_screens"
        else:
            assert hook.subscribe.screen_change_calls == []

        if case["include_scratchpad"]:
            assert "scratch-1" in probe.groups_map
            assert any(g.name == "scratch-1" for g in probe.groups)
        else:
            assert "scratch-1" not in probe.groups_map

        if case["state_mode"] == "none":
            assert probe.state_apply_tags == []
            assert removed_paths == []
        elif case["state_mode"] == "object":
            assert probe.state_apply_tags == ["object-state"]
            assert removed_paths == []
        elif case["state_mode"] == "path_success":
            assert probe.state_apply_tags == ["pickle-state"]
            assert len(removed_paths) == 1
        else:
            assert case["state_mode"] == "path_error"
            assert probe.state_apply_tags == []
            assert len(removed_paths) == 1
            assert any("failed restoring state" in msg for msg in log_exceptions)

        if case["state_mode"] == "none":
            for group in screen_groups:
                assert group.layout.show_calls == []
                assert group.layout_all_calls == 0
        else:
            for group in screen_groups:
                assert group.layout.show_calls == [(10, 20, 300, 200)]
                assert group.layout_all_calls == 1

        assert probe._state is None
