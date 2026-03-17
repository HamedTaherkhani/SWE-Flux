from telegram.ext import ApplicationBuilder
from telegram.request import HTTPXRequest


class TestApplicationBuilderBuildRequestDefUsePairsQA:
    def test_applicationbuilder_build_request_def_use_pairs_case(self):
        builder = (
            ApplicationBuilder()
            .token("123456:DEF_USE_TOKEN")
            .connection_pool_size(11)
            .get_updates_connection_pool_size(3)
            .connect_timeout(4.5)
            .read_timeout(7.5)
            .write_timeout(8.5)
            .pool_timeout(9.5)
            .get_updates_connect_timeout(1.5)
            .get_updates_read_timeout(2.5)
            .get_updates_write_timeout(3.5)
            .get_updates_pool_timeout(4.5)
            .http_version("1.1")
            .get_updates_http_version("1.1")
        )

        req_main = builder._build_request(get_updates=False)
        req_updates = builder._build_request(get_updates=True)

        override_builder = ApplicationBuilder().token("123456:DEF_USE_OVERRIDE_TOKEN")
        override_builder.request(HTTPXRequest(connection_pool_size=5, http_version="1.1"))
        override_builder.get_updates_request(
            HTTPXRequest(connection_pool_size=2, http_version="1.1")
        )
        req_main_override = override_builder._build_request(get_updates=False)
        req_updates_override = override_builder._build_request(get_updates=True)

        assert req_main is not None
        assert req_updates is not None
        assert req_main_override is not None
        assert req_updates_override is not None
