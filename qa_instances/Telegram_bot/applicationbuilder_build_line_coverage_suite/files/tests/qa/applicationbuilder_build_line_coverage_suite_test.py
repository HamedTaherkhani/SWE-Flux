from __future__ import annotations

from asyncio import Queue

import pytest

from telegram.ext import (
    Application,
    ApplicationBuilder,
    ContextTypes,
    Defaults,
    DictPersistence,
)


class QAApplication(Application):
    def __init__(self, qa_flag: str = "default", **kwargs):
        super().__init__(**kwargs)
        self.qa_flag = qa_flag


class QAJobQueue:
    def __init__(self) -> None:
        self.bound_application: Application | None = None

    def set_application(self, application: Application) -> None:
        self.bound_application = application


def _base_builder() -> ApplicationBuilder:
    return ApplicationBuilder().token("123:ABC")


@pytest.mark.parametrize(
    "case_id",
    [
        "default",
        "updater_none",
        "custom_update_queue",
        "custom_application_class",
        "custom_application_class_kwargs",
        "context_types",
        "defaults_html",
        "local_mode_true",
        "arbitrary_callback_data_true",
        "connection_pool_size",
        "get_updates_connection_pool_size",
        "timeouts_main",
        "timeouts_get_updates",
        "proxies",
        "http_versions",
        "dict_persistence",
        "job_queue_callback",
    ],
)
def test_applicationbuilder_build_line_coverage_suite(case_id: str) -> None:
    builder = _base_builder()
    job_queue: QAJobQueue | None = None

    if case_id == "default":
        builder = builder.job_queue(None)
    elif case_id == "updater_none":
        builder = builder.job_queue(None).updater(None)
    elif case_id == "custom_update_queue":
        builder = builder.job_queue(None).update_queue(Queue())
    elif case_id == "custom_application_class":
        builder = builder.job_queue(None).application_class(QAApplication)
    elif case_id == "custom_application_class_kwargs":
        builder = builder.job_queue(None).application_class(
            QAApplication,
            kwargs={"qa_flag": "configured"},
        )
    elif case_id == "context_types":
        builder = builder.job_queue(None).context_types(ContextTypes())
    elif case_id == "defaults_html":
        builder = builder.job_queue(None).defaults(Defaults(parse_mode="HTML"))
    elif case_id == "local_mode_true":
        builder = builder.job_queue(None).local_mode(True)
    elif case_id == "arbitrary_callback_data_true":
        builder = builder.job_queue(None).arbitrary_callback_data(True)
    elif case_id == "connection_pool_size":
        builder = builder.job_queue(None).connection_pool_size(7)
    elif case_id == "get_updates_connection_pool_size":
        builder = builder.job_queue(None).get_updates_connection_pool_size(3)
    elif case_id == "timeouts_main":
        builder = (
            builder.job_queue(None)
            .connect_timeout(1.25)
            .read_timeout(2.5)
            .write_timeout(3.75)
            .pool_timeout(5.0)
            .media_write_timeout(6.25)
        )
    elif case_id == "timeouts_get_updates":
        builder = (
            builder.job_queue(None)
            .get_updates_connect_timeout(1.0)
            .get_updates_read_timeout(2.0)
            .get_updates_write_timeout(3.0)
            .get_updates_pool_timeout(4.0)
        )
    elif case_id == "proxies":
        builder = (
            builder.job_queue(None)
            .proxy("http://127.0.0.1:8080")
            .get_updates_proxy("socks5://127.0.0.1:9999")
        )
    elif case_id == "http_versions":
        builder = builder.job_queue(None).http_version("1.1").get_updates_http_version("2")
    elif case_id == "dict_persistence":
        builder = builder.job_queue(None).persistence(DictPersistence())
    elif case_id == "job_queue_callback":
        job_queue = QAJobQueue()
        builder = builder.job_queue(job_queue)
    else:
        raise AssertionError(f"unexpected case: {case_id}")

    application = builder.build()

    assert isinstance(application, Application)
    if case_id == "custom_application_class":
        assert isinstance(application, QAApplication)
        assert application.qa_flag == "default"
    if case_id == "custom_application_class_kwargs":
        assert isinstance(application, QAApplication)
        assert application.qa_flag == "configured"
    if case_id == "job_queue_callback":
        assert job_queue is not None
        assert job_queue.bound_application is application


def test_applicationbuilder_build_line_coverage_suite_missing_token_runtime_error() -> None:
    with pytest.raises(RuntimeError, match="No bot token was set"):
        ApplicationBuilder().job_queue(None).build()
