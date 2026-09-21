"""Optional test-report output; no real Google calls in the test suite."""
import json
from pathlib import Path


def pytest_addoption(parser):
    parser.addoption("--load-report", default=None, help="Write measured fake-Google concurrency results to this JSON file.")


def pytest_sessionfinish(session, exitstatus):
    target = session.config.getoption("--load-report")
    if target:
        from tests.test_concurrency import RESULTS
        Path(target).write_text(json.dumps({"soloMocks": True, "exitstatus": exitstatus, "resultados": RESULTS},
                                         ensure_ascii=False, indent=2), encoding="utf-8")
