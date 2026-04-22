import argparse

import libcst

from libqtile.scripts import migrate as migrate_mod


class _MigrationAlpha:
    ID = "migration_alpha"
    AFTER_VERSION = "0.1.0"
    DIFF_TEXT = "--- alpha diff ---"
    UPDATED_CODE = "value = 'alpha'\n"

    @classmethod
    def show_summary(cls):
        return "Apply alpha changes"

    @classmethod
    def show_help(cls):
        return "Help alpha"

    def migrate(self, source):
        self.original = source
        self.updated = libcst.parse_module(self.UPDATED_CODE)

    def show_diff(self, _no_colour):
        return self.DIFF_TEXT


class _MigrationBeta:
    ID = "migration_beta"
    AFTER_VERSION = "0.2.0"
    DIFF_TEXT = "--- beta diff ---"
    UPDATED_CODE = "value = 'beta'\nflag = 1\n"

    @classmethod
    def show_summary(cls):
        return "Apply beta changes"

    @classmethod
    def show_help(cls):
        return "Help beta"

    def migrate(self, source):
        self.original = source
        self.updated = libcst.parse_module(self.UPDATED_CODE)

    def show_diff(self, _no_colour):
        return self.DIFF_TEXT


class _MigrationGamma:
    ID = "migration_gamma"
    AFTER_VERSION = "0.3.0"
    DIFF_TEXT = ""
    UPDATED_CODE = "value = 'gamma'\n"

    @classmethod
    def show_summary(cls):
        return "Gamma no-op"

    @classmethod
    def show_help(cls):
        return "Help gamma"

    def migrate(self, source):
        self.original = source
        self.updated = libcst.parse_module(self.UPDATED_CODE)

    def show_diff(self, _no_colour):
        return self.DIFF_TEXT


class _MigrationDelta:
    ID = "migration_delta"
    AFTER_VERSION = "0.4.0"
    DIFF_TEXT = "--- delta diff ---"
    UPDATED_CODE = "value = 'delta'\ncount = 4\n"

    @classmethod
    def show_summary(cls):
        return "Apply delta changes"

    @classmethod
    def show_help(cls):
        return "Help delta"

    def migrate(self, source):
        self.original = source
        self.updated = libcst.parse_module(self.UPDATED_CODE)

    def show_diff(self, _no_colour):
        return self.DIFF_TEXT


class _MigrationEpsilon:
    ID = "migration_epsilon"
    AFTER_VERSION = "0.5.0"
    DIFF_TEXT = ""
    UPDATED_CODE = "value = 'epsilon'\n"

    @classmethod
    def show_summary(cls):
        return "Epsilon no-op"

    @classmethod
    def show_help(cls):
        return "Help epsilon"

    def migrate(self, source):
        self.original = source
        self.updated = libcst.parse_module(self.UPDATED_CODE)

    def show_diff(self, _no_colour):
        return self.DIFF_TEXT


class TestScriptsMigrateDirectMigrateDefUsePairsQA:
    def test_scripts_migrate_direct_migrate_def_use_pairs_case(self, tmp_path, monkeypatch):
        migrate_mod.libcst = libcst

        config_path = tmp_path / "config.py"
        config_path.write_text("value = 'start'\n", encoding="utf-8")

        probe = migrate_mod.QtileMigrate()

        probe.args = argparse.Namespace(no_colour=True, show_diff=True, yes=False)
        probe.migrations = [_MigrationAlpha, _MigrationBeta, _MigrationGamma]

        responses = iter(["invalid", "n", "y", "??", "y"])
        monkeypatch.setattr("builtins.input", lambda _prompt: next(responses))

        first_result = probe.migrate(str(config_path))
        assert first_result is True
        assert config_path.read_text(encoding="utf-8") == _MigrationBeta.UPDATED_CODE

        probe.args = argparse.Namespace(no_colour=False, show_diff=False, yes=True)
        probe.migrations = [_MigrationDelta]

        second_result = probe.migrate(str(config_path))
        assert second_result is True
        assert config_path.read_text(encoding="utf-8") == _MigrationDelta.UPDATED_CODE

        probe.args = argparse.Namespace(no_colour=False, show_diff=False, yes=True)
        probe.migrations = [_MigrationEpsilon]

        third_result = probe.migrate(str(config_path))
        assert third_result is False
        assert config_path.read_text(encoding="utf-8") == _MigrationDelta.UPDATED_CODE
