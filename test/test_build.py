"""
Test Binder installation capability to build repository
"""

import json
import os
import subprocess
import sys
import tempfile
import datetime
import time
from contextlib import contextmanager

import pytest  # pylint: disable=unused-import
import requests


TIMEOUT = 30


@contextmanager
def push_dummy_gh_branch(repo, branch):
    """
    Makes a dummy commit on a given github repo as a given branch

    Requires that the branch not exist. keyfile should be an absolute path.

    Should be used as a contextmanager, it will delete the branch & the
    clone directory when done.
    """

    with tempfile.TemporaryDirectory() as gitdir:
        subprocess.check_call(["git", "clone", repo, gitdir])
        subprocess.check_call(
            ["git", "config", "--global", "user.email", "bot@notebooks.gesis.org"],
            cwd=gitdir,
        )
        subprocess.check_call(
            ["git", "config", "--global", "user.name", "Test bot"], cwd=gitdir
        )
        branchfile = os.path.join(gitdir, "branchname")
        with open(branchfile, "w", encoding="utf-8") as _file:
            _file.write(branch)
        subprocess.check_call(["git", "add", branchfile], cwd=gitdir)
        subprocess.check_call(
            ["git", "commit", "-m", f"Dummy update for {branch}"], cwd=gitdir
        )
        subprocess.check_call(
            ["git", "push", "origin", f"HEAD:{branch}"],
            cwd=gitdir,
        )

        try:
            yield
        finally:
            # Delete the branch so we don't clutter!
            subprocess.check_call(
                ["git", "push", "origin", f":{branch}"],
                cwd=gitdir,
            )


def test_build_binder(binder_url):
    """
    We can launch an image that we know hasn't been built
    """
    branch = str(time.time())
    repo = "gesiscss/orc2-test-build"

    SECRET_GITHUB_TOKEN = os.getenv(  # pylint: disable=invalid-name
        "SECRET_GITHUB_TOKEN"
    )
    if SECRET_GITHUB_TOKEN is None:
        raise Exception(  # pylint: disable=broad-exception-raised
            "SECRET_GITHUB_TOKEN is empty"
        )

    with push_dummy_gh_branch(
        f"https://bot:{SECRET_GITHUB_TOKEN}@github.com:/{repo}.git",
        branch,
    ):
        build_url = binder_url + f"/build/gh/{repo}/{branch}"

        begin_of_request = datetime.datetime.now()

        response = requests.get(build_url, stream=True, timeout=TIMEOUT)
        response.raise_for_status()
        for line in response.iter_lines():
            now = datetime.datetime.now()
            request_duration = now - begin_of_request
            if request_duration.seconds > 300:  # 5min
                response.close()
                break

            line = line.decode("utf8")
            if line.startswith("data:"):
                data = json.loads(line.split(":", 1)[1])
                # include message output for debugging
                if data.get("message"):
                    sys.stdout.write(data["message"])
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
