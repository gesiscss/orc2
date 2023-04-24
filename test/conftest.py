"""
Sharing scope for test

Read https://docs.pytest.org/en/6.2.x/fixture.html#scope-sharing-fixtures-across-classes-modules-packages-or-session for more information.
"""

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--binder-url", help="Fully qualified URL to the binder installation"
    )

    parser.addoption("--hub-url", help="Fully qualified URL to the hub installation")


@pytest.fixture
def binder_url(request):
    return request.config.getoption("--binder-url").rstrip("/")


@pytest.fixture
def hub_url(request):
    return request.config.getoption("--hub-url").rstrip("/")
