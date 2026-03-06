import os

from keras.src.test import trace_plugin


def pytest_runtest_setup(item):
    if os.environ.get("TRACE_ON") == "1":
        trace_plugin.enable()


def pytest_runtest_teardown(item, nextitem):
    trace_plugin.disable()
