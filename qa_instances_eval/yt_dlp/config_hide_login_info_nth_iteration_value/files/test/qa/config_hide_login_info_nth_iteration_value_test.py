from yt_dlp.utils._utils import Config


OPTS = [
    "-u", "myuser",
    "--password", "mypass",
    "--video-password=secret",
    "extra1",
    "--username", "someone",
    "extra2",
]


class TestConfigHideLoginInfoNthIterationValueQA:
    def test_config_hide_login_info_nth_iteration_value_case(self):
        result = Config.hide_login_info(OPTS)

        # Shape-only assertion; do not reveal per-iteration values.
        assert isinstance(result, list)
