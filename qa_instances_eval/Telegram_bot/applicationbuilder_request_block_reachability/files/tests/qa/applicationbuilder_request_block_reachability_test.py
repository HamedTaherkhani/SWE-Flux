import socket

from telegram.ext import ApplicationBuilder
from telegram.request import HTTPXRequest


class TestApplicationBuilderRequestBlockReachabilityQA:
    def test_applicationbuilder_request_block_reachability_case(self):
        custom_request = HTTPXRequest(
            connection_pool_size=5,
            read_timeout=9.0,
            write_timeout=9.0,
            connect_timeout=9.0,
            pool_timeout=9.0,
            http_version="1.1",
        )

        builder = (
            ApplicationBuilder()
            .token("123456:ABCDEF_TEST_TOKEN")
            .get_updates_connection_pool_size(2)
            .get_updates_socket_options(
                [
                    (socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1),
                    (socket.IPPROTO_TCP, socket.TCP_NODELAY, 1),
                ]
            )
            .get_updates_http_version("1.1")
            .request(custom_request)
        )

        application = builder.build()

        assert application.bot.request is custom_request
        assert application.bot._request[0] is not None
        assert application.updater is not None
