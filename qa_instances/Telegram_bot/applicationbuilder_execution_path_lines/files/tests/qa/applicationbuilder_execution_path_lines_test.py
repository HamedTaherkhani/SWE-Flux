from telegram.ext import ApplicationBuilder


class TestApplicationBuilderExecutionPathLinesQA:
    def test_applicationbuilder_execution_path_lines_case(self):
        timeout_seed = sum((idx + 1) * value for idx, value in enumerate([2, 5, 3, 7]))

        app = (
            ApplicationBuilder()
            .token("123456:ABCdefGHIjklMNOpqrSTUvwxYZ")
            .base_url("https://api.telegram.org/bot")
            .base_file_url("https://api.telegram.org/file/bot")
            .connect_timeout((timeout_seed % 4) + 1)
            .read_timeout((timeout_seed % 5) + 3)
            .write_timeout((timeout_seed % 6) + 4)
            .pool_timeout((timeout_seed % 3) + 2)
            .http_version("1.1")
            .connection_pool_size((timeout_seed % 8) + 8)
            .build()
        )

        assert app is not None
        assert app.bot is not None
        assert app.bot.base_url is not None
