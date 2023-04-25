"""
Sharing scope for test

Read https://docs.pytest.org/en/6.2.x/fixture.html
for more information.
"""

import pytest


def pytest_addoption(parser):
    """Add extra options to command line parser."""
    parser.addoption(
        "--binder-url",
        help="Fully qualified URL to the Binder installation",
        required=True,
    )

    parser.addoption(
        "--hub-url",
        help="Fully qualified URL to the JupyterHub installation",
        required=True,
    )


@pytest.fixture
def binder_url(request):
    """Get Binder URL from command line arguments."""
    return request.config.getoption("--binder-url").rstrip("/")


@pytest.fixture
def hub_url(request):
    """Get Jupyter Hub URL from command line arguments."""
    return request.config.getoption("--hub-url").rstrip("/")
