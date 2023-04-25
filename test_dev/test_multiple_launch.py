"""
Test Binder installation capability to launch multiple repositories
"""

import json

import logging

import pytest  # pylint: disable=unused-import
import requests

TIMEOUT = 30

LOGGER = logging.getLogger(__name__)


def launch_binder(binder_url, repo):
    """
    We can launch an image that most likely already has been built.
    """
    build_url = f"{binder_url}/build/gh/{repo['slang']}/{repo['branch']}"
    response = requests.get(build_url, stream=True, timeout=TIMEOUT)
    response.raise_for_status()
    for line in response.iter_lines():
        line = line.decode("utf8")
        print(line)
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

    return notebook_url, token

def shutdown_binder(binder_url, notebook_url, token):
    """
    Shutdown image.
    """
    headers = {"Authorization": f"token {token}"}
    response = requests.post(notebook_url + "/api/shutdown", headers=headers, timeout=TIMEOUT)
    assert response.status_code == 200

def test_multiple_launch_binder(binder_url):
    """
    We can launch many image that most likely already has been built.
    """
    repositories_to_build = [
        {
            "slang": 'explosion/spacy-io-binder',
            "branch": 'spacy.io'
        },
        {
            "slang": 'bokeh/bokeh-notebooks',
            "branch": 'main'
        },
        {
            "slang": 'scikit-learn/scikit-learn',
            "branch": 'main'
        },
        {
            "slang": 'ChenShizhe/StatDataScience',
            "branch": 'master'
        },
        {
            "slang": 'jupyter-xeus/xeus-cling',
            "branch": 'main'
        },
        {
            "slang": 'hughshanahan/CS2900-Lab-1',
            "branch": 'master'
        },
    ]

    built_notebook_url = []
    built_notebook_token = []

    for repository in repositories_to_build:
        notebook_url, notebook_token = launch_binder(binder_url, repository)
        built_notebook_url.append(notebook_url)
        built_notebook_token.append(notebook_token)
    
    for i in range(len(repositories_to_build)):
        shutdown_binder(binder_url, built_notebook_url[i], built_notebook_token[i])
