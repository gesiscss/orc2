"""
Test Binder installation capability to launch repository
"""

import json

import logging

import pytest  # pylint: disable=unused-import
import requests

TIMEOUT = 30

LOGGER = logging.getLogger(__name__)


def test_launch_binder(binder_url):
    """
    We can launch an image that most likely already has been built.
    """
    repo = "binder-examples/requirements"
    ref = "50533eb470ee6c24e872043d30b2fee463d6943f"
    build_url = f"{binder_url}/build/gh/{repo}/{ref}"
    response = requests.get(build_url, stream=True, timeout=TIMEOUT)
    response.raise_for_status()
    for line in response.iter_lines():
        line = line.decode("utf8")
        if line.startswith("data:"):
            data = json.loads(line.split(":", 1)[1])
            if data.get("phase") == "ready":
                notebook_url = data["url"]
                token = data["token"]
                break
    else:
        # This means we never got a 'Ready'!
        assert False

    headers = {"Authorization": f"token {token}"}
    response = requests.get(notebook_url + "/api", headers=headers, timeout=TIMEOUT)
    assert response.status_code == 200
    assert "version" in response.json()

    response = requests.post(
        notebook_url + "/api/shutdown", headers=headers, timeout=TIMEOUT
    )
    assert response.status_code == 200
