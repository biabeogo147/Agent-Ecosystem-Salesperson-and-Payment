"""Pytest plugin to execute asyncio marked tests without external dependencies."""

from __future__ import annotations

import asyncio
import inspect

import pytest


@pytest.hookimpl
def pytest_configure(config: pytest.Config) -> None:  # pragma: no cover - pytest hook
    config.addinivalue_line(
        "markers",
        "asyncio: mark test to run inside an event loop",
    )


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem: pytest.Function) -> bool:  # pragma: no cover - pytest hook
    if "asyncio" not in pyfuncitem.keywords:
        return False

    test_function = pyfuncitem.obj
    if not inspect.iscoroutinefunction(test_function):
        return False

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(test_function(**pyfuncitem.funcargs))
    finally:
        loop.close()
    return True
