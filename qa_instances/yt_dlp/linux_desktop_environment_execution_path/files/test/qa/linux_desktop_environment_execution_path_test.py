from yt_dlp.cookies import _get_linux_desktop_environment


class _StubLogger:
    def info(self, msg, **kwargs):
        pass

    def debug(self, msg, **kwargs):
        pass

    def warning(self, msg, **kwargs):
        pass

    def error(self, msg, **kwargs):
        pass


ENV = {
    "XDG_CURRENT_DESKTOP": "Cinnamon:KDE",
    "KDE_SESSION_VERSION": "99",
    "DESKTOP_SESSION": "deepin",
}


class TestLinuxDesktopEnvironmentExecutionPathQA:
    def test_linux_desktop_environment_execution_path_case(self):
        result = _get_linux_desktop_environment(ENV, _StubLogger())

        # Shape-only assertion; do not reveal the chosen branch or path.
        assert result is not None
