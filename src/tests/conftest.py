import asyncio
from loguru import logger
import pytest
from _pytest.logging import LogCaptureFixture
import pytest_asyncio

from src.config.services import setup_services
from src.main import app


# integrates loguru with caplog
@pytest.fixture
def caplog(caplog: LogCaptureFixture):
    handler_id = logger.add(
        caplog.handler,
        format="{message}",
        level=0,
        filter=lambda record: record["level"].no >= caplog.handler.level,
        enqueue=False,  # Set to 'True' if your test is spawning child processes.
    )
    yield caplog
    logger.remove(handler_id)


# propagates logger statements to pytest terminal output
@pytest.fixture
def reportlog(pytestconfig):
    logging_plugin = pytestconfig.pluginmanager.getplugin("logging-plugin")
    handler_id = logger.add(logging_plugin.report_handler, format="{message}")
    yield
    logger.remove(handler_id)


@pytest_asyncio.fixture(scope="session", autouse=True)
def event_loop():
    """Create an instance of the default event loop for each test case."""

    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def initialize_app_services():
    """Initializes app services to enable their access across the test suite."""

    async with setup_services(app):
        yield
