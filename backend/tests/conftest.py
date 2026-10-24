import re
from collections import defaultdict
from collections.abc import AsyncIterator

import httpx
import pytest

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def settings() -> Settings:
    return Settings(app_env="test", source_mode="fixtures", rate_limit_per_minute=10_000)


@pytest.fixture
async def client(settings: Settings) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=create_app(settings), raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


# --- Requirement traceability: `pytest --traceability` --------------------------------------
# Tests declare the SRS requirements they cover with @pytest.mark.req("FR-011", ...).

_requirements_by_test: dict[str, list[str]] = {}
_outcomes: dict[str, str] = {}


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--traceability",
        action="store_true",
        help="print which tests cover each SRS requirement, and whether they passed",
    )


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        ids = [req for marker in item.iter_markers("req") for req in marker.args]
        if ids:
            _requirements_by_test[item.nodeid] = ids


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    if report.when == "call" or report.failed:
        _outcomes[report.nodeid] = report.outcome


def pytest_terminal_summary(
    terminalreporter: pytest.TerminalReporter, config: pytest.Config
) -> None:
    if not config.getoption("traceability"):
        return
    tests_by_requirement: dict[str, list[str]] = defaultdict(list)
    for test, ids in _requirements_by_test.items():
        for req in ids:
            tests_by_requirement[req].append(test)

    terminalreporter.section("SRS requirement coverage")
    for req in sorted(tests_by_requirement, key=_requirement_order):
        tests = tests_by_requirement[req]
        passed = sum(1 for test in tests if _outcomes.get(test) == "passed")
        status = "ok" if passed == len(tests) else "FAILING"
        terminalreporter.write_line(f"{req:<8} {passed:>3}/{len(tests):<3} tests passed  {status}")


def _requirement_order(req: str) -> tuple[str, int]:
    match = re.fullmatch(r"([A-Z]+)-(\d+)", req)
    return (match[1], int(match[2])) if match else (req, 0)
